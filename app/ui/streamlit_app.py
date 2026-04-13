# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/12 21:05
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Any

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASK_LOG_PATH = PROJECT_ROOT / "data" / "outputs" / "ask_logs.jsonl"


def call_ask_api(
        question: str,
        endpoint: str,
        top_k: int,
        use_vector: bool,
        include_trace: bool,
) -> dict[str, Any]:
    url = f"{API_BASE_URL}{endpoint}"
    payload = {
        "question": question,
        "top_k": top_k,
        "use_vector": use_vector,
        "include_trace": include_trace,
    }

    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def load_recent_logs(limit: int = 5) -> list[dict[str, Any]]:
    """
    读取 ask_logs.jsonl 最近几条记录。
    """
    if not ASK_LOG_PATH.exists():
        return []

    rows: list[dict[str, Any]] = []

    try:
        with ASK_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    return list(reversed(rows[-limit:]))


def shorten_text(text: str, max_chars: int = 120) -> str:
    text = str(text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def render_basic_result(result: dict[str, Any]) -> None:
    st.subheader("最终回答")
    st.write(result.get("answer", ""))

    st.subheader("基础信息")

    route = result.get("route") or result.get("task_type") or "unknown"
    st.write(f"**问题类型：** {route}")

    tools_used = result.get("tools_used")
    if tools_used:
        st.write(f"**调用工具：** {', '.join(tools_used)}")

    if "question" in result:
        st.write(f"**问题：** {result.get('question')}")

    if "use_vector" in result:
        st.write(f"**向量检索：** {'是' if result.get('use_vector') else '否'}")

    if "top_k" in result:
        st.write(f"**Top K：** {result.get('top_k')}")


def render_analysis_section(result: dict[str, Any]) -> None:
    analysis_result = result.get("analysis_result")
    if not analysis_result:
        return

    st.subheader("分析结果")

    summary = analysis_result.get("summary")
    if summary:
        st.info(summary)

    stats = analysis_result.get("stats")
    if isinstance(stats, dict) and stats:
        st.write("**统计信息**")
        st.json(stats)

    table = analysis_result.get("table")
    if isinstance(table, list) and table:
        st.write("**结果表预览**")
        st.dataframe(table, use_container_width=True)


def render_evidence_section(result: dict[str, Any]) -> None:
    retrieval_result = result.get("retrieval_result")
    if not retrieval_result:
        return

    evidences = retrieval_result.get("evidences", [])
    if not evidences:
        return

    st.subheader("证据片段")

    topic = retrieval_result.get("topic")
    mode = retrieval_result.get("mode")
    retrieved_count = retrieval_result.get("retrieved_count")

    meta_parts = []
    if topic:
        meta_parts.append(f"规则主题：{topic}")
    if mode:
        meta_parts.append(f"检索模式：{mode}")
    if retrieved_count is not None:
        meta_parts.append(f"命中数量：{retrieved_count}")

    if meta_parts:
        st.caption(" | ".join(meta_parts))

    for evidence in evidences:
        rank = evidence.get("rank", "")
        doc_title = evidence.get("doc_title", "")
        section_title = evidence.get("section_title", "")
        score = evidence.get("score", "")
        preview_text = evidence.get("preview_text", "")

        title = f"证据 {rank}｜{doc_title or '未知文档'}"
        with st.expander(title, expanded=(rank == 1)):
            if section_title:
                st.write(f"**章节：** {section_title}")
            st.write(f"**分数：** {score}")
            if preview_text:
                st.write(f"**摘要：** {preview_text}")

            score_reasons = evidence.get("score_reasons")
            if score_reasons:
                st.write("**命中原因：**")
                st.json(score_reasons)

            body_text = evidence.get("body_text")
            if body_text:
                st.write("**正文片段：**")
                st.code(body_text)

            full_text = evidence.get("full_text")
            if full_text and full_text != body_text:
                st.write("**完整文本：**")
                st.code(full_text)


def render_explanation_section(result: dict[str, Any]) -> None:
    explanation_result = result.get("explanation_result")
    if not explanation_result:
        return

    st.subheader("异常解释")

    final_explanation = explanation_result.get("final_explanation")
    if final_explanation:
        st.write(f"**最终解释：** {final_explanation}")

    rule_summary = explanation_result.get("rule_summary")
    if rule_summary:
        st.write(f"**规则摘要：** {rule_summary}")

    review_suggestion = explanation_result.get("review_suggestion")
    if review_suggestion:
        st.write(f"**复核建议：** {review_suggestion}")


def render_trace_section(result: dict[str, Any]) -> None:
    trace = result.get("trace", [])
    if not trace:
        return

    st.subheader("工具调用链路")

    for item in trace:
        step = item.get("step", "")
        tool_name = item.get("tool_name", "")
        status = item.get("status", "")
        note = item.get("note", "")

        st.markdown(f"**Step {step} · {tool_name} · {status}**")
        if note:
            st.write(note)
        st.divider()


def render_recent_logs(limit: int = 5) -> None:
    st.subheader("最近问答日志")

    rows = load_recent_logs(limit=limit)
    if not rows:
        st.info("当前还没有可展示的 ask 日志。")
        return

    display_rows: list[dict[str, Any]] = []
    for row in rows:
        display_rows.append(
            {
                "时间": row.get("timestamp", ""),
                "路由": row.get("route", ""),
                "问题": shorten_text(row.get("question", ""), max_chars=60),
                "工具": ", ".join(row.get("tools_used", []) or []),
                "回答摘要": shorten_text(row.get("answer", ""), max_chars=100),
            }
        )

    st.dataframe(display_rows, use_container_width=True)

    with st.expander("查看最近日志原文", expanded=False):
        st.code(
            json.dumps(rows, ensure_ascii=False, indent=2, default=str),
            language="json",
        )


def render_raw_json(result: dict[str, Any]) -> None:
    with st.expander("查看原始返回 JSON", expanded=False):
        st.code(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            language="json",
        )


def submit_and_store_result(
        question: str,
        endpoint: str,
        top_k: int,
        use_vector: bool,
        include_trace: bool,
) -> None:
    result = call_ask_api(
        question=question,
        endpoint=endpoint,
        top_k=top_k,
        use_vector=use_vector,
        include_trace=include_trace,
    )
    st.session_state["last_result"] = result
    st.session_state["last_question"] = question


def main() -> None:
    st.set_page_config(
        page_title="Price Audit Copilot",
        page_icon="📊",
        layout="wide",
    )

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "last_question" not in st.session_state:
        st.session_state["last_question"] = ""

    st.title("📊 Price Audit Copilot")
    st.caption("第五周：系统展示页（含汇报按钮与日志预览）")

    with st.sidebar:
        st.header("调用参数")

        api_mode = st.radio(
            "接口模式",
            options=["标准模式 /ask", "LangChain 模式 /ask-lc"],
            index=0,
        )
        endpoint = "/ask" if api_mode == "标准模式 /ask" else "/ask-lc"

        retrieval_mode = st.radio(
            "规则检索模式",
            options=["baseline", "faiss"],
            index=0,
        )
        use_vector = retrieval_mode == "faiss"

        top_k = st.slider("Top K", min_value=1, max_value=10, value=3, step=1)
        include_trace = st.checkbox("返回 trace", value=True)

        st.markdown("---")
        st.markdown("**后端地址**")
        st.code(API_BASE_URL)

        st.markdown("---")
        st.markdown("**快捷动作**")

        if st.button("生成简短汇报", use_container_width=True):
            report_question = "先找出低价商品，再按规则给我写一段简短汇报。"
            try:
                with st.spinner("正在生成简短汇报..."):
                    submit_and_store_result(
                        question=report_question,
                        endpoint="/ask",
                        top_k=top_k,
                        use_vector=use_vector,
                        include_trace=include_trace,
                    )
                st.success("简短汇报已生成。")
            except requests.exceptions.RequestException as e:
                st.error(f"汇报接口调用失败：{e}")
            except Exception as e:
                st.error(f"汇报生成异常：{type(e).__name__}: {e}")

    default_question = st.session_state["last_question"] or "近7天哪个平台异常低价最多？"
    question = st.text_area(
        "请输入你的问题",
        value=default_question,
        height=100,
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        run_button = st.button("提交问题", use_container_width=True)
    with col2:
        st.info("第三版目标：补日志预览，并支持一键生成简短汇报")

    if run_button:
        question = question.strip()

        if not question:
            st.warning("问题不能为空。")
            return

        try:
            with st.spinner("正在调用后端接口..."):
                submit_and_store_result(
                    question=question,
                    endpoint=endpoint,
                    top_k=top_k,
                    use_vector=use_vector,
                    include_trace=include_trace,
                )
            st.success("调用成功。")

        except requests.exceptions.RequestException as e:
            st.error(f"接口调用失败：{e}")
        except Exception as e:
            st.error(f"页面运行异常：{type(e).__name__}: {e}")

    result = st.session_state.get("last_result")
    if result:
        render_basic_result(result)
        render_analysis_section(result)
        render_evidence_section(result)
        render_explanation_section(result)
        render_trace_section(result)
        render_raw_json(result)

    st.markdown("---")
    render_recent_logs(limit=5)


if __name__ == "__main__":
    main()
