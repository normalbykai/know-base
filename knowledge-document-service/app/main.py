from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import get_settings

# API 只暴露业务契约；数据库建表由 Alembic migration 负责。
app = FastAPI(title="Knowledge Document Service", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(documents_router)
