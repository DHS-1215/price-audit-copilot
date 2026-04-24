# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/07 21:27
IDE       :PyCharm
作者      :董宏升

5号窗口：FAISS 向量索引构建模块

本模块负责：
1. 读取 data/rag/rule_chunks.jsonl；
2. 调用 Ollama embedding 接口，把每个 chunk 变成向量；
3. 用 FAISS 构建向量索引；
4. 保存索引文件和 metadata；
5. metadata 保留 5号窗口 RAG 解释所需字段：
   rule_code / rule_version / anomaly_type / doc_title / section_title /
   section_path / chunk_type / keywords_json / metadata_json 等。

注意：
当前向量索引仍然基于 JSONL 构建。
JSONL 由 ingest_rules_to_db 同步生成，是 rule_chunk 表的镜像产物。
这样可以减少当前阶段改动，不直接把 FAISS 构建耦合到数据库查询。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import requests

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_EMBED_MODEL = "qwen3-embedding"

DEFAULT_CHUNKS_PATH = "data/rag/rule_chunks.jsonl"
DEFAULT_FAISS_DIR = "data/faiss"

DEFAULT_INDEX_FILENAME = "rule_index.faiss"
DEFAULT_META_FILENAME = "rule_index_meta.json"

DEFAULT_BATCH_SIZE = 8
DEFAULT_TIMEOUT = 120


def get_project_root() -> Path:
    """
    获取项目根目录。

    当前文件路径：
    project_root / app / rag / stores / faiss_store.py

    parents[3] 才是 project_root。
    """
    return Path(__file__).resolve().parents[3]


def resolve_path(relative_path: str) -> Path:
    return get_project_root() / relative_path


def load_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """
    读取 JSONL chunk 文件。

    兼容：
    1. 标准 JSONL：每行一个 JSON 对象；
    2. 整个文件是 JSON 数组。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"未找到 chunk 文件：{file_path}")

    raw_text = file_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    records: list[dict[str, Any]] = []
    jsonl_ok = True

    for idx, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"第 {idx} 行不是 JSON 对象")
            records.append(obj)
        except Exception:
            jsonl_ok = False
            break

    if jsonl_ok:
        return records

    data = json.loads(raw_text)
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data

    raise ValueError(f"无法读取 chunk 文件：{file_path}")


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


def batch_iter(items: list[Any], batch_size: int) -> list[list[Any]]:
    batches: list[list[Any]] = []

    for start in range(0, len(items), batch_size):
        end = start + batch_size
        batches.append(items[start:end])

    return batches


def embed_texts(
        texts: list[str],
        model: str = DEFAULT_EMBED_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
) -> list[list[float]]:
    """
    调 Ollama /api/embed 生成 embedding。
    """
    if not texts:
        return []

    url = f"{base_url}/api/embed"
    payload = {
        "model": model,
        "input": texts,
    }

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if "embeddings" in data and isinstance(data["embeddings"], list):
        return data["embeddings"]

    if "embedding" in data and isinstance(data["embedding"], list):
        return [data["embedding"]]

    raise ValueError(f"Ollama embedding 返回结构异常：{data}")


def normalize_embeddings(matrix: np.ndarray) -> np.ndarray:
    """
    L2 归一化。

    配合 IndexFlatIP 使用，归一化后的内积约等于 cosine similarity。
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    return matrix / norms


def build_embedding_text(chunk: dict[str, Any]) -> str:
    """
    构造真正用于 embedding 的文本。

    不只使用 chunk_text，而是拼接文档、章节、规则编码、异常类型等上下文。
    这样向量检索召回时不容易丢失规则归属。
    """
    metadata = safe_dict(chunk.get("metadata_json"))

    doc_title = safe_text(chunk.get("doc_title") or chunk.get("doc_name") or chunk.get("source_file"))
    section_title = safe_text(chunk.get("section_title"))
    section_path = safe_text(chunk.get("section_path") or metadata.get("section_path"))
    rule_code = safe_text(chunk.get("rule_code") or metadata.get("rule_code"))
    anomaly_type = safe_text(chunk.get("anomaly_type") or metadata.get("anomaly_type"))
    chunk_type = safe_text(chunk.get("chunk_type") or metadata.get("chunk_type"))

    text = safe_text(chunk.get("text") or chunk.get("chunk_text") or chunk.get("body_text"))

    return (
        f"文档：{doc_title}\n"
        f"章节：{section_path or section_title}\n"
        f"规则编码：{rule_code or '无单一主规则'}\n"
        f"异常类型：{anomaly_type or '通用'}\n"
        f"chunk类型：{chunk_type or 'unknown'}\n\n"
        f"{text}"
    ).strip()


def build_records(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    将 JSONL chunk 转换为 FAISS 可入库记录。

    这里必须保留新版 metadata 字段，保证 vector_retriever 能输出 RetrievalResult。
    """
    records: list[dict[str, Any]] = []

    for idx, chunk in enumerate(chunks, start=1):
        raw_chunk_id = chunk.get("chunk_id")
        chunk_id = safe_text(raw_chunk_id).strip() or f"chunk_{idx:06d}"

        text = build_embedding_text(chunk)
        if not text:
            continue

        metadata_json = safe_dict(chunk.get("metadata_json"))

        metadata = {
            "chunk_id": chunk_id,

            # 规则归属
            "rule_code": chunk.get("rule_code") or metadata_json.get("rule_code"),
            "rule_version": chunk.get("rule_version") or metadata_json.get("rule_version"),
            "anomaly_type": chunk.get("anomaly_type") or metadata_json.get("anomaly_type"),
            "rule_definition_id": chunk.get("rule_definition_id"),

            # 文档来源
            "doc_id": chunk.get("doc_id"),
            "doc_name": chunk.get("doc_name") or chunk.get("source_file"),
            "doc_title": chunk.get("doc_title") or metadata_json.get("doc_title"),
            "source_file": chunk.get("source_file") or chunk.get("doc_name"),
            "source_path": chunk.get("source_path") or chunk.get("source_doc_path"),
            "source_doc_path": chunk.get("source_doc_path") or metadata_json.get("source_doc_path"),

            # 章节定位
            "section_title": chunk.get("section_title") or metadata_json.get("section_title"),
            "section_path": chunk.get("section_path") or metadata_json.get("section_path"),
            "section_level": chunk.get("section_level"),
            "section_index": chunk.get("section_index"),

            # chunk 信息
            "chunk_index": chunk.get("chunk_index") or chunk.get("chunk_index_in_doc"),
            "chunk_index_in_section": chunk.get("chunk_index_in_section"),
            "chunk_index_in_doc": chunk.get("chunk_index_in_doc"),
            "chunk_type": chunk.get("chunk_type") or metadata_json.get("chunk_type"),

            # 文本
            "text": chunk.get("text") or chunk.get("chunk_text"),
            "body_text": chunk.get("body_text") or chunk.get("chunk_text") or chunk.get("text"),
            "embedding_text": text,

            # 检索辅助
            "keywords_json": chunk.get("keywords_json") or metadata_json.get("keywords"),
            "metadata_json": metadata_json,
            "is_active": chunk.get("is_active", metadata_json.get("is_active", True)),
        }

        records.append(
            {
                "id": chunk_id,
                "text": text,
                "metadata": metadata,
            }
        )

    return records


def build_faiss_index(
        chunks_path: Path,
        output_dir: Path,
        embed_model: str = DEFAULT_EMBED_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    构建 FAISS 索引主流程。
    """
    print("开始读取规则 chunk 文件...")
    chunks = load_jsonl(chunks_path)
    print(f"读取完成，原始 chunk 数量：{len(chunks)}")

    records = build_records(chunks)
    print(f"可入库 chunk 数量：{len(records)}")

    if not records:
        raise ValueError("没有可入库的 chunk 记录，请检查 rule_chunks.jsonl 内容。")

    all_embeddings: list[list[float]] = []

    record_batches = batch_iter(records, batch_size=batch_size)
    total_batches = len(record_batches)

    for batch_index, batch in enumerate(record_batches, start=1):
        print(f"\n正在处理第 {batch_index}/{total_batches} 批...")

        texts = [item["text"] for item in batch]

        print("正在调用 Ollama 生成 embedding...")
        embeddings = embed_texts(
            texts=texts,
            model=embed_model,
        )

        if len(embeddings) != len(texts):
            raise ValueError(
                f"embedding 数量和文本数量不一致：{len(embeddings)} != {len(texts)}"
            )

        all_embeddings.extend(embeddings)
        print(f"本批 embedding 完成，数量：{len(embeddings)}")

    print("\n正在构建向量矩阵...")
    embedding_matrix = np.array(all_embeddings, dtype="float32")

    if embedding_matrix.ndim != 2:
        raise ValueError(f"embedding 矩阵维度异常：{embedding_matrix.shape}")

    embedding_matrix = normalize_embeddings(embedding_matrix)

    dimension = embedding_matrix.shape[1]
    print(f"向量维度：{dimension}")

    print("正在创建 FAISS IndexFlatIP 索引...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embedding_matrix)

    print(f"索引内向量数量：{index.ntotal}")

    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = output_dir / DEFAULT_INDEX_FILENAME
    meta_path = output_dir / DEFAULT_META_FILENAME

    print("正在保存 FAISS 索引文件...")
    faiss.write_index(index, str(index_path))

    print("正在保存 metadata 文件...")
    meta_payload = {
        "embed_model": embed_model,
        "dimension": dimension,
        "count": len(records),
        "records": [item["metadata"] for item in records],
    }

    meta_path.write_text(
        json.dumps(meta_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "chunks_path": str(chunks_path),
        "output_dir": str(output_dir),
        "index_path": str(index_path),
        "meta_path": str(meta_path),
        "embed_model": embed_model,
        "input_chunk_count": len(chunks),
        "stored_chunk_count": len(records),
        "vector_count": int(index.ntotal),
        "dimension": int(dimension),
    }


def run_faiss_store_build(
        chunks_relative_path: str = DEFAULT_CHUNKS_PATH,
        faiss_relative_dir: str = DEFAULT_FAISS_DIR,
        embed_model: str = DEFAULT_EMBED_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    对外统一入口。
    """
    chunks_path = resolve_path(chunks_relative_path)
    output_dir = resolve_path(faiss_relative_dir)

    return build_faiss_index(
        chunks_path=chunks_path,
        output_dir=output_dir,
        embed_model=embed_model,
        batch_size=batch_size,
    )


if __name__ == "__main__":
    result = run_faiss_store_build()

    print("\n" + "=" * 80)
    print("FAISS 向量入库完成。")
    print(f"chunk 文件：{result['chunks_path']}")
    print(f"输出目录：{result['output_dir']}")
    print(f"索引文件：{result['index_path']}")
    print(f"metadata 文件：{result['meta_path']}")
    print(f"Embedding 模型：{result['embed_model']}")
    print(f"原始 chunk 数量：{result['input_chunk_count']}")
    print(f"可入库 chunk 数量：{result['stored_chunk_count']}")
    print(f"索引向量数量：{result['vector_count']}")
    print(f"向量维度：{result['dimension']}")
