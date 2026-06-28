"""
Async database session management for Pharmaco Navigator.

Engine construction is intentionally deferred and cached so no connection pool
is opened at import time. All external callers receive a request-scoped
AsyncSession via FastAPI's Depends() mechanism.
"""

import logging
import sys
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

logger = logging.getLogger("pharmaco.navigator.db")


# --------------------------------------------------------------------------- #
# Private helpers                                                              #
# --------------------------------------------------------------------------- #

def _normalise_url(raw: str) -> str:
    """
    Coerce any postgresql:// string to the postgresql+asyncpg:// scheme and
    translate the ``sslmode`` query parameter to asyncpg's ``ssl`` keyword so
    the driver does not reject the connection string.
    """
    if raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(raw)
    params = parse_qs(parsed.query, keep_blank_values=True)

    if "sslmode" in params:
        params["ssl"] = params.pop("sslmode")

    normalised = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(params, doseq=True),
            parsed.fragment,
        )
    )
    return normalised


def _build_connect_args(is_production: bool) -> dict:
    """
    Return asyncpg ``connect_args``.
    Server-side SSL is enforced unconditionally; ``ssl="require"`` instructs
    asyncpg to demand a TLS-encrypted channel and verify the server certificate.
    """
    return {"ssl": "require"} if is_production else {}


# --------------------------------------------------------------------------- #
# Engine + session factory (cached per unique connection parameters)           #
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=4)
def _get_engine(
    db_url: str,
    pool_size: int,
    max_overflow: int,
    is_production: bool,
) -> AsyncEngine:
    """
    Create and cache one AsyncEngine per distinct set of connection parameters.
    Accepts only primitive, hashable arguments so lru_cache can key on them.
    """
    url = _normalise_url(db_url)
    connect_args = _build_connect_args(is_production)

    logger.info(
        "Creating async engine: pool_size=%d max_overflow=%d ssl=%s",
        pool_size,
        max_overflow,
        connect_args.get("ssl", "off"),
    )

    return create_async_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,   # validate connections before checkout
        pool_recycle=3600,    # retire connections after SESSION_MAX_AGE
        echo=not is_production,
        connect_args=connect_args,
    )


@lru_cache(maxsize=4)
def _get_session_factory(
    db_url: str,
    pool_size: int,
    max_overflow: int,
    is_production: bool,
) -> async_sessionmaker[AsyncSession]:
    engine = _get_engine(db_url, pool_size, max_overflow, is_production)
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# --------------------------------------------------------------------------- #
# FastAPI dependency                                                           #
# --------------------------------------------------------------------------- #

async def get_db_session(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a request-scoped AsyncSession.

    Commits on clean exit; rolls back and re-raises on any exception.
    The session is always closed — the engine returns its connection to the pool.
    """
    factory = _get_session_factory(
        settings.DATABASE_URL,
        settings.DATABASE_POOL_SIZE,
        settings.DATABASE_MAX_OVERFLOW,
        settings.is_production,
    )
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Session rolled back due to unhandled exception")
            raise


# Convenience type alias — use in route signatures instead of the full Annotated form.
DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# --------------------------------------------------------------------------- #
# Backwards-compatible aliases consumed by existing service layer             #
# --------------------------------------------------------------------------- #

def get_async_engine() -> AsyncEngine:
    """Return the cached engine built from the current settings."""
    cfg = get_settings()
    return _get_engine(
        cfg.DATABASE_URL,
        cfg.DATABASE_POOL_SIZE,
        cfg.DATABASE_MAX_OVERFLOW,
        cfg.is_production,
    )


# Session factory aliases — consumed by legacy service layer (pre-Depends() code).
# New code should use the DbSession type alias instead.
AsyncSessionLocal: async_sessionmaker[AsyncSession] = _get_session_factory(
    get_settings().DATABASE_URL,
    get_settings().DATABASE_POOL_SIZE,
    get_settings().DATABASE_MAX_OVERFLOW,
    get_settings().is_production,
)

# Phase 1 name kept for backward-compatible imports.
async_session_factory = AsyncSessionLocal
