# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/11 19:09
IDE       :PyCharm
作者      :董宏升

6号窗口：/ask 正式主链编排器

职责：
- 负责 /ask 主链的受控编排
- 负责 route 分类
- 负责 analysis / retrieval / explanation / mixed / unknown 的流程调度
- 不负责 LangChain Agent
- 不负责重新判定异常规则
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException

from app.schemas.ask import AskRequest, AskResponse
from app.schemas.common import ToolTraceItem

from app.llm.ollama_client import ask_llm

from app.tools.analysis_tools import (
    count_low_price_by_platform,
    get_spec_risk_items,
    get_suspected_low_price_items,
    load_csv,
    max_price_gap_by_brand,
)
from app.tools.explanation_tools import explain_anomaly_row
from app.rag.retrieval_service import search_rules_simple
from app.rag.rule_explanation_service import explain_audit_result_simple
from app.rag.schemas import RetrievalMode, RetrievalResponse, ExplanationSchema
from app.tools.report_tools import build_brief_report
from app.tools.log_tools import append_ask_log, build_ask_log_record

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANALYZED_CSV_CANDIDATES = [
    PROJECT_ROOT / "data" / "processed" / "audit_results_preview.csv",
    PROJECT_ROOT / "data" / "audit_results_preview.csv",
]


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def normalize_text(text: Any) -> str:
    return safe_text(text).strip().lower()


def build_trace_item(step: int, tool_name: str, status: str, note: str) -> ToolTraceItem:
    return ToolTraceItem(
        step=step,
        tool_name=tool_name,
        status=status,
        note=note,
    )


def resolve_analyzed_csv_path() -> Path:
    for path in ANALYZED_CSV_CANDIDATES:
        if path.exists():
            return path

    # 返回首选路径，方便报错信息明确
    return ANALYZED_CSV_CANDIDATES[0]


def load_analyzed_df() -> pd.DataFrame:
    csv_path = resolve_analyzed_csv_path()

    if not csv_path.exists():
        raise FileNotFoundError(
            f"未找到异常结果文件：{csv_path}。"
            f"请确认 data/processed/audit_results_preview.csv 是否存在。"
        )

    df = load_csv(csv_path)

    required_cols = [
        "是否疑似异常低价",
        "是否跨平台价差异常",
        "是否规格识别风险",
        "是否存在任一异常",
        "异常原因",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"异常结果文件缺少必要列：{missing_cols}")

    return df


def apply_time_filter_if_needed(df: pd.DataFrame, question: str) -> pd.DataFrame:
    q = normalize_text(question)
    time_keywords = [
        "近7天", "最近7天", "7天内",
        "近七天", "最近七天", "七天内",
        "近一周", "最近一周",
    ]

    if not any(keyword in q for keyword in time_keywords):
        return df

    date_col = None
    for candidate in ["干净日期", "日期", "date"]:
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is None:
        return df

    copied = df.copy()
    copied[date_col] = pd.to_datetime(copied[date_col], errors="coerce")

    max_date = copied[date_col].max()
    if pd.isna(max_date):
        return df

    threshold = max_date - pd.Timedelta(days=6)
    return copied[copied[date_col] >= threshold].copy()


def detect_route(question: str) -> tuple[str, str]:
    """
    6号窗口主链 route classifier。

    返回：
    - route
    - route_reason

    当前仍采用规则式分类，优先保证稳定、可控、可解释。
    """
    q = normalize_text(question)

    analysis_keywords = [
        "多少", "最多", "最少", "统计", "数量", "占比",
        "平台", "品牌", "近7天", "最近7天", "7天内",
        "近七天", "最近七天", "近一周", "最近一周",
    ]

    retrieval_keywords = [
        "规则", "依据", "怎么处理", "如何处理", "复核",
        "定义", "什么意思", "口径", "流程", "文档",
    ]

    explanation_keywords = [
        "为什么", "高风险", "被判", "判成", "命中",
        "audit_result_id", "clean_id", "rule_hit",
        "为什么这个商品", "为什么该商品",
    ]

    mixed_keywords = [
        "先", "再", "然后", "并结合", "汇报",
        "总结", "写一段", "报告", "简短说明",
    ]

    has_analysis = any(keyword in q for keyword in analysis_keywords)
    has_retrieval = any(keyword in q for keyword in retrieval_keywords)
    has_explanation = any(keyword in q for keyword in explanation_keywords)
    has_mixed = any(keyword in q for keyword in mixed_keywords)

    if has_mixed and (has_analysis or has_retrieval or has_explanation):
        return "mixed", "命中混合编排关键词，同时包含分析/检索/解释意图。"

    if has_explanation:
        return "explanation", "命中异常解释类关键词，需要解释已有异常结果。"

    if has_analysis:
        return "analysis", "命中统计分析类关键词，需要分析异常结果数据。"

    if has_retrieval:
        return "retrieval", "命中规则/依据/流程类关键词，需要检索规则文档。"

    return "unknown", "未命中明确业务路由，进入通用兜底。"


def analyze_price_data(question: str) -> dict[str, Any]:
    df = load_analyzed_df()
    filtered_df = apply_time_filter_if_needed(df, question)
    q = normalize_text(question)

    if ("平台" in q) and ("低价" in q or "异常低价" in q) and ("最多" in q or "数量" in q):
        result_df = count_low_price_by_platform(filtered_df)

        top_platform = None
        if not result_df.empty:
            first_row = result_df.iloc[0]
            top_platform = {
                "platform": first_row.get("干净平台"),
                "count": int(first_row.get("低价数量", 0)),
            }

        return {
            "ok": True,
            "analysis_type": "count_low_price_by_platform",
            "row_count": int(len(filtered_df)),
            "top_platform": top_platform,
            "table": result_df.to_dict(orient="records"),
            "summary": (
                f"共统计 {len(filtered_df)} 条记录。"
                f"异常低价数量最多的平台为 {top_platform['platform']}，共 {top_platform['count']} 条。"
                if top_platform
                else "当前没有统计到异常低价平台结果。"
            ),
        }

    if ("品牌" in q) and ("跨平台" in q or "价差" in q) and ("最大" in q or "最高" in q):
        result_df = max_price_gap_by_brand(filtered_df)

        top_brand = None
        if not result_df.empty:
            first_row = result_df.iloc[0]
            top_brand = {
                "brand": first_row.get("标准化品牌"),
                "spec": first_row.get("规范化规格"),
                "gap_amount": float(first_row.get("价差金额", 0)),
                "gap_ratio": (
                    float(first_row.get("价差比例"))
                    if pd.notna(first_row.get("价差比例"))
                    else None
                ),
            }

        return {
            "ok": True,
            "analysis_type": "max_price_gap_by_brand",
            "row_count": int(len(filtered_df)),
            "top_brand": top_brand,
            "table": result_df.to_dict(orient="records"),
            "summary": (
                f"当前跨平台价差最大的品牌是 {top_brand['brand']}，规格为 {top_brand['spec']}，"
                f"价差金额 {top_brand['gap_amount']:.2f}。"
                if top_brand
                else "当前没有统计到品牌跨平台价差结果。"
            ),
        }

    if "低价商品" in q or "低价样本" in q:
        result_df = get_suspected_low_price_items(filtered_df)
        preview = result_df.head(10)

        return {
            "ok": True,
            "analysis_type": "suspected_low_price_items",
            "row_count": int(len(result_df)),
            "table": preview.to_dict(orient="records"),
            "summary": f"当前共识别出 {len(result_df)} 条疑似异常低价样本，已返回前 {len(preview)} 条。",
        }

    if "规格风险" in q or "规格识别风险" in q:
        result_df = get_spec_risk_items(filtered_df)
        preview = result_df.head(10)

        return {
            "ok": True,
            "analysis_type": "spec_risk_items",
            "row_count": int(len(result_df)),
            "table": preview.to_dict(orient="records"),
            "summary": f"当前共识别出 {len(result_df)} 条规格识别风险样本，已返回前 {len(preview)} 条。",
        }

    anomaly_count = int(filtered_df["是否存在任一异常"].fillna(False).sum())
    low_price_count = int(filtered_df["是否疑似异常低价"].fillna(False).sum())
    cross_platform_count = int(filtered_df["是否跨平台价差异常"].fillna(False).sum())
    spec_risk_count = int(filtered_df["是否规格识别风险"].fillna(False).sum())

    return {
        "ok": True,
        "analysis_type": "overview",
        "row_count": int(len(filtered_df)),
        "summary": (
            f"当前共 {len(filtered_df)} 条记录，"
            f"其中任一异常 {anomaly_count} 条，"
            f"疑似异常低价 {low_price_count} 条，"
            f"跨平台价差异常 {cross_platform_count} 条，"
            f"规格识别风险 {spec_risk_count} 条。"
        ),
        "stats": {
            "anomaly_count": anomaly_count,
            "low_price_count": low_price_count,
            "cross_platform_count": cross_platform_count,
            "spec_risk_count": spec_risk_count,
        },
    }


def score_row_for_question(row: pd.Series, question: str) -> int:
    q = normalize_text(question)
    score = 0

    for field in ["干净标题", "标准化品牌", "规范化规格", "干净平台"]:
        value = normalize_text(row.get(field))
        if value and value in q:
            score += 3

    if "低价" in q and bool(row.get("是否疑似异常低价", False)):
        score += 2

    if ("跨平台" in q or "价差" in q) and bool(row.get("是否跨平台价差异常", False)):
        score += 2

    if "规格" in q and bool(row.get("是否规格识别风险", False)):
        score += 2

    if ("高风险" in q or "异常" in q) and bool(row.get("是否存在任一异常", False)):
        score += 1

    return score


def select_best_matching_row(df: pd.DataFrame, question: str) -> dict[str, Any]:
    anomaly_df = df[df["是否存在任一异常"] == True].copy()

    if anomaly_df.empty:
        raise ValueError("当前异常结果文件中没有可解释的异常样本。")

    scored_rows: list[tuple[int, int]] = []
    for idx, row in anomaly_df.iterrows():
        scored_rows.append((score_row_for_question(row, question), idx))

    scored_rows.sort(key=lambda x: x[0], reverse=True)
    best_score, best_idx = scored_rows[0]

    if best_score <= 0:
        q = normalize_text(question)

        if "低价" in q:
            low_df = anomaly_df[anomaly_df["是否疑似异常低价"] == True]
            if not low_df.empty:
                return low_df.iloc[0].to_dict()

        if "跨平台" in q or "价差" in q:
            gap_df = anomaly_df[anomaly_df["是否跨平台价差异常"] == True]
            if not gap_df.empty:
                return gap_df.iloc[0].to_dict()

        if "规格" in q:
            spec_df = anomaly_df[anomaly_df["是否规格识别风险"] == True]
            if not spec_df.empty:
                return spec_df.iloc[0].to_dict()

        return anomaly_df.iloc[0].to_dict()

    return anomaly_df.loc[best_idx].to_dict()


def run_explanation(question: str, top_k: int, retrieval_mode: str = "baseline") -> dict[str, Any]:
    """
    当前仍保留第四周旧解释链作为第一批结构修复的兼容方案。

    第二批会升级为优先调用：
    app.rag.rule_explanation_service.explain_audit_result_simple
    """
    df = load_analyzed_df()
    row = select_best_matching_row(df, question)
    return explain_anomaly_row(
        row=row,
        user_question=question,
        top_k=top_k,
        retrieval_mode=retrieval_mode,
    )


def select_retrieval_mode(use_vector: bool) -> RetrievalMode:
    """
    6号窗口第二批正式检索模式选择。

    use_vector=True：
        走纯 vector，便于测试语义召回。

    use_vector=False：
        默认走 hybrid，符合 5号窗口交接口径。
    """
    return RetrievalMode.VECTOR if use_vector else RetrievalMode.HYBRID


def model_to_dict(value: Any) -> dict[str, Any]:
    """
    兼容 Pydantic v2 model_dump。
    """
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {"value": value}


def build_retrieval_answer(response: RetrievalResponse) -> str:
    """
    基于 5号窗口 RetrievalResponse 构建 /ask retrieval 回答。
    """
    if not response.results:
        return "当前没有检索到明确相关的规则依据。"

    top = response.results[0]
    doc_title = top.doc_title or "规则文档"
    section_title = top.section_title or "相关章节"

    return (
        f"当前检索模式为 {response.retrieval_mode.value}，共返回 {response.total} 条规则依据。"
        f"最相关依据来自《{doc_title}》的《{section_title}》。"
    )


def build_mixed_retrieval_query(question: str, analysis_result: dict[str, Any] | None) -> str:
    """
    mixed 场景不能直接拿原问题做规则检索。

    原问题通常是：
    “先统计当前异常情况，再结合规则写一段简短汇报”

    这种 query 太宽，会检索到平台字段、价格清洗等通用规则。
    所以这里根据 analysis_result 收紧检索问题。
    """
    if not analysis_result:
        return question

    analysis_type = str(analysis_result.get("analysis_type") or "").strip()
    stats = analysis_result.get("stats") or {}

    if analysis_type == "suspected_low_price_items":
        return "低价异常规则是怎么定义的？低价样本复核时应重点关注什么？"

    if analysis_type == "count_low_price_by_platform":
        return "低价异常规则是怎么定义的？平台低价样本复核时应关注什么？"

    if analysis_type == "max_price_gap_by_brand":
        return "跨平台价差异常是怎么定义的？跨平台价差复核时应关注什么？"

    if analysis_type == "spec_risk_items":
        return "规格识别风险是怎么定义的？标题规格与规格列不一致时应怎么处理？"

    if analysis_type == "overview":
        focus_parts: list[str] = []

        if int(stats.get("low_price_count") or 0) > 0:
            focus_parts.append("低价异常规则")

        if int(stats.get("cross_platform_count") or 0) > 0:
            focus_parts.append("跨平台价差异常规则")

        if int(stats.get("spec_risk_count") or 0) > 0:
            focus_parts.append("规格识别风险规则")

        if focus_parts:
            return "、".join(focus_parts) + "分别是什么？业务人员复核时应关注什么？"

    return question


def run_structured_explanation_if_possible(
        req: AskRequest,
        retrieval_mode: RetrievalMode,
) -> ExplanationSchema | None:
    """
    优先走 5号窗口正式解释链。

    条件：
    1. 有 audit_result_id
    2. 或者有 clean_id + anomaly_type

    没有这些结构化参数时，暂时返回 None，
    由旧 CSV 解释链兜底。
    """
    if req.audit_result_id is not None:
        return explain_audit_result_simple(
            audit_result_id=req.audit_result_id,
            retrieval_mode=retrieval_mode,
            chunk_top_k=min(req.top_k, 5),
            rerank_enabled=False,
        )

    if req.clean_id is not None and req.anomaly_type:
        return explain_audit_result_simple(
            clean_id=req.clean_id,
            anomaly_type=req.anomaly_type,
            retrieval_mode=retrieval_mode,
            chunk_top_k=min(req.top_k, 5),
            rerank_enabled=False,
        )

    return None


def finalize_response(
        req: AskRequest,
        route: str,
        answer: str,
        tools_used: list[str],
        trace: list[ToolTraceItem],
        analysis_result: dict[str, Any] | None = None,
        retrieval_result: dict[str, Any] | None = None,
        explanation_result: dict[str, Any] | None = None,
        route_reason: str | None = None,
        retrieval_mode: str | None = None,
) -> AskResponse:
    response = AskResponse(
        route=route,
        answer=answer,
        tools_used=tools_used,
        route_reason=route_reason,
        retrieval_mode=retrieval_mode,
        analysis_result=analysis_result,
        retrieval_result=retrieval_result,
        explanation_result=explanation_result,
        trace=trace if req.include_trace else [],
    )

    try:
        log_record = build_ask_log_record(
            question=req.question.strip(),
            route=response.route,
            tools_used=response.tools_used,
            answer=response.answer,
            analysis_result=response.analysis_result,
            retrieval_result=response.retrieval_result,
            explanation_result=response.explanation_result,
            trace=trace,
        )
        append_ask_log(log_record)
    except Exception as log_error:
        trace.append(
            build_trace_item(
                len(trace) + 1,
                "ask_log",
                "failed",
                f"问答日志写入失败，但不影响本次回答：{type(log_error).__name__}: {log_error}",
            )
        )
        if req.include_trace:
            response.trace = trace

    return response


def run_ask(req: AskRequest) -> AskResponse:
    """
    /ask 正式主链入口。

    这条链是 6号窗口主链：
    - 不走自由 Agent
    - 不重新判定异常
    - 只做受控路由与工具编排
    """
    trace: list[ToolTraceItem] = []
    tools_used: list[str] = []

    try:
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="question 不能为空。")

        retrieval_mode = select_retrieval_mode(req.use_vector)

        route, route_reason = detect_route(question)
        trace.append(
            build_trace_item(
                1,
                "route_classifier",
                "success",
                f"路由结果：{route}；原因：{route_reason}",
            )
        )

        if route == "analysis":
            tools_used.append("analysis_tools")

            analysis_result = analyze_price_data(question)
            trace.append(
                build_trace_item(
                    2,
                    "analysis_tools",
                    "success",
                    analysis_result.get("summary", ""),
                )
            )

            return finalize_response(
                req=req,
                route="analysis",
                answer=analysis_result.get("summary", "分析完成。"),
                tools_used=tools_used,
                analysis_result=analysis_result,
                retrieval_result=None,
                explanation_result=None,
                trace=trace,
            )

        if route == "retrieval":
            tools_used.append("retrieval_service")

            retrieval_response = search_rules_simple(
                query=question,
                top_k=req.top_k,
                retrieval_mode=retrieval_mode,
                rerank_enabled=False,
            )

            retrieval_result = model_to_dict(retrieval_response)
            answer = build_retrieval_answer(retrieval_response)

            trace.append(
                build_trace_item(
                    2,
                    "retrieval_service",
                    "success",
                    f"{answer}",
                )
            )

            return finalize_response(
                req=req,
                route="retrieval",
                answer=answer,
                tools_used=tools_used,
                analysis_result=None,
                retrieval_result=retrieval_result,
                explanation_result=None,
                trace=trace,
                route_reason=route_reason,
                retrieval_mode=retrieval_mode.value,
            )

        if route == "explanation":
            structured_explanation = run_structured_explanation_if_possible(
                req=req,
                retrieval_mode=retrieval_mode,
            )

            if structured_explanation is not None:
                tools_used.append("rule_explanation_service")

                explanation_result = model_to_dict(structured_explanation)
                answer = structured_explanation.final_summary

                trace.append(
                    build_trace_item(
                        2,
                        "rule_explanation_service",
                        "success",
                        structured_explanation.final_summary,
                    )
                )

                return finalize_response(
                    req=req,
                    route="explanation",
                    answer=answer,
                    tools_used=tools_used,
                    analysis_result=None,
                    retrieval_result=None,
                    explanation_result=explanation_result,
                    trace=trace,
                    route_reason=route_reason,
                    retrieval_mode=retrieval_mode.value,
                )

            # 没有 audit_result_id / clean_id 时，保留旧 CSV 解释链兜底
            tools_used.append("explanation_tools_fallback")

            explanation_result = run_explanation(
                question=question,
                top_k=req.top_k,
                retrieval_mode=retrieval_mode.value,
            )

            trace.append(
                build_trace_item(
                    2,
                    "explanation_tools_fallback",
                    "success",
                    safe_text(explanation_result.get("rule_summary")),
                )
            )

            return finalize_response(
                req=req,
                route="explanation",
                answer=explanation_result.get("final_explanation", "解释完成。"),
                tools_used=tools_used,
                analysis_result=None,
                retrieval_result=explanation_result.get("rule_search"),
                explanation_result=explanation_result,
                trace=trace,
                route_reason=route_reason,
                retrieval_mode=retrieval_mode.value,
            )

        if route == "mixed":
            tools_used.extend(["analysis_tools", "retrieval_service", "report_tools"])

            analysis_result = analyze_price_data(question)
            trace.append(
                build_trace_item(
                    2,
                    "analysis_tools",
                    "success",
                    analysis_result.get("summary", ""),
                )
            )

            retrieval_query = build_mixed_retrieval_query(
                question=question,
                analysis_result=analysis_result,
            )

            retrieval_response = search_rules_simple(
                query=retrieval_query,
                top_k=req.top_k,
                retrieval_mode=retrieval_mode,
                rerank_enabled=False,
            )

            retrieval_result = model_to_dict(retrieval_response)
            retrieval_summary = build_retrieval_answer(retrieval_response)

            trace.append(
                build_trace_item(
                    3,
                    "retrieval_service",
                    "success",
                    f"{retrieval_summary} 检索问题：{retrieval_query}",
                )
            )

            retrieval_result = model_to_dict(retrieval_response)
            retrieval_summary = build_retrieval_answer(retrieval_response)

            trace.append(
                build_trace_item(
                    3,
                    "retrieval_service",
                    "success",
                    f"{retrieval_summary} 当前检索模式：{retrieval_mode.value}",
                )
            )

            final_answer = build_brief_report(
                question=question,
                analysis_result=analysis_result,
                retrieval_result=retrieval_result,
            )
            trace.append(
                build_trace_item(
                    4,
                    "report_tools",
                    "success",
                    "已生成简短汇报。",
                )
            )

            return finalize_response(
                req=req,
                route="mixed",
                answer=final_answer,
                tools_used=tools_used,
                analysis_result=analysis_result,
                retrieval_result=retrieval_result,
                explanation_result=None,
                trace=trace,
                route_reason=route_reason,
                retrieval_mode=retrieval_mode.value,
            )

        tools_used.append("ask_llm")
        answer = ask_llm(question)

        trace.append(
            build_trace_item(
                2,
                "ask_llm",
                "success",
                "未命中明确路由，已走通用模型兜底。",
            )
        )

        return finalize_response(
            req=req,
            route="unknown",
            answer=answer,
            tools_used=tools_used,
            analysis_result=None,
            retrieval_result=None,
            explanation_result=None,
            trace=trace,
        )

    except HTTPException:
        raise

    except Exception as e:
        print("\n" + "=" * 100)
        print("run_ask() 发生未捕获异常，开始打印 traceback：")
        traceback.print_exc()
        print("=" * 100 + "\n")

        trace.append(
            build_trace_item(
                len(trace) + 1,
                "ask_pipeline",
                "failed",
                f"{type(e).__name__}: {e}",
            )
        )

        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
