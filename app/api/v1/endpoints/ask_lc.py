# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/11 20:36
IDE       :PyCharm
作者      :董宏升

6号窗口：/ask-lc 接口入口

职责：
- 只接收请求
- 调用 LangChain 增强链 orchestrator
- 不替代 /ask 主链
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import traceback

from fastapi import APIRouter, HTTPException

from app.schemas.ask import AskRequest
from app.orchestrators.ask_lc_orchestrator import run_langchain_ask

router = APIRouter(prefix="", tags=["ask-langchain"])


@router.post("/ask-lc")
def ask_langchain(req: AskRequest):
    try:
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="question 不能为空。")

        return run_langchain_ask(
            question=question,
            top_k=req.top_k,
            use_vector=req.use_vector,
        )

    except HTTPException:
        raise

    except Exception as e:
        print("\n" + "=" * 100)
        print("ask_langchain() 发生未捕获异常，开始打印 traceback：")
        traceback.print_exc()
        print("=" * 100 + "\n")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")