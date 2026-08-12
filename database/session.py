"""Async SQLAlchemy engine and session factory management.

The module exposes a single lazily-initialised engine/sessionmaker pair so
the rest of the application can simply call :func:`get_sessionmaker` without
worrying about setup order.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _normalise_url(database_url: str) -> str:
    """Ensure the URL uses the asyncpg driver.

    Railway and Heroku-style providers commonly hand out
    ``postgres://`` or ``postgresql://`` URLs, which the synchronous
    psycopg driver expects. This rewrites them to the async driver used by
    the application at runtime.
    """
    if database_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + database_url[len("postgres://") :]
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url[len("postgresql://") :]
    return database_url


def init_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create (or return the existing) async engine for ``database_url``.

    A connect-level timeout is set so an unreachable database fails fast
    with a clear error instead of hanging the process indefinitely (as
    happens with no timeout when a host is unreachable or misconfigured).
    """
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(
            _normalise_url(database_url),
            echo=echo,
            pool_pre_ping=True,
            connect_args={"timeout": 10},
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, initialising it if needed."""
    if _sessionmaker is None:
        from config import settings

        init_engine(settings.database_url)
    assert _sessionmaker is not None
    return _sessionmaker


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool. Call on shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
