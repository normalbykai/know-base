import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeBase(Base):
    """知识库是文档检索和权限隔离的一级业务边界。"""

    __tablename__ = "knowledge_bases"
    __table_args__ = {"comment": "知识库主表，保存可独立管理、检索和授权的资料集合。"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="知识库 UUID 主键。")
    name: Mapped[str] = mapped_column(String(128), unique=True, comment="知识库名称，当前单租户范围内唯一。")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="知识库用途和内容范围说明，可为空。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="知识库创建时间，含时区。")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="知识库最后更新时间，含时区。")
