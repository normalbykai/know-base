from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """集中读取运行配置；环境变量是唯一的生产配置来源。"""
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_reload: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "sqlite:///./knowledge.db"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "documents"
    document_parser: str = "deepseek_vision"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    # DeepSeek 官方以 deepseek-flash 作为 V4.1-Flash 的稳定模型别名，并支持 Vision。
    deepseek_vision_model: str = "deepseek-flash"
    deepseek_max_pages: int = Field(default=30, ge=1, le=200)
    deepseek_max_output_tokens: int = Field(default=8192, ge=256, le=32768)
    mineru_base_url: str = "http://localhost:8080"
    max_upload_bytes: int = 52_428_800
    # 解析页数与外部服务响应时间差异很大，因此默认保守设置为 90 分钟。
    parse_task_timeout_seconds: int = Field(default=5400, ge=60, le=86_400)
    task_recovery_interval_seconds: int = Field(default=60, ge=10, le=3600)
    document_chunk_max_characters: int = Field(default=1200, ge=200, le=8000)


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免每个请求重复解析环境变量。"""
    return Settings()
