"""
app/db/session.py
──────────────────
Async SQLAlchemy engine and session factory.
Uses asyncpg driver for PostgreSQL — fastest async PG driver available.

Connection pool is tuned for a production workload:
- pool_size: maintained connections
- max_overflow: burst connections above pool_size
- pool_pre_ping: validates connections before use (handles DB restarts)
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base.
    All ORM models inherit from this.
    """
    pass


def create_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine with production-tuned pool settings."""
    return create_async_engine(
        settings.database_url,
        # Connection pool configuration
        pool_size=10,           # Maintain 10 connections
        max_overflow=20,        # Allow 20 burst connections
        pool_timeout=30,        # Wait 30s for a connection before raising
        pool_recycle=1800,      # Recycle connections every 30 min
        pool_pre_ping=True,     # Test connection liveness before use
        # Echo SQL in dev only
        echo=settings.is_development,
        echo_pool=False,
    )


# Module-level engine — created once at import
engine: AsyncEngine = create_engine()

# Session factory — reuse this to create sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (async safety)
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    Handles commit/rollback automatically.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(...)
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("database_session_error", error=str(e), exc_info=True)
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injection for database sessions.

    Usage in route:
        async def my_route(db: AsyncSession = Depends(get_db)):
    """
    async with get_db_session() as session:
        yield session


async def init_db() -> None:
    """
    Create all tables from ORM models.
    Used in tests and initial setup.
    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_initialized")


async def close_db() -> None:
    """Dispose engine connections. Call on application shutdown."""
    await engine.dispose()
    logger.info("database_connections_closed")
