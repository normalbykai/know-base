"""一次性回填历史解析版本的命令入口。"""

import json

from app.core.database import SessionLocal
from app.services.chunk_backfill_service import ChunkBackfillService


def run() -> int:
    """输出机器可读汇总；存在失败版本时返回非零退出码。"""
    db = SessionLocal()
    try:
        report = ChunkBackfillService(db).run()
        print(json.dumps({"processed": report.processed, "skipped": report.skipped, "failed": report.failed}, ensure_ascii=False))
        return 1 if report.failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
