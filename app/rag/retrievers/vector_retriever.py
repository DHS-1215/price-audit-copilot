# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/07 21:49
IDE       :PyCharm
作者      :董宏升

5号窗口：FAISS 向量检索器

本模块负责：
1. 读取 faiss_store.py 生成的索引和 metadata；
2. 把用户 query 转成 embedding；
3. 用 FAISS 检索语义相似的规则 chunk；
4. 将结果统一转换为 RetrievalResult / RetrievalResponse；
5. 保留 retrieve_rules_faiss(query, top_k) 兼容旧工具层调用。

注意：
vector retriever 是语义召回增强层，不负责重新定义异常事实。
在 explanation 场景中，仍必须服从：
audit_result -> rule_hit -> rule_definition -> rule_chunk
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import json
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import requests

from app.rag.schemas import RetrievalMode, RetrievalResponse, RetrievalResult, build_preview_text


OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_EMBED_MODEL = "qwen3-embedding"

DEFAULT_FAISS_DIR = "data/faiss"
DEFAULT_INDEX_FILENAME = "rule_index.faiss"
DEFAULT_META_FILENAME = "rule_index_meta.json"

DEFAULT_TOP_K = 5
DEFAULT_TIMEOUT = 120


def get_project_root() -> Path:
    """
    获取项目根目录。

    当前文件路径：
    project_root / app / rag / retrievers / vector_retriever.py

    parents[3] 才是 project_root。
    """
    return Path(__file__).resolve().parents[3]


def resolve_path(relative_path: str) -> Path:
    return get_project_root() / relative_path


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def normalize_query_text(text: str | None) -> str:
    text = safe_text(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_embeddings(matrix: np.ndarray) -> np.ndarray:
    """
    L2 归一化。

    配合 FAISS IndexFlatIP 使用，归一化后内积近似 cosine similarity。
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    return matrix / norms


def load_faiss_index(index_path: Path) -> faiss.Index:
    if not index_path.exists():
        raise FileNotFoundError(f"未找到 FAISS 索引文件：{index_path}")

    return faiss.read_index(str(index_path))


def load_metadata(meta_path: Path) -> dict[str, Any]:
    if not meta_path.exists():
        raise FileNotFoundError(f"未找到 metadata 文件：{meta_path}")

    return json.loads(meta_path.read_text(encoding="utf-8"))


def embed_query(
    query: str,
    model: str = DEFAULT_EMBED_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    timeout: int = DEFAULT_TIMEOUT,
) -> np.ndarray:
    """
    把 query 转成 shape=(1, dimension) 的 float32 向量。
    """
    query = normalize_query_text(query)
    if not query:
        raise ValueError("查询为空，无法生成 embedding。")

    url = f"{base_url}/api/embed"
    payload = {
        "model": model,
        "input": [query],
    }

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if "embeddings" in data and isinstance(data["embeddings"], list):
        vector = data["embeddings"][0]
    elif "embedding" in data and isinstance(data["embedding"], list):
        vector = data["embedding"]
    else:
        raise ValueError(f"Ollama embedding 返回结构异常：{data}")

    matrix = np.array([vector], dtype="float32")
    matrix = normalize_embeddings(matrix)
    return matrix


def metadata_match_rule_code(metadata: dict[str, Any], rule_code: str | None) -> bool:
    if not rule_code:
        return True

    meta_rule_code = safe_text(metadata.get("rule_code"))
    related_rule_codes = [safe_text(item) for item in safe_list(metadata.get("related_rule_codes"))]

    return meta_rule_code == rule_code or rule_code in related_rule_codes


def metadata_match_anomaly_type(metadata: dict[str, Any], anomaly_type: str | None) -> bool:
    if not anomaly_type:
        return True

    meta_anomaly_type = safe_text(metadata.get("anomaly_type"))
    related_anomaly_types = [safe_text(item) for item in safe_list(metadata.get("related_anomaly_types"))]

    return meta_anomaly_type == anomaly_type or anomaly_type in related_anomaly_types


def build_score_reasons(
    metadata: dict[str, Any],
    rule_code: str | None,
    anomaly_type: str | None,
) -> list[str]:
    reasons = ["vector_similarity_match"]

    if rule_code and metadata_match_rule_code(metadata, rule_code):
        reasons.append("rule_code_constraint_match")

    if anomaly_type and metadata_match_anomaly_type(metadata, anomaly_type):
        reasons.append("anomaly_type_constraint_match")

    if metadata.get("source_doc_path"):
        reasons.append("source_doc_path_present")

    if metadata.get("chunk_type"):
        reasons.append(f"chunk_type:{metadata.get('chunk_type')}")

    return reasons


def vector_result_from_metadata(
    metadata: dict[str, Any],
    score: float,
    rank: int,
    rule_code: str | None = None,
    anomaly_type: str | None = None,
) -> RetrievalResult:
    """
    将 FAISS metadata 转成统一 RetrievalResult。
    """
    chunk_text = safe_text(metadata.get("text") or metadata.get("body_text"))
    preview_text = build_preview_text(chunk_text)

    score_reasons = build_score_reasons(
        metadata=metadata,
        rule_code=rule_code,
        anomaly_type=anomaly_type,
    )

    return RetrievalResult(
        chunk_id=metadata.get("chunk_id"),
        rule_definition_id=metadata.get("rule_definition_id"),

        rule_code=metadata.get("rule_code"),
        rule_version=metadata.get("rule_version"),
        anomaly_type=metadata.get("anomaly_type"),

        doc_name=metadata.get("doc_name") or metadata.get("source_file"),
        doc_title=metadata.get("doc_title") or metadata.get("doc_name") or metadata.get("source_file"),
        source_doc_path=metadata.get("source_doc_path") or metadata.get("source_path"),

        section_title=metadata.get("section_title"),
        section_path=metadata.get("section_path"),

        chunk_index=metadata.get("chunk_index") or metadata.get("chunk_index_in_doc"),
        chunk_text=chunk_text,
        preview_text=preview_text,
        chunk_type=metadata.get("chunk_type"),

        metadata=metadata,

        baseline_score=None,
        vector_score=float(score),
        fusion_score=float(score),
        rerank_score=None,
        final_score=float(score),

        score_reasons=score_reasons,
        retrieval_mode=RetrievalMode.VECTOR,
    )


def search_vector_rule_chunks(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    faiss_relative_dir: str = DEFAULT_FAISS_DIR,
    rule_code: str | None = None,
    anomaly_type: str | None = None,
    include_inactive: bool = False,
    fetch_multiplier: int = 5,
) -> RetrievalResponse:
    """
    向量检索主函数。

    retrieval 场景：
        query="低价异常是怎么判断的？"

    explanation 场景可传约束：
        rule_code="LOW_PRICE_EXPLICIT", anomaly_type="low_price"

    注意：
    约束用于过滤明显不相关结果，防止 explanation 场景下向量召回漂移。
    """
    query = normalize_query_text(query)

    if not query:
        return RetrievalResponse(
            query=query,
            retrieval_mode=RetrievalMode.VECTOR,
            top_k=top_k,
            results=[],
            total=0,
            trace_notes=["query 为空，向量检索未执行。"],
        )

    faiss_dir = resolve_path(faiss_relative_dir)
    index_path = faiss_dir / DEFAULT_INDEX_FILENAME
    meta_path = faiss_dir / DEFAULT_META_FILENAME

    index = load_faiss_index(index_path)
    meta_payload = load_metadata(meta_path)

    embed_model = safe_text(meta_payload.get("embed_model")) or DEFAULT_EMBED_MODEL
    records = meta_payload.get("records", []) or []

    if not records:
        return RetrievalResponse(
            query=query,
            retrieval_mode=RetrievalMode.VECTOR,
            top_k=top_k,
            results=[],
            total=0,
            trace_notes=["FAISS metadata records 为空。"],
        )

    query_vector = embed_query(query=query, model=embed_model)

    fetch_k = min(max(top_k * fetch_multiplier, top_k), len(records))

    distances, indices = index.search(query_vector, fetch_k)

    results: list[RetrievalResult] = []

    for rank, (score, idx) in enumerate(zip(distances[0], indices[0]), start=1):
        if idx < 0:
            continue

        if idx >= len(records):
            continue

        metadata = safe_dict(records[idx])

        if not include_inactive and metadata.get("is_active") is False:
            continue

        if rule_code and not metadata_match_rule_code(metadata, rule_code):
            continue

        if anomaly_type and not metadata_match_anomaly_type(metadata, anomaly_type):
            continue

        item = vector_result_from_metadata(
            metadata=metadata,
            score=float(score),
            rank=rank,
            rule_code=rule_code,
            anomaly_type=anomaly_type,
        )

        results.append(item)

        if len(results) >= top_k:
            break

    trace_notes = [
        "vector retriever 使用 FAISS + Ollama embedding 检索。",
        f"embedding_model={embed_model}",
        f"faiss_records={len(records)}",
    ]

    if rule_code or anomaly_type:
        trace_notes.append(
            "当前向量检索包含 explanation 约束："
            f"rule_code={rule_code}, anomaly_type={anomaly_type}。"
        )

    return RetrievalResponse(
        query=query,
        retrieval_mode=RetrievalMode.VECTOR,
        top_k=top_k,
        results=results,
        total=len(results),
        trace_notes=trace_notes,
    )


def retrieve_rules_faiss(query: str, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    """
    兼容旧工具层调用的 dict 返回接口。
    """
    response = search_vector_rule_chunks(
        query=query,
        top_k=top_k,
    )

    return {
        "query": response.query,
        "retrieval_mode": response.retrieval_mode.value,
        "results": [
            {
                "rank": idx,
                "score": item.final_score,
                "chunk_id": item.chunk_id,
                "rule_code": item.rule_code,
                "rule_version": item.rule_version,
                "anomaly_type": item.anomaly_type,
                "doc_title": item.doc_title,
                "section_title": item.section_title,
                "section_path": item.section_path,
                "source_doc_path": item.source_doc_path,
                "chunk_type": item.chunk_type,
                "text": item.chunk_text,
                "body_text": item.chunk_text,
                "preview_text": item.preview_text,
                "score_reasons": item.score_reasons,
                "metadata": item.metadata,
            }
            for idx, item in enumerate(response.results, start=1)
        ],
    }


def pretty_print_results(results: list[RetrievalResult]) -> None:
    if not results:
        print("未检索到相关规则片段。")
        return

    for idx, item in enumerate(results, start=1):
        print("=" * 80)
        print(f"结果 {idx}")
        print(f"score         : {item.final_score:.4f}" if item.final_score is not None else "score         : None")
        print(f"chunk_id      : {item.chunk_id}")
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

    for demo_query in demo_queries:
        print("\n" + "#" * 100)
        print(f"查询问题：{demo_query}")

        response = search_vector_rule_chunks(
            query=demo_query,
            top_k=5,
        )

        print(f"命中数量：{response.total}")
        for note in response.trace_notes:
            print(f"trace: {note}")

        pretty_print_results(response.results)