# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 21:23
IDE       :PyCharm
作者      :董宏升

规则命中明细模型
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RuleHit(Base, TimestampMixin):
    __tablename__ = "rule_hit"
    __table_args__ = (
        UniqueConstraint(
            "audit_result_id",
            "rule_code",
            "rule_version",
            name="uk_rule_hit_audit_rule_version",
        ),
        Index("idx_rule_hit_audit_result_id", "audit_result_id"),
        Index("idx_rule_hit_clean_id", "clean_id"),
        Index("idx_rule_hit_anomaly_type_hit", "anomaly_type", "is_hit"),
        Index("idx_rule_hit_rule_definition_id", "rule_definition_id"),
        Index("idx_rule_hit_rule_code_version", "rule_code", "rule_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")

    audit_result_id: Mapped[int] = mapped_column(
        ForeignKey("audit_result.id"),
        nullable=False,
        comment="对应 audit_result.id",
    )
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

    rule_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="规则编码",
    )
    rule_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="规则版本",
    )
    rule_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("rule_definition.id"),
        nullable=True,
        comment="对应 rule_definition.id",
    )

    is_hit: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="该条规则是否命中",
    )

    input_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="判定输入快照",
    )
    computed_value_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="计算结果快照，如 group_avg_price / gap_ratio",
    )
    threshold_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="阈值配置快照",
    )

    hit_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="命中说明",
    )
    hit_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="命中顺序，同一 audit_result 下用于展示排序",
    )

    audit_result: Mapped["AuditResult"] = relationship(back_populates="rule_hits")
    clean_record: Mapped["ProductClean"] = relationship(back_populates="rule_hits")
    rule_definition: Mapped["RuleDefinition | None"] = relationship(back_populates="rule_hits")
