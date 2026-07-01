"""Request dependencies: session-derived current user / workspace."""
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.models import User


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
