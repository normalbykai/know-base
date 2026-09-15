import json
from datetime import datetime, timezone

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import update

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.parse_task import ParseTask
from app.parsers.router import ParserRouter
from app.services.document_service import DocumentService, TaskNoLongerActive
from app.services.normalizer import DocumentNormalizer

# worker 与 API 共用 Redis broker，API 只投递 ID，避免在消息中传输大文件。
dramatiq.set_broker(RedisBroker(url=get_settings().redis_url))


def error_code_for(exc: Exception) -> str:
    """将常见可恢复失败归类，前端无需解析供应商的错误文本。"""
    message = str(exc).lower()
    if "not configured" in message:
        return "PARSER_NOT_CONFIGURED"
    if "currently supports" in message or "unsupported" in message:
        return "UNSUPPORTED_FILE"
    if "max_pages" in message or "pages;" in message:
        return "DOCUMENT_LIMIT_EXCEEDED"
    if "unavailable" in message or "request failed" in message or "http status" in message:
        return "PARSER_UNAVAILABLE"
    return "PARSE_FAILED"


@dramatiq.actor(max_retries=0)
def parse_document(task_id: str) -> None:
    """消费一个解析任务，负责状态迁移、解析、标准化和失败记录。"""
    db = SessionLocal()
    try:
        task = db.get(ParseTask, task_id)
        if task is None:
            return
        # 条件更新是领取任务的唯一入口；重复消息只能由一个 Worker 成功领取。
        started_at = datetime.now(timezone.utc)
        claim = db.execute(
            update(ParseTask)
            .where(ParseTask.id == task_id, ParseTask.status == DocumentStatus.QUEUED)
            .values(status=DocumentStatus.PARSING, started_at=started_at)
        )
        if claim.rowcount != 1:
            # 幂等保护：重复消息或被重试替代的旧任务无需再次处理。
            db.rollback()
            return
        document = db.get(Document, task.document_id)
        if document is None:
            db.rollback()
            return
        document.status = DocumentStatus.PARSING
        db.commit()
        db.refresh(task)
        service = DocumentService(db)
        try:
            source = service.storage.get_bytes(document.storage_path)
            parser = ParserRouter().resolve(document.content_type, document.filename, task.parser)
            parsed = parser.parse(document.filename, document.content_type, source)
            model = DocumentNormalizer().normalize(document.id, document.filename, document.content_type, parsed.raw_json, parsed.markdown)
            service.save_result(document, task, json.dumps(parsed.raw_json, ensure_ascii=False).encode(), parsed.markdown.encode(), model.model_dump_json().encode(), parser.name, parsed.parser_version)
        except TaskNoLongerActive:
            # 恢复器已提交超时终态；保留它的错误码和用户可读原因。
            return
        except Exception as exc:
            # 任务失败不抛回 broker 自动重试，由用户明确执行重试并保留原因。
            task.status = document.status = DocumentStatus.FAILED
            task.error_code = error_code_for(exc)
            task.error_message = str(exc)[:4000]
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
