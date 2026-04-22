# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:24
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RuleDefinition(Base, TimestampMixin):
    __tablename__ = "rule_definition"
    __table_args__ = (
        UniqueConstraint("rule_code", "version", name="uk_rule_definition_code_version"),
        Index("idx_rule_definition_rule_type", "rule_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="规则编码")
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="规则名称")
    rule_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="规则类型，如 low_price / gap / spec_risk"
    )
    business_domain: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="所属业务域"
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False, comment="规则版本")
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True, comment="是否启用")
    threshold_config_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="阈值配置"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="规则说明")
    source_doc_path: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="来源规则文档路径"
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="生效开始时间"
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="生效结束时间"
    )

    chunks: Mapped[list["RuleChunk"]] = relationship(
        back_populates="rule_definition",
        cascade="all, delete-orphan",
    )
    audit_results: Mapped[list["AuditResult"]] = relationship(back_populates="rule_definition")
