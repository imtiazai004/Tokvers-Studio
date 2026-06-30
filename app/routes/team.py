"""Team API — members, invites, and workspace switching (all real, owner-gated)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_user_id, require_workspace_id
from core import team
from core.config import settings
from core.db import get_session
from core.email import send_email

router = APIRouter(prefix="/api", tags=["team"])


async def _require_owner(session, ws, uid):
    role = await team.get_role(session, ws, uid)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only the workspace owner can do this.")


@router.get("/team")
async def get_team(uid=Depends(require_user_id), ws=Depends(require_workspace_id),
                   session: AsyncSession = Depends(get_session)):
    return {
        "my_role": await team.get_role(session, ws, uid),
        "my_user_id": str(uid),
        "members": await team.list_members(session, ws),
        "invites": await team.list_invites(session, ws),
    }


class InviteIn(BaseModel):
    email: str
    role: str = "member"


@router.post("/team/invite")
async def invite_member(data: InviteIn, uid=Depends(require_user_id),
                        ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    await _require_owner(session, ws, uid)
    result = await team.invite(session, ws, data.email, data.role, uid)
    if result["status"] == "invalid":
        return JSONResponse({"error": "Enter a valid email."}, status_code=400)
    if result["status"] == "invited":  # new user — email them a signup link
        try:
            await send_email(
                data.email.strip().lower(), "You're invited to a Tokverse Studio workspace",
                f"You've been invited to collaborate on Tokverse Studio.\n\n"
                f"Create your account to join:\n{settings.app_base_url}/signup",
            )
        except Exception:
            pass
    return result


class RemoveIn(BaseModel):
    user_id: str


@router.post("/team/remove")
async def remove_member(data: RemoveIn, uid=Depends(require_user_id),
                        ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    await _require_owner(session, ws, uid)
    result = await team.remove_member(session, ws, uuid.UUID(data.user_id))
    if result["status"] == "cannot_remove_owner":
        return JSONResponse({"error": "You can't remove the workspace owner."}, status_code=400)
    return result


@router.get("/workspaces")
async def my_workspaces(request: Request, uid=Depends(require_user_id),
                        session: AsyncSession = Depends(get_session)):
    return {
        "current": request.session.get("workspace_id"),
        "workspaces": await team.list_workspaces(session, uid),
    }


class SwitchIn(BaseModel):
    workspace_id: str


@router.post("/workspaces/switch")
async def switch_workspace(data: SwitchIn, request: Request, uid=Depends(require_user_id),
                           session: AsyncSession = Depends(get_session)):
    target = uuid.UUID(data.workspace_id)
    if not await team.is_member(session, target, uid):
        raise HTTPException(status_code=403, detail="You're not a member of that workspace.")
    request.session["workspace_id"] = str(target)
    return {"status": "ok", "workspace_id": str(target)}
