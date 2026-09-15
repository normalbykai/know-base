from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.document import Document, DocumentStatus
from app.models.parse_task import ParseTask
from app.services.task_recovery_service import TASK_TIMEOUT_CODE, TaskRecoveryService


def make_session() -> Session:
    """使用隔离内存库验证恢复逻辑，无需依赖本地 PostgreSQL。"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_parsing_task(db: Session, started_at: datetime) -> tuple[Document, ParseTask]:
    document = Document(filename="handbook.pdf", content_type="application/pdf", file_size=1, storage_path="raw/test/original", status=DocumentStatus.PARSING)
    db.add(document)
    db.flush()
    task = ParseTask(document_id=document.id, parser="deepseek_vision", status=DocumentStatus.PARSING, started_at=started_at)
    db.add(task)
    db.commit()
    return document, task


def test_recovery_marks_only_timed_out_parsing_task_as_failed() -> None:
    db = make_session()
    now = datetime.now(timezone.utc)
    document, task = add_parsing_task(db, now - timedelta(seconds=120))

    recovered = TaskRecoveryService(db).recover_timed_out_tasks(timeout_seconds=60, now=now)

    assert recovered == [task.id]
    assert db.get(ParseTask, task.id).status == DocumentStatus.FAILED
    assert db.get(ParseTask, task.id).error_code == TASK_TIMEOUT_CODE
    assert db.get(Document, document.id).status == DocumentStatus.FAILED


def test_recovery_leaves_recent_and_non_parsing_tasks_unchanged() -> None:
    db = make_session()
    now = datetime.now(timezone.utc)
    document, task = add_parsing_task(db, now - timedelta(seconds=30))
    completed = ParseTask(document_id=document.id, parser="deepseek_vision", status=DocumentStatus.PARSED, started_at=now - timedelta(days=1))
    db.add(completed)
    db.commit()

    assert TaskRecoveryService(db).recover_timed_out_tasks(timeout_seconds=60, now=now) == []
    assert db.get(ParseTask, task.id).status == DocumentStatus.PARSING
    assert db.get(ParseTask, completed.id).status == DocumentStatus.PARSED
