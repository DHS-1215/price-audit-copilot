# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:26
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import RouteType, ToolTraceItem

LogStatus = Literal[
    "success",
    "failed",
    "partial_success",
]


class AskLogBase(BaseModel):
    trace_id: str = Field(..., description="全链路 trace_id")
    question: str = Field(..., description="用户问题")
    route: RouteType = Field(..., description="路由类型")
    answer_text: str | None = Field(default=None, description="最终回答")

    tools_used_json: list[str] | None = Field(
        default=None,
        description="实际调用工具列表",
    )
    analysis_result_json: dict[str, Any] | None = Field(
        default=None,
        description="分析结果",
    )
    retrieval_result_json: dict[str, Any] | None = Field(
        default=None,
        description="检索结果",
    )
    explanation_result_json: dict[str, Any] | None = Field(
        default=None,
        description="解释结果",
    )
    trace_json: list[dict[str, Any]] | list[ToolTraceItem] | None = Field(
        default=None,
        description="工具调用链路",
    )
    subject_audit_result_id: int | None = Field(
        default=None,
        description="关联的审核结果ID",
    )
    status: LogStatus = Field(default="success", description="请求状态")


class AskLogCreate(AskLogBase):
    pass


class AskLogRead(AskLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")


class AskLogQuery(BaseModel):
    trace_id: str | None = Field(default=None, description="按 trace_id 查询")
    route: RouteType | None = Field(default=None, description="按路由类型查询")
    status: LogStatus | None = Field(default=None, description="按请求状态查询")
    subject_audit_result_id: int | None = Field(default=None, description="按审核结果查询")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class ModelCallLogBase(BaseModel):
    ask_log_id: int = Field(..., description="对应 ask_log.id")
    trace_id: str = Field(..., description="trace_id")
    call_stage: str = Field(..., description="调用阶段")
    model_vendor: str | None = Field(default=None, description="模型提供方")
    model_name: str | None = Field(default=None, description="模型名称")
    request_payload_json: dict[str, Any] | None = Field(
        default=None,
        description="请求载荷",
    )
    response_payload_json: dict[str, Any] | None = Field(
        default=None,
        description="响应载荷",
    )
    prompt_tokens: int | None = Field(default=None, ge=0, description="输入 tokens")
    completion_tokens: int | None = Field(default=None, ge=0, description="输出 tokens")
    latency_ms: int | None = Field(default=None, ge=0, description="耗时毫秒")
    error_message: str | None = Field(default=None, description="错误信息")


class ModelCallLogCreate(ModelCallLogBase):
    pass


class ModelCallLogRead(ModelCallLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")


class ModelCallLogQuery(BaseModel):
    ask_log_id: int | None = Field(default=None, description="按 ask_log_id 查询")
    trace_id: str | None = Field(default=None, description="按 trace_id 查询")
    call_stage: str | None = Field(default=None, description="按调用阶段查询")
    model_name: str | None = Field(default=None, description="按模型名查询")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
