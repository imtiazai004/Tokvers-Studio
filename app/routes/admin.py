"""Admin API — metrics, runtime toggles, and anti-abuse flag review.
All routes are admin-gated (require_admin)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_admin
from core import appsettings, billing
from core.config import settings as cfg
from core.db import get_session
from core.models import GenerationJob, Membership, User, Video, Workspace

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Flags an admin can flip live (key -> env fallback used when unset).
_TOGGLES = {
    "generation_enabled": lambda: cfg.generation_enabled,
    "signup_enabled": lambda: True,
}


@router.get("/metrics")
async def metrics(_admin: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    async def count(stmt):
        return int(await session.scalar(stmt) or 0)

    jobs_by_status = {}
    for st in ("queued", "running", "done", "failed"):
        jobs_by_status[st] = await count(
            select(func.count()).select_from(GenerationJob).where(GenerationJob.status == st)
        )
    return {
        "users": await count(select(func.count()).select_from(User)),
        "users_verified": await count(select(func.count()).select_from(User).where(User.email_verified.is_(True))),
        "users_flagged": await count(select(func.count()).select_from(User).where(User.flagged.is_(True))),
        "workspaces": await count(select(func.count()).select_from(Workspace)),
        "videos": await count(select(func.count()).select_from(Video)),
        "jobs": jobs_by_status,
        "credits_outstanding": float(await session.scalar(select(func.coalesce(func.sum(Workspace.credit_balance), 0))) or 0),
    }


@router.get("/settings")
async def get_settings(_admin: User = Depends(require_admin)):
    """Effective value of each live toggle (DB override, else env default)."""
    out = {}
    for key, env_default in _TOGGLES.items():
        out[key] = await appsettings.get_bool(key, env_default())
    return {"settings": out}


class ToggleIn(BaseModel):
    key: str
    value: bool


@router.post("/settings")
async def set_setting(data: ToggleIn, _admin: User = Depends(require_admin)):
    if data.key not in _TOGGLES:
        raise HTTPException(status_code=400, detail="Unknown setting")
    await appsettings.set_value(data.key, "true" if data.value else "false")
    return {"status": "ok", "key": data.key, "value": data.value}


@router.get("/flagged")
async def list_flagged(_admin: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    """Accounts held for review (e.g. same device as an existing account)."""
    rows = list(await session.scalars(
        select(User).where(User.flagged.is_(True)).order_by(User.created_at.desc()).limit(200)
    ))
    return {"flagged": [
        {
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "flag_reason": u.flag_reason,
            "signup_ip": u.signup_ip,
            "fingerprint": (u.signup_fp[:16] + "…") if u.signup_fp else None,
            "email_verified": bool(u.email_verified),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in rows
    ]}


@router.post("/users/{user_id}/approve")
async def approve_user(user_id: uuid.UUID, grant_credits: bool = True,
                       _admin: User = Depends(require_admin),
                       session: AsyncSession = Depends(get_session)):
    """Clear a user's flag. By default also grants the free-plan credits that
    were withheld while flagged (so an approved account starts normally)."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.flagged = False
    user.flag_reason = None
    if grant_credits:
        wid = await session.scalar(
            select(Membership.workspace_id)
            .where(Membership.user_id == user_id)
            .order_by(Membership.created_at).limit(1)
        )
        if wid:
            await billing.activate_plan(session, wid, "free")
    await session.commit()
    return {"status": "ok"}
