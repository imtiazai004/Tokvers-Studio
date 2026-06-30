"""TikTok OAuth API — connect / callback / status / disconnect (Login Kit v2)."""
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
from core import tiktok
from core.config import settings
from core.db import get_session

router = APIRouter(prefix="/api/tiktok", tags=["tiktok"])


@router.get("/status")
async def status(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    acct = await tiktok.get_account(session, ws)
    return {
        "configured": settings.tiktok_configured,
        "connected": acct is not None,
        "display_name": acct.display_name if acct else None,
        "avatar_url": acct.avatar_url if acct else None,
        "scope": acct.scope if acct else None,
    }


@router.get("/connect")
async def connect(request: Request, ws=Depends(require_workspace_id)):
    """Redirect the user to TikTok's consent screen (state stored for CSRF)."""
    if not settings.tiktok_configured:
        return RedirectResponse("/analytics?tiktok=unconfigured", status_code=302)
    state = secrets.token_urlsafe(24)
    request.session["tiktok_oauth_state"] = state
    return RedirectResponse(tiktok.authorize_url(state), status_code=302)


@router.get("/callback")
async def callback(request: Request, ws=Depends(require_workspace_id),
                   session: AsyncSession = Depends(get_session),
                   code: str | None = None, state: str | None = None):
    """Handle TikTok's redirect: verify state, exchange code, store tokens."""
    expected = request.session.pop("tiktok_oauth_state", None)
    if not code or not state or state != expected:
        return RedirectResponse("/analytics?tiktok=error", status_code=302)
    try:
        token = await tiktok.exchange_code(code)
        await tiktok.save_from_token(session, ws, token)
        await session.commit()
    except tiktok.TikTokError:
        return RedirectResponse("/analytics?tiktok=error", status_code=302)
    return RedirectResponse("/analytics?tiktok=connected", status_code=302)


@router.post("/disconnect")
async def disconnect(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    await tiktok.disconnect(session, ws)
    await session.commit()
    return {"status": "ok"}
