"""数据库引擎与会话工厂。

SQLite 开发期也必须开启外键约束。数据库迁移全部由 Alembic 管理，
不允许启动时静默重建表。
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _enable_sqlite_fk(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(url: str) -> Engine:
    """按 URL 构建引擎；SQLite 启用外键约束并放宽线程检查（测试/本地单进程）。"""
    engine_kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **engine_kwargs)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_fk)
    return engine


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings().database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def reset_engine() -> None:
    """释放缓存的引擎与会话工厂，使后续调用按最新配置重建（测试用）。"""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_session() -> Iterator[Session]:
    """FastAPI 依赖：每个请求一个会话。"""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
