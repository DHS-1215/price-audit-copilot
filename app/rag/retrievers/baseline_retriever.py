# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/02 21:58
IDE       :PyCharm
作者      :董宏升

第三周：规则知识库检索器

该模块目标很明确：
1· 读取 ingest.py产出的 rule_chunks.jsonl
2· 接收用户问题
3· 根据问题做基本的业务路由和关键词匹配
4· 给每个 chunk 打分
5· 返回最相关的若干条规则片段

注意：
这不是最终版“高级检索器”，而是第三周的暂时可解释版本。
价值在于：能方便理解、调试、以及怎么命中的 chunk，之后这个 baseline 完成后，将会从该模块升级成“向量检索”
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import json
import re
from pathlib import Path
from typing import Any

"""1. 路径配置"""


# 获取项目根目录。
def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# ingest 产出的 chunk 文件路径
def get_chunks_path() -> Path:
    return get_project_root() / "data" / "rag" / "rule_chunks.jsonl"


"""2. 基础读取"""


def load_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """
    我考虑到 JSON 的特性是一行一个 JSON 对象，就非常适合存 chunk，而且检索读取也方便。
    :param file_path:
    :return:
    """
    if not file_path.exists():
        raise FileNotFoundError(f"未找到 chunk 文件：{file_path}")

    records: list[dict[str, Any]] = []

    with file_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    return records


"""3. 查询预处理"""
# 一些非常常见、但对检索帮助不大的词。这块我不是做自然语言处理，知识轻微去噪
STOPWORDS = {
    "为什么", "怎么", "如何", "是什么", "哪些", "哪个", "一下", "一下子",
    "这个", "那个", "这条", "那条", "一个", "一种", "一下吧", "一下呢",
    "被判成", "判成", "判为", "命中", "一下看看", "请问", "我想问",
    "如果", "时候", "情况", "处理", "说明", "规则", "依据"
}

"""
这里是“当前项目领域里的高价值关键词词表”。因为我做的是业务背景项目，不是通用搜索引擎；正因如此我需要手工列一份。
如：低价 / 跨平台 / 规格 / 复核 / 平台归并 / FAQ 等。
"""
DOMAIN_TERMS = [
    "低价", "疑似异常低价", "显式阈值", "统计规则", "低价规则来源",
    "组均价", "均价", "当前价格", "阈值",
    "跨平台", "价差", "跨平台价差", "最低价", "最高价", "价差比例",
    "规格", "规范化规格", "标题规范提示", "标题规格", "规格列", "规格识别风险",
    "平台", "平台归并", "价格清洗", "价格质量",
    "人工复核", "复核", "异常原因", "FAQ", "标题不完整"
]


# 对查询做最基本的标准化
def normalize_query_text(text: str) -> str:
    """
    1.转成字符串
    2.去除首尾空格
    3.连续空白压成一个空格
    如果深入处理会导致很多关键信息丢失或错误
    """
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


# 用轻量方法，从问题里抽一些基础 token
def extract_basic_tokens(query: str) -> list[str]:
    """
    根据经验中文不像英文那样天然按空格分词，所以采用关键词抽取
    接下来会抽取：
    - 连续中文串
    - 英文串
    - 数字串
    """
    parts = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", query)
    parts = [part.strip() for part in parts if part.strip()]

    return parts


# 生成“用于检索打分”的关键词列表
def extract_query_terms(query: str) -> list[str]:
    """
    策略中我分两层：
    1.先从领域词中找：如果问题里包含某些核心业务词，就优先加入
    2.再补一些基础 token

    最后会去重，然后长度按照降序排序。（长词通常更具体，如：“低价规则来源”比“低价”更有信息量）
    """
    query = normalize_query_text(query)
    found_terms: list[str] = []

    # 先找领域词
    for term in DOMAIN_TERMS:
        if term in query:
            found_terms.append(term)

    # 补充基础 Token
    basic_tokens = extract_basic_tokens(query)

    for token in basic_tokens:
        if token in STOPWORDS:
            continue
        if len(token) < 2:
            continue
        if len(token) > 12:
            continue
        found_terms.append(token)

    # 去重
    dedup_terms = list(dict.fromkeys(found_terms))

    # 长词优先
    dedup_terms.sort(key=len, reverse=True)

    return dedup_terms


"""4. 业务路由：优先缩小检索范围"""


def infer_preferred_doc_ids(query: str) -> list[str]:
    """
    根据我提的问题内容，推断“更应该命中哪些文档。”
    此处像轻量的 query routing
    不是为了替代全文检索，而是为了：
    - 让打分更贴合业务
    - 减少明显跑偏的结果
    - 模拟第四周统一入口里“先判断问题类型”的思路

    返回的是 doc_id 的 列表，例如：
    - ["low_price_detection_rules", "faq"]
    - ["spec_normalization_rules", "faq"]
    """
    query = normalize_query_text(query)
    preferred: list[str] = []

    # 低价类问题
    if any(word in query for word in ['低价', '显式阈值', '统计规则', '组均价', '低价规则来源']):
        preferred.extend(["low_price_detection_rules", "faq"])

    # 跨平台价差类问题
    if any(word in query for word in ["跨平台", "价差", "最低价", "最高价"]):
        preferred.extend(["cross_platform_gap_rules", "faq"])

    # 人工复核类问题
    if any(word in query for word in ["复核", "人工复核", "怎么复查", "复核建议"]):
        preferred.extend(['manual_review_process', 'faq'])

    # 平台价格口径类问题
    if any(word in query for word in ['平台', '平台归并', '价格清洗', '价格字段']):
        preferred.extend(['platform_price_rules', 'faq'])

    # 规格识别类问题
    if any(word in query for word in ["规格", "规范化规格", "标题规格", "标题不完整", "规格列", "规格识别风险"]):
        preferred.extend(["spec_normalization_rules", 'faq'])

    # 去重并保持顺序
    return list(dict.fromkeys(preferred))


"""5. 打分逻辑"""


def safe_text(value: Any) -> str:
    """
    把任意值稳妥转成字符串，避免 None 导致后面 in 判断错误。
    """
    if value is None:
        return ""

    return str(value)


def score_chunk(
        query: str,
        query_terms: list[str],
        preferred_doc_ids: list[str],
        chunk: dict[str, Any],
) -> tuple[int, list[str]]:
    """
    给单个 chunk 打分。
    返回两个东西： score和 reasons（方便调试）
    此处为当前 retriever 的核心，先用业务可解释的规则打分
    :param query:原始问题
    :param query_terms: 从问题里拆出来的关键字列表
    :param preferred_doc_ids: 优先考虑的文档 id 列表
    :param chunk: 当前被打分的那块文本数据
    """
    score = 0
    reasons: list[str] = []

    query = normalize_query_text(query)
    doc_id = safe_text(chunk.get('doc_id'))
    doc_title = safe_text(chunk.get('doc_title'))
    section_title = safe_text(chunk.get('section_title'))
    body_text = safe_text(chunk.get('body_text'))
    full_text = safe_text(chunk.get('text'))

    # 1) 如果这个 chunk 所在文档就是当前问题的优先文档，先加一笔高权重
    if doc_id in preferred_doc_ids:
        # 按 preferred_doc_ids 的顺序给权重
        rank = preferred_doc_ids.index(doc_id)

        # 第一优先文档权重更高，第二优先通常是 FAQ，低一些
        if rank == 0:
            score += 24
            reasons.append(f"命中第一优先文档:{doc_id}(+24)")
        elif rank == 1:
            score += 14
            reasons.append(f"命中第二优先文档:{doc_id}(+14)")
        else:
            score += 8
            reasons.append(f"命中其他优先文档:{doc_id}(+8)")

    # 2) 如果完整问题问题文本直接命中标题 / 正文，补一层强信号
    # 这里我还是分数不给太高，否则 FAQ 容易因为 “标题像问题” 而过度抢分
    if query:
        if section_title != doc_title and query in section_title:
            score += 12
            reasons.append('完整问题命中章节标题(+12)')
        elif query in doc_title:
            score += 8
            reasons.append('完整问题命中文档标题(+8)')
        elif query in body_text:
            score += 5
            reasons.append('完整问题命中正文(+5)')

    # 3) 如果是明显的问句风格，FAQ 文档可以给一点偏好
    if (
            doc_id == 'faq'
            and section_title != doc_title
            and any(word in query for word in ["为什么", "怎么", "什么情况下", "如果"])
    ):
        score += 6
        reasons.append('问句偏向FAQ(+6)')

    # 4) 逐个关键词打分
    for term in query_terms:
        if not term:
            continue

        term_len = len(term)

        # 长词命中章节标题，最值钱
        if term_len >= 3 and term in section_title:
            score += 10
            reasons.append(f"关键词命中章节标题:{term}(+10)")
        elif term_len >= 3 and term in doc_title:
            score += 8
            reasons.append(f"关键词命中文档标题:{term}(+8)")
        elif term in body_text:
            # 正文命中给基础分
            score += 4
            reasons.append(f"关键词命中正文:{term}(+4)")

    # 减少“只命中文档标题，但没命中具体规则段”情况。
    if section_title == doc_title:
        score -= 12
        reasons.append('标题占位chunk降权(-12)')

    return score, reasons


"""6. 主检索函数"""


def search_rule_chunks(
        query: str,
        top_k: int = 3,
        min_score: int = 1,
) -> list[dict[str, Any]]:
    """
    对规则 chunk 做检索，返回 top-k 条相关结果。
    :param query: 用户问题
    :param top_k: 返回前几条
    :param min_score: 最低分数门槛，低于这个值就不返回

    我这写的函数返回结果会保留：
    - score
    - score_reasons
    - doc_title
    - section_title
    - text
    """
    query = normalize_query_text(query)
    if not query:
        return []

    chunks = load_jsonl(get_chunks_path())
    query_terms = extract_query_terms(query)
    preferred_doc_ids = infer_preferred_doc_ids(query)

    scored_results: list[dict[str, Any]] = []
    for chunk in chunks:
        score, reasons = score_chunk(
            query=query,
            query_terms=query_terms,
            preferred_doc_ids=preferred_doc_ids,
            chunk=chunk
        )

        if score < min_score:
            continue

        result = {
            "chunk_id": chunk.get('chunk_id'),
            'doc_id': chunk.get('doc_id'),
            'doc_title': chunk.get('doc_title'),
            'section_title': chunk.get('section_title'),
            'section_level': chunk.get('section_level'),
            'source_file': chunk.get('source_file'),
            'score': score,
            'score_reasons': reasons,
            'text': chunk.get('text'),
            'body_text': chunk.get('body_text'),
        }
        scored_results.append(result)

    # 先按分数倒序，再按文档标题 / 章节标题排序，让结果更稳定
    scored_results.sort(
        key=lambda x: (
            -int(x['score']),
            safe_text(x['doc_title']),
            safe_text(x['section_title']),
        )
    )

    # 去掉完全重复的 chunk_id(正常是不太会重复，这里只是稳一手)
    dedup_results: list[dict[str, Any]] = []
    seen_chunk_ids = set()

    for item in scored_results:
        chunk_id = item.get('chunk_id')
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        dedup_results.append(item)

    return dedup_results[:top_k]


"""7. 调试打印"""


def pretty_print_results(results: list[dict[str, Any]]) -> None:
    """
    以更易读的方式打印检索结果。
    """
    if not results:
        print("未检索到相关规则片段。")
        return

    for idx, item in enumerate(results, start=1):
        print("=" * 80)
        print(f"结果 {idx}")
        print(f"score         : {item['score']}")
        print(f"doc_title     : {item['doc_title']}")
        print(f"section_title : {item['section_title']}")
        print(f"source_file   : {item['source_file']}")
        print("score_reasons :")
        for reason in item["score_reasons"]:
            print(f"  - {reason}")
        print("text :")
        print(item["text"])
        print()


"""8. 对外简单接口"""


def retrieve_rules(query: str, top_k: int = 3) -> dict[str, Any]:
    """
    提供一个更合适后面工具层调用的接口。
    返回结构比单纯 list 更完整，
    方面之后 retrieval_tools.py 直接接
    """
    query = normalize_query_text(query)
    query_terms = extract_query_terms(query)
    preferred_doc_ids = infer_preferred_doc_ids(query)
    results = search_rule_chunks(query=query, top_k=top_k)

    return {
        'query': query,
        'query_terms': query_terms,
        'preferred_doc_ids': preferred_doc_ids,
        'results': results,
    }


"""本地调试入口"""
if __name__ == '__main__':
    demo_queries = [
        "为什么这个商品会被判成疑似异常低价？",
        "跨平台价差异常是怎么判的？",
        "如果标题不完整，规格规则上怎么处理？",
        "人工复核时应该先看什么？",
    ]
    for query in demo_queries:
        print("\n" + "#" * 100)
        print(f"查询问题：{query}")
        payload = retrieve_rules(query=query, top_k=3)
        print(f"提取关键词：{payload['query_terms']}")
        print(f"优先文档：{payload['preferred_doc_ids']}")
        print("命中结果数量：", len(payload["results"]))
        pretty_print_results(payload["results"])
