from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from app.config import settings


def create_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """
    Создаёт асинхронный движок SQLAlchemy
    
    Args:
        database_url: URL подключения к БД (если None - берётся из настроек)
    
    Returns:
        AsyncEngine: асинхронный движок SQLAlchemy
    
    Examples:
        >>> engine = create_engine()  # из настроек
        >>> engine = create_engine("sqlite+aiosqlite:///test.db")
        >>> engine = create_engine("postgresql+asyncpg://user:pass@localhost/db")
    """
    url = database_url or settings.DATABASE_URL
    
    # Общие настройки для всех БД
    engine_kwargs = {
        "echo": False,  # SQL-логирование (можно включить для отладки)
        "future": True,  # Использовать новое API SQLAlchemy 2.0
    }
    
    # Специфичные настройки для SQLite
    if "sqlite" in url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    
    # Специфичные настройки для PostgreSQL
    elif "postgresql" in url:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
        engine_kwargs["pool_pre_ping"] = True
    
    # Для других БД (если понадобятся) - стандартные настройки
    
    return create_async_engine(url, **engine_kwargs)


# Глобальный движок (создаётся при первом импорте)
_engine: Optional[AsyncEngine] = None


def get_engine() -> AsyncEngine:
    """
    Возвращает глобальный движок (singleton)
    
    Returns:
        AsyncEngine: глобальный движок SQLAlchemy
    """
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def create_session_factory(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """
    Создаёт фабрику сессий для работы с БД
    
    Args:
        engine: движок SQLAlchemy (если None - используется глобальный)
    
    Returns:
        async_sessionmaker[AsyncSession]: фабрика асинхронных сессий
    """
    if engine is None:
        engine = get_engine()
    
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Не истекать после коммита
        autocommit=False,
        autoflush=False
    )


# Глобальная фабрика сессий
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Возвращает глобальную фабрику сессий (singleton)
    
    Returns:
        async_sessionmaker[AsyncSession]: глобальная фабрика сессий
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory()
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии БД в хендлерах
    
    Yields:
        AsyncSession: сессия SQLAlchemy
    
    Examples:
        @app.get("/")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transaction whose commit does not depend on generator exhaustion."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(engine: Optional[AsyncEngine] = None) -> None:
    """
    Инициализирует БД (создаёт таблицы)
    
    Args:
        engine: движок SQLAlchemy (если None - используется глобальный)
    
    Note:
        В production используйте Alembic миграции!
        Эта функция только для быстрого старта в development.
    """
    if engine is None:
        engine = get_engine()
    
    async with engine.begin() as conn:
        # Импортируем модели для регистрации в Base.metadata
        from app.models import Ticket, UserSession, BotGroup  # noqa
        from app.database.base import Base
        
        await conn.run_sync(Base.metadata.create_all)


async def close_db(engine: Optional[AsyncEngine] = None) -> None:
    """
    Закрывает соединение с БД
    
    Args:
        engine: движок SQLAlchemy (если None - используется глобальный)
    """
    if engine is None:
        engine = get_engine()
    
    await engine.dispose()


# Для удобного импорта
__all__ = [
    "create_engine",
    "get_engine",
    "create_session_factory",
    "get_session_factory",
    "get_session",
    "session_scope",
    "init_db",
    "close_db",
    "Base"
]
