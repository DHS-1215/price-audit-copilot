# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/07 21:49
IDE       :PyCharm
作者      :董宏升

第三周收口：FAISS 向量检索器

这个模块负责：
1. 读取 faiss_store.py 生成的索引和 metadata
2. 把用户 query 变成 embedding
3. 用 FAISS 检索最相似的 chunk
4. 返回 top-k 规则片段

当前定位：
这是第三周向量检索版 retriever。
我可以拿它和 baseline retriever 做对比，
看哪类问题向量检索更稳、哪类问题规则检索更稳。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import json
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import requests

"""1. 基础配置"""

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_EMBED_MODEL = "qwen3-embedding"

DEFAULT_FAISS_DIR = "data/faiss"
DEFAULT_INDEX_FILENAME = "rule_index.faiss"
DEFAULT_META_FILENAME = "rule_index_meta.json"

DEFAULT_TOP_K = 3
DEFAULT_TIMEOUT = 120

"""2. 路径工具"""


def get_project_root() -> Path:
    """
    获取项目根目录。
    """
    return Path(__file__).resolve().parents[2]


def resolve_path(relative_path: str) -> Path:
    """
    把项目内相对路径转绝对路径。
    """
    return get_project_root() / relative_path


"""3. 小工具"""


def safe_text(value: Any) -> str:
    """
    把任意值稳妥转成字符串。
    """
    if value is None:
        return ""
    return str(value)


def normalize_query_text(text: str) -> str:
    """
    对用户问题做基础标准化。

    我这里只做轻清洗，不做重写。
    因为第三周我主要想看向量检索自己的语义能力。
    """
    text = safe_text(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


# 对向量做 L2 归一化，和 faiss_store.py 保持一致。
def normalize_embeddings(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    return matrix / norms


"""4. 加载索引与 metadata"""


# 读取本地 FAISS 索引文件。
def load_faiss_index(index_path: Path) -> faiss.Index:
    if not index_path.exists():
        raise FileNotFoundError(f"未找到 FAISS 索引文件：{index_path}")

    return faiss.read_index(str(index_path))


# 读取 metadata 文件。
def load_metadata(meta_path: Path) -> dict[str, Any]:
    if not meta_path.exists():
        raise FileNotFoundError(f"未找到 metadata 文件：{meta_path}")

    return json.loads(meta_path.read_text(encoding="utf-8"))


"""5. 调 Ollama 生成 query embedding"""


def embed_query(
        query: str,
        model: str = DEFAULT_EMBED_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
) -> np.ndarray:
    """
    把 query 变成一个 embedding 向量。

    返回 shape = (1, dimension) 的 numpy float32 数组，
    方便直接丢给 FAISS search。
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
    response.raise_for_status()  # 请求失败主动抛出异常
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


"""6. 向量检索主函数"""


# 对规则知识库做向量检索
def search_faiss_rules(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    faiss_relative_dir: str = DEFAULT_FAISS_DIR,
) -> dict[str, Any]:
    """
    对规则知识库做向量检索。

    返回：
    - query
    - embed_model
    - results（top-k）
    """
    query = normalize_query_text(query)
    if not query:
        return {
            "query": query,
            "embed_model": DEFAULT_EMBED_MODEL,
            "results": [],
        }

    faiss_dir = resolve_path(faiss_relative_dir)
    index_path = faiss_dir / DEFAULT_INDEX_FILENAME
    meta_path = faiss_dir / DEFAULT_META_FILENAME

    index = load_faiss_index(index_path)
    meta_payload = load_metadata(meta_path)

    embed_model = safe_text(meta_payload.get("embed_model")) or DEFAULT_EMBED_MODEL
    records = meta_payload.get("records", []) or []

    query_vector = embed_query(query=query, model=embed_model)

    # distances / indices 的 shape 都是 (1, top_k)
    distances, indices = index.search(query_vector, top_k)

    results: list[dict[str, Any]] = []

    for rank, (score, idx) in enumerate(zip(distances[0], indices[0]), start=1):
        # FAISS 没找到时，idx 可能是 -1
        if idx < 0:
            continue

        if idx >= len(records):
            continue

        record = records[idx]

        results.append(
            {
                "rank": rank,
                "score": float(score),
                "chunk_id": record.get("chunk_id"),
                "doc_id": record.get("doc_id"),
                "doc_title": record.get("doc_title"),
                "section_title": record.get("section_title"),
                "source_file": record.get("source_file"),
                "source_path": record.get("source_path"),
                "text": record.get("text"),
                "body_text": record.get("body_text"),
            }
        )

    return {
        "query": query,
        "embed_model": embed_model,
        "results": results,
    }


"""7. 调试打印"""


def pretty_print_results(results: list[dict[str, Any]]) -> None:
    """
    更易读地打印检索结果。
    """
    if not results:
        print("未检索到相关规则片段。")
        return

    for item in results:
        print("=" * 80)
        print(f"结果 {item['rank']}")
        print(f"score         : {item['score']:.4f}")
        print(f"doc_title     : {item['doc_title']}")
        print(f"section_title : {item['section_title']}")
        print(f"source_file   : {item['source_file']}")
        print("text :")
        print(item["text"])
        print()


# -----------------------------------
# 8. 本地调试入口
# -----------------------------------

if __name__ == "__main__":
    demo_queries = [
        "为什么这个商品会被判成疑似异常低价？",
        "跨平台价差异常是怎么判的？",
        "如果标题不完整，规则上该怎么处理？",
        "人工复核时应该先看什么？",
    ]

    for query in demo_queries:
        print("\n" + "#" * 100)
        print(f"查询问题：{query}")

        payload = search_faiss_rules(query=query, top_k=3)

        print(f"Embedding 模型：{payload['embed_model']}")
        print(f"命中数量：{len(payload['results'])}")
        pretty_print_results(payload["results"])
