# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 21:47
IDE       :PyCharm
作者      :董宏升

新增 rule_hit 表
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rule_hit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),

        sa.Column(
            "audit_result_id",
            sa.Integer(),
            sa.ForeignKey("audit_result.id"),
            nullable=False,
            comment="对应 audit_result.id",
        ),
        sa.Column(
            "clean_id",
            sa.Integer(),
            sa.ForeignKey("product_clean.id"),
            nullable=False,
            comment="对应 product_clean.id",
        ),

        sa.Column(
            "anomaly_type",
            sa.String(length=64),
            nullable=False,
            comment="异常类型，如 low_price / cross_platform_gap / spec_risk",
        ),

        sa.Column(
            "rule_code",
            sa.String(length=64),
            nullable=False,
            comment="规则编码",
        ),
        sa.Column(
            "rule_version",
            sa.String(length=32),
            nullable=False,
            comment="规则版本",
        ),
        sa.Column(
            "rule_definition_id",
            sa.Integer(),
            sa.ForeignKey("rule_definition.id"),
            nullable=True,
            comment="对应 rule_definition.id",
        ),

        sa.Column(
            "is_hit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
            comment="该条规则是否命中",
        ),

        sa.Column(
            "input_snapshot_json",
            sa.JSON(),
            nullable=True,
            comment="判定输入快照",
        ),
        sa.Column(
            "computed_value_json",
            sa.JSON(),
            nullable=True,
            comment="计算结果快照",
        ),
        sa.Column(
            "threshold_snapshot_json",
            sa.JSON(),
            nullable=True,
            comment="阈值配置快照",
        ),

        sa.Column(
            "hit_message",
            sa.Text(),
            nullable=True,
            comment="命中说明",
        ),
        sa.Column(
            "hit_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="命中顺序，同一 audit_result 下用于展示排序",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),

        sa.UniqueConstraint(
            "audit_result_id",
            "rule_code",
            "rule_version",
            name="uk_rule_hit_audit_rule_version",
        ),
    )

    op.create_index(
        "idx_rule_hit_audit_result_id",
        "rule_hit",
        ["audit_result_id"],
    )
    op.create_index(
        "idx_rule_hit_clean_id",
        "rule_hit",
        ["clean_id"],
    )
    op.create_index(
        "idx_rule_hit_anomaly_type_hit",
        "rule_hit",
        ["anomaly_type", "is_hit"],
    )
    op.create_index(
        "idx_rule_hit_rule_definition_id",
        "rule_hit",
        ["rule_definition_id"],
    )
    op.create_index(
        "idx_rule_hit_rule_code_version",
        "rule_hit",
        ["rule_code", "rule_version"],
    )


def downgrade() -> None:
    op.drop_index("idx_rule_hit_rule_code_version", table_name="rule_hit")
    op.drop_index("idx_rule_hit_rule_definition_id", table_name="rule_hit")
    op.drop_index("idx_rule_hit_anomaly_type_hit", table_name="rule_hit")
    op.drop_index("idx_rule_hit_clean_id", table_name="rule_hit")
    op.drop_index("idx_rule_hit_audit_result_id", table_name="rule_hit")

    op.drop_table("rule_hit")
