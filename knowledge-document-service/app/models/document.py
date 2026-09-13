import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    """文档与解析任务共用的受控状态机枚举。"""
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    FAILED = "FAILED"


class Document(Base):
    """用户上传的逻辑文档；解析产物及历史版本不直接挂在此表。"""
    __tablename__ = "documents"
    __table_args__ = {"comment": "逻辑文档主表，记录用户上传文件及其当前处理状态。"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="文档 UUID 主键。")
    knowledge_base_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True, comment="所属知识库 UUID；第一阶段允许为空。")
    filename: Mapped[str] = mapped_column(String(512), comment="用户上传时的原始文件名，仅用于展示。")
    content_type: Mapped[str] = mapped_column(String(255), comment="上传文件的 MIME 内容类型。")
    file_size: Mapped[int] = mapped_column(Integer, comment="原始文件大小，单位为字节。")
    storage_path: Mapped[str] = mapped_column(String(1024), unique=True, comment="原始文件在对象存储中的内部路径。")
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, comment="当前处理状态：UPLOADED、QUEUED、PARSING、PARSED 或 FAILED。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="文档记录创建时间，含时区。")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="文档记录最后更新时间，含时区。")


class DocumentVersion(Base):
    """一次成功解析对应一个不可变版本，允许安全升级或替换解析器。"""
    __tablename__ = "document_versions"
    __table_args__ = {"comment": "文档成功解析后的不可变版本记录，保存标准化产物位置。"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="文档版本 UUID 主键。")
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, comment="关联的逻辑文档 UUID。")
    version: Mapped[int] = mapped_column(Integer, comment="同一文档内从 1 开始递增的解析版本号。")
    source_path: Mapped[str] = mapped_column(String(1024), comment="本版本对应的原始文件对象存储路径。")
    markdown_path: Mapped[str] = mapped_column(String(1024), comment="标准化 Markdown 产物的对象存储路径。")
    json_path: Mapped[str] = mapped_column(String(1024), comment="标准化 DocumentModel JSON 的对象存储路径。")
    parser: Mapped[str] = mapped_column(String(64), comment="生成该版本的解析器标识，例如 mineru。")
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="解析器或模型版本；未知时为空。")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="该解析版本创建时间，含时区。")
