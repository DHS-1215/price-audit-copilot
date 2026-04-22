# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/11 19:09
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any
from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from app.orchestrators.ask_lc_orchestrator import LANGCHAIN_TOOLS,build_report_tool

SYSTEM_PROMPT = """
你是电商价格异常审核 Copilot。

你必须遵守以下规则：

一、工具选择规则
1. 用户问数据分析类问题时，优先调用 analyze_price_data_tool。
2. 用户问规则检索类问题时，优先调用 search_rules_tool。
3. 用户问异常解释类问题时，优先调用 explain_anomaly_tool。
4. 用户问混合类问题，尤其包含“先…再… / 汇报 / 总结 / 简短说明 / 写一段说明”等表达时，必须优先调用 build_report_tool。
5. 对于 mixed / 汇报类问题，不要自己直接写汇报，必须先调用 build_report_tool。

二、回答约束规则
6. 你只能基于工具返回的显式字段回答。
7. 不允许脱离工具结果自行补充规则细节。
8. 不允许把 section_title、preview_text 扩写成未明确返回的规则定义。
9. 如果工具只返回了标题级证据，你只能说“当前证据显示该问题与某规则主题相关”，不能自行补充具体规则内容。
10. 如果证据不足，就明确说证据不足，不要自行脑补。
11. 优先引用工具结果中的 topic、doc_title、section_title。
12. 不要自行创造“比如要求包含品牌名称或型号”这类细节。

三、mixed / 汇报问题的特殊规则
13. mixed / 汇报问题的最终输出，应优先来自 build_report_tool，而不是你自行总结。
14. mixed / 汇报问题中，如果已经有专门的 report tool，就不要自己重复组合 analysis 和 retrieval 结果后直接作答。
15. 不要把规则检索问题泛化成“电商价格异常规则”这类过宽问句；如果需要规则检索，应围绕具体异常主题进行。

四、输出风格
16. 回答要清楚、业务化、直接，不要空泛。
17. 在规则类问题中，若证据不足，应如实说明“当前证据不足以直接给出具体处理规则”。
""".strip()


# 创建 LangChain Agent,这里先用我本地模型。
def build_langchain_agent(model_name: str = 'qwen2.5:7b'):
    model = ChatOllama(
        model=model_name,
        temperature=0,
        base_url="http://127.0.0.1:11434",
        client_kwargs={"trust_env": False},
        sync_client_kwargs={"trust_env": False},
    )
    agent = create_agent(
        model=model,
        tools=LANGCHAIN_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


# 尽量从 Langchain agent 返回结果里提取最终文本
def _extract_text_from_agent_result(result: Any) -> str:
    """
    LangChain agent.invoke(...) 通常返回一个包含 messages 的状态对象。
    """
    if isinstance(result, dict):
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]

            # LangChain message object
            content = getattr(last_message, "content", None)

            # 如果是 dict 风格
            if content is None and isinstance(last_message, dict):
                content = last_message.get("content")

            if isinstance(content, str):
                return content

            if isinstance(content, list):
                texts: list[str] = []
                for item in content:
                    if isinstance(item, str):
                        texts.append(item)
                    elif isinstance(item, dict):
                        text = item.get("text")
                        if text:
                            texts.append(str(text))
                if texts:
                    return "\n".join(texts).strip()

    return str(result)


# 运行智能体
def run_langchain_ask(
        question: str,
        top_k: int = 3,
        use_vector: bool = False,
        model_name: str = "qwen2.5:7b",
) -> dict[str, Any]:
    """
    我把 top_k / use_vector明确写在用户消息中，让 agent 在调用 search_rules_tool / explain_anomaly_tool 时能用到。
    """
    retrieval_mode = "faiss" if use_vector else "baseline"
    task_type = detect_langchain_task_type(question)

    # mixed 问题：直接强制走 report tool
    if task_type == "mixed":
        report_text = build_report_tool(
            question=question,
            top_k=top_k,
            mode=retrieval_mode,
        )
        return {
            "ok": True,
            "question": question,
            "top_k": top_k,
            "use_vector": use_vector,
            "task_type": task_type,
            "answer": report_text,
            "raw_result": {
                "forced_tool": "build_report_tool"
            },
        }

    # 非 mixed：继续走自由 agent
    agent = build_langchain_agent(model_name=model_name)

    user_message = (
        f"用户问题：{question}\n"
        f"规则检索 top_k：{top_k}\n"
        f"规则检索模式：{retrieval_mode}\n"
        f"请根据问题自行决定调用哪些工具，并给出最终答案。"
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        }
    )

    answer = _extract_text_from_agent_result(result)

    return {
        "ok": True,
        "question": question,
        "top_k": top_k,
        "use_vector": use_vector,
        "task_type": task_type,
        "answer": answer,
        "raw_result": result,
    }


def detect_langchain_task_type(question: str) -> str:
    q = question.strip().lower()

    mixed_keywords = ["先", "再", "然后", "汇报", "总结", "写一段", "简短说明", "报告"]
    explanation_keywords = ["为什么", "高风险", "被判", "判成"]
    retrieval_keywords = ["规则", "依据", "怎么处理", "如何处理", "复核", "定义", "口径"]
    analysis_keywords = ["多少", "最多", "最少", "统计", "数量", "占比", "平台", "品牌", "近7天", "最近7天", "近七天"]

    has_mixed = any(k in q for k in mixed_keywords)
    has_explanation = any(k in q for k in explanation_keywords)
    has_retrieval = any(k in q for k in retrieval_keywords)
    has_analysis = any(k in q for k in analysis_keywords)

    if has_mixed and (has_analysis or has_retrieval or has_explanation):
        return "mixed"
    if has_explanation:
        return "explanation"
    if has_retrieval and not has_analysis:
        return "retrieval"
    if has_analysis:
        return "analysis"
    return "unknown"
