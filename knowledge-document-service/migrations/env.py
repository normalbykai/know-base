from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base
import app.models  # noqa: F401

# Alembic 从 alembic.ini 读取基础配置（脚本目录、日志等）。
config = context.config
# 数据库连接地址以应用 Settings 为准：可由 .env 或环境变量 DATABASE_URL 覆盖，
# 因而不依赖 alembic.ini 中仅用于兜底/示例的 sqlalchemy.url。
config.set_main_option("sqlalchemy.url", get_settings().database_url)
# 导入 app.models 会注册所有 ORM 表；Base.metadata 供 --autogenerate 比对模型与数据库结构。
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # 离线模式不建立数据库连接，只根据 URL 方言将迁移操作渲染为 SQL。
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # 在线模式按 sqlalchemy.* 配置创建一次性连接；NullPool 避免迁移进程维护连接池。
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # 将实际连接和模型元数据交给 Alembic，在事务中依次执行各版本升级/降级操作。
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    # 例如 alembic upgrade head --sql：输出 SQL，适合交由 DBA 审核或手工执行。
    run_migrations_offline()
else:
    # 常规 alembic upgrade head：直接连接数据库并应用迁移。
    run_migrations_online()
