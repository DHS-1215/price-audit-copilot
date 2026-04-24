# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 21:58
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

RULE_DEFINITION_TABLE = sa.table(
    "rule_definition",
    sa.column("rule_code", sa.String),
    sa.column("threshold_config_json", sa.JSON),
    sa.column("description", sa.Text),
)


def upgrade() -> None:
    # 1) 显式低价规则：把 examples 升级成真正可执行的 rules 列表
    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "LOW_PRICE_EXPLICIT")
        .values(
            threshold_config_json={
                "mode": "explicit",
                "rules": [
                    {"brand": "鸿茅", "spec": "500ml", "threshold": 180.0},
                    {"brand": "鸿茅", "spec": "500ml*4瓶", "threshold": 799.0},
                ],
            },
            description="用于命中业务明确定义的显式低价阈值；按品牌+规格匹配显式价格下限。",
        )
    )

    # 2) 统计低价规则：补上最小样本数和价格比阈值
    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "LOW_PRICE_STAT")
        .values(
            threshold_config_json={
                "mode": "stat",
                "compare_field": "price_to_group_avg_ratio",
                "min_group_size": 3,
                "ratio_threshold": 0.80,
            },
            description="用于命中组内均价比异常的统计低价规则；要求组内有效价格样本数达到最小阈值。",
        )
    )

    # 3) 跨平台价差规则：补上平台数、价差阈值、是否只标最低价
    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "CROSS_PLATFORM_GAP")
        .values(
            threshold_config_json={
                "mode": "gap",
                "min_distinct_platforms": 2,
                "gap_ratio_threshold": 0.25,
                "flag_only_lowest_price": True,
            },
            description="用于判断同品牌同规格跨平台价格差异异常；默认只标记组内最低价记录为异常对象。",
        )
    )

    # 4) 规格识别风险规则：明确支持的触发条件
    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "SPEC_RISK")
        .values(
            threshold_config_json={
                "mode": "spec_risk",
                "conditions": [
                    "title_spec_mismatch",
                    "missing_normalized_spec",
                ],
            },
            description="用于识别规格抽取失败或规格归一风险，包括标题规格冲突和规范化规格缺失。",
        )
    )


def downgrade() -> None:
    # 回退到 0005 的原始 seed 配置
    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "LOW_PRICE_EXPLICIT")
        .values(
            threshold_config_json={
                "mode": "explicit",
                "examples": [
                    "鸿茅药酒 500ml 单瓶 < 180",
                    "500ml*4 < 799",
                ],
            },
            description="用于命中业务明确定义的显式低价阈值",
        )
    )

    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "LOW_PRICE_STAT")
        .values(
            threshold_config_json={
                "mode": "stat",
                "compare_field": "price_to_group_avg_ratio",
            },
            description="用于命中组内均价比异常的统计低价规则",
        )
    )

    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "CROSS_PLATFORM_GAP")
        .values(
            threshold_config_json={
                "mode": "gap",
            },
            description="用于判断同品牌同规格跨平台价格差异异常",
        )
    )

    op.execute(
        RULE_DEFINITION_TABLE.update()
        .where(RULE_DEFINITION_TABLE.c.rule_code == "SPEC_RISK")
        .values(
            threshold_config_json={
                "mode": "parse_risk",
            },
            description="用于识别规格抽取失败或规格归一风险",
        )
    )
