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


# 先保留一个原始结果区，方便联调
def render_raw_json(result: dict[str, Any]) -> None:
    with st.expander('查看原始返回 JSON', expanded=False):
        st.code(
            json.dumps(
                result, ensure_ascii=False, indent=2, default=str
            ), language='json',
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
        st.info("第一版目标：先跑通页面 -> 接口 -> 返回结果")

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
            render_raw_json(result)

        except requests.exceptions.RequestException as e:
            st.error(f"接口调用失败：{e}")
        except Exception as e:
            st.error(f"页面运行异常：{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
