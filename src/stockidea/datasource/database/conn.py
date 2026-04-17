from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from stockidea.constants import DATABASE_URL


_engine = None


async def _get_engine() -> AsyncEngine:
    """Get SQLAlchemy async engine for the database."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


@asynccontextmanager
async def get_db_session():
    """Get an async database session context manager."""
    engine = await _get_engine()
    async with AsyncSession(bind=engine) as session:
        yield session
