# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/21 12:19
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Optional, Any
from pydantic import BaseModel, Field

from app.schemas.common import RouteType, ToolTraceItem


class AskRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    top_k: int = Field(default=3, ge=1, le=10, description="规则检索返回数量")
    use_vector: bool = Field(default=False, description="是否使用纯向量检索；默认 false 时主链使用 hybrid")
    include_trace: bool = Field(default=True, description="是否返回工具调用链路")

    # 6号窗口：解释型问题的正式入口参数
    audit_result_id: Optional[int] = Field(default=None, description="异常结果ID，解释类问题优先使用")
    clean_id: Optional[int] = Field(default=None, description="清洗后商品ID，可用于解释类问题")
    anomaly_type: Optional[str] = Field(
        default=None,
        description="异常类型，如 low_price / cross_platform_gap / spec_risk",
    )


class AskResponse(BaseModel):
    route: RouteType = Field(..., description="问题路由类型")
    answer: str = Field(..., description="最终回答")
    tools_used: list[str] = Field(default_factory=list, description="实际调用的工具列表")

    # 6号窗口：便于调试、验收、面试讲解
    route_reason: Optional[str] = Field(default=None, description="路由判断原因")
    retrieval_mode: Optional[str] = Field(default=None, description="本次规则检索模式")

    analysis_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="数据分析结果",
    )
    retrieval_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="规则检索结果",
    )
    explanation_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="异常解释结果",
    )
    trace: list[ToolTraceItem] = Field(
        default_factory=list,
        description="工具调用链路",
    )