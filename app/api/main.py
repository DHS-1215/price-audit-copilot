# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from app.api.routes_ask import router as ask_router
from app.api.routes_ask_langchain import router as ask_langchain_router

# 第一周：结构化抽取能力
from app.core.llm_ollama import ask_llm, extract_product
from app.core.schemas import (
    AskRequest,
    AskResponse,
    ExtractRequest,
    ProductExtractResult,
)

"""
FastAPI 应用主入口
    1. 创建 FastAPI app
    2. 挂载 ask 路由
    3. 保留 /extract 接口
"""
app = FastAPI(
    title="Price Audit Copilot",
    description="Week 4 unified ask entry",
    version="0.4.0"
)

# 把 routes_ask.py 里的 /ask 挂起来
app.include_router(ask_router)
app.include_router(ask_langchain_router)

@app.get("/")
def root():
    """
    健康检查接口。
    用来快速确认服务是否启动正常。
    """
    return {"message": "Price Audit Copilot API is running."}


@app.post('/extract', response_model=ProductExtractResult)
def extract(req: ExtractRequest):
    try:
        result = extract_product(req.title)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
