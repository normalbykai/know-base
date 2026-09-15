from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.tag import DocumentTag, Tag


class KnowledgeBaseService:
    """协调知识库、标签和文档归属，确保检索边界由服务端统一维护。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def delete_knowledge_base(self, knowledge_base: KnowledgeBase) -> None:
        """有文档时拒绝删除，防止资料在未确认的情况下失去检索归属。"""
        if self.db.scalar(select(func.count()).select_from(Document).where(Document.knowledge_base_id == knowledge_base.id)):
            raise ValueError("知识库仍包含文档，请先转移或删除其中的文档")
        self.db.delete(knowledge_base)
        self.db.commit()

    def assign_document(self, document: Document, knowledge_base_id: str | None) -> None:
        """归档前确认目标知识库存在；null 用于将历史文档移回未归档区。"""
        if knowledge_base_id and not self.db.get(KnowledgeBase, knowledge_base_id):
            raise ValueError("目标知识库不存在")
        document.knowledge_base_id = knowledge_base_id
        self.db.commit()
        self.db.refresh(document)

    def replace_document_tags(self, document: Document, tag_ids: list[str]) -> list[Tag]:
        """标签集合整体替换，拒绝不存在标签以避免产生孤儿关联。"""
        unique_ids = list(dict.fromkeys(tag_ids))
        tags = list(self.db.scalars(select(Tag).where(Tag.id.in_(unique_ids)))) if unique_ids else []
        if len(tags) != len(unique_ids):
            raise ValueError("包含不存在的标签")
        self.db.query(DocumentTag).filter(DocumentTag.document_id == document.id).delete(synchronize_session=False)
        self.db.add_all([DocumentTag(document_id=document.id, tag_id=tag_id) for tag_id in unique_ids])
        self.db.commit()
        return tags

    def document_tags(self, document_id: str) -> list[Tag]:
        """按标签名称返回文档标签，确保管理页稳定展示。"""
        return list(self.db.scalars(
            select(Tag).join(DocumentTag, DocumentTag.tag_id == Tag.id).where(DocumentTag.document_id == document_id).order_by(Tag.name)
        ))
