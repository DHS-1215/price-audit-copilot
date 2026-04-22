# app/main.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.endpoints.ask import router as ask_router
from app.api.v1.endpoints.ask_lc import router as ask_langchain_router
from app.core.handlers import register_exception_handlers
from app.core.logger import setup_logging
from app.core.middleware import register_middlewares
from app.core.response import success_response

# 第一周：结构化抽取能力
from app.llm.ollama_client import extract_product
from app.core.schemas import ExtractRequest, ProductExtractResult

setup_logging()

app = FastAPI(
    title="Price Audit Copilot",
    description="Week 4 unified ask entry",
    version="0.4.0",
)

register_middlewares(app)
register_exception_handlers(app)

app.include_router(ask_router)
app.include_router(ask_langchain_router)


@app.get("/")
def root():
    return success_response(data={"message": "Price Audit Copilot API is running."})


@app.post("/extract", response_model=ProductExtractResult)
def extract(req: ExtractRequest):
    # 这里先不强行改 response_model，避免现有 extract 合同被 3 号窗口误伤
    # 真正统一接口响应外壳时，建议在后续逐步收口，不要一刀把旧接口全砍了
    return extract_product(req.title)