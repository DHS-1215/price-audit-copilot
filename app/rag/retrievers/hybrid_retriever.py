# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/24 21:46
IDE       :PyCharm
作者      :董宏升

5号窗口：轻量混合检索器

本模块负责把 baseline 检索和 vector 检索合并为 hybrid 检索。

当前定位：
1. baseline 负责高精度、可解释、metadata 强约束；
2. vector 负责自然语言语义召回；
3. hybrid 负责合并两路结果、去重、融合分数、输出统一 RetrievalResponse；
4. rerank 当前只预留，不在本文件中做复杂模型重排。

注意：
hybrid retriever 仍然只是规则依据召回层。
在 explanation 场景中，它不能绕开：
audit_result -> rule_hit -> rule_definition -> rule_chunk
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.rag.schemas import RetrievalMode, RetrievalResponse, RetrievalResult
from app.rag.retrievers.baseline_retriever import retrieve_rule_chunks as baseline_retrieve_rule_chunks
from app.rag.retrievers.vector_retriever import search_vector_rule_chunks


DEFAULT_BASELINE_WEIGHT = 0.65
DEFAULT_VECTOR_WEIGHT = 0.35


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def normalize_score(score: float | None, max_score: float | None) -> float:
    """
    将不同来源的分数归一到 0-1。

    baseline 分数通常是几十；
    vector 分数通常是 0.x；
    所以 hybrid 必须先做简单归一化，不能直接相加。
    """
    if score is None:
        return 0.0

    if not max_score or max_score <= 0:
        return 0.0

    return float(score) / float(max_score)


def build_result_key(item: RetrievalResult) -> str:
    """
    构造去重 key。

    注意：
    baseline 的 chunk_id 来自数据库 int；
    vector 的 chunk_id 来自 JSONL 字符串；
    二者不一定能直接对齐。

    因此这里不用 chunk_id 做唯一依据，而是用规则文档定位信息做近似去重。
    """
    source_doc_path = safe_text(item.source_doc_path)
    section_path = safe_text(item.section_path)
    rule_code = safe_text(item.rule_code)
    chunk_type = safe_text(item.chunk_type)
    preview = safe_text(item.preview_text)[:120]

    return "|".join(
        [
            source_doc_path,
            section_path,
            rule_code,
            chunk_type,
            preview,
        ]
    )


def merge_score_reasons(*reason_lists: list[str]) -> list[str]:
    """合并 score_reasons，并去重保持顺序。"""
    merged: list[str] = []

    for reasons in reason_lists:
        for reason in reasons:
            if reason not in merged:
                merged.append(reason)

    return merged


def as_hybrid_item(item: RetrievalResult) -> RetrievalResult:
    """把 baseline/vector 单路结果标记为 HYBRID 候选。"""
    return item.model_copy(
        update={
            "retrieval_mode": RetrievalMode.HYBRID,
        }
    )


def fuse_results(
    baseline_results: list[RetrievalResult],
    vector_results: list[RetrievalResult],
    top_k: int,
    baseline_weight: float = DEFAULT_BASELINE_WEIGHT,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
) -> list[RetrievalResult]:
    """
    融合 baseline 和 vector 结果。

    最小策略：
    1. 两路结果合并；
    2. 按文档定位信息去重；
    3. baseline_score 和 vector_score 分别归一化；
    4. fusion_score = baseline_weight * baseline_norm + vector_weight * vector_norm；
    5. final_score = fusion_score；
    6. 按 final_score 排序。
    """
    merged: dict[str, RetrievalResult] = {}

    for item in baseline_results:
        key = build_result_key(item)

        hybrid_item = as_hybrid_item(item)

        merged[key] = hybrid_item.model_copy(
            update={
                "baseline_score": item.baseline_score or item.final_score,
                "vector_score": None,
                "fusion_score": None,
                "rerank_score": None,
                "final_score": None,
                "score_reasons": merge_score_reasons(
                    item.score_reasons,
                    ["hybrid_source:baseline"],
                ),
            }
        )

    for item in vector_results:
        key = build_result_key(item)

        if key in merged:
            old = merged[key]

            merged[key] = old.model_copy(
                update={
                    "vector_score": item.vector_score or item.final_score,
                    "score_reasons": merge_score_reasons(
                        old.score_reasons,
                        item.score_reasons,
                        ["hybrid_source:vector"],
                    ),
                }
            )
        else:
            hybrid_item = as_hybrid_item(item)

            merged[key] = hybrid_item.model_copy(
                update={
                    "baseline_score": None,
                    "vector_score": item.vector_score or item.final_score,
                    "fusion_score": None,
                    "rerank_score": None,
                    "final_score": None,
                    "score_reasons": merge_score_reasons(
                        item.score_reasons,
                        ["hybrid_source:vector"],
                    ),
                }
            )

    items = list(merged.values())

    max_baseline_score = max(
        [item.baseline_score or 0 for item in items],
        default=0,
    )
    max_vector_score = max(
        [item.vector_score or 0 for item in items],
        default=0,
    )

    fused_items: list[RetrievalResult] = []

    for item in items:
        baseline_norm = normalize_score(item.baseline_score, max_baseline_score)
        vector_norm = normalize_score(item.vector_score, max_vector_score)

        fusion_score = baseline_weight * baseline_norm + vector_weight * vector_norm

        reasons = merge_score_reasons(
            item.score_reasons,
            [
                f"hybrid_fusion:baseline_weight={baseline_weight}",
                f"hybrid_fusion:vector_weight={vector_weight}",
            ],
        )

        fused_items.append(
            item.model_copy(
                update={
                    "fusion_score": fusion_score,
                    "final_score": fusion_score,
                    "score_reasons": reasons,
                    "retrieval_mode": RetrievalMode.HYBRID,
                }
            )
        )

    fused_items.sort(
        key=lambda item: (
            -(item.final_score or 0),
            safe_text(item.doc_title),
            safe_text(item.section_title),
            safe_text(item.rule_code),
        )
    )

    return fused_items[:top_k]


def retrieve_hybrid_rule_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    rule_code: str | None = None,
    rule_version: str | None = None,
    anomaly_type: str | None = None,
    include_inactive: bool = False,
    baseline_weight: float = DEFAULT_BASELINE_WEIGHT,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
) -> RetrievalResponse:
    """
    hybrid 检索主入口。

    retrieval 场景：
        query="低价异常是怎么判断的？"

    explanation 场景可传：
        rule_code="LOW_PRICE_EXPLICIT"
        rule_version="v1"
        anomaly_type="low_price"
    """
    baseline_response = baseline_retrieve_rule_chunks(
        db=db,
        query=query,
        top_k=top_k * 2,
        min_score=1.0,
        rule_code=rule_code,
        rule_version=rule_version,
        anomaly_type=anomaly_type,
        include_inactive=include_inactive,
    )

    vector_response = search_vector_rule_chunks(
        query=query,
        top_k=top_k * 2,
        rule_code=rule_code,
        anomaly_type=anomaly_type,
        include_inactive=include_inactive,
    )

    results = fuse_results(
        baseline_results=baseline_response.results,
        vector_results=vector_response.results,
        top_k=top_k,
        baseline_weight=baseline_weight,
        vector_weight=vector_weight,
    )

    trace_notes = [
        "hybrid retriever 使用 baseline + vector 两路召回。",
        "baseline 负责 metadata 强约束和高精度匹配。",
        "vector 负责自然语言语义补召回。",
        "当前 hybrid 为最小可用实现，rerank 仅预留。",
        f"baseline_results={len(baseline_response.results)}",
        f"vector_results={len(vector_response.results)}",
        f"baseline_weight={baseline_weight}",
        f"vector_weight={vector_weight}",
    ]

    if rule_code or rule_version or anomaly_type:
        trace_notes.append(
            "当前 hybrid 检索包含 explanation 约束："
            f"rule_code={rule_code}, rule_version={rule_version}, anomaly_type={anomaly_type}。"
        )

    return RetrievalResponse(
        query=query,
        retrieval_mode=RetrievalMode.HYBRID,
        top_k=top_k,
        results=results,
        total=len(results),
        trace_notes=trace_notes,
    )


def retrieve_rules_hybrid(query: str, top_k: int = 5) -> dict[str, Any]:
    """
    兼容工具层的 dict 返回接口。
    """
    db = SessionLocal()

    try:
        response = retrieve_hybrid_rule_chunks(
            db=db,
            query=query,
            top_k=top_k,
        )

        return {
            "query": response.query,
            "retrieval_mode": response.retrieval_mode.value,
            "trace_notes": response.trace_notes,
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
                    "baseline_score": item.baseline_score,
                    "vector_score": item.vector_score,
                    "fusion_score": item.fusion_score,
                    "final_score": item.final_score,
                    "score_reasons": item.score_reasons,
                    "preview_text": item.preview_text,
                    "text": item.chunk_text,
                    "metadata": item.metadata,
                }
                for item in response.results
            ],
        }

    finally:
        db.close()


def pretty_print_results(results: list[RetrievalResult]) -> None:
    if not results:
        print("未检索到相关规则片段。")
        return

    for idx, item in enumerate(results, start=1):
        print("=" * 80)
        print(f"结果 {idx}")
        print(f"final_score    : {item.final_score:.4f}" if item.final_score is not None else "final_score    : None")
        print(f"baseline_score : {item.baseline_score}")
        print(f"vector_score   : {item.vector_score}")
        print(f"chunk_id       : {item.chunk_id}")
        print(f"rule_code      : {item.rule_code}")
        print(f"anomaly_type   : {item.anomaly_type}")
        print(f"doc_title      : {item.doc_title}")
        print(f"section_title  : {item.section_title}")
        print(f"chunk_type     : {item.chunk_type}")
        print("score_reasons  :")
        for reason in item.score_reasons:
            print(f"  - {reason}")
        print("preview_text   :")
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

            response = retrieve_hybrid_rule_chunks(
                db=db,
                query=demo_query,
                top_k=5,
            )

            for note in response.trace_notes:
                print(f"trace: {note}")

            pretty_print_results(response.results)

    finally:
        db.close()