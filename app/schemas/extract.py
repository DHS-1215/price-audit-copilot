# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/21 12:19
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Optional
from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    title: str = Field(..., description="Product title")


class ProductExtractResult(BaseModel):
    brand: Optional[str] = Field(default=None, description="商品品牌")
    product_name: Optional[str] = Field(default=None, description="商品名")
    spec: Optional[str] = Field(default=None, description="规格")
    price: Optional[float] = Field(default=None, description="价格（人民币）")
    currency: str = Field(default="CNY", description="货币单位")
    promo_text: Optional[str] = Field(default=None, description="促销文案")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="抽取置信度"
    )