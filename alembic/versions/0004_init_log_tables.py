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

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ask_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("trace_id", sa.String(length=64), nullable=False, comment="全链路trace_id"),
        sa.Column("question", sa.String(length=2000), nullable=False, comment="用户问题"),
        sa.Column("route", sa.String(length=32), nullable=False, comment="路由类型"),
        sa.Column("answer_text", sa.Text(), nullable=True, comment="最终回答"),
        sa.Column("tools_used_json", sa.JSON(), nullable=True, comment="工具列表"),
        sa.Column("analysis_result_json", sa.JSON(), nullable=True, comment="分析结果"),
        sa.Column("retrieval_result_json", sa.JSON(), nullable=True, comment="检索结果"),
        sa.Column("explanation_result_json", sa.JSON(), nullable=True, comment="解释结果"),
        sa.Column("trace_json", sa.JSON(), nullable=True, comment="工具调用链路"),
        sa.Column("subject_audit_result_id", sa.Integer(), nullable=True, comment="关联审核结果ID"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success", comment="请求状态"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
        sa.ForeignKeyConstraint(
            ["subject_audit_result_id"],
            ["audit_result.id"],
            name="fk_ask_log_subject_audit_result_id_audit_result",
        ),
    )
    op.create_index("idx_ask_log_trace_id", "ask_log", ["trace_id"])
    op.create_index("idx_ask_log_route", "ask_log", ["route"])
    op.create_index("idx_ask_log_created_at", "ask_log", ["created_at"])

    op.create_table(
        "model_call_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("ask_log_id", sa.Integer(), nullable=False, comment="对应 ask_log.id"),
        sa.Column("trace_id", sa.String(length=64), nullable=False, comment="trace_id"),
        sa.Column("call_stage", sa.String(length=64), nullable=False, comment="调用阶段"),
        sa.Column("model_vendor", sa.String(length=64), nullable=True, comment="模型提供方"),
        sa.Column("model_name", sa.String(length=128), nullable=True, comment="模型名称"),
        sa.Column("request_payload_json", sa.JSON(), nullable=True, comment="请求载荷"),
        sa.Column("response_payload_json", sa.JSON(), nullable=True, comment="响应载荷"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True, comment="输入tokens"),
        sa.Column("completion_tokens", sa.Integer(), nullable=True, comment="输出tokens"),
        sa.Column("latency_ms", sa.Integer(), nullable=True, comment="耗时毫秒"),
        sa.Column("error_message", sa.String(length=1000), nullable=True, comment="错误信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
                  comment="创建时间"),
        sa.ForeignKeyConstraint(
            ["ask_log_id"],
            ["ask_log.id"],
            name="fk_model_call_log_ask_log_id_ask_log",
        ),
    )
    op.create_index("idx_model_call_log_ask_log_id", "model_call_log", ["ask_log_id"])
    op.create_index("idx_model_call_log_trace_id", "model_call_log", ["trace_id"])
    op.create_index("idx_model_call_log_call_stage", "model_call_log", ["call_stage"])


def downgrade() -> None:
    op.drop_index("idx_model_call_log_call_stage", table_name="model_call_log")
    op.drop_index("idx_model_call_log_trace_id", table_name="model_call_log")
    op.drop_index("idx_model_call_log_ask_log_id", table_name="model_call_log")
    op.drop_table("model_call_log")

    op.drop_index("idx_ask_log_created_at", table_name="ask_log")
    op.drop_index("idx_ask_log_route", table_name="ask_log")
    op.drop_index("idx_ask_log_trace_id", table_name="ask_log")
    op.drop_table("ask_log")
