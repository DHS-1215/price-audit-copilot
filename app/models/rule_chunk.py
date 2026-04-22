# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:24
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class RuleChunk(Base, CreatedAtMixin):
    __tablename__ = "rule_chunk"
    __table_args__ = (
        UniqueConstraint("rule_definition_id", "chunk_index", name="uk_rule_chunk_rule_idx"),
        Index("idx_rule_chunk_rule_definition_id", "rule_definition_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    rule_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("rule_definition.id"),
        nullable=True,
        comment="对应 rule_definition.id，可空以兼容FAQ类文档块",
    )
    doc_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文档名")
    section_title: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="章节标题"
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="chunk序号")
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False, comment="chunk内容")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="metadata"
    )
    embedding_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="向量索引引用标识"
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, comment="是否启用")

    rule_definition: Mapped["RuleDefinition | None"] = relationship(back_populates="chunks")
