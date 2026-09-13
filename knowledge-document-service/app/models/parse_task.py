import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.document import DocumentStatus


class ParseTask(Base):
    """异步解析任务；错误保留在任务中，避免污染文档元数据。"""
    __tablename__ = "parse_tasks"
    __table_args__ = {"comment": "异步文档解析任务表，保存执行状态、错误信息和重试次数。"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="解析任务 UUID 主键。")
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, comment="待解析文档的 UUID。")
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.QUEUED, comment="任务状态：QUEUED、PARSING、PARSED 或 FAILED。")
    parser: Mapped[str] = mapped_column(String(64), default="mineru", comment="本任务选用的解析器标识。")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Worker 实际开始处理的时间，未开始时为空。")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="任务成功或失败结束的时间，未结束时为空。")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="程序可识别的失败错误码；成功时为空。")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="供排障和用户提示使用的失败详情；成功时为空。")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="该文档因失败重新入队的累计次数。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="任务创建时间，含时区。")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="任务最后更新时间，含时区。")
