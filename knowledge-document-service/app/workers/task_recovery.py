"""独立运行的解析任务恢复进程。"""

import logging
import threading

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.task_recovery_service import TaskRecoveryService


logger = logging.getLogger(__name__)


def recover_once() -> list[str]:
    """每次扫描独占一个数据库会话，避免长期循环持有失效连接。"""
    settings = get_settings()
    db = SessionLocal()
    try:
        return TaskRecoveryService(db).recover_timed_out_tasks(settings.parse_task_timeout_seconds)
    finally:
        db.close()


def run(stop_event: threading.Event | None = None) -> None:
    """按配置间隔扫描；容器收到终止信号时由运行时结束进程。"""
    settings = get_settings()
    stopper = stop_event or threading.Event()
    while not stopper.is_set():
        try:
            recovered = recover_once()
            if recovered:
                logger.warning("Recovered timed-out parse tasks: %s", ", ".join(recovered))
        except Exception:
            # 基础设施短暂不可用时保活，下一轮继续扫描，不让恢复能力本身成为单点故障。
            logger.exception("Timed-out parse-task recovery scan failed")
        stopper.wait(settings.task_recovery_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run()
