from dataclasses import dataclass, field

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.schemas.document import DocumentModel
from app.services.chunking_service import DocumentChunkService
from app.services.storage_service import StorageService


@dataclass
class ChunkBackfillReport:
    """历史分块回填结果，失败项保留版本 ID 和原因以便定向排查。"""
    processed: int = 0
    skipped: int = 0
    failed: dict[str, str] = field(default_factory=dict)


class ChunkBackfillService:
    """为旧解析版本补充分块；只处理没有任何 Chunk 的版本并可安全重复执行。"""

    def __init__(self, db: Session, storage: StorageService | None = None) -> None:
        self.db = db
        self.storage = storage or StorageService()

    def run(self) -> ChunkBackfillReport:
        """逐版本提交，单份历史产物损坏不会阻断其他版本回填。"""
        report = ChunkBackfillReport()
        versions = list(self.db.scalars(
            select(DocumentVersion)
            .where(~exists(select(DocumentChunk.id).where(DocumentChunk.document_version_id == DocumentVersion.id)))
            .order_by(DocumentVersion.created_at)
        ))
        for version in versions:
            version_id = version.id
            try:
                chunk_service = DocumentChunkService(self.db, get_settings().document_chunk_max_characters)
                if chunk_service.version_has_chunks(version_id):
                    report.skipped += 1
                    continue
                model = DocumentModel.model_validate_json(self.storage.get_bytes(version.json_path))
                chunk_service.add_version_chunks(version, model)
                self.db.commit()
                report.processed += 1
            except IntegrityError:
                # 并行回填已先完成时唯一约束会保护数据，本进程将该版本视为已跳过。
                self.db.rollback()
                report.skipped += 1
            except Exception as exc:
                self.db.rollback()
                report.failed[version_id] = str(exc)[:1000]
        return report
