# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 22:54
IDE       :PyCharm
作者      :董宏升

数据库 Session 统一入口。

8号窗口调整：
1. 不再在这里硬编码数据库连接串
2. DATABASE_URL 统一从 app.core.config.Settings 读取
3. 本地、Docker、测试环境都通过环境变量切换数据库
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()