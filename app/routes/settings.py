"""Settings API — profile, password, and per-workspace generation defaults (all real)."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_user_id, require_workspace_id
from core.db import get_session
from core.models import User, Workspace
from core.security import hash_password, verify_password

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Allowed keys for generation defaults (ignore anything else).
_DEFAULT_KEYS = {"provider", "voice_provider", "video_type", "scenes", "niche"}


@router.get("")
async def get_settings(uid=Depends(require_user_id), ws=Depends(require_workspace_id),
                       session: AsyncSession = Depends(get_session)):
    user = await session.get(User, uid)
    workspace = await session.get(Workspace, ws)
    return {
        "profile": {
            "name": user.name if user else None,
            "email": user.email if user else None,
            "email_verified": bool(user.email_verified) if user else False,
        },
        "workspace": {"name": workspace.name if workspace else None},
        "defaults": (workspace.gen_defaults or {}) if workspace else {},
    }


class ProfileIn(BaseModel):
    name: str | None = None
    workspace_name: str | None = None


@router.post("/profile")
async def update_profile(data: ProfileIn, uid=Depends(require_user_id),
                         ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, uid)
    if user and data.name is not None:
        user.name = data.name.strip() or None
    if data.workspace_name is not None:
        workspace = await session.get(Workspace, ws)
        if workspace and data.workspace_name.strip():
            workspace.name = data.workspace_name.strip()
    await session.commit()
    return {"status": "ok"}


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.post("/password")
async def change_password(data: PasswordIn, uid=Depends(require_user_id),
                          session: AsyncSession = Depends(get_session)):
    user = await session.get(User, uid)
    if not user or not verify_password(data.current_password, user.password_hash):
        return JSONResponse({"error": "Current password is incorrect."}, status_code=400)
    if len(data.new_password or "") < 8:
        return JSONResponse({"error": "New password must be at least 8 characters."}, status_code=400)
    user.password_hash = hash_password(data.new_password)
    await session.commit()
    return {"status": "ok"}


class DefaultsIn(BaseModel):
    provider: str | None = None
    voice_provider: str | None = None
    video_type: str | None = None
    scenes: int | None = None
    niche: str | None = None


@router.post("/defaults")
async def save_defaults(data: DefaultsIn, ws=Depends(require_workspace_id),
                        session: AsyncSession = Depends(get_session)):
    workspace = await session.get(Workspace, ws)
    if workspace:
        clean = {k: v for k, v in data.model_dump().items() if k in _DEFAULT_KEYS and v not in (None, "")}
        workspace.gen_defaults = clean
        await session.commit()
    return {"status": "ok", "defaults": clean if workspace else {}}
