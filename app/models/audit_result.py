# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:24
IDE       :PyCharm
作者      :董宏升
异常规则和判定依据
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AuditResult(Base, TimestampMixin):
    __tablename__ = "audit_result"
    __table_args__ = (
        Index("idx_audit_result_clean_id", "clean_id"),
        Index("idx_audit_result_anomaly_type_hit", "anomaly_type", "is_hit"),
        Index("idx_audit_result_rule_definition_id", "rule_definition_id"),
        Index("idx_audit_result_audited_at", "audited_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    clean_id: Mapped[int] = mapped_column(
        ForeignKey("product_clean.id"),
        nullable=False,
        comment="对应 product_clean.id",
    )

    anomaly_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="异常类型，如 low_price / cross_platform_gap / spec_risk",
    )
    is_hit: Mapped[bool] = mapped_column(nullable=False, comment="是否命中异常")
    hit_rule_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="命中规则编码"
    )
    hit_rule_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="命中规则版本"
    )
    rule_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("rule_definition.id"),
        nullable=True,
        comment="对应 rule_definition.id",
    )

    explicit_low_price_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="显式低价阈值"
    )
    group_avg_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="组内均价"
    )
    price_to_group_avg_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="当前价格/组均价比"
    )
    low_price_rule_source: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="低价规则来源"
    )
    reason_text: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="异常原因"
    )
    input_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="判定输入快照"
    )
    result_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_review",
        comment="结果状态，如 pending_review / reviewed",
    )
    audited_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="判定时间"
    )

    clean_record: Mapped["ProductClean"] = relationship(back_populates="audit_results")
    rule_definition: Mapped["RuleDefinition | None"] = relationship(back_populates="audit_results")
    review_tasks: Mapped[list["ReviewTask"]] = relationship(
        back_populates="audit_result",
        cascade="all, delete-orphan",
    )

    rule_hits: Mapped[list["RuleHit"]] = relationship(
        back_populates="audit_result",
        cascade="all, delete-orphan",
    )

    ask_logs: Mapped[list["AskLog"]] = relationship(back_populates="subject_audit_result")
