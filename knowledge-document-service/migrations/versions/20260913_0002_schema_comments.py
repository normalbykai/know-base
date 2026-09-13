"""为文档基础设施表补充中文数据字典注释。"""

from alembic import op

revision = "20260913_0002"
down_revision = "20260913_0001"
branch_labels = None
depends_on = None


TABLE_COMMENTS = {
    "documents": "逻辑文档主表，记录用户上传文件及其当前处理状态。",
    "document_versions": "文档成功解析后的不可变版本记录，保存标准化产物位置。",
    "parse_tasks": "异步文档解析任务表，保存执行状态、错误信息和重试次数。",
}

COLUMN_COMMENTS = {
    "documents": {
        "id": "文档 UUID 主键。", "knowledge_base_id": "所属知识库 UUID；第一阶段允许为空。", "filename": "用户上传时的原始文件名，仅用于展示。", "content_type": "上传文件的 MIME 内容类型。", "file_size": "原始文件大小，单位为字节。", "storage_path": "原始文件在对象存储中的内部路径。", "status": "当前处理状态：UPLOADED、QUEUED、PARSING、PARSED 或 FAILED。", "created_at": "文档记录创建时间，含时区。", "updated_at": "文档记录最后更新时间，含时区。",
    },
    "document_versions": {
        "id": "文档版本 UUID 主键。", "document_id": "关联的逻辑文档 UUID。", "version": "同一文档内从 1 开始递增的解析版本号。", "source_path": "本版本对应的原始文件对象存储路径。", "markdown_path": "标准化 Markdown 产物的对象存储路径。", "json_path": "标准化 DocumentModel JSON 的对象存储路径。", "parser": "生成该版本的解析器标识，例如 mineru。", "parser_version": "解析器或模型版本；未知时为空。", "created_at": "该解析版本创建时间，含时区。",
    },
    "parse_tasks": {
        "id": "解析任务 UUID 主键。", "document_id": "待解析文档的 UUID。", "status": "任务状态：QUEUED、PARSING、PARSED 或 FAILED。", "parser": "本任务选用的解析器标识。", "started_at": "Worker 实际开始处理的时间，未开始时为空。", "finished_at": "任务成功或失败结束的时间，未结束时为空。", "error_code": "程序可识别的失败错误码；成功时为空。", "error_message": "供排障和用户提示使用的失败详情；成功时为空。", "retry_count": "该文档因失败重新入队的累计次数。", "created_at": "任务创建时间，含时区。", "updated_at": "任务最后更新时间，含时区。",
    },
}


def upgrade() -> None:
    """使用 PostgreSQL COMMENT 写入已部署数据库的数据字典。"""
    op.execute("COMMENT ON TYPE documentstatus IS '文档与解析任务状态枚举：UPLOADED已上传、QUEUED待处理、PARSING解析中、PARSED已解析、FAILED失败。'")
    for table, comment in TABLE_COMMENTS.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}'")
    for table, columns in COLUMN_COMMENTS.items():
        for column, comment in columns.items():
            op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{comment}'")


def downgrade() -> None:
    """回滚时移除本迁移新增的注释，不修改业务数据。"""
    op.execute("COMMENT ON TYPE documentstatus IS NULL")
    for table in TABLE_COMMENTS:
        op.execute(f"COMMENT ON TABLE {table} IS NULL")
    for table, columns in COLUMN_COMMENTS.items():
        for column in columns:
            op.execute(f"COMMENT ON COLUMN {table}.{column} IS NULL")
