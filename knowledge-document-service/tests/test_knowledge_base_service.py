import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.database import Base
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.tag import DocumentTag, Tag
from app.services.knowledge_base_service import KnowledgeBaseService


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_assign_and_replace_document_tags_requires_existing_records() -> None:
    db = make_session()
    knowledge_base = KnowledgeBase(name="人力资源")
    tag_a, tag_b = Tag(name="制度"), Tag(name="内部")
    document = Document(filename="handbook.pdf", content_type="application/pdf", file_size=1, storage_path="raw/knowledge-test/original")
    db.add_all([knowledge_base, tag_a, tag_b, document])
    db.commit()
    service = KnowledgeBaseService(db)

    service.assign_document(document, knowledge_base.id)
    tags = service.replace_document_tags(document, [tag_a.id, tag_b.id, tag_a.id])

    assert db.get(Document, document.id).knowledge_base_id == knowledge_base.id
    assert {tag.name for tag in tags} == {"制度", "内部"}
    assert db.query(DocumentTag).filter(DocumentTag.document_id == document.id).count() == 2
    with pytest.raises(ValueError, match="不存在"):
        service.replace_document_tags(document, ["missing-tag"])


def test_nonempty_knowledge_base_cannot_be_deleted() -> None:
    db = make_session()
    knowledge_base = KnowledgeBase(name="产品资料")
    db.add(knowledge_base)
    db.flush()
    db.add(Document(filename="spec.pdf", content_type="application/pdf", file_size=1, storage_path="raw/knowledge-delete/original", knowledge_base_id=knowledge_base.id))
    db.commit()

    with pytest.raises(ValueError, match="仍包含文档"):
        KnowledgeBaseService(db).delete_knowledge_base(knowledge_base)
