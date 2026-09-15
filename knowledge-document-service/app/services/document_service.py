from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.models.parse_task import ParseTask
from app.core.config import get_settings
from app.schemas.document import DocumentModel
from app.services.chunking_service import DocumentChunker
from app.services.storage_service import StorageService


class TaskNoLongerActive(Exception):
    """任务已被超时恢复器终止，Worker 不应覆盖其最终状态。"""


class DocumentService:
    """协调文档、任务、版本和对象存储的领域服务。"""
    def __init__(self, db: Session, storage: StorageService | None = None) -> None:
        """允许注入存储实现，便于在测试中替换外部 MinIO。"""
        self.db, self.storage = db, storage or StorageService()

    def create_document(self, filename: str, content_type: str, data: bytes, knowledge_base_id: str | None = None) -> Document:
        """先取得 UUID，再以该 UUID 生成安全、不可猜测的原始文件路径。"""
        document = Document(filename=filename, content_type=content_type, file_size=len(data), storage_path="", knowledge_base_id=knowledge_base_id)
        self.db.add(document)
        self.db.flush()
        document.storage_path = f"raw/{document.id}/original"
        self.storage.put_bytes(document.storage_path, data, content_type)
        self.db.commit()
        self.db.refresh(document)
        return document

    def queue_parse(self, document: Document, retry: bool = False) -> ParseTask:
        """创建待消费任务；解析进行中禁止重复入队以避免版本竞争。"""
        if document.status == DocumentStatus.PARSING:
            raise ValueError("Document is already being parsed")
        previous = self.db.scalar(select(ParseTask).where(ParseTask.document_id == document.id).order_by(ParseTask.created_at.desc()))
        # 入队时固化解析器，避免环境变量变更后任务记录与实际执行器不一致。
        task = ParseTask(document_id=document.id, status=DocumentStatus.QUEUED, parser=get_settings().document_parser.lower(), retry_count=(previous.retry_count + 1 if retry and previous else 0))
        document.status = DocumentStatus.QUEUED
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def latest_task(self, document_id: str) -> ParseTask | None:
        """返回最新任务，供前端轮询解析状态。"""
        return self.db.scalar(select(ParseTask).where(ParseTask.document_id == document_id).order_by(ParseTask.created_at.desc()))

    def delete_document(self, document: Document) -> None:
        """删除文档的三层对象与关联元数据；解析中的文档禁止删除以避免 Worker 竞争。"""
        if document.status in {DocumentStatus.QUEUED, DocumentStatus.PARSING}:
            raise ValueError("正在处理的文档不能删除，请等待任务结束后再试")
        # 对象路径仅以服务端 UUID 构造，不依赖用户输入的文件名。
        for prefix in (f"raw/{document.id}/", f"parsed/{document.id}/", f"normalized/{document.id}/"):
            self.storage.delete_prefix(prefix)
        self.db.execute(delete(ParseTask).where(ParseTask.document_id == document.id))
        self.db.execute(delete(DocumentVersion).where(DocumentVersion.document_id == document.id))
        self.db.delete(document)
        self.db.commit()

    def save_result(self, document: Document, task: ParseTask, raw_json: bytes, markdown: bytes, normalized_json: bytes, document_model: DocumentModel, parser: str, parser_version: str | None) -> DocumentVersion:
        """保存三层产物并创建不可变版本；锁定任务避免覆盖超时恢复的状态。"""
        # 解析期间恢复器可能已将任务标记为超时。行锁确保两条终态路径只能有一方提交。
        locked_task = self.db.scalar(select(ParseTask).where(ParseTask.id == task.id).with_for_update().execution_options(populate_existing=True))
        locked_document = self.db.scalar(select(Document).where(Document.id == document.id).with_for_update().execution_options(populate_existing=True))
        if not locked_task or not locked_document or locked_task.status != DocumentStatus.PARSING or locked_document.status != DocumentStatus.PARSING:
            raise TaskNoLongerActive()
        version = (self.db.scalar(select(func.max(DocumentVersion.version)).where(DocumentVersion.document_id == locked_document.id)) or 0) + 1
        # 标准产物路径按版本隔离，解析器升级不会覆盖旧结果。
        prefix = f"normalized/{locked_document.id}/v{version}"
        markdown_path, json_path = f"{prefix}/document.md", f"{prefix}/document.json"
        self.storage.put_bytes(f"parsed/{locked_document.id}/v{version}/parser.json", raw_json, "application/json")
        self.storage.put_bytes(f"parsed/{locked_document.id}/v{version}/parser.md", markdown, "text/markdown")
        self.storage.put_bytes(markdown_path, markdown, "text/markdown")
        self.storage.put_bytes(json_path, normalized_json, "application/json")
        document_version = DocumentVersion(document_id=locked_document.id, version=version, source_path=locked_document.storage_path, markdown_path=markdown_path, json_path=json_path, parser=parser, parser_version=parser_version)
        self.db.add(document_version)
        self.db.flush()
        # 分块与版本元数据在同一事务提交，保证已解析版本一定具备可检索的稳定片段。
        chunker = DocumentChunker(get_settings().document_chunk_max_characters)
        self.db.add_all([
            DocumentChunk(document_id=locked_document.id, document_version_id=document_version.id, chunk_index=index, content=draft.content, heading_path=draft.heading_path, page_start=draft.page_start, page_end=draft.page_end, character_count=len(draft.content), token_estimate=chunker.token_estimate(draft.content))
            for index, draft in enumerate(chunker.chunk(document_model))
        ])
        locked_document.status = locked_task.status = DocumentStatus.PARSED
        locked_task.finished_at = datetime.now(timezone.utc)
        locked_task.error_code = locked_task.error_message = None
        self.db.commit()
        return document_version
