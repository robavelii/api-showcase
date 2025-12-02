"""Async database engine setup.

Provides async SQLAlchemy engine configuration for PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from shared.config import get_settings


def create_engine() -> AsyncEngine:
    """Create async database engine with configured settings."""
    settings = get_settings()

    engine = create_async_engine(
        str(settings.database_url),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        echo=settings.debug and settings.is_development,
    )

    return engine


# Global engine instance
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global async engine instance."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


async def dispose_engine() -> None:
    """Dispose of the global engine instance."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
