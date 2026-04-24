# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/02 21:58
IDE       :PyCharm
作者      :董宏升

5号窗口：baseline 规则检索器

本模块负责基于数据库 rule_chunk 表做可解释的 baseline 检索。

升级点：
1. 不再只依赖 data/rag/rule_chunks.jsonl；
2. 默认读取数据库 rule_chunk；
3. 使用 rule_code / anomaly_type / doc_title / section_title / section_path / chunk_type / keywords_json / metadata_json 做 metadata 感知打分；
4. 输出 RetrievalResult；
5. 保留 retrieve_rules(query, top_k) 兼容旧工具层调用。

注意：
baseline retriever 是 5号窗口主链稳定器。
它不是向量检索的临时替代品，而是 explanation 场景下保证规则依据不漂移的核心检索器。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.rule_chunk import RuleChunk
from app.rag.schemas import RetrievalMode, RetrievalResponse, RetrievalResult, build_preview_text

STOPWORDS = {
    "为什么", "怎么", "如何", "是什么", "哪些", "哪个", "一下", "一下子",
    "这个", "那个", "这条", "那条", "一个", "一种", "一下吧", "一下呢",
    "被判成", "判成", "判为", "命中", "一下看看", "请问", "我想问",
    "如果", "时候", "情况", "处理", "说明", "规则", "依据", "是否",
}

DOMAIN_TERMS = [
    "低价", "疑似异常低价", "显式阈值", "显式低价", "统计规则", "统计低价",
    "低价规则来源", "组均价", "均价", "当前价格", "阈值",
    "跨平台", "价差", "跨平台价差", "最低价", "最高价", "价差比例",
    "规格", "规范化规格", "标题规范提示", "标题规格", "规格列", "规格识别风险",
    "平台", "平台归并", "价格清洗", "价格质量", "平台价格",
    "人工复核", "复核", "异常原因", "FAQ", "标题不完整",
    "误报", "确认异常", "备注",
]

RULE_CODE_ALIASES = {
    "LOW_PRICE_EXPLICIT": ["显式低价", "显式阈值", "最低维价", "阈值低价"],
    "LOW_PRICE_STAT": ["统计低价", "统计规则", "组均价", "均价", "价格比例"],
    "CROSS_PLATFORM_GAP": ["跨平台", "价差", "跨平台价差", "最低价", "最高价"],
    "SPEC_RISK": ["规格", "规格风险", "规格识别风险", "标题规格", "规格列", "规范化规格"],
}

ANOMALY_TYPE_ALIASES = {
    "low_price": ["低价", "疑似异常低价", "显式低价", "统计低价"],
    "cross_platform_gap": ["跨平台", "价差", "跨平台价差"],
    "spec_risk": ["规格", "规格风险", "规格识别风险", "标题规格", "规格列"],
}


def normalize_query_text(text: str | None) -> str:
    """标准化查询文本。"""
    if text is None:
        return ""

    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def safe_text(value: Any) -> str:
    """把任意值安全转为字符串。"""
    if value is None:
        return ""

    return str(value)


def normalize_json_list(value: Any) -> list[str]:
    """把 JSON / list / str 安全转成字符串列表。"""
    if value is None:
        return []

    if isinstance(value, list):
        return [safe_text(item) for item in value if safe_text(item)]

    if isinstance(value, tuple):
        return [safe_text(item) for item in value if safe_text(item)]

    if isinstance(value, str):
        return [value] if value else []

    return []


def extract_basic_tokens(query: str) -> list[str]:
    """轻量抽取中文、英文、数字 token。"""
    parts = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", query)
    return [part.strip() for part in parts if part.strip()]


def extract_query_terms(query: str) -> list[str]:
    """
    生成用于 baseline 打分的关键词列表。

    先抽领域词，再补基础 token。
    """
    query = normalize_query_text(query)
    found_terms: list[str] = []

    for term in DOMAIN_TERMS:
        if term in query:
            found_terms.append(term)

    for token in extract_basic_tokens(query):
        if token in STOPWORDS:
            continue
        if len(token) < 2:
            continue
        if len(token) > 20:
            continue
        found_terms.append(token)

    dedup_terms = list(dict.fromkeys(found_terms))
    dedup_terms.sort(key=len, reverse=True)
    return dedup_terms


def infer_rule_codes_from_query(query: str) -> list[str]:
    """从查询文本推断可能的规则编码。"""
    query = normalize_query_text(query)
    matched: list[str] = []

    for rule_code, aliases in RULE_CODE_ALIASES.items():
        if rule_code in query:
            matched.append(rule_code)
            continue

        if any(alias in query for alias in aliases):
            matched.append(rule_code)

    return list(dict.fromkeys(matched))


def infer_anomaly_types_from_query(query: str) -> list[str]:
    """从查询文本推断可能的异常类型。"""
    query = normalize_query_text(query)
    matched: list[str] = []

    for anomaly_type, aliases in ANOMALY_TYPE_ALIASES.items():
        if anomaly_type in query:
            matched.append(anomaly_type)
            continue

        if any(alias in query for alias in aliases):
            matched.append(anomaly_type)

    return list(dict.fromkeys(matched))


def get_metadata_value(metadata: dict[str, Any] | None, key: str) -> Any:
    if not metadata:
        return None

    return metadata.get(key)


def score_chunk(
        chunk: RuleChunk,
        query: str,
        query_terms: list[str],
        expected_rule_codes: list[str] | None = None,
        expected_anomaly_types: list[str] | None = None,
        rule_code: str | None = None,
        rule_version: str | None = None,
        anomaly_type: str | None = None,
) -> tuple[float, list[str]]:
    """
    给单个 RuleChunk 打 baseline 分数。

    分数设计原则：
    1. explanation 场景下，强匹配 rule_code / rule_version / anomaly_type；
    2. retrieval 场景下，结合 query_terms、标题、章节、正文、keywords；
    3. FAQ / manual_review 可被召回，但不应压过正式规则说明。
    """
    score = 0.0
    reasons: list[str] = []

    metadata = chunk.metadata_json or {}

    chunk_rule_code = chunk.rule_code or safe_text(get_metadata_value(metadata, "rule_code"))
    chunk_rule_version = chunk.rule_version or safe_text(get_metadata_value(metadata, "rule_version"))
    chunk_anomaly_type = chunk.anomaly_type or safe_text(get_metadata_value(metadata, "anomaly_type"))

    doc_title = safe_text(chunk.doc_title or chunk.doc_name)
    section_title = safe_text(chunk.section_title)
    section_path = safe_text(chunk.section_path)
    chunk_text = safe_text(chunk.chunk_text)
    chunk_type = safe_text(chunk.chunk_type or get_metadata_value(metadata, "chunk_type"))
    source_doc_path = safe_text(chunk.source_doc_path or get_metadata_value(metadata, "source_doc_path"))

    keywords = normalize_json_list(chunk.keywords_json)
    metadata_keywords = normalize_json_list(get_metadata_value(metadata, "keywords"))
    metadata_tags = normalize_json_list(get_metadata_value(metadata, "tags"))
    related_rule_codes = normalize_json_list(get_metadata_value(metadata, "related_rule_codes"))
    related_anomaly_types = normalize_json_list(get_metadata_value(metadata, "related_anomaly_types"))

    all_keywords = list(dict.fromkeys(keywords + metadata_keywords + metadata_tags))

    expected_rule_codes = expected_rule_codes or []
    expected_anomaly_types = expected_anomaly_types or []

    # ===== explanation 场景强约束 =====

    if rule_code:
        if chunk_rule_code == rule_code:
            score += 40
            reasons.append("rule_code_exact_match(+40)")
        elif rule_code in related_rule_codes:
            score += 24
            reasons.append("rule_code_related_match(+24)")
        else:
            # explanation 场景下，如果明确传入 rule_code，却不匹配，轻微降权。
            score -= 12
            reasons.append("rule_code_mismatch(-12)")

    if rule_version:
        if chunk_rule_version == rule_version:
            score += 12
            reasons.append("rule_version_match(+12)")

    if anomaly_type:
        if chunk_anomaly_type == anomaly_type:
            score += 28
            reasons.append("anomaly_type_match(+28)")
        elif anomaly_type in related_anomaly_types:
            score += 12
            reasons.append("anomaly_type_related_match(+12)")
        elif chunk_anomaly_type:
            score -= 10
            reasons.append("anomaly_type_mismatch(-10)")

    # ===== retrieval 场景推断规则 =====

    for expected_rule_code in expected_rule_codes:
        if chunk_rule_code == expected_rule_code:
            score += 24
            reasons.append(f"query_rule_code_match:{expected_rule_code}(+24)")
        elif expected_rule_code in related_rule_codes:
            score += 14
            reasons.append(f"query_related_rule_code_match:{expected_rule_code}(+14)")

    for expected_anomaly_type in expected_anomaly_types:
        if chunk_anomaly_type == expected_anomaly_type:
            score += 18
            reasons.append(f"query_anomaly_type_match:{expected_anomaly_type}(+18)")
        elif expected_anomaly_type in related_anomaly_types:
            score += 8
            reasons.append(f"query_related_anomaly_type_match:{expected_anomaly_type}(+8)")

    # ===== chunk 类型加权 =====

    if chunk_type in {"threshold", "rule_text"}:
        score += 8
        reasons.append(f"chunk_type_priority:{chunk_type}(+8)")
    elif chunk_type == "definition":
        score += 5
        reasons.append("chunk_type_priority:definition(+5)")
    elif chunk_type == "manual_review":
        if "复核" in query or "人工" in query:
            score += 12
            reasons.append("manual_review_query_match(+12)")
        else:
            score += 2
            reasons.append("manual_review_low_priority(+2)")
    elif chunk_type == "faq":
        if any(word in query for word in ["为什么", "怎么", "什么", "是否"]):
            score += 8
            reasons.append("faq_question_match(+8)")
        else:
            score += 1
            reasons.append("faq_low_priority(+1)")

    # ===== 文档 / 章节 / 正文关键词命中 =====

    for term in query_terms:
        if not term:
            continue

        if term in section_title:
            score += 10
            reasons.append(f"section_title_match:{term}(+10)")
        elif term in section_path:
            score += 8
            reasons.append(f"section_path_match:{term}(+8)")
        elif term in doc_title:
            score += 6
            reasons.append(f"doc_title_match:{term}(+6)")
        elif term in all_keywords:
            score += 7
            reasons.append(f"keyword_exact_match:{term}(+7)")
        elif any(term in keyword for keyword in all_keywords):
            score += 5
            reasons.append(f"keyword_partial_match:{term}(+5)")
        elif term in chunk_text:
            score += 3
            reasons.append(f"chunk_text_match:{term}(+3)")

    # 完整 query 命中
    if query:
        if query in section_title:
            score += 12
            reasons.append("full_query_section_title_match(+12)")
        elif query in doc_title:
            score += 8
            reasons.append("full_query_doc_title_match(+8)")
        elif query in chunk_text:
            score += 5
            reasons.append("full_query_chunk_text_match(+5)")

    # active chunk 信号
    if chunk.is_active:
        score += 2
        reasons.append("active_chunk(+2)")

    # 来源文档路径有值，说明可追溯性更好
    if source_doc_path:
        score += 1
        reasons.append("source_doc_path_present(+1)")

    return score, reasons


def to_retrieval_result(
        chunk: RuleChunk,
        score: float,
        reasons: list[str],
) -> RetrievalResult:
    """将 RuleChunk 转换为统一 RetrievalResult。"""
    metadata = chunk.metadata_json or {}
    preview_text = build_preview_text(chunk.chunk_text)

    return RetrievalResult(
        chunk_id=chunk.id,
        rule_definition_id=chunk.rule_definition_id,
        rule_code=chunk.rule_code or metadata.get("rule_code"),
        rule_version=chunk.rule_version or metadata.get("rule_version"),
        anomaly_type=chunk.anomaly_type or metadata.get("anomaly_type"),
        doc_name=chunk.doc_name,
        doc_title=chunk.doc_title or chunk.doc_name,
        source_doc_path=chunk.source_doc_path or metadata.get("source_doc_path"),
        section_title=chunk.section_title,
        section_path=chunk.section_path,
        chunk_index=chunk.chunk_index,
        chunk_text=chunk.chunk_text,
        preview_text=preview_text,
        chunk_type=chunk.chunk_type or metadata.get("chunk_type"),
        metadata=metadata,
        baseline_score=score,
        vector_score=None,
        fusion_score=score,
        rerank_score=None,
        final_score=score,
        score_reasons=reasons,
        retrieval_mode=RetrievalMode.BASELINE,
    )


def search_rule_chunks(
        db: Session,
        query: str | None = None,
        top_k: int = 5,
        min_score: float = 1.0,
        rule_code: str | None = None,
        rule_version: str | None = None,
        anomaly_type: str | None = None,
        include_inactive: bool = False,
) -> list[RetrievalResult]:
    """
    baseline 检索主函数。

    既支持 retrieval 场景：
        query="低价异常怎么判断？"

    也支持 explanation 场景：
        rule_code="LOW_PRICE_EXPLICIT", anomaly_type="low_price"
    """
    query = normalize_query_text(query)

    query_terms = extract_query_terms(query)
    expected_rule_codes = infer_rule_codes_from_query(query)
    expected_anomaly_types = infer_anomaly_types_from_query(query)

    q = db.query(RuleChunk)

    if not include_inactive:
        q = q.filter(RuleChunk.is_active.is_(True))

    # explanation 场景可以先做弱过滤，减少明显跑偏。
    # 注意：FAQ / manual_review 允许 rule_code 为空，因此这里只对强规则字段做 OR 会复杂。
    # 当前先不硬过滤，主要靠打分控制，避免误杀通用说明。
    chunks = q.all()

    scored_results: list[RetrievalResult] = []

    for chunk in chunks:
        score, reasons = score_chunk(
            chunk=chunk,
            query=query,
            query_terms=query_terms,
            expected_rule_codes=expected_rule_codes,
            expected_anomaly_types=expected_anomaly_types,
            rule_code=rule_code,
            rule_version=rule_version,
            anomaly_type=anomaly_type,
        )

        if score < min_score:
            continue

        scored_results.append(
            to_retrieval_result(
                chunk=chunk,
                score=score,
                reasons=reasons,
            )
        )

    scored_results.sort(
        key=lambda item: (
            -(item.final_score or 0),
            safe_text(item.doc_title),
            safe_text(item.section_title),
            item.chunk_id or 0,
        )
    )

    # 去重：理论上 DB id 不重复，这里稳一手。
    dedup_results: list[RetrievalResult] = []
    seen_chunk_ids: set[int | str] = set()

    for item in scored_results:
        if item.chunk_id in seen_chunk_ids:
            continue
        if item.chunk_id is not None:
            seen_chunk_ids.add(item.chunk_id)
        dedup_results.append(item)

    return dedup_results[:top_k]


def retrieve_rule_chunks(
        db: Session,
        query: str | None = None,
        top_k: int = 5,
        min_score: float = 1.0,
        rule_code: str | None = None,
        rule_version: str | None = None,
        anomaly_type: str | None = None,
        include_inactive: bool = False,
) -> RetrievalResponse:
    """返回统一 RetrievalResponse。"""
    results = search_rule_chunks(
        db=db,
        query=query,
        top_k=top_k,
        min_score=min_score,
        rule_code=rule_code,
        rule_version=rule_version,
        anomaly_type=anomaly_type,
        include_inactive=include_inactive,
    )

    trace_notes: list[str] = [
        "baseline retriever 使用数据库 rule_chunk 表检索。",
        "检索结果包含 metadata、score_reasons，可用于 evidence/citation 构建。",
    ]

    if rule_code or rule_version or anomaly_type:
        trace_notes.append(
            "当前检索包含 explanation 约束："
            f"rule_code={rule_code}, rule_version={rule_version}, anomaly_type={anomaly_type}。"
        )

    return RetrievalResponse(
        query=query,
        retrieval_mode=RetrievalMode.BASELINE,
        top_k=top_k,
        results=results,
        total=len(results),
        trace_notes=trace_notes,
    )


def retrieve_rules(query: str, top_k: int = 3) -> dict[str, Any]:
    """
    兼容旧工具层的对外接口。

    旧版 retrieval_tools.py 可能还会调用这个函数，所以这里保留 dict 返回。
    """
    db = SessionLocal()

    try:
        response = retrieve_rule_chunks(
            db=db,
            query=query,
            top_k=top_k,
            min_score=1.0,
        )

        return {
            "query": response.query,
            "query_terms": extract_query_terms(query),
            "preferred_rule_codes": infer_rule_codes_from_query(query),
            "preferred_anomaly_types": infer_anomaly_types_from_query(query),
            "results": [
                {
                    "chunk_id": item.chunk_id,
                    "rule_code": item.rule_code,
                    "rule_version": item.rule_version,
                    "anomaly_type": item.anomaly_type,
                    "doc_title": item.doc_title,
                    "section_title": item.section_title,
                    "section_path": item.section_path,
                    "source_doc_path": item.source_doc_path,
                    "chunk_type": item.chunk_type,
                    "score": item.final_score,
                    "score_reasons": item.score_reasons,
                    "text": item.chunk_text,
                    "body_text": item.chunk_text,
                    "preview_text": item.preview_text,
                    "metadata": item.metadata,
                }
                for item in response.results
            ],
        }

    finally:
        db.close()


def pretty_print_results(results: list[RetrievalResult]) -> None:
    """调试打印。"""
    if not results:
        print("未检索到相关规则片段。")
        return

    for idx, item in enumerate(results, start=1):
        print("=" * 80)
        print(f"结果 {idx}")
        print(f"chunk_id      : {item.chunk_id}")
        print(f"score         : {item.final_score}")
        print(f"rule_code     : {item.rule_code}")
        print(f"anomaly_type  : {item.anomaly_type}")
        print(f"doc_title     : {item.doc_title}")
        print(f"section_title : {item.section_title}")
        print(f"chunk_type    : {item.chunk_type}")
        print("score_reasons :")
        for reason in item.score_reasons:
            print(f"  - {reason}")
        print("preview_text :")
        print(item.preview_text)
        print()


if __name__ == "__main__":
    demo_queries = [
        "低价异常是怎么判断的？",
        "跨平台价差规则是什么？",
        "规格识别风险一般什么情况下会命中？",
        "业务人员看到异常后应该怎么复核？",
    ]

    db = SessionLocal()

    try:
        for demo_query in demo_queries:
            print("\n" + "#" * 100)
            print(f"查询问题：{demo_query}")

            response = retrieve_rule_chunks(
                db=db,
                query=demo_query,
                top_k=5,
            )

            pretty_print_results(response.results)

    finally:
        db.close()
