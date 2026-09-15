"""识别并终止失联的解析任务，防止文档永久停留在 PARSING。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.parse_task import ParseTask


TASK_TIMEOUT_CODE = "TASK_TIMEOUT"
TASK_TIMEOUT_MESSAGE = "解析任务超过允许执行时间，请重新解析；若反复出现，请检查解析服务。"


class TaskRecoveryService:
    """恢复器只处理已开始且超时的任务，不自动重试以避免产生不可控的外部调用。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def recover_timed_out_tasks(self, timeout_seconds: int, now: datetime | None = None) -> list[str]:
        """使用行锁领取超时任务，使恢复器与解析 Worker 的终态写入互斥。"""
        current_time = now or datetime.now(timezone.utc)
        cutoff = current_time - timedelta(seconds=timeout_seconds)
        candidates = list(self.db.scalars(
            select(ParseTask)
            .where(ParseTask.status == DocumentStatus.PARSING, ParseTask.started_at.is_not(None), ParseTask.started_at < cutoff)
            .order_by(ParseTask.started_at)
            .with_for_update(skip_locked=True)
        ))
        recovered: list[str] = []
        for task in candidates:
            # 同一顺序锁定文档，避免与 Worker 保存结果、其他恢复器形成死锁。
            document = self.db.scalar(
                select(Document).where(Document.id == task.document_id).with_for_update().execution_options(populate_existing=True)
            )
            if task.status != DocumentStatus.PARSING or document is None:
                continue
            task.status = DocumentStatus.FAILED
            task.error_code = TASK_TIMEOUT_CODE
            task.error_message = TASK_TIMEOUT_MESSAGE
            task.finished_at = current_time
            if document.status == DocumentStatus.PARSING:
                document.status = DocumentStatus.FAILED
            recovered.append(task.id)
        self.db.commit()
        return recovered
