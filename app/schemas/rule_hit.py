# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 21:24
IDE       :PyCharm
作者      :董宏升
规则命中明细 schema
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RuleHitAnomalyType = Literal[
    "low_price",
    "cross_platform_gap",
    "spec_risk",
]


class RuleHitBase(BaseModel):
    audit_result_id: int = Field(..., description="对应 audit_result.id")
    clean_id: int = Field(..., description="对应 product_clean.id")
    anomaly_type: RuleHitAnomalyType = Field(..., description="异常类型")

    rule_code: str = Field(..., description="规则编码")
    rule_version: str = Field(..., description="规则版本")
    rule_definition_id: int | None = Field(default=None, description="规则定义ID")

    is_hit: bool = Field(..., description="该条规则是否命中")

    input_snapshot_json: dict[str, Any] | None = Field(
        default=None,
        description="判定输入快照",
    )
    computed_value_json: dict[str, Any] | None = Field(
        default=None,
        description="计算结果快照",
    )
    threshold_snapshot_json: dict[str, Any] | None = Field(
        default=None,
        description="阈值配置快照",
    )

    hit_message: str | None = Field(default=None, description="命中说明")
    hit_order: int = Field(default=1, ge=1, description="命中顺序")


class RuleHitCreate(RuleHitBase):
    pass


class RuleHitUpdate(BaseModel):
    is_hit: bool | None = Field(default=None, description="该条规则是否命中")
    input_snapshot_json: dict[str, Any] | None = Field(default=None, description="判定输入快照")
    computed_value_json: dict[str, Any] | None = Field(default=None, description="计算结果快照")
    threshold_snapshot_json: dict[str, Any] | None = Field(default=None, description="阈值配置快照")
    hit_message: str | None = Field(default=None, description="命中说明")
    hit_order: int | None = Field(default=None, ge=1, description="命中顺序")


class RuleHitRead(RuleHitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class RuleHitListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    audit_result_id: int = Field(..., description="对应 audit_result.id")
    clean_id: int = Field(..., description="对应 product_clean.id")
    anomaly_type: RuleHitAnomalyType = Field(..., description="异常类型")
    rule_code: str = Field(..., description="规则编码")
    rule_version: str = Field(..., description="规则版本")
    is_hit: bool = Field(..., description="是否命中")
    hit_message: str | None = Field(default=None, description="命中说明")
    hit_order: int = Field(..., description="命中顺序")
    created_at: datetime = Field(..., description="创建时间")


class RuleHitQuery(BaseModel):
    audit_result_id: int | None = Field(default=None, description="按 audit_result.id 筛选")
    clean_id: int | None = Field(default=None, description="按 product_clean.id 筛选")
    anomaly_type: RuleHitAnomalyType | None = Field(default=None, description="按异常类型筛选")
    rule_code: str | None = Field(default=None, description="按规则编码筛选")
    is_hit: bool | None = Field(default=None, description="按命中状态筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
