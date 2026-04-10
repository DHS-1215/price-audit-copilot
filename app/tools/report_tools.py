# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/10 16:54
IDE       :PyCharm
作者      :董宏升

第四周：汇报生成工具层 report_tools.py

此模块定位：
不是负责“查数据”，也不是负责“检索规则”，
而是把前面已经得到的 analysis_result / retrieval_result / explanation_result
整理成更适合业务阅读的一段简短汇报。

如果屏幕前的你在看这个模块，可以理解成：
    1· analysis_tools 负责找事实
    2. retrieval_tools 负责找规则依据
    3.report_tools 负责把这些东西组织成“像人写的总结”

需求：
    - 先支持 mixed 问题里的简短汇报
    - 先重点覆盖“低价样本 + 规则依据 + 复核建议”这种场景。
    - 后面第五周上前端，或者第六周补日报周报，可以继续扩。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from typing import Any

"""1.小工具"""


def safe_text(value: Any) -> str:
    """
    因为工具层之间尽量少互相依赖内部小函数，
    否则后面文件一多，很容易牵一发而动全身。
    """
    if value is None:
        return ""
    return str(value)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


# 判断当前问题是否带“汇报 / 总结 / 概括”意图。
def has_report_intent(question: str) -> bool:
    """
    先做轻量判断器，不做复杂判断器
    """
    q = safe_text(question).strip()
    keywords = ["汇报", "总结", "概括", "简短汇报", "写一段", "写个说明"]
    return any(keyword in q for keyword in keywords)


"""2. analysis 结果摘要"""


# 把 analysis_result 里的核心信息抽成一句更适合汇报的摘要
def summarize_analysis_result(analysis_result: dict[str, Any]) -> str:
    """
    analysis_result 里已经有 summary，但 report_tools 这里的目标不是简单照抄，而是尽量让后面的最终文本更像业务说明，

    当前优先支持几类：
    - suspected_low_price_items
    - count_low_price_by_platform
    - max_price_gap_by_brand
    - overview
    """
    if not analysis_result:
        return "当前未取得数据分析结果。"

    analysis_type = safe_text(analysis_result.get("analysis_type"))
    row_count = safe_int(analysis_result.get("row_count"), default=0)

    if analysis_type == "suspected_low_price_items":
        return f"当前共识别出 {row_count} 条疑似异常低价样本。"

    if analysis_type == "count_low_price_by_platform":
        top_platform = analysis_result.get("top_platform") or {}
        platform = safe_text(top_platform.get("platform"))
        count = safe_int(top_platform.get("count"), default=0)

        if platform:
            return f"异常低价数量最多的平台为 {platform}，共 {count} 条。"
        return "已完成按平台的异常低价统计。"

    if analysis_type == "max_price_gap_by_brand":
        top_brand = analysis_result.get("top_brand") or {}
        brand = safe_text(top_brand.get("brand"))
        spec = safe_text(top_brand.get("spec"))
        gap_amount = top_brand.get("gap_amount")

        if brand and spec and gap_amount is not None:
            return f"当前跨平台价差最大的品牌为 {brand}，规格为 {spec}。"
        return "已完成按品牌的跨平台价差统计。"

    if analysis_type == "overview":
        return safe_text(analysis_result.get("summary")) or "已完成异常结果总览统计。"

    # 兜底：如果当前 analysis_type 还没专门适配，就退回已有 summary
    return safe_text(analysis_result.get("summary")) or "已完成数据分析。"


"""3. retrieval 结果摘要"""


# 给汇报挑一条“主依据”
def choose_primary_evidence_for_report(retrieval_result: dict[str, Any]) -> dict[str, Any] | None:
    """
    1. 优先选非 FAQ 文档
    2. 如果全是 FAQ，退回第一条

    考虑到 FAQ 更像补充层，主规则文档更适合作为正式汇报里的主要依据来源。

    这个思路和第三周 explanation_tools 里的 choose_primary_evidence 很接近，
    只是这里不直接跨文件调用，保持 report_tools 自己的边界清晰。
    """
    evidences = retrieval_result.get("evidences", []) or []
    if not evidences:
        return None

    for evidence in evidences:
        if safe_text(evidence.get("doc_id")) != "faq":
            return evidence

    return evidences[0]


# 把规则检索结果整理成一段适合汇报使用的“依据说明”
def summarize_retrieval_result(retrieval_result: dict[str, Any]) -> str:
    """
    和 retrieval_tools.py 里的 build_rule_search_summary() 不同，这里更偏“汇报口吻”，而不是“接口工具摘要”
    """
    if not retrieval_result:
        return "当前未取得规则依据。"

    ok = bool(retrieval_result.get("ok", False))
    if not ok:
        return safe_text(retrieval_result.get("message")) or "规则检索失败。"

    topic = safe_text(retrieval_result.get("topic")).strip() or "通用规则"
    primary = choose_primary_evidence_for_report(retrieval_result)

    if primary is None:
        return f"当前暂未检索到高相关的“{topic}”规则依据。"

    doc_title = safe_text(primary.get("doc_title")).strip()
    section_title = safe_text(primary.get("section_title")).strip()

    if doc_title and section_title:
        return f"规则依据方面，当前主要命中“{topic}”相关内容，主要参考《{doc_title}》的《{section_title}》章节。"

    return f"规则依据方面，当前主要命中“{topic}”相关内容。"


"""4. 复核建议"""


# 生成一条简短复核建议
def build_review_advice(question: str, analysis_result: dict[str, Any], retrieval_result: dict[str, Any]) -> str:
    """
    当前先用规则型建议，后面如果要做日报 or 周报，可以继续细化。
    """
    analysis_type = safe_text(analysis_result.get("analysis_type"))
    topic = safe_text(retrieval_result.get("topic"))

    # 如果问题本身就是低价样本 + 规则汇报
    if analysis_type == "suspected_low_price_items" or "低价" in topic:
        return "建议后续优先复核低价样本的价格口径、活动口径及规格口径，确认是否存在券后价、补贴价或组合装等特殊情况。"

    if "跨平台" in topic or "价差" in topic:
        return "建议进一步核对不同平台的价格采集口径、活动机制及规格映射是否一致。"

    if "规格" in topic:
        return "建议重点复核标题规格提示、规格列填写及规范化规格是否一致。"

    if has_report_intent(question):
        return "建议结合规则依据与异常样本明细继续做人工复核。"

    return ""


"""5. 对外主入口：生成简短汇报"""


# 生成一段简短汇报
def build_brief_report(
        question: str,
        analysis_result: dict[str, Any] | None = None,
        retrieval_result: dict[str, Any] | None = None,
        explanation_result: dict[str, Any] | None = None,
) -> str:
    """
    当前优先支持 mixed 场景：
    - 先拿 analysis_result 讲事实
    - 再拿 retrieval_result 讲依据
    - 最后补一句复核建议

    explanation_result 这里先预留参数，后面如果想让“解释型问题”也生成书面化说明，就能直接扩。
    """

    parts: list[str] = []

    # 1）数据事实
    if analysis_result:
        parts.append(summarize_analysis_result(analysis_result))

    # 2）规则依据
    if retrieval_result:
        parts.append(summarize_retrieval_result(retrieval_result))

    # 3）复核建议
    advice = build_review_advice(
        question=question,
        analysis_result=analysis_result or {},
        retrieval_result=retrieval_result or {},
    )
    if advice:
        parts.append(advice)

    # 4）如果 analysis / retrieval 都没有，但 explanation 有值，也给个兜底
    if not parts and explanation_result:
        final_explanation = safe_text(explanation_result.get("final_explanation")).strip()
        if final_explanation:
            parts.append(final_explanation)

    # 5）都没有时，给个兜底文本
    if not parts:
        return "当前暂无足够信息生成汇报。"

    return " ".join(parts).strip()


"""本地调试"""
if __name__ == "__main__":
    demo_analysis_result = {
        "ok": True,
        "analysis_type": "suspected_low_price_items",
        "row_count": 10,
        "summary": "当前共识别出 10 条疑似异常低价样本，已返回前 10 条。",
    }

    demo_retrieval_result = {
        "ok": True,
        "topic": "低价异常规则",
        "evidences": [
            {
                "doc_id": "low_price_detection_rules",
                "doc_title": "疑似异常低价判定规则说明",
                "section_title": "1. 文档目的",
            }
        ],
    }

    report = build_brief_report(
        question="先找出低价商品，再按规则给我写一段简短汇报。",
        analysis_result=demo_analysis_result,
        retrieval_result=demo_retrieval_result,
    )

    print(report)
