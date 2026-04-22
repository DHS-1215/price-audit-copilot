# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 21:04
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_raw",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("batch_no", sa.String(length=64), nullable=False, comment="采集批次号"),
        sa.Column("source_platform", sa.String(length=64), nullable=False, comment="来源平台"),
        sa.Column("source_shop_name", sa.String(length=255), nullable=True, comment="来源店铺名"),
        sa.Column("source_product_title", sa.String(length=1000), nullable=False, comment="原始商品标题"),
        sa.Column("source_spec_text", sa.String(length=255), nullable=True, comment="原始规格文本"),
        sa.Column("source_price_text", sa.String(length=255), nullable=True, comment="原始价格文本"),
        sa.Column("source_price_value", sa.Numeric(10, 2), nullable=True, comment="解析出的原始价格值"),
        sa.Column("product_url", sa.String(length=1000), nullable=True, comment="商品链接"),
        sa.Column("sku_id", sa.String(length=128), nullable=True, comment="商品SKU或平台唯一标识"),
        sa.Column("capture_time", sa.DateTime(), nullable=True, comment="抓取时间"),
        sa.Column("source_payload_json", sa.JSON(), nullable=True, comment="原始扩展载荷"),
        sa.Column("ingest_source", sa.String(length=64), nullable=True, comment="导入来源"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
    )
    op.create_index("idx_product_raw_batch_no", "product_raw", ["batch_no"])
    op.create_index("idx_product_raw_platform_capture", "product_raw", ["source_platform", "capture_time"])
    op.create_index("idx_product_raw_sku_id", "product_raw", ["sku_id"])

    op.create_table(
        "product_clean",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("raw_id", sa.Integer(), nullable=False, comment="对应 product_raw.id"),
        sa.Column("standardized_brand", sa.String(length=255), nullable=True, comment="标准化品牌"),
        sa.Column("normalized_spec", sa.String(length=255), nullable=True, comment="规范化规格"),
        sa.Column("clean_platform", sa.String(length=64), nullable=True, comment="干净平台"),
        sa.Column("clean_price", sa.Numeric(10, 2), nullable=True, comment="干净价格"),
        sa.Column("clean_title", sa.String(length=1000), nullable=True, comment="干净标题"),
        sa.Column("clean_spec", sa.String(length=255), nullable=True, comment="干净规格"),
        sa.Column("normalize_note", sa.String(length=500), nullable=True, comment="标题规范提示/清洗说明"),
        sa.Column("product_name_normalized", sa.String(length=255), nullable=True, comment="归一后的商品名"),
        sa.Column("package_quantity", sa.Numeric(10, 2), nullable=True, comment="包装数量"),
        sa.Column("package_unit", sa.String(length=32), nullable=True, comment="包装单位"),
        sa.Column("spec_parse_status", sa.String(length=32), nullable=True, comment="规格解析状态"),
        sa.Column("clean_version", sa.String(length=32), nullable=False, server_default="v1", comment="清洗规则版本"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="更新时间"),
        sa.ForeignKeyConstraint(["raw_id"], ["product_raw.id"], name="fk_product_clean_raw_id_product_raw"),
    )
    op.create_index("idx_product_clean_raw_id", "product_clean", ["raw_id"])
    op.create_index(
        "idx_product_clean_brand_spec_platform",
        "product_clean",
        ["standardized_brand", "normalized_spec", "clean_platform"],
    )

    op.create_table(
        "rule_definition",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("rule_code", sa.String(length=64), nullable=False, comment="规则编码"),
        sa.Column("rule_name", sa.String(length=255), nullable=False, comment="规则名称"),
        sa.Column("rule_type", sa.String(length=64), nullable=False, comment="规则类型"),
        sa.Column("business_domain", sa.String(length=64), nullable=True, comment="所属业务域"),
        sa.Column("version", sa.String(length=32), nullable=False, comment="规则版本"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true(), comment="是否启用"),
        sa.Column("threshold_config_json", sa.JSON(), nullable=True, comment="阈值配置"),
        sa.Column("description", sa.Text(), nullable=True, comment="规则说明"),
        sa.Column("source_doc_path", sa.String(length=1000), nullable=True, comment="来源规则文档路径"),
        sa.Column("effective_from", sa.DateTime(), nullable=True, comment="生效开始时间"),
        sa.Column("effective_to", sa.DateTime(), nullable=True, comment="生效结束时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="更新时间"),
        sa.UniqueConstraint("rule_code", "version", name="uk_rule_definition_code_version"),
    )
    op.create_index("idx_rule_definition_rule_type", "rule_definition", ["rule_type"])

    op.create_table(
        "rule_chunk",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("rule_definition_id", sa.Integer(), nullable=True, comment="对应 rule_definition.id"),
        sa.Column("doc_name", sa.String(length=255), nullable=False, comment="文档名"),
        sa.Column("section_title", sa.String(length=255), nullable=True, comment="章节标题"),
        sa.Column("chunk_index", sa.Integer(), nullable=False, comment="chunk序号"),
        sa.Column("chunk_text", sa.Text(), nullable=False, comment="chunk内容"),
        sa.Column("metadata_json", sa.JSON(), nullable=True, comment="metadata"),
        sa.Column("embedding_ref", sa.String(length=255), nullable=True, comment="向量索引引用标识"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), comment="是否启用"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
        sa.ForeignKeyConstraint(
            ["rule_definition_id"],
            ["rule_definition.id"],
            name="fk_rule_chunk_rule_definition_id_rule_definition",
        ),
        sa.UniqueConstraint("rule_definition_id", "chunk_index", name="uk_rule_chunk_rule_idx"),
    )
    op.create_index("idx_rule_chunk_rule_definition_id", "rule_chunk", ["rule_definition_id"])


def downgrade() -> None:
    op.drop_index("idx_rule_chunk_rule_definition_id", table_name="rule_chunk")
    op.drop_table("rule_chunk")

    op.drop_index("idx_rule_definition_rule_type", table_name="rule_definition")
    op.drop_table("rule_definition")

    op.drop_index("idx_product_clean_brand_spec_platform", table_name="product_clean")
    op.drop_index("idx_product_clean_raw_id", table_name="product_clean")
    op.drop_table("product_clean")

    op.drop_index("idx_product_raw_sku_id", table_name="product_raw")
    op.drop_index("idx_product_raw_platform_capture", table_name="product_raw")
    op.drop_index("idx_product_raw_batch_no", table_name="product_raw")
    op.drop_table("product_raw")
