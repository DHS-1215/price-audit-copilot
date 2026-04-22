# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 13:25
IDE       :PyCharm
作者      :董宏升

把统一响应外壳定死
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import ErrorCodes


class ApiResponse(BaseModel):
    success: bool = Field(description="是否成功")
    code: str = Field(description="业务错误码或成功码")
    message: str = Field(description="响应消息")
    trace_id: str = Field(default="", description="链路追踪ID")
    data: Any = Field(default=None, description="响应数据")


def success_response(data: Any = None, message: str = "success", trace_id: str = "") -> ApiResponse:
    return ApiResponse(
        success=True,
        code=ErrorCodes.OK.code,
        message=message,
        trace_id=trace_id,
        data=data,
    )


def error_response(code: str, message: str, trace_id: str = "", data: Any = None) -> ApiResponse:
    return ApiResponse(
        success=False,
        code=code,
        message=message,
        trace_id=trace_id,
        data=data,
    )
