import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Tag(Base):
    """标签提供跨知识库的轻量分类，不替代知识库的权限边界。"""

    __tablename__ = "tags"
    __table_args__ = {"comment": "文档标签主表，保存用于筛选和运营分类的受控标签。"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="标签 UUID 主键。")
    name: Mapped[str] = mapped_column(String(64), unique=True, comment="标签名称，当前单租户范围内唯一。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="标签创建时间，含时区。")


class DocumentTag(Base):
    """文档与标签的多对多关联，禁止同一标签重复标记同一文档。"""

    __tablename__ = "document_tags"
    __table_args__ = (
        UniqueConstraint("document_id", "tag_id", name="uq_document_tags_document_id_tag_id"),
        {"comment": "文档与标签关联表，记录一份文档拥有的多个分类标签。"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="关联记录 UUID 主键。")
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True, comment="关联文档 UUID 外键。")
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), index=True, comment="关联标签 UUID 外键。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="关联创建时间，含时区。")
