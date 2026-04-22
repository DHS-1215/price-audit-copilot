# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 21:05
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

RULE_DEFINITION_TABLE = sa.table(
    "rule_definition",
    sa.column("rule_code", sa.String),
    sa.column("rule_name", sa.String),
    sa.column("rule_type", sa.String),
    sa.column("business_domain", sa.String),
    sa.column("version", sa.String),
    sa.column("enabled", sa.Boolean),
    sa.column("threshold_config_json", sa.JSON),
    sa.column("description", sa.Text),
    sa.column("source_doc_path", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        RULE_DEFINITION_TABLE,
        [
            {
                "rule_code": "LOW_PRICE_EXPLICIT",
                "rule_name": "显式低价规则",
                "rule_type": "low_price",
                "business_domain": "price_audit",
                "version": "v1",
                "enabled": True,
                "threshold_config_json": {
                    "mode": "explicit",
                    "examples": [
                        "鸿茅药酒 500ml 单瓶 < 180",
                        "500ml*4 < 799",
                    ],
                },
                "description": "用于命中业务明确定义的显式低价阈值",
                "source_doc_path": "data/rules/low_price_detection_rules.md",
            },
            {
                "rule_code": "LOW_PRICE_STAT",
                "rule_name": "组内均价低价规则",
                "rule_type": "low_price",
                "business_domain": "price_audit",
                "version": "v1",
                "enabled": True,
                "threshold_config_json": {
                    "mode": "stat",
                    "compare_field": "price_to_group_avg_ratio",
                },
                "description": "用于命中组内均价比异常的统计低价规则",
                "source_doc_path": "data/rules/low_price_detection_rules.md",
            },
            {
                "rule_code": "CROSS_PLATFORM_GAP",
                "rule_name": "跨平台价差规则",
                "rule_type": "cross_platform_gap",
                "business_domain": "price_audit",
                "version": "v1",
                "enabled": True,
                "threshold_config_json": {
                    "mode": "gap",
                },
                "description": "用于判断同品牌同规格跨平台价格差异异常",
                "source_doc_path": "data/rules/cross_platform_gap_rules.md",
            },
            {
                "rule_code": "SPEC_RISK",
                "rule_name": "规格识别风险规则",
                "rule_type": "spec_risk",
                "business_domain": "price_audit",
                "version": "v1",
                "enabled": True,
                "threshold_config_json": {
                    "mode": "parse_risk",
                },
                "description": "用于识别规格抽取失败或规格归一风险",
                "source_doc_path": "data/rules/spec_normalization_rules.md",
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM rule_definition
            WHERE rule_code IN (
                'LOW_PRICE_EXPLICIT',
                'LOW_PRICE_STAT',
                'CROSS_PLATFORM_GAP',
                'SPEC_RISK'
            )
            """
        )
    )
