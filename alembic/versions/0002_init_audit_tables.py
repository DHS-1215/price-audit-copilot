# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 21:04
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""init audit tables

Revision ID: 0002_init_audit_tables
Revises: 0001_init_product_and_rule_tables
Create Date: 2026-04-21 13:35:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_result",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("clean_id", sa.Integer(), nullable=False, comment="对应 product_clean.id"),
        sa.Column("anomaly_type", sa.String(length=64), nullable=False, comment="异常类型"),
        sa.Column("is_hit", sa.Boolean(), nullable=False, comment="是否命中异常"),
        sa.Column("hit_rule_code", sa.String(length=64), nullable=True, comment="命中规则编码"),
        sa.Column("hit_rule_version", sa.String(length=32), nullable=True, comment="命中规则版本"),
        sa.Column("rule_definition_id", sa.Integer(), nullable=True, comment="对应 rule_definition.id"),
        sa.Column("explicit_low_price_threshold", sa.Numeric(10, 2), nullable=True, comment="显式低价阈值"),
        sa.Column("group_avg_price", sa.Numeric(10, 2), nullable=True, comment="组内均价"),
        sa.Column("price_to_group_avg_ratio", sa.Numeric(10, 4), nullable=True, comment="当前价格/组均价比"),
        sa.Column("low_price_rule_source", sa.String(length=64), nullable=True, comment="低价规则来源"),
        sa.Column("reason_text", sa.String(length=1000), nullable=True, comment="异常原因"),
        sa.Column("input_snapshot_json", sa.JSON(), nullable=True, comment="判定输入快照"),
        sa.Column("result_status", sa.String(length=32), nullable=False, server_default="pending_review",
                  comment="结果状态"),
        sa.Column("audited_at", sa.DateTime(), nullable=True, comment="判定时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="更新时间"),
        sa.ForeignKeyConstraint(["clean_id"], ["product_clean.id"], name="fk_audit_result_clean_id_product_clean"),
        sa.ForeignKeyConstraint(
            ["rule_definition_id"],
            ["rule_definition.id"],
            name="fk_audit_result_rule_definition_id_rule_definition",
        ),
    )
    op.create_index("idx_audit_result_clean_id", "audit_result", ["clean_id"])
    op.create_index("idx_audit_result_anomaly_type_hit", "audit_result", ["anomaly_type", "is_hit"])
    op.create_index("idx_audit_result_rule_definition_id", "audit_result", ["rule_definition_id"])
    op.create_index("idx_audit_result_audited_at", "audit_result", ["audited_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_result_audited_at", table_name="audit_result")
    op.drop_index("idx_audit_result_rule_definition_id", table_name="audit_result")
    op.drop_index("idx_audit_result_anomaly_type_hit", table_name="audit_result")
    op.drop_index("idx_audit_result_clean_id", table_name="audit_result")
    op.drop_table("audit_result")
