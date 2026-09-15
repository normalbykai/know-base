import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentChunk(Base):
    """解析版本的不可变检索片段；后续关键词和向量索引只消费此表。"""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_version_id", "chunk_index", name="uq_document_chunks_version_index"),
        {"comment": "文档解析版本的检索分块表，保存内容、标题上下文、页码与长度元数据。"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="分块 UUID 主键。")
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True, comment="所属逻辑文档 UUID 外键。")
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), index=True, comment="所属不可变解析版本 UUID 外键。")
    chunk_index: Mapped[int] = mapped_column(Integer, comment="版本内从 0 递增的稳定分块顺序。")
    content: Mapped[str] = mapped_column(Text, comment="供关键词、向量和引用展示使用的分块正文。")
    heading_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="分块所在标题层级路径，以大于号分隔；无标题时为空。")
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="分块起始页码，解析器未提供页码时为空。")
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="分块结束页码，解析器未提供页码时为空。")
    character_count: Mapped[int] = mapped_column(Integer, comment="分块正文字符数，用于长度控制和质量诊断。")
    token_estimate: Mapped[int] = mapped_column(Integer, comment="分块 token 估算值，当前按字符数近似计算。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="分块创建时间，含时区。")
