from pydantic import BaseModel, Field


class SearchResultOut(BaseModel):
    """可追溯的关键词命中，引用定位不依赖前端再次拼接数据库信息。"""
    chunk_id: str
    document_id: str
    filename: str
    version: int
    heading_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    content: str
    score: float = Field(ge=0)


class SearchResponse(BaseModel):
    """知识库范围内的分页检索响应。"""
    query: str
    total: int
    page: int
    page_size: int
    items: list[SearchResultOut]
