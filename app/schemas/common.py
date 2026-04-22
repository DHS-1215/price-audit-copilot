# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/21 12:19
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Literal
from pydantic import BaseModel, Field

RouteType = Literal[
    "analysis",
    "retrieval",
    "explanation",
    "mixed",
    "unknown",
]


class ToolTraceItem(BaseModel):
    step: int = Field(..., description="步骤序号")
    tool_name: str = Field(..., description="工具名")
    status: str = Field(..., description="执行状态，如 success / failed")
    note: str = Field(default="", description="简短说明")