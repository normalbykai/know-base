from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    """面向前端的文档元数据，刻意不暴露对象存储内部路径。"""
    id: str
    filename: str
    content_type: str
    file_size: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ParseTaskOut(BaseModel):
    """面向轮询界面的解析进度和可展示错误信息。"""
    task_id: str
    document_id: str
    status: str
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None


class DocumentBlock(BaseModel):
    """跨解析器的最小内容块；后续 Chunk 引擎只依赖此结构。"""
    id: str
    type: Literal["heading", "paragraph", "table", "image", "list", "code"]
    page: int | None = None
    level: int | None = None
    text: str | None = None
    content: str | None = None


class DocumentModel(BaseModel):
    """第一阶段稳定输出契约，隔离 MinerU、Docling 等供应商格式。"""
    document_id: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    blocks: list[DocumentBlock] = Field(default_factory=list)
