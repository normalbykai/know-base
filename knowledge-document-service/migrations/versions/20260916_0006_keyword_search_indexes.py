"""为中文关键词检索启用 trigram 索引。"""

from alembic import op


revision = "20260916_0006"
down_revision = "20260915_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """pg_trgm 支持中文子串的 GIN 加速和相似度排序，不依赖英文分词器。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX ix_document_chunks_content_trgm ON document_chunks USING gin (content gin_trgm_ops)")
    op.execute("CREATE INDEX ix_document_chunks_heading_path_trgm ON document_chunks USING gin (heading_path gin_trgm_ops)")


def downgrade() -> None:
    """仅移除本项目索引；扩展可能被其他表使用，因此不主动删除。"""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_heading_path_trgm")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_trgm")
