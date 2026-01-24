
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from stockidea.config import DATABASE_URL
from stockidea.datasource.database.models import Base


_engine = None


async def _get_engine() -> AsyncEngine:
    """Get SQLAlchemy async engine for the database."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=20,  # Allow up to 20 concurrent connections
            max_overflow=10,  # Allow overflow beyond pool_size
            pool_pre_ping=True,  # Verify connections before using
        )
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    return _engine


@asynccontextmanager
async def get_db_session():
    """Get an async database session context manager."""
    engine = await _get_engine()
    async with AsyncSession(bind=engine) as session:
        yield session
