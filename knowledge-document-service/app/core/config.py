from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中读取运行配置；环境变量是唯一的生产配置来源。"""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./knowledge.db"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "documents"
    mineru_base_url: str = "http://localhost:8080"
    max_upload_bytes: int = 52_428_800


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免每个请求重复解析环境变量。"""
    return Settings()
