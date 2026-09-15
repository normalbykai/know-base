"""新增解析版本的不可变文档分块。"""

from alembic import op
import sqlalchemy as sa


revision = "20260915_0005"
down_revision = "20260915_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """分块只关联成功解析版本，避免未完成结果进入未来检索索引。"""
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("heading_path", sa.String(1024), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("document_version_id", "chunk_index", name="uq_document_chunks_version_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_document_version_id", "document_chunks", ["document_version_id"])
    op.execute("COMMENT ON TABLE document_chunks IS '文档解析版本的检索分块表，保存内容、标题上下文、页码与长度元数据。'")
    op.execute("COMMENT ON COLUMN document_chunks.id IS '分块 UUID 主键。'")
    op.execute("COMMENT ON COLUMN document_chunks.document_id IS '所属逻辑文档 UUID 外键。'")
    op.execute("COMMENT ON COLUMN document_chunks.document_version_id IS '所属不可变解析版本 UUID 外键。'")
    op.execute("COMMENT ON COLUMN document_chunks.chunk_index IS '版本内从 0 递增的稳定分块顺序。'")
    op.execute("COMMENT ON COLUMN document_chunks.content IS '供关键词、向量和引用展示使用的分块正文。'")
    op.execute("COMMENT ON COLUMN document_chunks.heading_path IS '分块所在标题层级路径，以大于号分隔；无标题时为空。'")
    op.execute("COMMENT ON COLUMN document_chunks.page_start IS '分块起始页码，解析器未提供页码时为空。'")
    op.execute("COMMENT ON COLUMN document_chunks.page_end IS '分块结束页码，解析器未提供页码时为空。'")
    op.execute("COMMENT ON COLUMN document_chunks.character_count IS '分块正文字符数，用于长度控制和质量诊断。'")
    op.execute("COMMENT ON COLUMN document_chunks.token_estimate IS '分块 token 估算值，当前按字符数近似计算。'")
    op.execute("COMMENT ON COLUMN document_chunks.created_at IS '分块创建时间，含时区。'")


def downgrade() -> None:
    """删除分块索引与表，不影响原始文档、版本和标准化产物。"""
    op.drop_index("ix_document_chunks_document_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
