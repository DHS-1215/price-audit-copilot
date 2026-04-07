# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/07 21:27
IDE       :PyCharm
作者      :董宏升

第三周收口：FAISS 向量入库模块

这个模块负责做 4 件事：

1. 读取 ingest.py 产出的 rule_chunks.jsonl
2. 调用 Ollama embedding 接口，把每个 chunk 变成向量
3. 用 FAISS 建一个向量索引
4. 把索引和 metadata 一起保存到本地文件

因为“向量检索”要先有向量库。
所以顺序应该是：

- 先把 chunk 向量化并入库
- 再写 faiss_retriever.py 去检索
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import requests

"""1. 基础配置"""

# Ollama 本地服务地址
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# 默认 embedding 模型
DEFAULT_EMBED_MODEL = "qwen3-embedding"

# ingest 产出的 chunk 文件
DEFAULT_CHUNKS_PATH = "data/rag/rule_chunks.jsonl"

# FAISS 输出目录
DEFAULT_FAISS_DIR = "data/faiss"

# FAISS 索引文件名
DEFAULT_INDEX_FILENAME = "rule_index.faiss"

# metadata 文件名
DEFAULT_META_FILENAME = "rule_index_meta.json"

# 每批 embedding 的条数，先设小一点，稳一点
DEFAULT_BATCH_SIZE = 8

# 请求超时时间
DEFAULT_TIMEOUT = 120

"""2. 路径工具"""


# 获取项目根目录。
def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# 把项目内相对路径转成绝对路径。
def resolve_path(relative_path: str) -> Path:
    return get_project_root() / relative_path


"""3. 读取 chunk 文件"""


def load_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """
    我这里直接兼容两种情况：
    1. 标准 JSONL：每行一个 JSON 对象
    2. 整个文件是 JSON 数组

    这样更稳，不容易因为文件格式细节翻车。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"未找到 chunk 文件：{file_path}")

    raw_text = file_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    # 先按标准 JSONL 读
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

    # 再兜底按“整个文件是 JSON 数组”读
    data = json.loads(raw_text)
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data

    raise ValueError(f"无法读取 chunk 文件：{file_path}")


"""4. 小工具"""


# 把任意值稳妥转成字符串。
def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


# 把列表按 batch_size 切成多批。
def batch_iter(items: list[Any], batch_size: int) -> list[list[Any]]:
    batches: list[list[Any]] = []

    for start in range(0, len(items), batch_size):
        end = start + batch_size
        batches.append(items[start:end])

    return batches


"""5. 调 Ollama 生成 embedding"""


def embed_texts(
        texts: list[str],
        model: str = DEFAULT_EMBED_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
) -> list[list[float]]:
    """
    调 Ollama /api/embed 生成向量。

    当前一次传一批文本，减少请求次数。
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


"""6. 构建可入库记录"""


def build_records(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    把 chunk 记录转换成更适合入 FAISS 的结构。

    这里我保留两块：
    1. text：真正拿去 embedding 的正文
    2. metadata：后面检索回来要展示的信息
    """
    records: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_id = safe_text(chunk.get("chunk_id")).strip()
        text = safe_text(chunk.get("text")).strip()

        if not chunk_id or not text:
            continue

        metadata = {
            "chunk_id": chunk_id,
            "doc_id": safe_text(chunk.get("doc_id")),
            "doc_title": safe_text(chunk.get("doc_title")),
            "section_title": safe_text(chunk.get("section_title")),
            "section_level": chunk.get("section_level"),
            "section_index": chunk.get("section_index"),
            "chunk_index_in_section": chunk.get("chunk_index_in_section"),
            "chunk_index_in_doc": chunk.get("chunk_index_in_doc"),
            "source_file": safe_text(chunk.get("source_file")),
            "source_path": safe_text(chunk.get("source_path")),
            "text": text,
            "body_text": safe_text(chunk.get("body_text")),
        }

        records.append(
            {
                "id": chunk_id,
                "text": text,
                "metadata": metadata,
            }
        )

    return records


"""7. 向量归一化"""


def normalize_embeddings(matrix: np.ndarray) -> np.ndarray:
    """
    对向量做 L2 归一化。

    因为后面我用 FAISS 的 IndexFlatIP（内积）做检索。
    在向量归一化后，内积就相当于 cosine 相似度。

    这样比较直观，也适合规则文本这种场景。
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    return matrix / norms


"""8. 主流程：构建 FAISS 索引"""


def build_faiss_index(
        chunks_path: Path,
        output_dir: Path,
        embed_model: str = DEFAULT_EMBED_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    主流程：
    1. 读取 chunk
    2. 构造可入库记录
    3. 分批生成 embedding
    4. 拼成一个向量矩阵
    5. 建 FAISS 索引
    6. 保存索引和 metadata
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

    # 做归一化，后面用 IndexFlatIP 近似 cosine 相似度
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


"""9. 对外入口"""


def run_faiss_store_build(
        chunks_relative_path: str = DEFAULT_CHUNKS_PATH,
        faiss_relative_dir: str = DEFAULT_FAISS_DIR,
        embed_model: str = DEFAULT_EMBED_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    对外统一入口。

    后面不管你是本地调试、API 调用还是页面触发，
    都优先调这一层。
    """
    chunks_path = resolve_path(chunks_relative_path)
    output_dir = resolve_path(faiss_relative_dir)

    return build_faiss_index(
        chunks_path=chunks_path,
        output_dir=output_dir,
        embed_model=embed_model,
        batch_size=batch_size,
    )


"""10. 本地调试入口"""

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
