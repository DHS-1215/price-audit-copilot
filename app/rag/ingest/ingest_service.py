# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/01 14:47
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""
5号窗口：规则文档 ingest 服务

本模块负责把规则文档读取、清洗、切分为 rule_chunk，并生成符合 5号窗口
RAG 检索解释层要求的 metadata。

核心职责：
1. 读取 docs/rules/ 或 data/rules/ 下的 Markdown 规则文档；
2. 按 Markdown 标题、段落切分 chunk；
3. 为每个 chunk 补齐 rule_code / rule_version / anomaly_type / section_path / chunk_type / keywords_json / metadata_json；
4. 保留 JSONL 落盘能力，兼容旧版 baseline；
5. 提供写入数据库 rule_chunk 表的能力，服务新版 RAG 检索解释链。

解释链路固定为：
audit_result -> rule_hit -> rule_definition -> rule_chunk

注意：
rule_chunk 是解释层资源，不参与异常判定。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.rule_chunk import RuleChunk
from app.models.rule_definition import RuleDefinition
from app.rag.schemas import ChunkType, RuleChunkDraft


SUPPORTED_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
SUPPORTED_SUFFIXES = {".md"}

DEFAULT_MAX_CHARS = 600
DEFAULT_OVERLAP_PARAGRAPHS = 1
DEFAULT_RULE_VERSION = "v1"


def get_project_root() -> Path:
    """
    从 app/rag/ingest/ingest_service.py 反推项目根目录。

    当前文件路径层级：
    project_root / app / rag / ingest / ingest_service.py
    所以 parents[3] 才是项目根目录。
    """
    return Path(__file__).resolve().parents[3]


def get_rules_dir() -> Path:
    """
    优先使用 docs/rules。

    如果当前项目还没有 docs/rules，则兼容旧版 data/rules。
    """
    project_root = get_project_root()

    docs_rules_dir = project_root / "docs" / "rules"
    if docs_rules_dir.exists():
        return docs_rules_dir

    return project_root / "data" / "rules"


def get_output_dir() -> Path:
    return get_project_root() / "data" / "rag"


def read_text_file(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"未找到文件：{file_path}")

    last_error: Exception | None = None

    for encoding in SUPPORTED_ENCODINGS:
        try:
            return file_path.read_text(encoding=encoding)
        except Exception as exc:
            last_error = exc

    raise ValueError(f"读取文本失败：{file_path}\n最后错误：{last_error}")


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """
    轻量解析 Markdown 头部 front matter。

    当前不引入 PyYAML，避免新增依赖。
    只做简单 key: value 和列表识别。

    示例：
    ---
    doc_id: low_price_rules
    doc_title: 低价异常规则说明
    anomaly_type: low_price
    version: v1
    is_active: true
    ---
    """
    text = text.strip()

    if not text.startswith("---"):
        return {}, text

    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, flags=re.DOTALL)
    if not match:
        return {}, text

    raw_meta = match.group(1)
    body = match.group(2).strip()

    meta: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in raw_meta.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        if line.strip().startswith("-") and current_list_key:
            value = line.strip()[1:].strip()
            meta.setdefault(current_list_key, []).append(value)
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not value:
            meta[key] = []
            current_list_key = key
            continue

        current_list_key = None

        if value.lower() == "true":
            meta[key] = True
        elif value.lower() == "false":
            meta[key] = False
        else:
            meta[key] = value

    return meta, body


def extract_doc_title(file_path: Path, text: str, front_matter: dict[str, Any] | None = None) -> str:
    front_matter = front_matter or {}

    doc_title = front_matter.get("doc_title")
    if doc_title:
        return str(doc_title).strip()

    match = re.match(r"^\s*#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()

    return file_path.stem


def list_rule_files(rules_dir: Path) -> list[Path]:
    if not rules_dir.exists():
        raise FileNotFoundError(f"规则目录不存在：{rules_dir}")

    rule_files = [
        path
        for path in rules_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]

    return sorted(rule_files)


def split_markdown_into_sections(text: str, fallback_title: str) -> list[dict[str, Any]]:
    """
    按 Markdown 标题切分章节。

    会保留：
    - section_title
    - section_level
    - section_path
    - section_text
    """
    lines = text.split("\n")
    heading_pattern = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")

    sections: list[dict[str, Any]] = []
    heading_stack: list[tuple[int, str]] = [(1, fallback_title)]

    current_title = fallback_title
    current_level = 1
    current_path = fallback_title
    buffer: list[str] = []

    def flush_buffer() -> None:
        section_text = "\n".join(buffer).strip()
        if not section_text:
            return

        sections.append(
            {
                "section_title": current_title,
                "section_level": current_level,
                "section_path": current_path,
                "section_text": section_text,
            }
        )

    for line in lines:
        heading_match = heading_pattern.match(line)

        if heading_match:
            flush_buffer()
            buffer = []

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            heading_stack = [(item_level, item_title) for item_level, item_title in heading_stack if item_level < level]
            heading_stack.append((level, title))

            current_title = title
            current_level = level
            current_path = " > ".join(item_title for _, item_title in heading_stack)
            continue

        buffer.append(line)

    flush_buffer()

    if not sections and text.strip():
        sections.append(
            {
                "section_title": fallback_title,
                "section_level": 1,
                "section_path": fallback_title,
                "section_text": text.strip(),
            }
        )

    return sections


def split_long_text(text: str, max_chars: int) -> list[str]:
    text = text.strip()

    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    sentence_parts = re.split(r"(?<=[。！？；.!?])", text)
    sentence_parts = [part.strip() for part in sentence_parts if part.strip()]

    if len(sentence_parts) > 1:
        pieces: list[str] = []
        current = ""

        for sentence in sentence_parts:
            if not current:
                current = sentence
            elif len(current) + len(sentence) <= max_chars:
                current = f"{current}{sentence}"
            else:
                pieces.append(current.strip())
                current = sentence

        if current.strip():
            pieces.append(current.strip())

        return pieces

    pieces = []
    start = 0

    while start < len(text):
        end = start + max_chars
        pieces.append(text[start:end].strip())
        start = end

    return [piece for piece in pieces if piece]


def split_section_into_units(section_text: str, max_chars: int) -> list[str]:
    raw_paragraphs = re.split(r"\n\s*\n", section_text)
    raw_paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    units: list[str] = []

    for paragraph in raw_paragraphs:
        if len(paragraph) <= max_chars:
            units.append(paragraph)
        else:
            units.extend(split_long_text(paragraph, max_chars))

    return units


def infer_doc_base_metadata(
    file_path: Path,
    doc_title: str,
    front_matter: dict[str, Any],
) -> dict[str, Any]:
    """
    根据文档路径、标题、front matter 推断文档级 metadata。
    """
    stem = file_path.stem.lower()
    title = doc_title.lower()

    rule_codes = front_matter.get("rule_codes")
    if isinstance(rule_codes, str):
        rule_codes = [rule_codes]

    anomaly_type = front_matter.get("anomaly_type")
    version = front_matter.get("version") or DEFAULT_RULE_VERSION

    if not anomaly_type:
        if "low_price" in stem or "低价" in doc_title:
            anomaly_type = "low_price"
        elif "cross_platform" in stem or "gap" in stem or "价差" in doc_title:
            anomaly_type = "cross_platform_gap"
        elif "spec" in stem or "规格" in doc_title:
            anomaly_type = "spec_risk"
        elif "review" in stem or "复核" in doc_title:
            anomaly_type = None
        elif "faq" in stem:
            anomaly_type = None

    if not rule_codes:
        if anomaly_type == "low_price":
            rule_codes = ["LOW_PRICE_EXPLICIT", "LOW_PRICE_STAT"]
        elif anomaly_type == "cross_platform_gap":
            rule_codes = ["CROSS_PLATFORM_GAP"]
        elif anomaly_type == "spec_risk":
            rule_codes = ["SPEC_RISK"]
        else:
            rule_codes = []

    return {
        "doc_id": front_matter.get("doc_id") or file_path.stem,
        "doc_title": doc_title,
        "rule_codes": rule_codes,
        "anomaly_type": anomaly_type,
        "version": version,
        "is_active": bool(front_matter.get("is_active", True)),
    }


def infer_primary_rule_code(
    anomaly_type: str | None,
    related_rule_codes: list[str],
    section_title: str,
    chunk_text: str,
) -> str | None:
    """
    根据章节和正文推断当前 chunk 的主规则编码。

    low_price 文档可能同时服务 LOW_PRICE_EXPLICIT 和 LOW_PRICE_STAT，
    所以需要尽量按章节内容区分。
    """
    text = f"{section_title}\n{chunk_text}"

    if anomaly_type == "low_price":
        if any(word in text for word in ["统计", "组均价", "均价", "价格比例", "price_ratio"]):
            return "LOW_PRICE_STAT"

        if any(word in text for word in ["显式", "阈值", "最低维价", "500ml", "250ml", "498", "298", "1048"]):
            return "LOW_PRICE_EXPLICIT"

        return None

    if anomaly_type == "cross_platform_gap":
        return "CROSS_PLATFORM_GAP"

    if anomaly_type == "spec_risk":
        return "SPEC_RISK"

    if len(related_rule_codes) == 1:
        return related_rule_codes[0]

    return None


def infer_chunk_type(section_title: str, chunk_text: str, doc_base: dict[str, Any]) -> str:
    text = f"{section_title}\n{chunk_text}"

    doc_id = str(doc_base.get("doc_id") or "").lower()

    if "faq" in doc_id or "常见问题" in section_title:
        return ChunkType.FAQ.value

    if "review" in doc_id or "复核" in section_title or "人工复核" in text:
        return ChunkType.MANUAL_REVIEW.value

    if any(word in text for word in ["阈值", "最低价", "最低维价", "比例", "门槛"]):
        return ChunkType.THRESHOLD.value

    if any(word in section_title for word in ["定义", "定位", "是什么"]):
        return ChunkType.DEFINITION.value

    if any(word in section_title for word in ["示例", "例子", "样例"]):
        return ChunkType.EXAMPLE.value

    if any(word in section_title for word in ["注意", "说明"]):
        return ChunkType.NOTE.value

    return ChunkType.RULE_TEXT.value


def infer_keywords(
    rule_code: str | None,
    anomaly_type: str | None,
    section_title: str,
    chunk_text: str,
    related_rule_codes: list[str],
) -> list[str]:
    keywords: list[str] = []

    if rule_code:
        keywords.append(rule_code)

    keywords.extend(related_rule_codes)

    if anomaly_type:
        keywords.append(anomaly_type)

    keyword_candidates = [
        "低价",
        "显式低价",
        "统计低价",
        "阈值",
        "组均价",
        "跨平台",
        "价差",
        "最低价",
        "最高价",
        "规格",
        "标题规格",
        "规格列",
        "规范化规格",
        "规格识别风险",
        "人工复核",
        "误报",
        "确认异常",
        "备注",
    ]

    text = f"{section_title}\n{chunk_text}"

    for word in keyword_candidates:
        if word in text:
            keywords.append(word)

    return list(dict.fromkeys(keywords))


def build_rule_chunk_drafts_for_document(
    file_path: Path,
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
) -> list[RuleChunkDraft]:
    """
    给单份规则文档生成 RuleChunkDraft 列表。
    """
    front_matter, body_text = extract_front_matter(text)
    body_text = normalize_text(body_text)

    doc_title = extract_doc_title(file_path=file_path, text=body_text, front_matter=front_matter)
    doc_base = infer_doc_base_metadata(
        file_path=file_path,
        doc_title=doc_title,
        front_matter=front_matter,
    )

    related_rule_codes = list(doc_base.get("rule_codes") or [])
    anomaly_type = doc_base.get("anomaly_type")
    rule_version = str(doc_base.get("version") or DEFAULT_RULE_VERSION)
    is_active = bool(doc_base.get("is_active", True))

    sections = split_markdown_into_sections(text=body_text, fallback_title=doc_title)

    drafts: list[RuleChunkDraft] = []
    doc_chunk_index = 0

    for section in sections:
        section_title = str(section["section_title"]).strip()
        section_path = str(section["section_path"]).strip()
        section_text = str(section["section_text"]).strip()

        units = split_section_into_units(section_text=section_text, max_chars=max_chars)
        if not units:
            continue

        current_units: list[str] = []

        for unit in units:
            if not current_units:
                current_units.append(unit)
                continue

            current_body = "\n\n".join(current_units)
            candidate_body = f"{current_body}\n\n{unit}"

            if len(candidate_body) <= max_chars:
                current_units.append(unit)
                continue

            chunk_body = "\n\n".join(current_units).strip()
            if chunk_body:
                doc_chunk_index += 1
                drafts.append(
                    build_single_chunk_draft(
                        file_path=file_path,
                        doc_title=doc_title,
                        section_title=section_title,
                        section_path=section_path,
                        chunk_index=doc_chunk_index,
                        chunk_body=chunk_body,
                        anomaly_type=anomaly_type,
                        rule_version=rule_version,
                        related_rule_codes=related_rule_codes,
                        is_active=is_active,
                    )
                )

            overlap_units = current_units[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
            current_units = overlap_units + [unit]

        if current_units:
            chunk_body = "\n\n".join(current_units).strip()
            if chunk_body:
                doc_chunk_index += 1
                drafts.append(
                    build_single_chunk_draft(
                        file_path=file_path,
                        doc_title=doc_title,
                        section_title=section_title,
                        section_path=section_path,
                        chunk_index=doc_chunk_index,
                        chunk_body=chunk_body,
                        anomaly_type=anomaly_type,
                        rule_version=rule_version,
                        related_rule_codes=related_rule_codes,
                        is_active=is_active,
                    )
                )

    return drafts


def build_single_chunk_draft(
    file_path: Path,
    doc_title: str,
    section_title: str,
    section_path: str,
    chunk_index: int,
    chunk_body: str,
    anomaly_type: str | None,
    rule_version: str,
    related_rule_codes: list[str],
    is_active: bool,
) -> RuleChunkDraft:
    source_doc_path = str(file_path.relative_to(get_project_root())).replace("\\", "/")
    doc_name = file_path.name

    rule_code = infer_primary_rule_code(
        anomaly_type=anomaly_type,
        related_rule_codes=related_rule_codes,
        section_title=section_title,
        chunk_text=chunk_body,
    )

    chunk_type = infer_chunk_type(
        section_title=section_title,
        chunk_text=chunk_body,
        doc_base={"doc_id": file_path.stem},
    )

    keywords = infer_keywords(
        rule_code=rule_code,
        anomaly_type=anomaly_type,
        section_title=section_title,
        chunk_text=chunk_body,
        related_rule_codes=related_rule_codes,
    )

    metadata_json: dict[str, Any] = {
        "rule_code": rule_code,
        "rule_version": rule_version,
        "anomaly_type": anomaly_type,
        "source_doc_path": source_doc_path,
        "doc_name": doc_name,
        "doc_title": doc_title,
        "section_title": section_title,
        "section_path": section_path,
        "chunk_type": chunk_type,
        "keywords": keywords,
        "tags": keywords,
        "is_active": is_active,
        "related_rule_codes": related_rule_codes,
    }

    chunk_text = (
        f"文档：{doc_title}\n"
        f"章节：{section_path}\n"
        f"规则编码：{rule_code or '无单一主规则'}\n"
        f"异常类型：{anomaly_type or '通用'}\n\n"
        f"{chunk_body}"
    )

    return RuleChunkDraft(
        rule_definition_id=None,
        rule_code=rule_code,
        rule_version=rule_version,
        anomaly_type=anomaly_type,
        doc_name=doc_name,
        doc_title=doc_title,
        source_doc_path=source_doc_path,
        section_title=section_title,
        section_path=section_path,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        chunk_type=chunk_type,
        keywords_json=keywords,
        metadata_json=metadata_json,
        embedding_ref=None,
        is_active=is_active,
    )


def build_rule_chunk_drafts(
    rules_dir: Path,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
) -> tuple[list[RuleChunkDraft], list[dict[str, Any]]]:
    rule_files = list_rule_files(rules_dir)

    all_drafts: list[RuleChunkDraft] = []
    manifest_docs: list[dict[str, Any]] = []

    for file_path in rule_files:
        raw_text = read_text_file(file_path)
        clean_text = normalize_text(raw_text)
        front_matter, body_text = extract_front_matter(clean_text)

        doc_title = extract_doc_title(file_path=file_path, text=body_text, front_matter=front_matter)

        doc_drafts = build_rule_chunk_drafts_for_document(
            file_path=file_path,
            text=clean_text,
            max_chars=max_chars,
            overlap_paragraphs=overlap_paragraphs,
        )

        all_drafts.extend(doc_drafts)

        manifest_docs.append(
            {
                "doc_id": file_path.stem,
                "doc_title": doc_title,
                "source_file": file_path.name,
                "source_path": str(file_path.relative_to(get_project_root())).replace("\\", "/"),
                "chunk_count": len(doc_drafts),
            }
        )

    return all_drafts, manifest_docs


def get_rule_definition_map(db: Session) -> dict[tuple[str, str], RuleDefinition]:
    """
    读取启用中的 rule_definition，按 (rule_code, version) 建索引。
    """
    rows = (
        db.query(RuleDefinition)
        .filter(RuleDefinition.enabled.is_(True))
        .all()
    )

    result: dict[tuple[str, str], RuleDefinition] = {}

    for row in rows:
        result[(row.rule_code, row.version)] = row

    return result


def attach_rule_definition_ids(
    drafts: list[RuleChunkDraft],
    db: Session,
) -> list[RuleChunkDraft]:
    """
    根据 rule_code + rule_version 给 RuleChunkDraft 补 rule_definition_id。
    """
    rule_map = get_rule_definition_map(db=db)

    updated: list[RuleChunkDraft] = []

    for draft in drafts:
        if not draft.rule_code or not draft.rule_version:
            updated.append(draft)
            continue

        rule_definition = rule_map.get((draft.rule_code, draft.rule_version))

        if rule_definition is None:
            updated.append(draft)
            continue

        updated.append(
            draft.model_copy(
                update={"rule_definition_id": rule_definition.id}
            )
        )

    return updated


def write_rule_chunks_to_db(
    db: Session,
    drafts: list[RuleChunkDraft],
    replace_existing: bool = True,
) -> dict[str, Any]:
    """
    将 RuleChunkDraft 写入 rule_chunk 表。

    默认 replace_existing=True：
    当前阶段 rule_chunk 属于可重建解释资源，开发期允许重建。
    """
    if replace_existing:
        db.query(RuleChunk).delete()
        db.flush()

    drafts = attach_rule_definition_ids(drafts=drafts, db=db)

    # 由于当前表上存在 uk_rule_chunk_rule_idx(rule_definition_id, chunk_index)，
    # 这里按 rule_definition_id 重新分配 chunk_index，避免同一规则下重复。
    counters: dict[int | str, int] = {}

    rows: list[RuleChunk] = []

    for draft in drafts:
        counter_key: int | str = draft.rule_definition_id if draft.rule_definition_id is not None else f"none:{draft.doc_name}"
        counters[counter_key] = counters.get(counter_key, 0) + 1

        db_chunk_index = counters[counter_key]

        row = RuleChunk(
            rule_definition_id=draft.rule_definition_id,
            rule_code=draft.rule_code,
            rule_version=draft.rule_version,
            anomaly_type=draft.anomaly_type,
            doc_name=draft.doc_name,
            doc_title=draft.doc_title,
            source_doc_path=draft.source_doc_path,
            section_title=draft.section_title,
            section_path=draft.section_path,
            chunk_index=db_chunk_index,
            chunk_text=draft.chunk_text,
            chunk_type=draft.chunk_type,
            keywords_json=draft.keywords_json,
            metadata_json=draft.metadata_json,
            embedding_ref=draft.embedding_ref,
            is_active=draft.is_active,
        )
        rows.append(row)

    db.add_all(rows)
    db.commit()

    return {
        "inserted": len(rows),
        "replace_existing": replace_existing,
    }


def rule_chunk_draft_to_legacy_json(draft: RuleChunkDraft, index: int) -> dict[str, Any]:
    """
    输出兼容旧版 JSONL retriever 的结构，同时加入新版字段。
    """
    doc_id = Path(draft.doc_name).stem

    return {
        "chunk_id": f"{doc_id}__chunk_{index:03d}",
        "doc_id": doc_id,
        "doc_title": draft.doc_title or draft.doc_name,
        "source_file": draft.doc_name,
        "source_path": draft.source_doc_path,
        "section_title": draft.section_title,
        "section_path": draft.section_path,
        "chunk_index_in_doc": draft.chunk_index,
        "text": draft.chunk_text,
        "body_text": draft.chunk_text,
        "char_count": len(draft.chunk_text),
        "rule_code": draft.rule_code,
        "rule_version": draft.rule_version,
        "anomaly_type": draft.anomaly_type,
        "chunk_type": draft.chunk_type,
        "keywords_json": draft.keywords_json,
        "metadata_json": draft.metadata_json,
    }


def save_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            line = json.dumps(record, ensure_ascii=False)
            f.write(line + "\n")


def save_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_manifest(
    rules_dir: Path,
    output_dir: Path,
    manifest_docs: list[dict[str, Any]],
    chunk_count: int,
    max_chars: int,
    overlap_paragraphs: int,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rules_dir": str(rules_dir.relative_to(get_project_root())).replace("\\", "/"),
        "output_dir": str(output_dir.relative_to(get_project_root())).replace("\\", "/"),
        "doc_count": len(manifest_docs),
        "chunk_count": chunk_count,
        "chunk_config": {
            "max_chars": max_chars,
            "overlap_paragraphs": overlap_paragraphs,
        },
        "documents": manifest_docs,
    }


def ingest_rules(
    rules_dir: Path | None = None,
    output_dir: Path | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
    save_jsonl_file: bool = True,
) -> dict[str, Any]:
    """
    兼容旧版的文件型 ingest。

    只负责生成 data/rag/rule_chunks.jsonl 和 rule_manifest.json。
    不写数据库。
    """
    rules_dir = rules_dir or get_rules_dir()
    output_dir = output_dir or get_output_dir()

    drafts, manifest_docs = build_rule_chunk_drafts(
        rules_dir=rules_dir,
        max_chars=max_chars,
        overlap_paragraphs=overlap_paragraphs,
    )

    chunks_path = output_dir / "rule_chunks.jsonl"
    manifest_path = output_dir / "rule_manifest.json"

    if save_jsonl_file:
        legacy_records = [
            rule_chunk_draft_to_legacy_json(draft=draft, index=index)
            for index, draft in enumerate(drafts, start=1)
        ]
        save_jsonl(legacy_records, chunks_path)

    manifest = build_manifest(
        rules_dir=rules_dir,
        output_dir=output_dir,
        manifest_docs=manifest_docs,
        chunk_count=len(drafts),
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
        "chunk_count": len(drafts),
    }


def ingest_rules_to_db(
    db: Session,
    rules_dir: Path | None = None,
    output_dir: Path | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
    replace_existing: bool = True,
    save_jsonl_file: bool = True,
) -> dict[str, Any]:
    """
    新版数据库型 ingest。

    5号窗口主用入口：
    - 构建 RuleChunkDraft；
    - 补 rule_definition_id；
    - 写入 rule_chunk 表；
    - 同时可选生成 JSONL，兼容旧版 retriever。
    """
    rules_dir = rules_dir or get_rules_dir()
    output_dir = output_dir or get_output_dir()

    drafts, manifest_docs = build_rule_chunk_drafts(
        rules_dir=rules_dir,
        max_chars=max_chars,
        overlap_paragraphs=overlap_paragraphs,
    )

    db_result = write_rule_chunks_to_db(
        db=db,
        drafts=drafts,
        replace_existing=replace_existing,
    )

    chunks_path = output_dir / "rule_chunks.jsonl"
    manifest_path = output_dir / "rule_manifest.json"

    if save_jsonl_file:
        legacy_records = [
            rule_chunk_draft_to_legacy_json(draft=draft, index=index)
            for index, draft in enumerate(drafts, start=1)
        ]
        save_jsonl(legacy_records, chunks_path)

    manifest = build_manifest(
        rules_dir=rules_dir,
        output_dir=output_dir,
        manifest_docs=manifest_docs,
        chunk_count=len(drafts),
        max_chars=max_chars,
        overlap_paragraphs=overlap_paragraphs,
    )

    manifest["db"] = db_result
    save_json(manifest, manifest_path)

    return {
        "rules_dir": rules_dir,
        "output_dir": output_dir,
        "chunks_path": chunks_path,
        "manifest_path": manifest_path,
        "doc_count": len(manifest_docs),
        "chunk_count": len(drafts),
        "db_inserted": db_result["inserted"],
        "replace_existing": db_result["replace_existing"],
    }


if __name__ == "__main__":
    result = ingest_rules()

    print("规则文档 ingest 完成。")
    print(f"规则目录：{result['rules_dir']}")
    print(f"输出目录：{result['output_dir']}")
    print(f"文档数量：{result['doc_count']}")
    print(f"chunk 数量：{result['chunk_count']}")
    print(f"chunks 文件：{result['chunks_path']}")
    print(f"manifest 文件：{result['manifest_path']}")