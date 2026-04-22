# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:26
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AuditAnomalyType = Literal[
    "low_price",
    "cross_platform_gap",
    "spec_risk",
]

AuditResultStatus = Literal[
    "pending_review",
    "reviewed",
    "closed",
]


class AuditResultBase(BaseModel):
    clean_id: int = Field(..., description="对应 product_clean.id")
    anomaly_type: AuditAnomalyType = Field(..., description="异常类型")
    is_hit: bool = Field(..., description="是否命中异常")

    hit_rule_code: str | None = Field(default=None, description="命中规则编码")
    hit_rule_version: str | None = Field(default=None, description="命中规则版本")
    rule_definition_id: int | None = Field(default=None, description="规则定义ID")

    explicit_low_price_threshold: Decimal | None = Field(
        default=None,
        description="显式低价阈值",
    )
    group_avg_price: Decimal | None = Field(
        default=None,
        description="组内均价",
    )
    price_to_group_avg_ratio: Decimal | None = Field(
        default=None,
        description="当前价格/组均价比",
    )
    low_price_rule_source: str | None = Field(
        default=None,
        description="低价规则来源，如 explicit_rule / stat_rule / both",
    )
    reason_text: str | None = Field(default=None, description="异常原因")
    input_snapshot_json: dict[str, Any] | None = Field(
        default=None,
        description="判定输入快照",
    )
    result_status: AuditResultStatus = Field(
        default="pending_review",
        description="结果状态",
    )
    audited_at: datetime | None = Field(default=None, description="判定时间")


class AuditResultCreate(AuditResultBase):
    pass


class AuditResultUpdate(BaseModel):
    is_hit: bool | None = Field(default=None, description="是否命中异常")
    hit_rule_code: str | None = Field(default=None, description="命中规则编码")
    hit_rule_version: str | None = Field(default=None, description="命中规则版本")
    rule_definition_id: int | None = Field(default=None, description="规则定义ID")

    explicit_low_price_threshold: Decimal | None = Field(default=None, description="显式低价阈值")
    group_avg_price: Decimal | None = Field(default=None, description="组内均价")
    price_to_group_avg_ratio: Decimal | None = Field(default=None, description="当前价格/组均价比")
    low_price_rule_source: str | None = Field(default=None, description="低价规则来源")
    reason_text: str | None = Field(default=None, description="异常原因")
    input_snapshot_json: dict[str, Any] | None = Field(default=None, description="判定输入快照")
    result_status: AuditResultStatus | None = Field(default=None, description="结果状态")
    audited_at: datetime | None = Field(default=None, description="判定时间")


class AuditResultRead(AuditResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class AuditResultListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    clean_id: int = Field(..., description="清洗结果ID")
    anomaly_type: AuditAnomalyType = Field(..., description="异常类型")
    is_hit: bool = Field(..., description="是否命中异常")
    hit_rule_code: str | None = Field(default=None, description="命中规则编码")
    hit_rule_version: str | None = Field(default=None, description="命中规则版本")
    result_status: AuditResultStatus = Field(..., description="结果状态")
    reason_text: str | None = Field(default=None, description="异常原因")
    audited_at: datetime | None = Field(default=None, description="判定时间")
    created_at: datetime = Field(..., description="创建时间")


class AuditResultQuery(BaseModel):
    anomaly_type: AuditAnomalyType | None = Field(default=None, description="按异常类型筛选")
    is_hit: bool | None = Field(default=None, description="按是否命中筛选")
    result_status: AuditResultStatus | None = Field(default=None, description="按结果状态筛选")
    standardized_brand: str | None = Field(default=None, description="按标准化品牌筛选")
    normalized_spec: str | None = Field(default=None, description="按规范化规格筛选")
    clean_platform: str | None = Field(default=None, description="按平台筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
