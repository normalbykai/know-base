from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.models.tag import DocumentTag
from app.schemas.search import SearchResponse, SearchResultOut


class KeywordSearchService:
    """在知识库边界内搜索最新解析版本，PostgreSQL 使用 pg_trgm 增强中文排序。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, knowledge_base_id: str, query: str, page: int, page_size: int, tag_ids: list[str] | None = None) -> SearchResponse:
        """只返回 PARSED 文档最新版本的 Chunk，历史版本仍可预览但不参与默认召回。"""
        keyword = query.strip()
        pattern = f"%{keyword}%"
        heading_match = DocumentChunk.heading_path.ilike(pattern)
        content_match = DocumentChunk.content.ilike(pattern)
        exact_score = case((heading_match, 1.0), (content_match, 0.8), else_=0.0)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            score = func.greatest(
                exact_score,
                func.similarity(func.coalesce(DocumentChunk.heading_path, ""), keyword),
                func.similarity(DocumentChunk.content, keyword),
            )
        else:
            # SQLite 用于单元测试和轻量开发，生产 PostgreSQL 会使用 trigram 相似度。
            score = exact_score
        latest_version = (
            select(func.max(DocumentVersion.version))
            .where(DocumentVersion.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )
        filters = [
            Document.knowledge_base_id == knowledge_base_id,
            Document.status == DocumentStatus.PARSED,
            DocumentVersion.version == latest_version,
            or_(heading_match, content_match),
        ]
        if tag_ids:
            filters.append(exists(select(DocumentTag.id).where(DocumentTag.document_id == Document.id, DocumentTag.tag_id.in_(tag_ids))))
        base = (
            select(DocumentChunk, Document, DocumentVersion, score.label("score"))
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.document_version_id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters)
        )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = self.db.execute(
            base.order_by(score.desc(), Document.updated_at.desc(), DocumentChunk.chunk_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return SearchResponse(
            query=keyword,
            total=total,
            page=page,
            page_size=page_size,
            items=[
                SearchResultOut(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    filename=document.filename,
                    version=version.version,
                    heading_path=chunk.heading_path,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    content=chunk.content,
                    score=round(float(row_score), 4),
                )
                for chunk, document, version, row_score in rows
            ],
        )
