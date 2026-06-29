"""
Async database layer (SQLAlchemy 2.0 + asyncpg).

`Base` is the declarative base for all models. The engine/session are created only
when DATABASE_URL is configured, so models can be imported (and DDL compiled) even
without a live database — useful for migrations authoring and CI.
"""
from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


def prepare_url(url: str) -> tuple[str, bool]:
    """
    Normalize a Postgres URL for asyncpg and strip params asyncpg rejects.

    Returns (url, needs_ssl). Neon-style `?sslmode=require&channel_binding=require`
    are removed; SSL is instead signalled via connect_args.
    """
    if not url:
        return "", False
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    needs_ssl = any(k == "sslmode" and v != "disable" for k, v in pairs)
    kept = [(k, v) for k, v in pairs if k not in ("sslmode", "channel_binding")]
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))
    return url, needs_ssl


engine = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None

if settings.database_url:
    _url, _needs_ssl = prepare_url(settings.database_url)
    # statement_cache_size=0 makes asyncpg safe behind Neon's PgBouncer pooler
    # (transaction pooling doesn't support server-side prepared statements).
    _connect_args: dict = {"statement_cache_size": 0}
    if _needs_ssl:
        _connect_args["ssl"] = True
    engine = create_async_engine(_url, pool_pre_ping=True, connect_args=_connect_args)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a scoped async session."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    async with SessionLocal() as session:
        yield session
