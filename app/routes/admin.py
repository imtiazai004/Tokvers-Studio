"""Admin API — review + clear anti-abuse flags. All routes are admin-gated."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_admin
from core import billing
from core.db import get_session
from core.models import Membership, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
