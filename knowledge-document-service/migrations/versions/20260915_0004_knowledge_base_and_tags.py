"""新增知识库、标签和文档归属关系。"""

from alembic import op
import sqlalchemy as sa


revision = "20260915_0004"
down_revision = "20260915_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """先建立归属实体，再为已有可空 knowledge_base_id 补齐外键约束。"""
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "document_tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("document_id", "tag_id", name="uq_document_tags_document_id_tag_id"),
    )
    op.create_index("ix_document_tags_document_id", "document_tags", ["document_id"])
    op.create_index("ix_document_tags_tag_id", "document_tags", ["tag_id"])
    # 旧阶段尚未有知识库表，历史预留值没有可验证的目标，迁移时统一归为未归档。
    op.execute("UPDATE documents SET knowledge_base_id = NULL WHERE knowledge_base_id IS NOT NULL")
    op.create_foreign_key("fk_documents_knowledge_base_id", "documents", "knowledge_bases", ["knowledge_base_id"], ["id"], ondelete="SET NULL")
    op.execute("COMMENT ON TABLE knowledge_bases IS '知识库主表，保存可独立管理、检索和授权的资料集合。'")
    op.execute("COMMENT ON COLUMN knowledge_bases.id IS '知识库 UUID 主键。'")
    op.execute("COMMENT ON COLUMN knowledge_bases.name IS '知识库名称，当前单租户范围内唯一。'")
    op.execute("COMMENT ON COLUMN knowledge_bases.description IS '知识库用途和内容范围说明，可为空。'")
    op.execute("COMMENT ON COLUMN knowledge_bases.created_at IS '知识库创建时间，含时区。'")
    op.execute("COMMENT ON COLUMN knowledge_bases.updated_at IS '知识库最后更新时间，含时区。'")
    op.execute("COMMENT ON TABLE tags IS '文档标签主表，保存用于筛选和运营分类的受控标签。'")
    op.execute("COMMENT ON COLUMN tags.id IS '标签 UUID 主键。'")
    op.execute("COMMENT ON COLUMN tags.name IS '标签名称，当前单租户范围内唯一。'")
    op.execute("COMMENT ON COLUMN tags.created_at IS '标签创建时间，含时区。'")
    op.execute("COMMENT ON TABLE document_tags IS '文档与标签关联表，记录一份文档拥有的多个分类标签。'")
    op.execute("COMMENT ON COLUMN document_tags.id IS '关联记录 UUID 主键。'")
    op.execute("COMMENT ON COLUMN document_tags.document_id IS '关联文档 UUID 外键。'")
    op.execute("COMMENT ON COLUMN document_tags.tag_id IS '关联标签 UUID 外键。'")
    op.execute("COMMENT ON COLUMN document_tags.created_at IS '关联创建时间，含时区。'")
    op.execute("COMMENT ON COLUMN documents.knowledge_base_id IS '所属知识库 UUID 外键；未归档文档为空。'")


def downgrade() -> None:
    """回滚归属与标签结构；文档本体和已有解析结果不删除。"""
    op.drop_constraint("fk_documents_knowledge_base_id", "documents", type_="foreignkey")
    op.execute("COMMENT ON COLUMN documents.knowledge_base_id IS '所属知识库 UUID；第一阶段允许为空。'")
    op.drop_index("ix_document_tags_tag_id", table_name="document_tags")
    op.drop_index("ix_document_tags_document_id", table_name="document_tags")
    op.drop_table("document_tags")
    op.drop_table("tags")
    op.drop_table("knowledge_bases")
