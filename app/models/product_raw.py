# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:23
IDE       :PyCharm
作者      :董宏升
原始商品数据 ORM
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
# -*- coding: utf-8 -*-


from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class ProductRaw(Base, CreatedAtMixin):
    __tablename__ = "product_raw"
    __table_args__ = (
        Index("idx_product_raw_batch_no", "batch_no"),
        Index("idx_product_raw_platform_capture", "source_platform", "capture_time"),
        Index("idx_product_raw_sku_id", "sku_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="采集批次号")
    source_platform: Mapped[str] = mapped_column(String(64), nullable=False, comment="来源平台")
    source_shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="来源店铺名")
    source_product_title: Mapped[str] = mapped_column(String(1000), nullable=False, comment="原始商品标题")
    source_spec_text: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="原始规格文本")
    source_price_text: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="原始价格文本")
    source_price_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="解析出的原始价格值"
    )
    product_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="商品链接")
    sku_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="商品SKU或平台唯一标识")
    capture_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="抓取时间")
    source_payload_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="原始扩展载荷"
    )
    ingest_source: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="导入来源，如 rpa/csv/api"
    )

    clean_records: Mapped[list["ProductClean"]] = relationship(
        back_populates="raw",
        cascade="all, delete-orphan",
    )
