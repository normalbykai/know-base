from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

# pool_pre_ping 会在复用连接前探测，降低长时间运行后拿到失效连接的概率。
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 实体的声明式基类，也是 Alembic 的元数据来源。"""
    pass


def get_db():
    """为单个 HTTP 请求创建并在结束时释放数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
