# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/01 14:47
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""
第三周：规则知识库文档导入（ingest）脚本

该模块先不接向量库，也不接 LangChain。
目标只有一个：

把 data/rules/ 目录下的规则文档：

1· 读进来
2· 清洗
3. 切块（chunk）
4. 落盘

为什么先这么做？
因为第三周当前最重要的是“让系统具备规则解释能力”，
而不是一上来就堆复杂技术栈。

后面 retriever.py 会基于脚本产出的chunk 文件做检索。

该模块运行完成后，默认会在 data/rag/ 下生成：
- rule_chunks.jsonl
- rule_manifest.json
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

"""1. 基础配置"""

# 兼容常见编码格式
SUPPORTED_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030"]

# 当前只 ingest markdown 规则文档。
SUPPORTED_SUFFIXES = {".md"}

# 单个 chunk 的“正文”最大字符串。
# 注意：这里控制的是正文长度，不是metadate 长度。
# 先做一个比较稳妥的值，后面如果检索不理想再微调。
DEFAULT_MAX_CHARS = 500

# chunk 之间保留多少个段落重叠（减少一刀切切断上下文情况）。
DEFAULT_OVERLAP_PARAGRAPHS = 1

"""2. 路径工具"""


# 通过当前文档位置，反推出根目录。
def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# 规则文档目录
def get_rules_dir() -> Path:
    return get_project_root() / "data" / "rules"


# ingest 产物输出目录：
def get_output_dir() -> Path:
    return get_project_root() / "data" / "rag"


"""3. 文本读取和清洗"""


def read_text_file(file_path: Path) -> str:
    """
    读取文本文件，兼容常见中文编码。

    为什么这里要做多编码兜底？
    因为中文项目最容易在“文件能看到，但程序读不进来”这一步翻车。
    第二周 CSV 已经踩过这个坑，这里继续保持稳健处理。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"未找到文件：{file_path}")

    last_error = None

    for encoding in SUPPORTED_ENCODINGS:
        try:
            return file_path.read_text(encoding=encoding)
        except Exception as exc:
            last_error = exc

    raise ValueError(f"读取文本失败：{file_path}\n最后错误：{last_error}")


# 对文本做基础清洗，减少后面切块噪声。
def normalize_text(text: str) -> str:
    """
    对文本做基础清洗，减少后面切块时的噪声。

    清洗内容：
    1. 去掉 BOM
    2. 统一换行符
    3. 去掉每行末尾多余空格
    4. 把连续 3 个以上空行压成 2 个空行

    注意：
    我们这里只做“轻清洗”，不做激进清洗。
    因为 markdown 的标题层级、空行分段，本身就是后面切块的重要依据。
    """
    # 去 BOM
    text = text.replace("\ufeff", "")

    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 去掉每行末尾空格
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 压缩多余空行：3 个及以上空行 -> 2 个空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# 提取文档标题。
def extract_doc_title(file_path: Path, text: str) -> str:
    """
    优先级：
        1.取 md 第一个一级标题（# 标题）
        2.如果没有一级标题，就退回到文件名（去掉后缀）

        这样后面每个chunk都能带上来自哪份文档的上下文。
    """
    match = re.match(r"^\s*#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()

    return file_path.stem


"""文档发现"""


def list_rule_files(rules_dir: Path) -> list[Path]:
    """
    列出 rules 目录下所有 md 文档

    这里用sorted是为了让产出顺序稳定。
    稳定顺序很重要：能方便调试，方便 git 看 diff，方便后面重跑对比结果
    """
    if not rules_dir.exists():
        raise FileNotFoundError(f'规则目录不存在：{rules_dir}')

    rule_files = [
        path for path in rules_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]

    return sorted(rule_files)


"""5. 按 md 标题切章节"""


def split_markdown_into_sections(text: str, fallback_title: str) -> list[dict[str, Any]]:
    """
    我先按照 markdown 标题切成“章节”。
    先切章节是因为规则文档天然标题结构，chunk语义会更完整，后面检索效果也会稳，因此没选用固定长度切。
    """
    lines = text.split('\n')
    sections: list[dict[str, Any]] = []

    # 默认先给一个“引言”章节，防止文档开头在第一个标题前还有正文
    current_title = fallback_title
    current_level = 1
    buffer: list[str] = []

    heading_pattern = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")

    for line in lines:
        heading_match = heading_pattern.match(line)

        # 遇到新标题：先把上一个节点收起来，再开启新章节
        if heading_match:
            section_text = "\n".join(buffer).strip()
            if section_text:
                sections.append(
                    {
                        "section_title": current_title,
                        "section_level": current_level,
                        "section_text": section_text,
                    }
                )

                current_level = len(heading_match.group(1))
                current_title = heading_match.group(2).strip()
                buffer = []
            else:
                buffer.append(line)

    # 收尾：把最后一个章节加入结果
    section_text = "\n".join(buffer).strip()
    if section_text:
        sections.append(
            {
                "section_title": current_title,
                "section_level": current_level,
                "section_text": section_text,
            }
        )

    # 如果整篇文档很短，或者无标题，至少给它个section
    if not sections:
        sections.append(
            {
                "section_title": fallback_title,
                'section_level': 1,
                'section_text': text.strip(),
            }
        )

    return sections


"""6. 长段落拆分工具"""


# 处理单个字段过长的情况。
def split_long_text(text: str, max_chars: int) -> list[str]:
    """
    正常情况下我们优先按段落切；
    但如果某个段落本身就很长，还是需要继续拆开，不然一个 chunk 会过大。

    拆分策略：
    1.先按中文 / 英文句子结束拆
    2. 如果还拆不开，就按固定长度硬切
    """
    text = text.strip()

    # 此处为防御性写法
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    # 先尝试按句子拆分
    sentence_parts = re.split(r"(?<=[。！？；.!?])", text)
    sentence_parts = [part.strip() for part in sentence_parts if part.split()]

    # 真正拆了多句，后面按句拼块逻辑才有意义。
    if len(sentence_parts) > 1:
        pieces: list[str] = []
        current = ''

        for sentence in sentence_parts:
            # 当前块还能放下这个句子就继续加
            if not current:
                current = sentence
            elif len(current) + 1 + len(sentence) <= max_chars:  # 加一为了给边界留空间
                current = f"{current}{sentence}"
            else:
                pieces.append(current.strip())
                current = sentence

        if current.strip():
            pieces.append(current.strip())

        return pieces

    # 如果连句号都拆不开，那就兜底按固定长度硬切
    pieces = []
    start = 0
    while start < len(text):
        end = start + max_chars
        pieces.append(text[start:end].strip())
        start = end

    return [piece for piece in pieces if piece]


# 把一个章节近一步拆成“可组装 chunk 的最小单元”。
def split_section_into_units(section_text: str, max_chars: int) -> list[str]:
    """
    把一个章节近一步拆成“可组装 chunk 的最小单元”。
    这里的最小单元优先是段落，如果段落过长，再继续拆成更短的句子块
    """
    # 先按空行切段落
    raw_paragraphs = re.split(r"\n\s*\n", section_text)
    raw_paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    units: list[str] = []
    for paragraph in raw_paragraphs:
        if len(paragraph) <= max_chars:
            units.append(paragraph)
        else:
            units.extend(split_long_text(paragraph, max_chars))

    return units


"""7. chunk 组装"""


def build_chunks_for_document(
        file_path: Path,
        text: str,
        max_chars: int = DEFAULT_MAX_CHARS,
        overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
) -> list[dict[str, Any]]:
    """
    给单份规则文档生成 chunk 列表。

    设计思路：
    1. 先按标题切 section
    2. section 再按段落拆成 units
    3. 多个 units 组装成 chunk
    4. chunk 保留少量段落重叠，减少上下文割裂

    每个 chunk 都会带 metadata，后面 retriever 就能利用这些信息：
    - 来自哪份文档
    - 来自哪一节
    - 第几个 chunk
    """
    doc_title = extract_doc_title(file_path, text)
    doc_id = file_path.stem

    sections = split_markdown_into_sections(text=text, fallback_title=doc_title)

    chunks: list[dict[str, Any]] = []
    doc_chunk_index = 0  # 整篇文档里面第几个 chunk

    for section_index, section in enumerate(sections, start=1):
        section_title = str(section["section_title"]).strip()
        section_level = int(section["section_level"])
        section_text = str(section["section_text"]).strip()

        # 拆成最小单元（优先段落）
        units = split_section_into_units(section_text, max_chars=max_chars)

        if not units:
            continue

        current_units: list[str] = []
        section_chunk_index = 0  # 一节里面第几个 chunk

        for unit in units:
            # 如果当前 chunk 还没内容，直接塞进去
            if not current_units:
                current_units.append(unit)
                continue

            # 用空行拼接后的长度，作为当前 chunk 正文长度
            current_body = "\n\n".join(current_units)
            candidate_body = f"{current_body}\n\n{unit}"

            # 没超过上限，就继续累加
            if len(candidate_body) <= max_chars:
                current_units.append(unit)
                continue

            # 超过上限：先把当前 chunk 落出来
            chunk_body = "\n\n".join(current_units).strip()

            section_chunk_index += 1
            doc_chunk_index += 1

            chunk_text = (
                f"文档标题：{doc_title}\n"
                f"章节标题：{section_title}\n\n"
                f"{chunk_body}"
            )

            # 加 metadata
            chunks.append(
                {
                    "chunk_id": f"{doc_id}__chunk_{doc_chunk_index:03d}",
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "source_file": file_path.name,
                    "source_path": str(file_path.relative_to(get_project_root())),
                    "section_title": section_title,
                    "section_level": section_level,
                    "section_index": section_index,
                    "chunk_index_in_section": section_chunk_index,  # 是 section 里的第几个 chunk
                    "chunk_index_in_doc": doc_chunk_index,  # 整篇文章里的第几个 chunk
                    "text": chunk_text,  # 完整的 chunk 文本
                    "body_text": chunk_body,  # 纯正文，如果我 debug 可能会用
                    "char_count": len(chunk_text),  # 完整文本长度
                    "body_char_count": len(chunk_body),  # 正文长度
                    "unit_count": len(current_units),  # 当前 chunk 有多少unit
                }
            )

            # 处理重叠：下一块开头保留上一块最后几个段落（overlap）
            overlap_units = current_units[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
            current_units = overlap_units + [unit]

        # 循环结束后，别忘了把最后一个 chunk 收尾
        if current_units:
            chunk_body = "\n\n".join(current_units).strip()

            section_chunk_index += 1
            doc_chunk_index += 1

            chunk_text = (
                f"文档标题：{doc_title}\n"
                f"章节标题：{section_title}\n\n"
                f"{chunk_body}"
            )

            chunks.append(
                {
                    "chunk_id": f"{doc_id}__chunk_{doc_chunk_index:03d}",
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "source_file": file_path.name,
                    "source_path": str(file_path.relative_to(get_project_root())),
                    "section_title": section_title,
                    "section_level": section_level,
                    "section_index": section_index,
                    "chunk_index_in_section": section_chunk_index,
                    "chunk_index_in_doc": doc_chunk_index,
                    "text": chunk_text,
                    "body_text": chunk_body,
                    "char_count": len(chunk_text),
                    "body_char_count": len(chunk_body),
                    "unit_count": len(current_units),
                }
            )

    return chunks


""" 8. 全量 ingest 主流程"""


# 对整个 rules 目录执行 ingest。
def build_rule_chunks(
        rules_dir: Path,
        max_chars: int = DEFAULT_MAX_CHARS,
        overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    对整个 rules 目录执行 ingest。

    我这个函数返回两个结果：
    1· chunks：所有切好的chunk
    2· manifest_docs：每份文档的摘要信息

    manifest_docs的作用：
    - 方便我检查到底 ingest 了哪些文档
    - 方便我统计每份文档切了多少块
    - 之后方便我 README 也能直接拿这些信息

    1· chunks 所有切好的chunk
    :param rules_dir: 规则文本地址
    :param max_chars: 最大分割为500
    :param overlap_paragraphs: chunk 之间保留1个重叠段落
    """
    rule_files = list_rule_files(rules_dir)
    all_chunks: list[dict[str, Any]] = []
    manifest_docs: list[dict[str, Any]] = []

    for file_path in rule_files:
        raw_text = read_text_file(file_path)
        clean_text = normalize_text(raw_text)

        doc_title = extract_doc_title(file_path, clean_text)
        sections = split_markdown_into_sections(clean_text, fallback_title=doc_title)
        doc_chunks = build_chunks_for_document(
            file_path=file_path,
            text=clean_text,
            max_chars=max_chars,
            overlap_paragraphs=overlap_paragraphs,
        )

        all_chunks.extend(doc_chunks)
        manifest_docs.append(
            {
                'doc_id': file_path.stem,
                'doc_title': doc_title,
                'source_file': file_path.name,
                'source_path': str(file_path.relative_to(get_project_root())),
                'section_count': len(sections),
                'chunk_count': len(doc_chunks)
            }
        )

    return all_chunks, manifest_docs


"""结果保存"""


def save_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    """
    保存为 JSONL（相当于每行一个 JSON 对象）。

    为什么这里用 JSON？
    因为 JSON 格式适合很多 chunk 一条一条存的场景（比如debug、好逐行读取、方便后面 retriever 、git diff 也比一个大 JSON 更友好）
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', encoding='utf-8') as f:
        for record in records:
            line = json.dumps(record, ensure_ascii=False)
            f.write(line + '\n')


# 保存普通 JSON 文件
def save_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


# 组装 manifest
def build_manifest(
        rules_dir: Path,
        output_dir: Path,
        manifest_doce: list[dict[str, Any]],
        chunk_count: int,
        max_chars: int,
        overlap_paragraphs: int,
) -> dict[str, Any]:
    """
    组装 manifest 信息。（方便我之后复习项目时明白这次 ingest 做了什么”的摘要记录。）
    :param rules_dir: 输入地址
    :param output_dir: 输出地址
    :param manifest_doce: 这次 ingest 做了什么”的摘要记录。
    :param chunk_count: 切好的chunk数量
    :param max_chars: 最大分割
    :param overlap_paragraphs: chunk 之间保留 1个重叠段落
    """
    return {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'rules_dir': str(rules_dir.relative_to(get_project_root())),
        'output_dir': str(output_dir.relative_to(get_project_root())),
        'doc_count': len(manifest_doce),
        'chunk_count': chunk_count,
        'chunk_config': {
            'max_chars': max_chars,
            'overlap_paragraphs': overlap_paragraphs,
        }, 'documents': manifest_doce,
    }


"""10.对外主入口"""


def ingest_rules(
        rules_dir: Path | None = None,
        output_dir: Path | None = None,
        max_chars: int = DEFAULT_MAX_CHARS,
        overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
) -> dict[str, Any]:
    """
    对外主入口函数（我后面本地调试还是 FastAPI、Streamlit 接入，都可以优先调这个函数，而不是去触碰底层逻辑）
    """
    rules_dir = rules_dir or get_rules_dir()
    output_dir = output_dir or get_output_dir()

    all_chunks, manifest_docs = build_rule_chunks(
        rules_dir=rules_dir,
        max_chars=max_chars,
        overlap_paragraphs=overlap_paragraphs,
    )

    chunks_path = output_dir / 'rule_chunks.jsonl'
    manifest_path = output_dir / 'rule_manifest.json'

    save_jsonl(all_chunks, chunks_path)

    manifest = build_manifest(
        rules_dir=rules_dir,
        output_dir=output_dir,
        manifest_doce=manifest_docs,
        chunk_count=len(all_chunks),
        max_chars=max_chars,
        overlap_paragraphs=overlap_paragraphs,
    )
    save_json(manifest, manifest_path)

    return {
        "rules_dir": rules_dir,
        "output_dir": output_dir,
        "chunks_path": chunks_path,
        "manifest_path": manifest_path,
        "doc_count": len(manifest_docs),
        "chunk_count": len(all_chunks),
    }


""" 11. 本地调试"""

if __name__ == '__main__':
    result = ingest_rules()

    print("规则文档 ingest 完成。")
    print(f"规则目录：{result['rules_dir']}")
    print(f"输出目录：{result['output_dir']}")
    print(f"文档数量：{result['doc_count']}")
    print(f"chunk 数量：{result['chunk_count']}")
    print(f"chunks 文件：{result['chunks_path']}")
    print(f"manifest 文件：{result['manifest_path']}")
