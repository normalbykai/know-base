"""为文档解析版本增加唯一性约束。"""

from alembic import op


revision = "20260915_0003"
down_revision = "20260913_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """数据库层确保同一文档的版本号不可重复，避免并发任务覆盖历史。"""
    op.create_unique_constraint(
        "uq_document_versions_document_id_version",
        "document_versions",
        ["document_id", "version"],
    )


def downgrade() -> None:
    """仅移除本次新增的约束，不删除任何版本记录。"""
    op.drop_constraint("uq_document_versions_document_id_version", "document_versions", type_="unique")
