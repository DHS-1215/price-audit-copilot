# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:24
IDE       :PyCharm
作者      :董宏升

5号窗口补充说明：
rule_chunk 是规则文档切片资源，服务于 RAG 检索、规则解释、evidence/citation 引用展示。
它不是异常判定结果，也不负责重新定义“为什么异常”。

解释链路固定为：
audit_result -> rule_hit -> rule_definition -> rule_chunk
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class RuleChunk(Base, CreatedAtMixin):
    """
    规则文档切片表。

    职责：
    1. 保存规则文档切片内容；
    2. 为 baseline / vector / hybrid 检索提供候选文本；
    3. 为 evidence / citation 提供可追溯的文档依据；
    4. 通过 rule_definition_id / rule_code / rule_version 与正式规则定义建立关系。

    注意：
    - rule_chunk 不参与异常判定；
    - rule_chunk 不覆盖 audit_result / rule_hit 的结果事实；
    - explanation 场景必须先消费 audit_result / rule_hit / rule_definition，再使用 rule_chunk 补充文档依据。
    """

    __tablename__ = "rule_chunk"

    __table_args__ = (
        UniqueConstraint(
            "rule_definition_id",
            "chunk_index",
            name="uk_rule_chunk_rule_idx",
        ),
        Index("idx_rule_chunk_rule_definition_id", "rule_definition_id"),
        Index("idx_rule_chunk_rule_code", "rule_code"),
        Index("idx_rule_chunk_anomaly_type", "anomaly_type"),
        Index("idx_rule_chunk_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键",
    )

    rule_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("rule_definition.id"),
        nullable=True,
        comment="对应 rule_definition.id；FAQ、人工复核类文档块可为空",
    )

    # ===== 5号窗口新增：规则归属字段 =====

    rule_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="规则编码，如 LOW_PRICE_EXPLICIT / LOW_PRICE_STAT / CROSS_PLATFORM_GAP / SPEC_RISK",
    )

    rule_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="规则版本，尽量与 rule_definition.version 保持一致",
    )

    anomaly_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="异常类型，如 low_price / cross_platform_gap / spec_risk",
    )

    # ===== 文档来源字段 =====

    doc_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="文档文件名或旧版文档名，保留以兼容已有逻辑",
    )

    doc_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="文档标题，如 低价异常规则说明 / 跨平台价差规则说明",
    )

    source_doc_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="来源规则文档路径，如 docs/rules/low_price_rules.md",
    )

    section_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="章节标题",
    )

    section_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="完整章节路径，如 低价异常规则说明 > 显式低价规则 > 阈值口径",
    )

    # ===== chunk 内容字段 =====

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="chunk 序号",
    )

    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="chunk 内容",
    )

    chunk_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="chunk 类型，如 rule_text / threshold / definition / example / manual_review / faq / note",
    )

    # ===== 检索 metadata 字段 =====

    keywords_json: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="关键词列表，用于 baseline 检索和 score_reasons",
    )

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="检索 metadata，如 rule_code、anomaly_type、section_path、chunk_type、tags 等",
    )

    embedding_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="向量索引引用标识",
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="是否启用；废弃或旧版本 chunk 可置为 False",
    )

    rule_definition: Mapped["RuleDefinition | None"] = relationship(
        back_populates="chunks",
    )