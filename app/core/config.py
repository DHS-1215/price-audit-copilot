# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 13:24
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    项目统一配置中心。

    设计原则：
    1. 所有配置统一从这里读取，不在业务代码里到处写死。
    2. 先兼容当前 DATABASE_URL，避免影响 Alembic 和现有数据库链路。
    3. 只放“项目级配置”，不要把一次性脚本参数硬塞进来。
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========= 基础应用配置 =========
    app_name: str = Field(default="price-audit-copilot", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    # ========= 数据库配置 =========
    database_url: str = Field(alias="DATABASE_URL")

    # ========= 日志配置 =========
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    log_file_name: str = Field(default="app.log", alias="LOG_FILE_NAME")

    # ========= Trace 配置 =========
    trace_header_name: str = Field(default="X-Trace-Id", alias="TRACE_HEADER_NAME")

    # ========= LLM / RAG 相关预留 =========
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")

    # ========= 功能开关 =========
    ask_log_enabled: bool = Field(default=True, alias="ASK_LOG_ENABLED")
    model_call_log_enabled: bool = Field(default=True, alias="MODEL_CALL_LOG_ENABLED")
    review_log_enabled: bool = Field(default=True, alias="REVIEW_LOG_ENABLED")

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() == "dev"

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() == "prod"

    @property
    def log_file_path(self) -> Path:
        return BASE_DIR / self.log_dir / self.log_file_name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    返回单例配置对象。
    用 lru_cache 保证整个进程里只初始化一次。
    """
    return Settings()
