"""
Database session management for Pharmaco-Navigator.

Provides a single async SQLAlchemy engine and a stateless session-injection
factory designed for FastAPI's dependency injection system.
"""

from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# URL normalisation
# Accepts both postgresql:// and postgresql+asyncpg:// connection strings and
# translates the psycopg-style `sslmode` query parameter to the asyncpg-style
# `ssl` parameter.
def _normalise_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not raw_url.startswith("postgresql+asyncpg://"):
        scheme = raw_url.split("://")[0] if "://" in raw_url else "invalid"
        raise ValueError(
            "DATABASE_URL must use the postgresql:// or postgresql+asyncpg:// "
            f"scheme. Got: {scheme}"
        )

    parsed = urlparse(raw_url)
    query_params = parse_qs(parsed.query)

    # Translate psycopg2-style sslmode → asyncpg-style ssl
    if "sslmode" in query_params:
        query_params["ssl"] = query_params.pop("sslmode")

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        urlencode(query_params, doseq=True),
        parsed.fragment,
    ))

# Engine - single instance, shared connection pool
# Created once at module load; never recreated per request.
engine = create_async_engine(
    _normalise_database_url(settings.DATABASE_URL),
    echo=False,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,   # Discard stale connections before handing them out
    pool_recycle=3600,    # Recycle connections after 1 hour
)

# Session factory - bound to the single engine above
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Dependency - stateless per-request session injection
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
