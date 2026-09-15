from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.database import Base
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.tag import DocumentTag, Tag
from app.services.search_service import KeywordSearchService


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_version(db: Session, document: Document, version_number: int, content: str) -> DocumentVersion:
    version = DocumentVersion(document_id=document.id, version=version_number, source_path=document.storage_path, markdown_path=f"n/{version_number}.md", json_path=f"n/{version_number}.json", parser="test")
    db.add(version)
    db.flush()
    db.add(DocumentChunk(document_id=document.id, document_version_id=version.id, chunk_index=0, content=content, heading_path="员工制度 > 请假", page_start=version_number, page_end=version_number, character_count=len(content), token_estimate=3))
    return version


def test_search_is_scoped_to_knowledge_base_latest_version_and_tags() -> None:
    db = make_session()
    target_base, other_base = KnowledgeBase(name="人力"), KnowledgeBase(name="其他")
    tag = Tag(name="制度")
    db.add_all([target_base, other_base, tag])
    db.flush()
    document = Document(filename="员工手册.pdf", content_type="application/pdf", file_size=1, storage_path="raw/search/a", status=DocumentStatus.PARSED, knowledge_base_id=target_base.id)
    other = Document(filename="其他.pdf", content_type="application/pdf", file_size=1, storage_path="raw/search/b", status=DocumentStatus.PARSED, knowledge_base_id=other_base.id)
    db.add_all([document, other])
    db.flush()
    add_version(db, document, 1, "旧版本请假办法")
    latest = add_version(db, document, 2, "员工请假需要提前申请")
    add_version(db, other, 1, "其他知识库的请假制度")
    db.add(DocumentTag(document_id=document.id, tag_id=tag.id))
    db.commit()

    result = KeywordSearchService(db).search(target_base.id, "请假", 1, 20, [tag.id])

    assert result.total == 1
    assert result.items[0].document_id == document.id
    assert result.items[0].version == latest.version
    assert result.items[0].page_start == 2
    assert KeywordSearchService(db).search(target_base.id, "请假", 1, 20, ["missing"]).total == 0
