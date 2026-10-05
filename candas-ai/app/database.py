from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import get_settings


class Base(DeclarativeBase):
    pass

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
_sessionmaker_override: ContextVar[async_sessionmaker[AsyncSession] | None] = ContextVar(
    'sessionmaker_override',
    default=None,
)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return _sessionmaker_override.get() or AsyncSessionLocal


@contextmanager
def override_sessionmaker(sessionmaker: async_sessionmaker[AsyncSession]):
    token = _sessionmaker_override.set(sessionmaker)
    try:
        yield
    finally:
        _sessionmaker_override.reset(token)


def make_worker_sessionmaker():
    worker_engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,
        pool_pre_ping=False,
    )
    worker_sessionmaker = async_sessionmaker(
        worker_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return worker_engine, worker_sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session
