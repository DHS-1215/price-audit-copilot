# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/11 16:33
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import json
from typing import Any

from langchain.tools import tool

# 直接用我写好的业务能力
from app.api.routes_ask import analyze_price_data, run_explanation
from app.tools.retrieval_tools import search_rules
from app.tools.report_tools import build_brief_report


# 把python对象统一转成字符串，方便 LangChain tool 返回
def _to_json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


# 用于处理数据分析类问题
def analyze_price_data_tool(question: str) -> str:
    """
    例如：
    - 近七天哪个平台异常低价最多
    - 哪个品牌跨平台价差最大
    - 当前低价样本有哪些？
    """
    result = analyze_price_data(question)
    return _to_json_text(result)


@tool
def search_rules_tool(question: str, top_k: int = 3, mode: str = 'baseline') -> str:
    """
    处理规则检索类问题
    """
    result = search_rules(query=question, top_k=top_k, mode=mode)
    return _to_json_text(result)


@tool
def explain_anomaly_tool(question: str, top_k: int = 3, mode: str = 'baseline') -> str:
    """
    用于解释某条异常样本为什么会被判为高风险、低价异常等。
    """
    result = run_explanation(question=question, top_k=top_k, retrieval_mode=mode)
    return _to_json_text(result)


# 给 mixed / 汇总类问题生成更聚焦的规则检索问句
def build_report_rule_query(question: str, analysis_result: dict[str, Any] | None) -> str:
    """
    agent测试中自己很容易把规则检索问句写成：
    “电商价格异常规则”
    这种过于宽泛的问法会导致检索结果发散，甚至查不到高相关规则。
    所以我根据 analysis_result 的类型，主动把规则检索问题收紧到更具体的方向。
    """
    if not analysis_result:
        return question
    analysis_type = str(analysis_result.get('analysis_type') or '').strip()

    if analysis_type == 'suspected_low_price_items':
        return '低价异常规则是怎么定义的？低价样本复核时应重点关注什么？'

    if analysis_type == 'count_low_price_by_platform':
        return '低价异常规则是怎么定义的？平台低价样本复核时应关注什么？'

    if analysis_type == 'max_price_gap_by_brand':
        return '跨平台价差异常是怎么定义的？跨平台价差复核时应关注什么？'

    if analysis_type == 'spec_risk_items':
        return '规格识别风险是怎么定义的？标题不完整或规格缺失时应怎么处理？'

    return question


# 根据前面工具返回结果，生成一段业务汇报
def build_report_tool(question: str, top_k: int = 3, mode: str = "baseline") -> str:
    """
    适用场景：
    - 先找出低价商品，再按规则给我写一段简短汇报
    - 先分析异常，再写总结
    - 请给我一段基于规则和数据结果的业务说明

    这个工具会自行完成：
    1. 数据分析
    2. 规则检索
    3. 汇报生成

    对于包含“先…再… / 汇报 / 总结 / 简短说明”等表达的问题，
    必须优先调用本工具，而不是直接自己写汇报。
    """
    analysis_result = analyze_price_data(question)

    retrieval_query = build_report_rule_query(
        question=question,
        analysis_result=analysis_result,
    )

    retrieval_result = search_rules(
        query=retrieval_query,
        top_k=top_k,
        mode=mode,
    )

    result = build_brief_report(
        question=question,
        analysis_result=analysis_result,
        retrieval_result=retrieval_result,
        explanation_result=None,
    )
    return result


LANGCHAIN_TOOLS = [
    analyze_price_data_tool,
    search_rules_tool,
    explain_anomaly_tool,
    build_report_tool,
]
