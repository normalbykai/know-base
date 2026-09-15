from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.database import Base
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.schemas.document import DocumentBlock, DocumentModel
from app.services.chunk_backfill_service import ChunkBackfillService


class FakeStorage:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects

    def get_bytes(self, path: str) -> bytes:
        return self.objects[path]


def test_backfill_creates_missing_chunks_and_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    document = Document(filename="history.pdf", content_type="application/pdf", file_size=1, storage_path="raw/backfill/a", status=DocumentStatus.PARSED)
    db.add(document)
    db.flush()
    version = DocumentVersion(document_id=document.id, version=1, source_path=document.storage_path, markdown_path="n/a.md", json_path="n/a.json", parser="test")
    db.add(version)
    db.commit()
    model = DocumentModel(document_id=document.id, title="历史", blocks=[DocumentBlock(id="b1", type="paragraph", text="可搜索的历史内容", page=3)])
    service = ChunkBackfillService(db, FakeStorage({version.json_path: model.model_dump_json().encode()}))

    first = service.run()
    second = service.run()

    assert first.processed == 1 and first.failed == {}
    assert second.processed == 0 and second.failed == {}
    assert db.query(DocumentChunk).filter(DocumentChunk.document_version_id == version.id).count() == 1
