"""Request dependencies: session-derived current user / workspace."""
import uuid

from fastapi import HTTPException, Request


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
