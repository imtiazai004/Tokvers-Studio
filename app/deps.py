"""Request dependencies: session-derived current user / workspace."""
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import get_session
from core.models import User


def client_ip(request: Request) -> str:
    """Real client IP for rate-limiting behind Render's proxy.

    Each proxy APPENDS the address it received the connection from to the right
    of X-Forwarded-For, so with N trusted proxies the genuine client IP is the
    Nth entry from the right — and it can't be spoofed by a client-supplied XFF
    (any forged value lands to the left of what our proxy appends)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        hops = max(1, settings.trusted_proxy_hops)
        if len(parts) >= hops:
            return parts[-hops]
        if parts:
            return parts[0]
    return request.client.host if request.client else "unknown"


def require_user_id(request: Request) -> uuid.UUID:
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    return uuid.UUID(uid)


def require_workspace_id(request: Request) -> uuid.UUID:
    wid = request.session.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=401, detail="Authentication required")
    return uuid.UUID(wid)


async def require_admin(
    uid: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Gate an endpoint to platform staff. 404 (not 403) to avoid advertising
    that the route exists to non-admins."""
    user = await session.get(User, uid)
    if not user or not user.is_admin:
        raise HTTPException(status_code=404, detail="Not found")
    return user
