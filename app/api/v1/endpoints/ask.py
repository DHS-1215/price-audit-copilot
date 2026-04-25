# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/09 11:49
IDE       :PyCharm
作者      :董宏升

6号窗口：/ask 接口入口

职责：
- 只接收请求
- 调用 /ask 主链 orchestrator
- 返回统一 AskResponse

具体编排逻辑放在：
app/orchestrators/ask_orchestrator.py
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import APIRouter

from app.schemas.ask import AskRequest, AskResponse
from app.orchestrators.ask_orchestrator import run_ask

router = APIRouter(prefix="", tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    return run_ask(req)