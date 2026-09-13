"""initial document infrastructure tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260913_0001"
down_revision = None
branch_labels = None
depends_on = None

# PostgreSQL 的 Enum 是独立数据库对象。create_type=False 防止 create_table 时再次创建它；
# upgrade 中的 checkfirst=True 则兼容上一次失败后仅残留 Enum 的本地开发数据库。
status = postgresql.ENUM("UPLOADED", "QUEUED", "PARSING", "PARSED", "FAILED", name="documentstatus", create_type=False)


def upgrade() -> None:
    # 只创建一次状态枚举；若此前失败迁移已经创建它，则安全复用。
    status.create(op.get_bind(), checkfirst=True)
    op.create_table("documents", sa.Column("id", sa.String(36), primary_key=True), sa.Column("knowledge_base_id", sa.String(36)), sa.Column("filename", sa.String(512), nullable=False), sa.Column("content_type", sa.String(255), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("storage_path", sa.String(1024), nullable=False, unique=True), sa.Column("status", status, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_index("ix_documents_knowledge_base_id", "documents", ["knowledge_base_id"])
    op.create_table("parse_tasks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False), sa.Column("status", status, nullable=False), sa.Column("parser", sa.String(64), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("error_code", sa.String(64)), sa.Column("error_message", sa.Text()), sa.Column("retry_count", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_index("ix_parse_tasks_document_id", "parse_tasks", ["document_id"])
    op.create_table("document_versions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("source_path", sa.String(1024), nullable=False), sa.Column("markdown_path", sa.String(1024), nullable=False), sa.Column("json_path", sa.String(1024), nullable=False), sa.Column("parser", sa.String(64), nullable=False), sa.Column("parser_version", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])


def downgrade() -> None:
    # 先删除引用该类型的表，再删除独立 Enum 类型。
    op.drop_table("document_versions")
    op.drop_table("parse_tasks")
    op.drop_table("documents")
    status.drop(op.get_bind(), checkfirst=True)
