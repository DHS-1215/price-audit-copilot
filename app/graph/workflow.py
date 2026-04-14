# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/12 21:06
IDE       :PyCharm
作者      :董宏升

该模块定位是 LangGraph 思维的轻量表达版

- 先把系统链路拆成节点
- 先让状态在节点之间流动
- 先把受控流程表达清楚
- 让第五周项目具备“流程感”
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from typing import Any, TypedDict
from app.api.routes_ask import (
    analyze_price_data,  # 分析类问题的执行函数
    detect_route,  # 规则式路由函数，用来判断问题类型
    run_explanation,  # explanation 场景的执行函数
)
from app.tools.retrieval_tools import search_rules
from app.tools.report_tools import build_brief_report


class WorkflowState(TypedDict, total=False):
    """
    第五周工作流状态对象。
    先把“状态在节点流动”思路立住。
    """
    # 输入字段
    question: str
    top_k: int
    mode: str

    # 过程判断字段
    route: str

    # 节点产出字段
    answer: str
    analysis_result: dict[str, Any] | None
    retrieval_result: dict[str, Any] | None
    explanation_result: dict[str, Any] | None
    review_suggestion: str | None

    # 过程记录字段
    trace: list[dict[str, Any]] | None


# 给当前工作流补一条 trace 记录。
def append_trace(
        state: WorkflowState,
        node_name: str,
        note: str,
        status: str = "success",
) -> None:
    """
    如果工作流没有过程记录，最后只看到 answer，却不知道中间发生什么，
    系统先路由，再分析，再检索，再组合答案。
    :param state: 当前工作流状态
    :param node_name: 当前执行的节点名称
    :param node: 这一步的简短说明
    """
    trace = state.setdefault("trace", [])
    trace.append(
        {
            "step": len(trace) + 1,
            "node_name": node_name,
            "status": status,
            "note": note,
        }
    )


# 根据用户问题，判断属于哪一类
def route_query_node(state: WorkflowState) -> WorkflowState:
    """
    根据 workflow 第一步：先判断问题类型，再决定走哪条链路。
    """
    question = str(state.get("question", "")).strip()

    # 放第四周 routes_ask.py 验证过的轻量路由器
    route = detect_route(question)
    state['route'] = route

    append_trace(state, 'route_query_node', f'路由结果：{route}')
    return state


# 数据分析节点
def run_analysis_node(state: WorkflowState) -> WorkflowState:
    """
    mixed问题也会走该节点（因为需要先看事实结果）

    这里我复用 analyze_price_data(question)，它会根据自然语言问题去调用第二周已有的分析能力。

    执行后会给 state 补上：
    - analysis_result
    - trace
    """
    question = str(state.get('question', '')).strip()
    result = analyze_price_data(question)
    state['analysis_result'] = result

    append_trace(
        state,
        'run_analysis_node',
        result.get('summary', '分析完成。')
    )
    return state


# 规则检索节点
def run_retrieval_node(state: WorkflowState) -> WorkflowState:
    """
    mixed 问题也会走这里，因为 mixed 往往需要“数据事实 + 规则依据一起给”
    此处复用 search_rules()
    支持：baseline 和 faiss

    result 后 会给 state 补上 retrieval_result 和 trace
    """
    question = str(state.get('question', '')).strip()
    top_k = int(state.get('top_k', 3))
    mode = str(state.get('mode', 'baseline'))

    result = search_rules(
        query=question,
        top_k=top_k,
        mode=mode
    )

    state['retrieval_result'] = result
    append_trace(
        state,
        "run_retrieval_node",
        f"规则检索完成，命中 {result.get('retrieved_count', 0)} 条。",
    )
    return state


# 异常解释节点
def run_explanation_node(
        state: WorkflowState
) -> WorkflowState:
    """
    上面的 retrieval只是查规则，
    而这个是：
    1.先选一条最相关异常样本
    2.再结合结果层事实
    3.再去检索规则
    4.最后给出：
        - fact_explanation
       - rule_summary
       - review_suggestion
       - final_explanation
    """
    question = str(state.get("question", "")).strip()
    top_k = int(state.get("top_k", 3))
    mode = str(state.get("mode", "baseline"))

    result = run_explanation(
        question=question,
        top_k=top_k,
        retrieval_mode=mode,
    )

    state['explanation_result'] = result

    # explanation_result 里本身带了 rule_search，
    # 为了让工作流后续展示层统一一些，这里顺手把 retrieval_result 也补上
    state["retrieval_result"] = result.get("rule_search")

    # explanation 场景通常已经会产出复核建议
    state["review_suggestion"] = result.get("review_suggestion")

    append_trace(
        state,
        "run_explanation_node",
        result.get("rule_summary", "异常解释完成。"),
    )
    return state


# 最终答案组合节点
def compose_answer_node(state: WorkflowState) -> WorkflowState:
    """
    考虑到分析、检索、解释是拿原材料，而组合最终回答是另一件事。

    这个节点认为是：根据 route 把前面结果整理成最后的答案。
    - analysis -> 用 analysis_result.summary
    - retrieval -> 根据最相关证据拼一句规则命中说明
    - explanation -> 用 final_explanation
    - mixed -> 用 build_brief_report() 生成简短汇报
    - unknown -> 给兜底说明
    """
    route = str(state.get("route", "unknown"))

    # -----------------------------
    # 1. analysis 类回答
    # -----------------------------
    if route == "analysis":
        analysis_result = state.get("analysis_result") or {}
        state["answer"] = analysis_result.get("summary", "分析完成。")

        append_trace(state, "compose_answer_node", "已生成 analysis 最终回答。")
        return state

    # -----------------------------
    # 2. retrieval 类回答
    # -----------------------------
    if route == "retrieval":
        retrieval_result = state.get("retrieval_result") or {}
        evidences = retrieval_result.get("evidences", [])
        topic = retrieval_result.get("topic", "通用规则")

        if evidences:
            top_evidence = evidences[0]
            doc_title = top_evidence.get("doc_title", "")
            section_title = top_evidence.get("section_title", "")

            state["answer"] = (
                f"该问题当前主要命中“{topic}”相关规则。"
                f"最相关证据来自《{doc_title}》的《{section_title}》章节。"
            )
        else:
            state["answer"] = "当前未检索到高相关规则片段。"

        append_trace(state, "compose_answer_node", "已生成 retrieval 最终回答。")
        return state

    # -----------------------------
    # 3. explanation 类回答
    # -----------------------------
    if route == "explanation":
        explanation_result = state.get("explanation_result") or {}
        state["answer"] = explanation_result.get("final_explanation", "解释完成。")

        append_trace(state, "compose_answer_node", "已生成 explanation 最终回答。")
        return state

    # -----------------------------
    # 4. mixed 类回答
    # -----------------------------
    if route == "mixed":
        """
        这里是第五周最重要的设计点之一：

        mixed 不走自由 agent，不让模型自己随便决定流程，
        而是走受控流程：
        先 analysis -> 再 retrieval -> 再 report

        因为 mixed 问题往往是高约束的：
        - 先找低价样本
        - 再给规则依据
        - 最后写简短汇报

        这类问题如果全交给自由 agent，
        很容易出现：
        - 自己改写问题
        - 跳过 report tool
        - 用错规则主题
        - 把样本统计漂成平台统计

        所以这里明确走受控 build_brief_report()。
        """
        report = build_brief_report(
            question=str(state.get("question", "")),
            analysis_result=state.get("analysis_result"),
            retrieval_result=state.get("retrieval_result"),
            explanation_result=state.get("explanation_result"),
        )
        state["answer"] = report

        append_trace(state, "compose_answer_node", "已生成 mixed 简短汇报。")
        return state

    # -----------------------------
    # 5. unknown 兜底
    # -----------------------------
    state["answer"] = "当前暂未识别到清晰的问题类型。"
    append_trace(state, "compose_answer_node", "已生成 unknown 兜底回答。")
    return state


# 人工复核节点
def human_review_node(
        state: WorkflowState,
) -> WorkflowState:
    """
    考虑到我的项目是带审核主题的，而该类天然需要人工确认、复核口径、最终判断。
    当前策略：
    - mixed：统一给一条业务化人工复核建议。
    - explanation：如果 explanation_result 没给 review_suggestion，就补一条通用建议
    - 其他类型：保持现状
    """
    route = str(state.get("route", ""))

    if route == "mixed":
        state["review_suggestion"] = (
            "建议业务人员结合异常样本、规则依据和平台口径继续人工复核。"
        )

    elif route == "explanation" and not state.get("review_suggestion"):
        state["review_suggestion"] = (
            "建议对该异常样本继续做人工复核，确认价格口径与规格口径是否一致。"
        )

    else:
        # 其他情况不强行补建议，保持原样
        state["review_suggestion"] = state.get("review_suggestion")

    append_trace(state, "human_review_node", "已保留人工复核节点。")
    return state


# 工作流主入口
def run_workflow(question: str, top_k: int = 3, mode: str = 'baseline') -> WorkflowState:
    """
    负责：
    1.初始化状态
    2.先做路由
    3.根据 route 走不同节点
    4.最后组成答案
    5.留出 human review 节点

    当前链路设计如下：
    1.analysis（route -> analysis -> compose -> human_review）
    2.retrieval（route -> retrieval -> compose -> human_review）
    3.explanation（route -> explanation -> compose -> human_review）
    4.mixed（route -> analysis -> retrieval -> compose -> human_review）
    mixed 仍然是受控流程，不交给自由 agent 猜。
    """
    # 1.初始化一份结构完整的空状态
    state: WorkflowState = {
        'question': question,
        'top_k': top_k,
        'mode': mode,

        # 字段先给空值，后面由对应节点逐步展开
        'analysis_result': None,
        "retrieval_result": None,
        "explanation_result": None,
        "review_suggestion": None,

        # trace 从空列表开始
        'trace': [],
    }

    # 2.第一步先做问题路由
    state = route_query_node(state)
    route = str(state.get('route', 'unknown'))

    # 3.根据 route 决定走哪条节点链
    if route == 'analysis':
        state = run_analysis_node(state)
    elif route == 'retrieval':
        state = run_retrieval_node(state)
    elif route == 'explanation':
        state = run_explanation_node(state)
    elif route == 'mixed':
        # mixed 先分析事实，然后找依据
        state = run_analysis_node(state)
        state = run_retrieval_node(state)

    # unknown 当前不走工具节点，下面的 compose 会给兜底答案
    # 4.统一生成最终答案
    state = compose_answer_node(state)

    # 5.最后人工复核收尾
    state = human_review_node(state)
    return state


if __name__ == "__main__":
    """
    本地调试入口。
    """
    demo_question = "先找出低价商品，再按规则给我写一段简短汇报。"

    result = run_workflow(
        question=demo_question,
        top_k=3,
        mode="baseline",
    )

    print("route =", result.get("route"))
    print("answer =", result.get("answer"))
    print("review_suggestion =", result.get("review_suggestion"))
    print("trace =")
    for item in result.get("trace", []):
        print(item)
