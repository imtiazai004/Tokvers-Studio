"""Admin-toggleable runtime flags backed by the `app_settings` table.

A missing key falls back to the env/config default, so nothing breaks before an
admin sets anything. Reads are cached (short TTL) so hot paths like credit
charging don't hit the DB every call; a write busts the cache immediately.
"""
from __future__ import annotations

import time

from sqlalchemy import select

from .db import SessionLocal
from .models import AppSetting

_TRUE = {"1", "true", "yes", "on"}
_cache: dict[str, str] = {}
_cache_at: float = 0.0
_TTL = 10.0


async def _refresh() -> None:
    global _cache, _cache_at
    if SessionLocal is None:
        _cache, _cache_at = {}, time.time()
        return
    async with SessionLocal() as s:
        rows = list(await s.scalars(select(AppSetting)))
    _cache = {r.key: r.value for r in rows}
    _cache_at = time.time()


async def _ensure_fresh() -> None:
    if time.time() - _cache_at > _TTL:
        try:
            await _refresh()
        except Exception:
            pass  # transient DB issue — serve last-known (or env default)


async def get(key: str, default: str | None = None) -> str | None:
    await _ensure_fresh()
    return _cache.get(key, default)


async def get_bool(key: str, env_default: bool) -> bool:
    await _ensure_fresh()
    v = _cache.get(key)
    return env_default if v is None else v.strip().lower() in _TRUE


async def set_value(key: str, value: str) -> None:
    global _cache_at
    if SessionLocal is None:
        return
    async with SessionLocal() as s:
        row = await s.get(AppSetting, key)
        if row:
            row.value = value
        else:
            s.add(AppSetting(key=key, value=value))
        await s.commit()
    _cache_at = 0.0  # force reload on next read
