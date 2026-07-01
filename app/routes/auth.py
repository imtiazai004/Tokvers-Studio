"""Auth API — workspace-aware signup/login on Neon (replaces legacy aiosqlite auth)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import client_ip
from core import appsettings
from core import auth as auth_core
from core import ratelimit
from core.config import settings
from core.db import get_session
from core.email import send_email
from core.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _throttle(request: Request, name: str, limit: int, window: int):
    """Per-IP brute-force throttle; raises 429 when the window is exhausted."""
    ip = client_ip(request)
    ok, retry = await ratelimit.check(f"{name}:{ip}", limit, window)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Please try again in {retry} seconds.",
        )


async def _send_verification_email(session: AsyncSession, user: User) -> None:
    """Issue a verify token and email the confirmation link. Best-effort — a
    mail failure must never break signup."""
    try:
        raw = await auth_core.create_token(session, user.id, "verify", ttl_minutes=1440)
        link = f"{settings.app_base_url}/api/auth/verify?token={raw}"
        await send_email(
            user.email, "Verify your Tokverse Studio email",
            f"Confirm your email to start generating (valid 24 hours):\n\n{link}",
        )
    except Exception:
        pass


class SignupIn(BaseModel):
    email: str
    password: str
    name: str | None = ""
    fingerprint: str | None = None   # client-side device signal (anti-abuse)


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(request: Request, data: SignupIn, session: AsyncSession = Depends(get_session)):
    if not await appsettings.get_bool("signup_enabled", True):
        return JSONResponse({"error": "New signups are temporarily closed."}, status_code=403)
    await _throttle(request, "signup", limit=5, window=3600)   # 5 / hour / IP
    try:
        user, workspace = await auth_core.create_account(
            session, data.email, data.password, data.name or "",
            signup_ip=client_ip(request), fingerprint=(data.fingerprint or None),
        )
    except auth_core.AuthError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    await _send_verification_email(session, user)   # confirm-email link (needed before generation)
    request.session["user_id"] = str(user.id)
    request.session["workspace_id"] = str(workspace.id)
    request.session["sv"] = user.session_version
    return {"status": "ok", "workspace_id": str(workspace.id)}


@router.post("/login")
async def login(request: Request, data: LoginIn, session: AsyncSession = Depends(get_session)):
    await _throttle(request, "login", limit=10, window=300)    # 10 / 5 min / IP
    user = await auth_core.authenticate(session, data.email, data.password)
    if not user:
        return JSONResponse({"error": "Invalid email or password."}, status_code=401)
    workspace = await auth_core.get_primary_workspace(session, user.id)
    request.session["user_id"] = str(user.id)
    request.session["workspace_id"] = str(workspace.id) if workspace else None
    request.session["sv"] = user.session_version
    return {"status": "ok"}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    token: str
    password: str


@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotIn, session: AsyncSession = Depends(get_session)):
    await _throttle(request, "forgot", limit=5, window=3600)
    user = await auth_core.get_user_by_email(session, data.email)
    if user:  # silent when not found — no account enumeration
        raw = await auth_core.create_token(session, user.id, "reset", ttl_minutes=60)
        link = f"{settings.app_base_url}/reset?token={raw}"
        await send_email(
            user.email, "Reset your Tokverse Studio password",
            f"Click to reset your password (valid 1 hour):\n\n{link}\n\n"
            f"If you didn't request this, ignore this email.",
        )
    return {"status": "ok"}  # always ok


@router.post("/reset-password")
async def reset_password(request: Request, data: ResetIn, session: AsyncSession = Depends(get_session)):
    await _throttle(request, "reset", limit=10, window=3600)
    try:
        ok = await auth_core.reset_password(session, data.token, data.password)
    except auth_core.AuthError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if not ok:
        return JSONResponse({"error": "This reset link is invalid or has expired."}, status_code=400)
    return {"status": "ok"}


@router.post("/request-verify")
async def request_verify(request: Request, session: AsyncSession = Depends(get_session)):
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    await _throttle(request, "verify-req", limit=5, window=3600)
    user = await session.get(User, uuid.UUID(uid))
    if user and not user.email_verified:
        await _send_verification_email(session, user)
    return {"status": "ok"}


@router.get("/verify")
async def verify(token: str, session: AsyncSession = Depends(get_session)):
    ok = await auth_core.verify_email(session, token)
    return RedirectResponse(f"/login?verified={'1' if ok else '0'}", status_code=302)


@router.get("/me")
async def me(request: Request, session: AsyncSession = Depends(get_session)):
    uid = request.session.get("user_id")
    if not uid:
        return {"authenticated": False}
    user = await session.get(User, uuid.UUID(uid))
    if not user or user.session_version != request.session.get("sv", 0):
        request.session.clear()   # user gone, or session invalidated by a password change
        return {"authenticated": False}
    return {
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "workspace_id": request.session.get("workspace_id"),
    }
