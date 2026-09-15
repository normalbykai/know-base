import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.models.parse_task import ParseTask
from app.schemas.document import DocumentBlock, DocumentModel
from app.services.document_service import DocumentService


class FakeStorage:
    """记录对象清理前缀，验证删除流程不依赖真实 MinIO。"""

    def __init__(self) -> None:
        self.deleted_prefixes: list[str] = []

    def delete_prefix(self, prefix: str) -> None:
        self.deleted_prefixes.append(prefix)

    def put_bytes(self, path: str, data: bytes, content_type: str) -> None:
        """保存调用痕迹即可；分块持久化测试不依赖实际对象存储。"""


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_delete_document_removes_metadata_and_all_document_storage_prefixes() -> None:
    db = make_session()
    document = Document(filename="guide.pdf", content_type="application/pdf", file_size=3, storage_path="raw/doc-1/original", status=DocumentStatus.PARSED)
    db.add(document)
    db.flush()
    db.add(ParseTask(document_id=document.id, parser="deepseek_vision", status=DocumentStatus.PARSED))
    db.add(DocumentVersion(document_id=document.id, version=1, source_path=document.storage_path, markdown_path="normalized/doc-1/v1/document.md", json_path="normalized/doc-1/v1/document.json", parser="deepseek_vision"))
    db.commit()
    storage = FakeStorage()

    DocumentService(db, storage=storage).delete_document(document)

    assert db.get(Document, document.id) is None
    assert storage.deleted_prefixes == [f"raw/{document.id}/", f"parsed/{document.id}/", f"normalized/{document.id}/"]


def test_delete_document_rejects_active_parse_before_removing_objects() -> None:
    db = make_session()
    document = Document(filename="active.pdf", content_type="application/pdf", file_size=3, storage_path="raw/doc-2/original", status=DocumentStatus.PARSING)
    db.add(document)
    db.commit()
    storage = FakeStorage()

    with pytest.raises(ValueError, match="不能删除"):
        DocumentService(db, storage=storage).delete_document(document)

    assert storage.deleted_prefixes == []
    assert db.get(Document, document.id) is not None


def test_save_result_persists_chunks_with_its_immutable_version() -> None:
    db = make_session()
    document = Document(filename="chunk.pdf", content_type="application/pdf", file_size=3, storage_path="raw/chunk/original", status=DocumentStatus.PARSING)
    db.add(document)
    db.flush()
    task = ParseTask(document_id=document.id, parser="deepseek_vision", status=DocumentStatus.PARSING)
    db.add(task)
    db.commit()
    model = DocumentModel(document_id=document.id, title="分块", blocks=[DocumentBlock(id="b1", type="heading", level=1, text="规则", page=1), DocumentBlock(id="b2", type="paragraph", text="正文内容", page=1)])

    version = DocumentService(db, storage=FakeStorage()).save_result(document, task, b"{}", "# 规则\n正文内容".encode(), model.model_dump_json().encode(), model, "deepseek_vision", "test")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_version_id == version.id).all()
    assert len(chunks) == 1
    assert chunks[0].heading_path == "规则"
    assert chunks[0].content == "正文内容"
