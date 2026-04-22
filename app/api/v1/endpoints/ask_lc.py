# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/11 20:36
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import traceback
from fastapi import APIRouter, HTTPException

from app.orchestrators.ask_orchestrator import run_langchain_ask
from app.core.schemas import AskRequest

router = APIRouter(prefix="", tags=["ask-langchain"])


@router.post("/ask-lc")
def ask_langchain(req: AskRequest):
    try:
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="question 不能为空。")

        result = run_langchain_ask(
            question=question,
            top_k=req.top_k,
            use_vector=req.use_vector,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        print("\n" + "=" * 100)
        print("ask_langchain() 发生未捕获异常，开始打印 traceback：")
        traceback.print_exc()
        print("=" * 100 + "\n")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
