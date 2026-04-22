# -*- coding: utf-8 -*-
from __future__ import annotations
"""
创建时间    :2026/04/21 21:05
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""init review tables

Revision ID: 0003_init_review_tables
Revises: 0002_init_audit_tables
Create Date: 2026-04-21 13:40:00
"""


from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_task",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("audit_result_id", sa.Integer(), nullable=False, comment="对应 audit_result.id"),
        sa.Column("task_status", sa.String(length=32), nullable=False, server_default="pending", comment="任务状态"),
        sa.Column("priority", sa.String(length=16), nullable=True, comment="优先级"),
        sa.Column("assigned_to", sa.String(length=64), nullable=True, comment="分配对象"),
        sa.Column("assigned_at", sa.DateTime(), nullable=True, comment="分配时间"),
        sa.Column("due_at", sa.DateTime(), nullable=True, comment="截止时间"),
        sa.Column("created_by", sa.String(length=64), nullable=True, comment="创建人"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.ForeignKeyConstraint(
            ["audit_result_id"],
            ["audit_result.id"],
            name="fk_review_task_audit_result_id_audit_result",
        ),
    )
    op.create_index("idx_review_task_audit_result_id", "review_task", ["audit_result_id"])
    op.create_index("idx_review_task_status_assigned", "review_task", ["task_status", "assigned_to"])

    op.create_table(
        "review_record",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("review_task_id", sa.Integer(), nullable=False, comment="对应 review_task.id"),
        sa.Column("action_type", sa.String(length=32), nullable=False, comment="动作类型"),
        sa.Column("action_result", sa.String(length=64), nullable=True, comment="动作结果"),
        sa.Column("reviewer", sa.String(length=64), nullable=True, comment="复核人"),
        sa.Column("remark", sa.String(length=1000), nullable=True, comment="备注"),
        sa.Column("evidence_snapshot_json", sa.JSON(), nullable=True, comment="操作时依据快照"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(
            ["review_task_id"],
            ["review_task.id"],
            name="fk_review_record_review_task_id_review_task",
        ),
    )
    op.create_index("idx_review_record_task_id", "review_record", ["review_task_id"])
    op.create_index("idx_review_record_created_at", "review_record", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_review_record_created_at", table_name="review_record")
    op.drop_index("idx_review_record_task_id", table_name="review_record")
    op.drop_table("review_record")

    op.drop_index("idx_review_task_status_assigned", table_name="review_task")
    op.drop_index("idx_review_task_audit_result_id", table_name="review_task")
    op.drop_table("review_task")