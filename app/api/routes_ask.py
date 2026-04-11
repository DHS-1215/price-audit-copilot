# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/09 11:49
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from app.tools.report_tools import build_brief_report
from app.tools.log_tools import append_ask_log, build_ask_log_record

# 1. 导入已有能力
# 第一周已有：通用模型问答（作为兜底用）
from app.core.llm_ollama import ask_llm

# 第四周扩过的 schema
from app.core.schemas import AskRequest, AskResponse, ToolTraceItem

# 第二周已有：分析相关函数
from app.tools.analysis_tools import (
    count_low_price_by_platform,
    get_spec_risk_items,
    get_suspected_low_price_items,
    load_csv,
    max_price_gap_by_brand,
)

# 第三周已有：解释单条异常样本
from app.tools.explanation_tools import explain_anomaly_row

# 第三周已有：规则检索工具
from app.tools.retrieval_tools import build_rule_search_summary, search_rules

# 2. 创建路由对象
router = APIRouter(prefix="", tags=["ask"])

# -------------------------
# 3. 路径常量
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 第二周产出的异常明细文件路径
# 第四周很多数据分析、解释都要基于它
ANALYZED_CSV_PATH = PROJECT_ROOT / "data" / "异常明细.csv"


# 4. 小工具函数
def safe_text(value: Any) -> str:
    """
    把任意值尽量稳妥地转成字符串。

    为什么这里也要单独写一份？
    因为 routes_ask.py 作为入口层，最好不要强耦合依赖别的模块内部小函数。
    入口层自己有一些轻量小工具，会更稳。
    """
    if value is None:
        return ""
    return str(value)


def normalize_text(text: str) -> str:
    """
    对文本做最基础标准化：
    - 先转字符串
    - 去掉首尾空白
    - 转成小写

    作用：
    方便后面做关键词路由判断，减少大小写和空格干扰。
    """
    return safe_text(text).strip().lower()


def build_trace_item(step: int, tool_name: str, status: str, note: str) -> ToolTraceItem:
    """
    构造一条 trace 记录。

    trace 的作用：
    - 告诉我们这个问题走了哪些步骤
    - 每一步调了什么工具
    - 工具是否成功
    - 返回了什么简短说明

    这样后面调试时，不会只看到最后答案，却不知道中间发生了什么。
    """
    return ToolTraceItem(
        step=step,
        tool_name=tool_name,
        status=status,
        note=note,
    )


# 5. 加载第二周结果层文件
def load_analyzed_df() -> pd.DataFrame:
    """
    读取第二周已经产出的“异常明细.csv”。

    为什么第四周很多能力都从这里读？
    因为：
    - analysis 问题靠它做统计
    - explanation 问题靠它找具体异常样本
    - mixed 问题通常也要先查这里的事实结果

    这里顺手做两层保护：
    1. 文件不存在就报错
    2. 关键列缺失也报错
    """
    if not ANALYZED_CSV_PATH.exists():
        raise FileNotFoundError(
            f"未找到异常结果文件：{ANALYZED_CSV_PATH}，请先运行第二周分析流程生成“异常明细.csv”。"
        )

    # 这里直接复用 analysis_tools.py 里的 load_csv，兼容中文编码
    df = load_csv(ANALYZED_CSV_PATH)

    # 第四周统一入口最少依赖这些字段
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


# 6. 时间过滤：支持“近7天”这类问法
def apply_time_filter_if_needed(df: pd.DataFrame, question: str) -> pd.DataFrame:
    """
    如果用户问题里提到了“近7天 / 最近7天 / 7天内”，
    那就尝试按日期列过滤数据。

    这里先做一个够用版本，不追求太复杂：
    - 只识别近 7 天相关问法
    - 自动找日期列
    - 以数据里最大日期作为“当前参考日期”

    这样做的好处是：
    即使你本地样本不是今天的数据，也仍然可以基于样本内部日期做演示。
    """
    question = normalize_text(question)

    # 如果问题里没有“近7天”相关表达，直接原样返回
    if "近7天" not in question and "最近7天" not in question and "7天内" not in question:
        return df

    # 尝试寻找日期列
    date_col = None
    for candidate in ["干净日期", "日期", "date"]:
        if candidate in df.columns:
            date_col = candidate
            break

    # 没找到日期列，就只能放弃过滤，直接返回原表
    if date_col is None:
        return df

    copied = df.copy()
    copied[date_col] = pd.to_datetime(copied[date_col], errors="coerce")

    # 用样本中最大的日期作为“最近”
    max_date = copied[date_col].max()

    if pd.isna(max_date):
        return df

    # 近7天：最大日期往前推6天，加上当天一共7天
    threshold = max_date - pd.Timedelta(days=6)
    return copied[copied[date_col] >= threshold].copy()


# 7. 路由判断：识别问题属于哪一类
def detect_route(question: str) -> str:
    """
    根据用户问题，做一个“规则式”的轻量路由。

    这里先不用复杂 LLM router，原因很现实：
    第四周第一版目标是先把链路打通，不是先追求非常智能。

    当前支持五类：
    - analysis：数据分析类
    - retrieval：规则检索类
    - explanation：单条异常解释类
    - mixed：混合类（先分析，再检索/总结）
    - unknown：暂时分不清，走通用模型兜底
    """
    q = normalize_text(question)

    # 数据分析类关键词
    analysis_keywords = [
        "多少", "最多", "最少", "统计", "数量", "占比", "平台", "品牌", "近7天", "最近7天", "7天内"
    ]

    # 规则检索类关键词
    retrieval_keywords = [
        "规则", "依据", "怎么处理", "如何处理", "复核", "定义", "什么意思", "口径"
    ]

    # 解释类关键词
    explanation_keywords = [
        "为什么",
        "高风险",
        "被判",
        "判成",
        "为什么这个商品",
        "为什么该商品",
    ]

    # 混合类关键词
    mixed_keywords = [
        "先", "再", "然后", "并结合", "汇报", "总结", "写一段"
    ]

    has_analysis = any(keyword in q for keyword in analysis_keywords)
    has_retrieval = any(keyword in q for keyword in retrieval_keywords)
    has_explanation = any(keyword in q for keyword in explanation_keywords)
    has_mixed = any(keyword in q for keyword in mixed_keywords)

    if has_mixed and (has_analysis or has_retrieval or has_explanation):
        return "mixed"

    # 先判 analysis
    # 因为“近7天 / 哪个 / 最多 / 数量 / 统计 / 平台 / 品牌”这类问题，
    # 本质上都是数据分析，不应该被“异常”这种泛词抢走。
    if has_analysis:
        return "analysis"

    # retrieval 一般是规则问法，而且没有明显统计倾向时再走
    if has_retrieval and not has_analysis:
        return "retrieval"

    # explanation 放后面
    if has_explanation:
        return "explanation"

    # 分不清就给 unknown，后面走 ask_llm 兜底
    return "unknown"


# 8. analysis 类问题处理
def analyze_price_data(question: str) -> dict[str, Any]:
    """
    根据用户问题，调用第二周已有的分析函数。

    这一层不是重新做分析逻辑，
    而是把“自然语言问题”映射到已有分析函数上。

    当前先支持几类典型问法：
    1. 哪个平台异常低价最多
    2. 哪个品牌跨平台价差最大
    3. 低价商品列表
    4. 规格风险样本列表
    5. 如果都不匹配，则返回总览统计
    """
    df = load_analyzed_df()
    filtered_df = apply_time_filter_if_needed(df, question)
    q = normalize_text(question)

    # 场景 1：近7天哪个平台异常低价最多？
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

    # 场景 2：哪个品牌跨平台价差最大？
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

    # 场景 3：低价商品 / 低价样本列表
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

    # 场景 4：规格风险样本
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

    # 场景 5：都不精确命中时，返回总览
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


# 9. explanation 类问题：先挑一条最相关样本

def score_row_for_question(row: pd.Series, question: str) -> int:
    """
    给一条异常样本和当前问题打一个“简单匹配分”。

    为什么要做这个？
    因为 explanation_tools.explain_anomaly_row() 需要传一条具体样本进去。
    但用户问“为什么这个商品会被判成高风险？”时，
    routes_ask 并不知道“这个商品”究竟是哪条。

    所以这里先做一个够用版：
    - 看问题里有没有提到标题 / 品牌 / 规格 / 平台
    - 看问题里更偏低价 / 跨平台 / 规格风险哪一类
    - 给更匹配的异常样本更高分
    """
    q = normalize_text(question)
    score = 0

    # 如果问题里提到了标题、品牌、规格、平台等信息，命中就加分
    for field in ["干净标题", "标准化品牌", "规范化规格", "干净平台"]:
        value = normalize_text(row.get(field))
        if value and value in q:
            score += 3

    # 问题里带“低价”，且该行确实是低价异常，加分
    if "低价" in q and bool(row.get("是否疑似异常低价", False)):
        score += 2

    # 问题里带“跨平台/价差”，且该行确实是跨平台异常，加分
    if ("跨平台" in q or "价差" in q) and bool(row.get("是否跨平台价差异常", False)):
        score += 2

    # 问题里带“规格”，且该行确实是规格风险，加分
    if "规格" in q and bool(row.get("是否规格识别风险", False)):
        score += 2

    # 问题里带“高风险/异常”，且该行本身有任一异常，也给一点基础分
    if ("高风险" in q or "异常" in q) and bool(row.get("是否存在任一异常", False)):
        score += 1

    return score


def select_best_matching_row(df: pd.DataFrame, question: str) -> dict[str, Any]:
    """
    从异常结果表里挑出“最适合拿来解释”的那一条样本。

    流程是：
    1. 先只保留异常样本
    2. 对每条样本打分
    3. 分数最高的作为候选
    4. 如果分数都不高，就按问题类型兜底挑一条
       - 提到低价 -> 挑一条低价异常
       - 提到跨平台/价差 -> 挑一条跨平台异常
       - 提到规格 -> 挑一条规格风险
       - 都没有 -> 返回第一条异常样本
    """
    anomaly_df = df[df["是否存在任一异常"] == True].copy()

    if anomaly_df.empty:
        raise ValueError("当前异常结果文件中没有可解释的异常样本。")

    scored_rows: list[tuple[int, int]] = []

    for idx, row in anomaly_df.iterrows():
        scored_rows.append((score_row_for_question(row, question), idx))

    scored_rows.sort(key=lambda x: x[0], reverse=True)
    best_score, best_idx = scored_rows[0]

    # 如果所有候选都几乎不匹配，就按异常类型粗兜底
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


def run_explanation(question: str, top_k: int) -> dict[str, Any]:
    """
    explanation 类问题的真正执行入口。

    它做的事情是：
    1. 先读异常结果表
    2. 选一条最相关异常样本
    3. 把这条样本交给 explain_anomaly_row()
       让第三周已经写好的解释链去完成：
       - 事实解释
       - 规则摘要
       - 复核建议
       - 最终解释
    """
    df = load_analyzed_df()
    row = select_best_matching_row(df, question)
    return explain_anomaly_row(row=row, user_question=question, top_k=top_k)


# 10. 对外主入口：/ask
@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """
    第四周统一问答入口。

    核心流程：
    1. 读取问题
    2. detect_route() 识别问题类型
    3. 根据类型调用不同工具
    4. 统一返回 AskResponse

    当前支持：
    - analysis
    - retrieval
    - explanation
    - mixed
    - unknown（兜底走通用模型）
    """
    trace: list[ToolTraceItem] = []
    tools_used: list[str] = []

    try:
        question = req.question.strip()

        # 防止空问题
        if not question:
            raise HTTPException(status_code=400, detail="question 不能为空。")

        # 第一步：先路由
        route = detect_route(question)
        trace.append(build_trace_item(1, "route_query", "success", f"路由结果：{route}"))

        # analysis：数据分析类问题
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

            response = AskResponse(
                route="analysis",
                answer=analysis_result.get("summary", "分析完成。"),
                tools_used=tools_used,
                analysis_result=analysis_result,
                retrieval_result=None,
                explanation_result=None,
                trace=trace if req.include_trace else [],
            )

            log_record = build_ask_log_record(
                question=question,
                route=response.route,
                tools_used=response.tools_used,
                answer=response.answer,
                analysis_result=response.analysis_result,
                retrieval_result=response.retrieval_result,
                explanation_result=response.explanation_result,
                trace=trace,
            )
            append_ask_log(log_record)

            return response

        # retrieval：规则检索类问题
        if route == "retrieval":
            tools_used.append("retrieval_tools")

            retrieval_result = search_rules(
                query=question,
                top_k=req.top_k,
            )
            summary = build_rule_search_summary(retrieval_result)

            trace.append(
                build_trace_item(
                    2,
                    "retrieval_tools",
                    "success",
                    summary,
                )
            )

            response = AskResponse(
                route="retrieval",
                answer=summary,
                tools_used=tools_used,
                analysis_result=None,
                retrieval_result=retrieval_result,
                explanation_result=None,
                trace=trace if req.include_trace else [],
            )

            log_record = build_ask_log_record(
                question=question,
                route=response.route,
                tools_used=response.tools_used,
                answer=response.answer,
                analysis_result=response.analysis_result,
                retrieval_result=response.retrieval_result,
                explanation_result=response.explanation_result,
                trace=trace,
            )
            append_ask_log(log_record)

            return response

        # explanation：单条异常解释类问题
        if route == "explanation":
            tools_used.append("explanation_tools")

            explanation_result = run_explanation(
                question=question,
                top_k=req.top_k,
            )

            trace.append(
                build_trace_item(
                    2,
                    "explanation_tools",
                    "success",
                    safe_text(explanation_result.get("rule_summary")),
                )
            )

            response = AskResponse(
                route="explanation",
                answer=explanation_result.get("final_explanation", "解释完成。"),
                tools_used=tools_used,
                analysis_result=None,
                retrieval_result=explanation_result.get("rule_search"),
                explanation_result=explanation_result,
                trace=trace if req.include_trace else [],
            )

            log_record = build_ask_log_record(
                question=question,
                route=response.route,
                tools_used=response.tools_used,
                answer=response.answer,
                analysis_result=response.analysis_result,
                retrieval_result=response.retrieval_result,
                explanation_result=response.explanation_result,
                trace=trace,
            )
            append_ask_log(log_record)

            return response

        # mixed：混合类问题
        if route == "mixed":
            tools_used.extend(["analysis_tools", "retrieval_tools", "report_tools"])

            analysis_result = analyze_price_data(question)
            trace.append(
                build_trace_item(
                    2,
                    "analysis_tools",
                    "success",
                    analysis_result.get("summary", ""),
                )
            )

            retrieval_result = search_rules(
                query=question,
                top_k=req.top_k,
            )
            retrieval_summary = build_rule_search_summary(retrieval_result)
            trace.append(
                build_trace_item(
                    3,
                    "retrieval_tools",
                    "success",
                    retrieval_summary,
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

            response = AskResponse(
                route="mixed",
                answer=final_answer,
                tools_used=tools_used,
                analysis_result=analysis_result,
                retrieval_result=retrieval_result,
                explanation_result=None,
                trace=trace if req.include_trace else [],
            )

            log_record = build_ask_log_record(
                question=question,
                route=response.route,
                tools_used=response.tools_used,
                answer=response.answer,
                analysis_result=response.analysis_result,
                retrieval_result=response.retrieval_result,
                explanation_result=response.explanation_result,
                trace=trace,
            )
            append_ask_log(log_record)

            return response

        # unknown：暂时无法准确识别类型，走通用模型兜底
        tools_used.append("ask_llm")
        answer = ask_llm(question)

        trace.append(
            build_trace_item(
                2,
                "ask_llm",
                "success",
                "未命中明确路由，已走通用模型回答。",
            )
        )

        response = AskResponse(
            route="unknown",
            answer=answer,
            tools_used=tools_used,
            analysis_result=None,
            retrieval_result=None,
            explanation_result=None,
            trace=trace if req.include_trace else [],
        )

        log_record = build_ask_log_record(
            question=question,
            route=response.route,
            tools_used=response.tools_used,
            answer=response.answer,
            analysis_result=response.analysis_result,
            retrieval_result=response.retrieval_result,
            explanation_result=response.explanation_result,
            trace=trace,
        )
        append_ask_log(log_record)

        return response

    except HTTPException:
        # HTTPException 直接抛回去，不做二次包裹
        raise

    except Exception as e:
        # 其他异常统一塞进 trace，方便调试
        trace.append(
            build_trace_item(
                len(trace) + 1,
                "ask_pipeline",
                "failed",
                str(e),
            )
        )
        raise HTTPException(status_code=500, detail=str(e))
