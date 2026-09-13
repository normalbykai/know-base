import json
from datetime import datetime, timezone

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.parse_task import ParseTask
from app.parsers.router import ParserRouter
from app.services.document_service import DocumentService
from app.services.normalizer import DocumentNormalizer

# worker 与 API 共用 Redis broker，API 只投递 ID，避免在消息中传输大文件。
dramatiq.set_broker(RedisBroker(url=get_settings().redis_url))


@dramatiq.actor(max_retries=0)
def parse_document(task_id: str) -> None:
    """消费一个解析任务，负责状态迁移、解析、标准化和失败记录。"""
    db = SessionLocal()
    try:
        task = db.get(ParseTask, task_id)
        if task is None or task.status != DocumentStatus.QUEUED:
            # 幂等保护：重复消息或被重试替代的旧任务无需再次处理。
            return
        document = db.get(Document, task.document_id)
        if document is None:
            return
        task.status = document.status = DocumentStatus.PARSING
        task.started_at = datetime.now(timezone.utc)
        db.commit()
        service = DocumentService(db)
        try:
            source = service.storage.get_bytes(document.storage_path)
            parser = ParserRouter().resolve(document.content_type, document.filename)
            parsed = parser.parse(document.filename, document.content_type, source)
            model = DocumentNormalizer().normalize(document.id, document.filename, document.content_type, parsed.raw_json, parsed.markdown)
            service.save_result(document, task, json.dumps(parsed.raw_json, ensure_ascii=False).encode(), parsed.markdown.encode(), model.model_dump_json().encode(), parser.name, parsed.parser_version)
        except Exception as exc:
            # 任务失败不抛回 broker 自动重试，由用户明确执行重试并保留原因。
            task.status = document.status = DocumentStatus.FAILED
            task.error_code = "PARSE_FAILED"
            task.error_message = str(exc)[:4000]
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
