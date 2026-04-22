# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:23
IDE       :PyCharm
作者      :董宏升
清洗与归一结果
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ProductClean(Base, TimestampMixin):
    __tablename__ = "product_clean"
    __table_args__ = (
        Index(
            "idx_product_clean_brand_spec_platform",
            "standardized_brand",
            "normalized_spec",
            "clean_platform",
        ),
        Index("idx_product_clean_raw_id", "raw_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    raw_id: Mapped[int] = mapped_column(
        ForeignKey("product_raw.id"),
        nullable=False,
        comment="对应 product_raw.id",
    )

    standardized_brand: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="标准化品牌"
    )
    normalized_spec: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="规范化规格"
    )
    clean_platform: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="干净平台"
    )
    clean_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="干净价格"
    )
    clean_title: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="干净标题"
    )
    clean_spec: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="干净规格"
    )
    normalize_note: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="标题规范提示/清洗说明"
    )
    product_name_normalized: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="归一后的商品名"
    )
    package_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="包装数量"
    )
    package_unit: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="包装单位"
    )
    spec_parse_status: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="规格解析状态"
    )
    clean_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="v1", comment="清洗规则版本"
    )

    raw: Mapped["ProductRaw"] = relationship(back_populates="clean_records")
    audit_results: Mapped[list["AuditResult"]] = relationship(
        back_populates="clean_record",
        cascade="all, delete-orphan",
    )
