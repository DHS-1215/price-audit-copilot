# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 12:29
IDE       :PyCharm
作者      :董宏升

5号窗口：RAG 检索统一服务层

本模块负责把 baseline / vector / hybrid 三种检索统一封装成一个服务入口。

目标：
1. 6号窗口以后只调用 retrieval_service，不直接关心底层 retriever；
2. 支持 retrieval_mode = baseline / vector / hybrid；
3. 统一返回 RetrievalResponse；
4. 统一接入 rerank 预留；
5. 统一保留 trace_notes；
6. 为后续 rule_explanation_service 提供稳定检索能力。

注意：
本模块只负责规则依据检索，不负责 /ask 总编排。
/ask 路由、问题分类、mixed 编排属于 6号窗口。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.rag.ranking.rerank_adapter import RerankConfig, rerank_results
from app.rag.retrievers.baseline_retriever import retrieve_rule_chunks as retrieve_baseline_rule_chunks
from app.rag.retrievers.hybrid_retriever import retrieve_hybrid_rule_chunks
from app.rag.retrievers.vector_retriever import search_vector_rule_chunks
from app.rag.schemas import RetrievalMode, RetrievalQuery, RetrievalResponse


def normalize_retrieval_mode(mode: RetrievalMode | str | None) -> RetrievalMode:
    """
    统一检索模式。

    默认使用 baseline，因为 baseline 是当前规则解释主链稳定器。
    """
    if mode is None:
        return RetrievalMode.BASELINE

    if isinstance(mode, RetrievalMode):
        return mode

    mode_text = str(mode).strip().lower()

    if mode_text == RetrievalMode.BASELINE.value:
        return RetrievalMode.BASELINE

    if mode_text == RetrievalMode.VECTOR.value:
        return RetrievalMode.VECTOR

    if mode_text == RetrievalMode.HYBRID.value:
        return RetrievalMode.HYBRID

    return RetrievalMode.BASELINE


def search_rules(
        db: Session,
        request: RetrievalQuery,
        rerank_enabled: bool = False,
) -> RetrievalResponse:
    """
    规则检索统一入口。

    支持三种模式：

    1. baseline：
       读取数据库 rule_chunk，走 metadata 感知打分。

    2. vector：
       读取 FAISS 索引，走语义召回。

    3. hybrid：
       baseline + vector 两路召回，做最小融合。

    explanation 场景可以传：
    - rule_code
    - rule_version
    - anomaly_type
    - audit_result_id
    - clean_id

    但注意：
    当前服务只负责检索，不负责读取 audit_result / rule_hit。
    读取结果层事实属于 rule_explanation_service。
    """
    mode = normalize_retrieval_mode(request.retrieval_mode)

    if mode == RetrievalMode.BASELINE:
        response = retrieve_baseline_rule_chunks(
            db=db,
            query=request.query,
            top_k=request.top_k,
            min_score=1.0,
            rule_code=request.rule_code,
            rule_version=request.rule_version,
            anomaly_type=request.anomaly_type,
            include_inactive=request.include_inactive,
        )

    elif mode == RetrievalMode.VECTOR:
        response = search_vector_rule_chunks(
            query=request.query or "",
            top_k=request.top_k,
            rule_code=request.rule_code,
            anomaly_type=request.anomaly_type,
            include_inactive=request.include_inactive,
        )

    elif mode == RetrievalMode.HYBRID:
        response = retrieve_hybrid_rule_chunks(
            db=db,
            query=request.query or "",
            top_k=request.top_k,
            rule_code=request.rule_code,
            rule_version=request.rule_version,
            anomaly_type=request.anomaly_type,
            include_inactive=request.include_inactive,
        )

    else:
        response = retrieve_baseline_rule_chunks(
            db=db,
            query=request.query,
            top_k=request.top_k,
            min_score=1.0,
            rule_code=request.rule_code,
            rule_version=request.rule_version,
            anomaly_type=request.anomaly_type,
            include_inactive=request.include_inactive,
        )

    rerank_config = RerankConfig(
        enabled=rerank_enabled,
        strategy="noop",
        top_k=request.top_k,
    )

    reranked_results = rerank_results(
        query=request.query or "",
        results=response.results,
        config=rerank_config,
    )

    trace_notes = list(response.trace_notes)

    if rerank_enabled:
        trace_notes.append("rerank_enabled=true，但当前使用 noop rerank 预留适配器，未接真实 rerank 模型。")
    else:
        trace_notes.append("rerank_enabled=false，当前未启用真实 rerank。")

    return response.model_copy(
        update={
            "retrieval_mode": mode,
            "results": reranked_results,
            "total": len(reranked_results),
            "trace_notes": trace_notes,
        }
    )


def search_rules_simple(
        query: str,
        top_k: int = 5,
        retrieval_mode: RetrievalMode | str = RetrievalMode.BASELINE,
        rule_code: str | None = None,
        rule_version: str | None = None,
        anomaly_type: str | None = None,
        include_inactive: bool = False,
        rerank_enabled: bool = False,
) -> RetrievalResponse:
    """
    简化调用入口。

    适合本地脚本、工具层、smoke test 使用。
    """
    db = SessionLocal()

    try:
        request = RetrievalQuery(
            query=query,
            top_k=top_k,
            retrieval_mode=normalize_retrieval_mode(retrieval_mode),
            rule_code=rule_code,
            rule_version=rule_version,
            anomaly_type=anomaly_type,
            include_inactive=include_inactive,
        )

        return search_rules(
            db=db,
            request=request,
            rerank_enabled=rerank_enabled,
        )

    finally:
        db.close()


def search_rules_as_dict(
        query: str,
        top_k: int = 5,
        retrieval_mode: RetrievalMode | str = RetrievalMode.BASELINE,
        rule_code: str | None = None,
        rule_version: str | None = None,
        anomaly_type: str | None = None,
        rerank_enabled: bool = False,
) -> dict[str, Any]:
    """
    兼容工具层的 dict 返回入口。

    后续如果旧 tools/retrieval_tools.py 不想立刻改 Pydantic，
    可以先调用这个函数。
    """
    response = search_rules_simple(
        query=query,
        top_k=top_k,
        retrieval_mode=retrieval_mode,
        rule_code=rule_code,
        rule_version=rule_version,
        anomaly_type=anomaly_type,
        rerank_enabled=rerank_enabled,
    )

    return {
        "query": response.query,
        "retrieval_mode": response.retrieval_mode.value,
        "top_k": response.top_k,
        "total": response.total,
        "trace_notes": response.trace_notes,
        "results": [
            {
                "chunk_id": item.chunk_id,
                "rule_definition_id": item.rule_definition_id,
                "rule_code": item.rule_code,
                "rule_version": item.rule_version,
                "anomaly_type": item.anomaly_type,
                "doc_name": item.doc_name,
                "doc_title": item.doc_title,
                "source_doc_path": item.source_doc_path,
                "section_title": item.section_title,
                "section_path": item.section_path,
                "chunk_index": item.chunk_index,
                "chunk_type": item.chunk_type,
                "preview_text": item.preview_text,
                "chunk_text": item.chunk_text,
                "baseline_score": item.baseline_score,
                "vector_score": item.vector_score,
                "fusion_score": item.fusion_score,
                "rerank_score": item.rerank_score,
                "final_score": item.final_score,
                "score_reasons": item.score_reasons,
                "retrieval_mode": item.retrieval_mode.value,
                "metadata": item.metadata,
            }
            for item in response.results
        ],
    }


def pretty_print_response(response: RetrievalResponse) -> None:
    """调试打印统一检索响应。"""
    print("=" * 100)
    print(f"query          : {response.query}")
    print(f"retrieval_mode : {response.retrieval_mode}")
    print(f"top_k          : {response.top_k}")
    print(f"total          : {response.total}")
    print("trace_notes    :")

    for note in response.trace_notes:
        print(f"  - {note}")

    for idx, item in enumerate(response.results, start=1):
        print("-" * 100)
        print(f"结果 {idx}")
        print(f"final_score    : {item.final_score}")
        print(f"baseline_score : {item.baseline_score}")
        print(f"vector_score   : {item.vector_score}")
        print(f"rerank_score   : {item.rerank_score}")
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


if __name__ == "__main__":
    demo_queries = [
        ("低价异常是怎么判断的？", RetrievalMode.BASELINE),
        ("低价异常是怎么判断的？", RetrievalMode.VECTOR),
        ("低价异常是怎么判断的？", RetrievalMode.HYBRID),
        ("跨平台价差规则是什么？", RetrievalMode.HYBRID),
        ("规格识别风险一般什么情况下会命中？", RetrievalMode.HYBRID),
        ("业务人员看到异常后应该怎么复核？", RetrievalMode.HYBRID),
    ]

    for query, mode in demo_queries:
        response = search_rules_simple(
            query=query,
            top_k=3,
            retrieval_mode=mode,
            rerank_enabled=False,
        )

        pretty_print_response(response)
