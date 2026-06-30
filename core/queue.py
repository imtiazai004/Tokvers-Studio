"""Arq queue connection helpers (shared by web enqueuer and worker)."""
from arq import create_pool
from arq.connections import RedisSettings

from .config import settings


def redis_settings() -> RedisSettings:
    url = (settings.redis_url or "").strip().strip('"').strip("'")
    if not url:
        raise RuntimeError("REDIS_URL not configured.")
    return RedisSettings.from_dsn(url)


async def get_pool():
    """Create an Arq Redis pool (used by the web tier to enqueue jobs)."""
    return await create_pool(redis_settings())
