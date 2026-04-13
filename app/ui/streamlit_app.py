# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/12 21:05
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import json
from typing import Any
import requests
import streamlit as st

API_BASE_URL = 'http://127.0.0.1:8000'


# 调用后端  /ask 或 /ask-lc 接口
def call_ask_api(
        question: str,
        endpoint: str,
        top_k: int,
        use_vector: bool,
        include_trace: bool,
) -> dict[str, Any]:
    url = F'{API_BASE_URL}{endpoint}'
    payload = {
        'question': question,
        'top_k': top_k,
        'use_vector': use_vector,
        'include_trace': include_trace,
    }

    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


# 先展示最核心信息
def render_basic_result(result: dict[str, Any]) -> None:
    """
    展示 answer、route、task_type、tools_used
    """
    st.subheader('最终回答')
    st.write(result.get('answer', ''))

    st.subheader('基础信息')

    route = result.get('route') or result.get('task_type') or 'unknown'
    st.write(f'**问题类型：** {route}')

    tools_used = result.get('tools_used')

    if tools_used:
        st.write(f"**调用工具：** {', '.join(tools_used)}")

    if 'question' in result:
        st.write(f"**问题：** {result.get('question')}")

    if 'use_vector' in result:
        st.write(f"**向量检索：** {'是' if result.get('use_vector') else '否'}")

    if 'top_k' in result:
        st.write(f"**Top K：** {result.get('top_k')}")


def render_analysis_section(result: dict[str, Any]) -> None:
    analysis_result = result.get('analysis_result')
    if not analysis_result:
        return

    st.subheader('分析结果')
    summary = analysis_result.get('summary')
    if summary:
        st.info(summary)

    stats = analysis_result.get('stats')
    if isinstance(stats, list) and stats:
        st.write('**统计信息**')
        st.json(stats)

    table = analysis_result.get('table')
    if isinstance(table, list) and table:
        st.write('**结果表预览**')
        st.dataframe(table, use_container_width=True)


def render_evidence_section(result: dict[str, Any]) -> None:
    retrieval_result = result.get('retrieval_result')
    if not retrieval_result:
        return

    evidences = retrieval_result.get('evidences', [])
    if not evidences:
        return

    st.subheader('证据片段')

    topic = retrieval_result.get('topic')
    mode = retrieval_result.get('mode')
    retrieved_count = retrieval_result.get('retrieved_count')

    meta_parts = []
    if topic:
        meta_parts.append(f'规则主题：{topic}')

    if mode:
        meta_parts.append(f"检索模式：{mode}")

    if retrieved_count is not None:
        meta_parts.append(f'命中数量：{retrieved_count}')

    if meta_parts:
        st.caption('|'.join(meta_parts))

    if meta_parts:
        st.caption('|'.join(meta_parts))

    for evidence in evidences:
        rank = evidence.get('rank', '')
        doc_title = evidence.get('doc_title', '')
        section_title = evidence.get('section_title', '')
        score = evidence.get('score', '')
        preview_text = evidence.get('preview_text', '')

        title = f"证据{rank} | {doc_title or '未知文档'}"
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


def render_raw_json(result: dict[str, Any]) -> None:
    with st.expander("查看原始返回 JSON", expanded=False):
        st.code(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            language="json",
        )


def main() -> None:
    st.set_page_config(
        page_title="Price Audit Copilot",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Price Audit Copilot")
    st.caption("第五周：Streamlit 最小联调页面")

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

    default_question = "近7天哪个平台异常低价最多？"
    question = st.text_area(
        "请输入你的问题",
        value=default_question,
        height=100,
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        run_button = st.button("提交问题", use_container_width=True)
    with col2:
        st.info("第二版目标：补分析结果、证据片段、异常解释和 trace 展示")

    if run_button:
        question = question.strip()

        if not question:
            st.warning("问题不能为空。")
            return

        try:
            with st.spinner("正在调用后端接口..."):
                result = call_ask_api(
                    question=question,
                    endpoint=endpoint,
                    top_k=top_k,
                    use_vector=use_vector,
                    include_trace=include_trace,
                )

            st.success("调用成功。")
            render_basic_result(result)
            render_analysis_section(result)
            render_evidence_section(result)
            render_explanation_section(result)
            render_trace_section(result)
            render_raw_json(result)

        except requests.exceptions.RequestException as e:
            st.error(f"接口调用失败：{e}")
        except Exception as e:
            st.error(f"页面运行异常：{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
