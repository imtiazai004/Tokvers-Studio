"""Auth API — workspace-aware signup/login on Neon (replaces legacy aiosqlite auth)."""
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core import auth as auth_core
from core.db import get_session
from core.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: str
    password: str
    name: str | None = ""


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(request: Request, data: SignupIn, session: AsyncSession = Depends(get_session)):
    try:
        user, workspace = await auth_core.create_account(
            session, data.email, data.password, data.name or ""
        )
    except auth_core.AuthError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    request.session["user_id"] = str(user.id)
    request.session["workspace_id"] = str(workspace.id)
    return {"status": "ok", "workspace_id": str(workspace.id)}


@router.post("/login")
async def login(request: Request, data: LoginIn, session: AsyncSession = Depends(get_session)):
    user = await auth_core.authenticate(session, data.email, data.password)
    if not user:
        return JSONResponse({"error": "Invalid email or password."}, status_code=401)
    workspace = await auth_core.get_primary_workspace(session, user.id)
    request.session["user_id"] = str(user.id)
    request.session["workspace_id"] = str(workspace.id) if workspace else None
    return {"status": "ok"}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


@router.get("/me")
async def me(request: Request, session: AsyncSession = Depends(get_session)):
    uid = request.session.get("user_id")
    if not uid:
        return {"authenticated": False}
    user = await session.get(User, uuid.UUID(uid))
    if not user:
        request.session.clear()
        return {"authenticated": False}
    return {
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "workspace_id": request.session.get("workspace_id"),
    }
