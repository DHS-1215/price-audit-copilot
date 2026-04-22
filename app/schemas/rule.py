# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:26
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuleDefinitionBase(BaseModel):
    rule_code: str = Field(..., description="规则编码")
    rule_name: str = Field(..., description="规则名称")
    rule_type: str = Field(..., description="规则类型，如 low_price / gap / spec_risk")
    business_domain: str | None = Field(default=None, description="所属业务域")
    version: str = Field(..., description="规则版本")
    enabled: bool = Field(default=True, description="是否启用")
    threshold_config_json: dict[str, Any] | None = Field(
        default=None,
        description="阈值配置",
    )
    description: str | None = Field(default=None, description="规则说明")
    source_doc_path: str | None = Field(default=None, description="来源规则文档路径")
    effective_from: datetime | None = Field(default=None, description="生效开始时间")
    effective_to: datetime | None = Field(default=None, description="生效结束时间")


class RuleDefinitionCreate(RuleDefinitionBase):
    pass


class RuleDefinitionUpdate(BaseModel):
    rule_name: str | None = Field(default=None, description="规则名称")
    rule_type: str | None = Field(default=None, description="规则类型")
    business_domain: str | None = Field(default=None, description="所属业务域")
    enabled: bool | None = Field(default=None, description="是否启用")
    threshold_config_json: dict[str, Any] | None = Field(default=None, description="阈值配置")
    description: str | None = Field(default=None, description="规则说明")
    source_doc_path: str | None = Field(default=None, description="来源规则文档路径")
    effective_from: datetime | None = Field(default=None, description="生效开始时间")
    effective_to: datetime | None = Field(default=None, description="生效结束时间")


class RuleDefinitionRead(RuleDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class RuleChunkBase(BaseModel):
    rule_definition_id: int | None = Field(
        default=None,
        description="对应 rule_definition.id，可空以兼容 FAQ 类文档块",
    )
    doc_name: str = Field(..., description="文档名")
    section_title: str | None = Field(default=None, description="章节标题")
    chunk_index: int = Field(..., ge=0, description="chunk序号")
    chunk_text: str = Field(..., description="chunk内容")
    metadata_json: dict[str, Any] | None = Field(default=None, description="metadata")
    embedding_ref: str | None = Field(default=None, description="向量索引引用标识")
    is_active: bool = Field(default=True, description="是否启用")


class RuleChunkCreate(RuleChunkBase):
    pass


class RuleChunkRead(RuleChunkBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")


class RuleDefinitionQuery(BaseModel):
    rule_code: str | None = Field(default=None, description="按规则编码筛选")
    rule_type: str | None = Field(default=None, description="按规则类型筛选")
    version: str | None = Field(default=None, description="按规则版本筛选")
    enabled: bool | None = Field(default=None, description="按启用状态筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
