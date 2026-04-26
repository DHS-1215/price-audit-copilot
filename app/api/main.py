# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.api.v1.endpoints.ask import router as ask_router
from app.api.v1.endpoints.ask_lc import router as ask_langchain_router
from app.api.v1.endpoints import audit
from app.core.handlers import register_exception_handlers
from app.core.logger import setup_logging
from app.core.middleware import register_middlewares
from app.core.response import success_response
from app.api.v1.endpoints import review
from app.core.trace import get_trace_id

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

# 现有主链接口
app.include_router(ask_router)
app.include_router(ask_langchain_router)
app.include_router(review.router, prefix="/api/v1")

# 新增审核接口
api_router = APIRouter()
api_router.include_router(audit.router)
app.include_router(api_router)


@app.get("/")
def root():
    return success_response(
        data={"message": "Price Audit Copilot API is running."},
        trace_id=get_trace_id(),
    )


@app.post("/extract", response_model=ProductExtractResult)
def extract(req: ExtractRequest):
    return extract_product(req.title)