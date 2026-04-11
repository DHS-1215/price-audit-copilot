# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/04 08:26
IDE       :PyCharm
作者      :董宏升

第三周：规则检索工具层

我写这个文件的定位不是重写一个 retrieve 而是把 retriever.py 已经跑通的检索能力，包装成后面统一问答入口、报告生成、解释链都能直接调用的工具层。

可以把它理解成两层：
第一层：retriever.py
    - 负责从 chunk 里找规则片段
    - 更偏底层检索逻辑

第二层：retrieval_tools.py
    - 负责把检索结果整理成“可被系统消费的格式”
    - 更偏工具输出、证据组织、上下文拼接

后面第四周 routes_ask.py / LangChain tools / Streamlit 页面，
都更适合接这一层，而不是直接去碰底层检索器
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re
from typing import Any
from app.rag.retriever import retrieve_rules as retrieve_rules_baseline
import importlib

print("已加载 retrieval_tools.py 文件路径：", __file__)
print("retrieve_rules_baseline 是否可调用：", callable(retrieve_rules_baseline))

"""1. 基础配置"""
DEFAULT_TOP_K = 3
DEFAULT_PREVIEW_CHARS = 220  # 默认预览文本最多显式220个字符

# 我这里给“规则主题”做一个轻量映射。
# 作用不是做复杂分类，而是让后面输出更像业务工具，而不是一坨原始检索结果。
DOC_TOPIC_LABELS = {
    'low_price_detection_rules': '低价异常规则',
    'cross_platform_gap_rules': '跨平台价差规则',
    'spec_normalization_rules': '规格归一与规格风险规则',
    'manual_review_process': '人工复核流程',
    'platform_price_rules': '平台价格审核规则',
    'faq': 'FAQ',
}

"""2. 小工具"""


# 把任意值转为字符串
def safe_text(value: Any) -> str:
    """
    根据经验因为工具层最好不要强依赖底层某个小函数是否可见。（我自己留一份小工具，模块边界更清楚）
    """
    if value is None:
        return ""
    return str(value)


# 对用户问题做基础标准化
def normalize_user_query(query: str) -> str:
    """
    我这里只做轻清洗，不做复杂改写。
    因为规则检索里，用户原句通常很重要。
    """
    query = safe_text(query).strip()
    query = re.sub(r"\s+", " ", query)
    return query


# 把文本压的更合适展示
def compact_text(text: str) -> str:
    """
    该函数只做三件事：
    1.统一换行
    2.把连续空白压紧一点
    3.保留基本可读性
    """
    text = safe_text(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# 生成短预览文本
def shorten_text(text: str, max_chars: int = DEFAULT_PREVIEW_CHARS) -> str:
    """
    因为 retrieval tool 给上层时，很多场景只需要“看个大概”，
    不需要把整段全文都塞进去，但是完整文本仍会保留在evidence里，方便后面我调用
    :param text:文本
    :param max_chars:最大字符
    """
    text = compact_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + '...'


# 给当前问题贴一个更易读的规则主题标签。-
def infer_rule_topic(preferred_doc_ids: list[str]) -> str:
    """
    根据 retriever 推断出来的 preferred_doc_ids，
    给当前问题贴一个更容易读的“规则主题”标签。
    我这里优先读取第一优先文档，因为该文档通常代表当前问题的主方向。
    :param preferred_doc_ids:优先考虑的文档 id 列表
    """
    if not preferred_doc_ids:
        return "通用规则"

    first_doc_id = preferred_doc_ids[0]
    return DOC_TOPIC_LABELS.get(first_doc_id, "通用规则")


# 动态加载 FAISS 检索器的对外主函数。
def load_faiss_retriever_callable():
    module = importlib.import_module("app.rag.faiss_retriever")

    candidate_names = [
        "retrieve_rules_faiss",
        "search_rules_faiss",
        "retrieve_rules",
        "search_rules",
        'search_faiss_rules',
    ]

    for name in candidate_names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn

    raise AttributeError(
        "app.rag.faiss_retriever 中未找到可用的检索函数。"
        "请确认该文件里是否暴露了 retrieve_rules_faiss / search_rules_faiss / retrieve_rules / search_rules。"
    )


# 把不同检索器返回的结果，统一整理策划给你 retrieval_tools 能消费的格式。
def normalize_retrieval_payload(payload: Any) -> dict[str, Any]:
    """
    baseline 目前通常返回：
    {
        "query_terms": ...,
        "preferred_doc_ids": ...,
        "results": [...]
    }

    但 FAISS 检索器有可能返回：
    - 直接一个 list
    - 或 dict，但字段名略有不同

    所以这里做一个“统一适配层”。
    """
    # 1. 如果本来就是标准 dict，直接尽量兼容
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return {
                "query_terms": payload.get("query_terms", []) or [],
                "preferred_doc_ids": payload.get("preferred_doc_ids", []) or [],
                "results": results,
            }

        # 有些实现可能叫 hits / items
        for candidate in ["hits", "items", "records"]:
            if isinstance(payload.get(candidate), list):
                return {
                    "query_terms": payload.get("query_terms", []) or [],
                    "preferred_doc_ids": payload.get("preferred_doc_ids", []) or [],
                    "results": payload.get(candidate) or [],
                }

    # 2. 如果直接返回 list，就包装成标准结构
    if isinstance(payload, list):
        return {
            "query_terms": [],
            "preferred_doc_ids": [],
            "results": payload,
        }

    # 3. 都不符合时，给个空结果兜底
    return {
        "query_terms": [],
        "preferred_doc_ids": [],
        "results": [],
    }


# 当某些检索器（如 FAISS）没显式返回 preferred_doc_id，我根据结果结果中出现的 doc_id 做轻量推断。
def infer_preferred_doc_ids_from_results(raw_results: list[dict[str, Any]]) -> list[str]:
    """
    按检索结果顺序扫描，保留前几个不重复 doc_id
    """
    doc_ids: list[str] = []

    for item in raw_results:
        doc_id = safe_text(item.get("doc_id")).strip()
        if not doc_id:
            continue
        if doc_id in doc_ids:
            continue
        doc_ids.append(doc_id)

    return doc_ids


# 根据模型选择使用 baseline 或 FAISS 检索
def retrieve_rules_by_mode(query: str, top_k: int, mode: str = "baseline") -> dict[str, Any]:
    """
    mode:
    - baseline：走第三周 baseline 检索
    - faiss：走第三周 FAISS 向量检索
    """
    print("进入 retrieve_rules_by_mode")
    print("query =", query)
    print("mode =", mode)

    if mode == "faiss":
        print("准备走 FAISS 检索")
    else:
        print("准备走 baseline 检索")

    mode = safe_text(mode).strip().lower() or "baseline"

    if mode == "faiss":
        faiss_fn = load_faiss_retriever_callable()
        payload = faiss_fn(query=query, top_k=top_k)
        return normalize_retrieval_payload(payload)

    # 默认走 baseline
    payload = retrieve_rules_baseline(query=query, top_k=top_k)
    return normalize_retrieval_payload(payload)


"""3.  证据整理"""


def build_evidence_item(
        result: dict[str, Any],
        rank: int,
        preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> dict[str, Any]:
    """
    把单条检索结果整理成更适合工具层返回的证据结构。
    此函数意义：
    - 补 rank
    - 补 preview
    - 统一字段结构
    - 给上层减少处理负担
    """
    doc_id = safe_text(result.get("doc_id"))
    doc_title = safe_text(result.get("doc_title"))
    section_title = safe_text(result.get("section_title"))
    source_file = safe_text(result.get("source_file"))
    body_text = compact_text(result.get("body_text"))
    full_text = compact_text(result.get("text"))

    # 预览优先用 body_text。
    # 因为 body_text 一般更聚焦规则正文；
    # 如果 body_text 为空，再退回完整 text。
    preview_source = body_text if body_text else full_text
    preview_text = shorten_text(preview_source, max_chars=preview_chars)

    return {
        "rank": rank,
        "chunk_id": result.get("chunk_id"),
        "doc_id": doc_id,
        "doc_title": doc_title,
        "section_title": section_title,
        "source_file": source_file,
        "score": int(result.get("score", 0)),
        "score_reasons": result.get("score_reasons", []),
        "preview_text": preview_text,
        "body_text": body_text,
        "full_text": full_text,
    }


# 把单条证据整理成适合 prompt / 日志 / 调试的文本块。
def format_evidence_block(evidence: dict[str, Any]) -> str:
    """
    之后我把 block 塞进统一问答入口、报告生成、调试日志中也会顺手
    """
    rank = evidence.get("rank")
    doc_title = safe_text(evidence.get("doc_title"))
    section_title = safe_text(evidence.get("section_title"))
    score = evidence.get("score", 0)
    preview_text = safe_text(evidence.get("preview_text"))

    return (
        f"[证据{rank}]\n"
        f"文档：{doc_title}\n"
        f"章节：{section_title}\n"
        f"分数：{score}\n"
        f"摘要：{preview_text}"
    )


"""4. 对外主工具：检索规则"""


# 工具层主入口：检索规则证据
def search_rules(
        query: str,
        top_k: int = DEFAULT_TOP_K,
        preview_chars: int = DEFAULT_PREVIEW_CHARS,
        mode: str = "baseline",
) -> dict[str, Any]:
    """
    把底层 retriever 的结果，整理成上层系统能直接使用的工具输出。
    此处函数返回包含：
    query、topic（规则主题）、提取到的关键词、优先文档、evidence列表、一份便于后面系统直接塞 prompt 的 context_text

    新增参数：
    mode
    - baseline：走规则型 baseline 检索
    - faiss：走向量检索
    """
    query = normalize_user_query(query)

    if not query:
        return {
            "ok": False,
            "query": query,
            "mode": mode,
            "topic": "通用规则",
            "message": "查询为空，无法检索规则。",
            "query_terms": [],
            "preferred_doc_ids": [],
            "retrieved_count": 0,
            "evidences": [],
            "context_text": "",
        }

    print("search_rules 已开始执行，mode =", mode)
    payload = retrieve_rules_by_mode(
        query=query,
        top_k=top_k,
        mode=mode,
    )

    query_terms = payload.get("query_terms", []) or []
    preferred_doc_ids = payload.get("preferred_doc_ids", []) or []
    raw_results = payload.get("results", []) or []

    # 如果检索器没有显式返回 preferred_doc_ids，就从结果里推断一份
    if not preferred_doc_ids:
        preferred_doc_ids = infer_preferred_doc_ids_from_results(raw_results)

    evidences: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_results, start=1):
        evidences.append(
            build_evidence_item(
                result=item,
                rank=idx,
                preview_chars=preview_chars,
            )
        )

    topic = infer_rule_topic(preferred_doc_ids)

    context_blocks = [format_evidence_block(item) for item in evidences]
    context_text = "\n\n".join(context_blocks)

    return {
        "ok": True,
        "query": query,
        "mode": mode,
        "topic": topic,
        "message": "规则检索完成。" if evidences else "未检索到高相关规则片段。",
        "query_terms": query_terms,
        "preferred_doc_ids": preferred_doc_ids,
        "retrieved_count": len(evidences),
        "evidences": evidences,
        "context_text": context_text,
    }


""" 5. 附加工具：给上一层一个简短摘要"""


def build_rule_search_summary(search_payload: dict[str, Any]) -> str:
    """
    此处不是最后答案，只是一个工具摘要，适合（接口返回提示、调试日志、界面简报）
    真实最终回答，后面会结合第二周结果层字段来拼。
    """
    if not search_payload.get("ok"):
        return safe_text(search_payload.get("message", "规则检索失败。"))

    evidences = search_payload.get("evidences", []) or []
    topic = safe_text(search_payload.get("topic"))
    query = safe_text(search_payload.get("query"))

    if not evidences:
        return f"问题“{query}”暂未检索到高相关规则片段。"

    top_evidence = evidences[0]
    doc_title = safe_text(top_evidence.get("doc_title"))
    section_title = safe_text(top_evidence.get("section_title"))

    return (
        f"该问题当前主要命中“{topic}”相关规则。"
        f"最相关证据来自《{doc_title}》的《{section_title}》章节。"
    )


# -----------------------------------
# 6. 本地调试入口
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

        payload = search_rules(query=query, top_k=3)

        print(f"规则主题：{payload['topic']}")
        print(f"提取关键词：{payload['query_terms']}")
        print(f"优先文档：{payload['preferred_doc_ids']}")
        print(f"命中数量：{payload['retrieved_count']}")
        print(f"摘要：{build_rule_search_summary(payload)}")

        if payload["evidences"]:
            print("\n证据上下文：")
            print(payload["context_text"])
        else:
            print("\n未检索到相关规则片段。")
