# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 21:04
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base

# 这行确保所有模型都被导入注册到 metadata
from app.models import (  # noqa: F401
    AskLog,
    AuditResult,
    ModelCallLog,
    ProductClean,
    ProductRaw,
    ReviewRecord,
    ReviewTask,
    RuleChunk,
    RuleDefinition,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 先走环境变量，没配就退回 alembic.ini
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
