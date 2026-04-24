# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/24 20:57
IDE       :PyCharm
作者      :董宏升

这一步的作用是让数据库里的 rule_chunk 表和你刚刚修改后的 app/models/rule_chunk.py 对齐。
当前 rule_chunk 已有 rule_definition_id、doc_name、section_title、chunk_index、chunk_text、metadata_json、embedding_ref、is_active 等字段，
但缺少 5 号窗口解释层需要的 rule_code、rule_version、anomaly_type、source_doc_path、doc_title、section_path、chunk_type、keywords_json。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008"

# 注意：
# 如果你 0007 文件里的 revision 不是 "0007_update_rule_definition_threshold_configs"，
# 就把这里改成 0007 文件中实际的 revision 值。
down_revision = "0007"

branch_labels = None
depends_on = None


def upgrade() -> None:
    """给 rule_chunk 表补齐 5号窗口 RAG 检索解释所需字段。"""

    op.add_column(
        "rule_chunk",
        sa.Column(
            "rule_code",
            sa.String(length=64),
            nullable=True,
            comment="规则编码，如 LOW_PRICE_EXPLICIT / LOW_PRICE_STAT / CROSS_PLATFORM_GAP / SPEC_RISK",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "rule_version",
            sa.String(length=32),
            nullable=True,
            comment="规则版本，尽量与 rule_definition.version 保持一致",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "anomaly_type",
            sa.String(length=64),
            nullable=True,
            comment="异常类型，如 low_price / cross_platform_gap / spec_risk",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "doc_title",
            sa.String(length=255),
            nullable=True,
            comment="文档标题，如 低价异常规则说明 / 跨平台价差规则说明",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "source_doc_path",
            sa.String(length=1000),
            nullable=True,
            comment="来源规则文档路径，如 docs/rules/low_price_rules.md",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "section_path",
            sa.String(length=1000),
            nullable=True,
            comment="完整章节路径，如 低价异常规则说明 > 显式低价规则 > 阈值口径",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "chunk_type",
            sa.String(length=64),
            nullable=True,
            comment="chunk 类型，如 rule_text / threshold / definition / example / manual_review / faq / note",
        ),
    )

    op.add_column(
        "rule_chunk",
        sa.Column(
            "keywords_json",
            sa.JSON(),
            nullable=True,
            comment="关键词列表，用于 baseline 检索和 score_reasons",
        ),
    )

    op.create_index(
        "idx_rule_chunk_rule_code",
        "rule_chunk",
        ["rule_code"],
        unique=False,
    )

    op.create_index(
        "idx_rule_chunk_anomaly_type",
        "rule_chunk",
        ["anomaly_type"],
        unique=False,
    )

    op.create_index(
        "idx_rule_chunk_is_active",
        "rule_chunk",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    """回滚 rule_chunk 表的 RAG metadata 扩展字段。"""

    op.drop_index("idx_rule_chunk_is_active", table_name="rule_chunk")
    op.drop_index("idx_rule_chunk_anomaly_type", table_name="rule_chunk")
    op.drop_index("idx_rule_chunk_rule_code", table_name="rule_chunk")

    op.drop_column("rule_chunk", "keywords_json")
    op.drop_column("rule_chunk", "chunk_type")
    op.drop_column("rule_chunk", "section_path")
    op.drop_column("rule_chunk", "source_doc_path")
    op.drop_column("rule_chunk", "doc_title")
    op.drop_column("rule_chunk", "anomaly_type")
    op.drop_column("rule_chunk", "rule_version")
    op.drop_column("rule_chunk", "rule_code")