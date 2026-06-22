"""
Database session management for Azure PostgreSQL.
Provides async SQLAlchemy engine and session factory for genomic data retrieval from the Azure-hosted genotypes table.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from app.core.config import settings


# Create async engine for Azure PostgreSQL
def get_async_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine for Azure PostgreSQL.
    """
    database_url = settings.DATABASE_URL
    
    # Ensure async driver is used
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            "DATABASE_URL must use postgresql:// or postgresql+asyncpg:// scheme. "
            f"Got: {database_url.split('://')[0] if '://' in database_url else 'invalid'}"
        )
    
    # Replace sslmode=require with ssl=require for asyncpg compatibility
    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query)
    
    if 'sslmode' in query_params:
        ssl_value = query_params['sslmode'][0]
        # Remove sslmode and add ssl parameter
        del query_params['sslmode']
        query_params['ssl'] = [ssl_value]
    
    # Rebuild query string
    new_query = urlencode(query_params, doseq=True)
    
    # Rebuild URL with fixed query string
    database_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    # Create engine with connection pooling
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query debugging
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )
    
    return engine


# Create async session factory
async_session_factory = async_sessionmaker(
    bind=get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects usable after commit
    autocommit=False,
    autoflush=False,
)
AsyncSessionLocal = async_session_factory

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get async database sessions.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global engine instance for service classes
engine = get_async_engine()
