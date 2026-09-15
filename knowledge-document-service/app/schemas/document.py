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
    knowledge_base_id: str | None = None

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    """文档管理列表的分页契约；total 供前端使用服务端分页。"""
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


class DocumentIdsRequest(BaseModel):
    """批量管理动作的文档 UUID 集合，至少包含一个目标。"""
    document_ids: list[str] = Field(min_length=1, max_length=100)


class BatchOperationOut(BaseModel):
    """批量操作结果；跳过项保留原因，避免用户误以为全部成功。"""
    processed_ids: list[str] = Field(default_factory=list)
    skipped: dict[str, str] = Field(default_factory=dict)


class ParseTaskOut(BaseModel):
    """面向轮询界面的解析进度和可展示错误信息。"""
    task_id: str
    document_id: str
    status: str
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    parser: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class DocumentVersionOut(BaseModel):
    """供管理端选择历史解析结果的只读版本元数据。"""
    id: str
    document_id: str
    version: int
    parser: str
    parser_version: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkOut(BaseModel):
    """供管理端检查分块边界、页码和标题上下文的只读契约。"""
    id: str
    document_id: str
    document_version_id: str
    chunk_index: int
    content: str
    heading_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    character_count: int
    token_estimate: int

    model_config = {"from_attributes": True}


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
