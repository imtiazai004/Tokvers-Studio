"""
TikTok integration — official OAuth (Login Kit v2). Plumbing only: connect /
callback / token storage / refresh. Posting + analytics build on top of
`valid_access_token()` once a TikTok app + approval exist.

No passwords are ever handled; only OAuth tokens, encrypted at rest.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import TikTokAccount
from .security import decrypt_secret, encrypt_secret

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/"


class TikTokError(Exception):
    """Surfaced when a TikTok API call fails or the integration isn't configured."""


def authorize_url(state: str) -> str:
    """Build the consent URL the user is redirected to."""
    if not settings.tiktok_configured:
        raise TikTokError("TikTok integration is not configured yet.")
    params = {
        "client_key": settings.tiktok_client_key,
        "scope": settings.tiktok_scopes,
        "response_type": "code",
        "redirect_uri": settings.tiktok_redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def _post_token(data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TOKEN_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    body = resp.json()
    if resp.status_code != 200 or "access_token" not in body:
        raise TikTokError(f"TikTok token exchange failed: {body}")
    return body


async def exchange_code(code: str) -> dict:
    return await _post_token({
        "client_key": settings.tiktok_client_key,
        "client_secret": settings.tiktok_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.tiktok_redirect_uri,
    })


async def refresh_access_token(refresh_token: str) -> dict:
    return await _post_token({
        "client_key": settings.tiktok_client_key,
        "client_secret": settings.tiktok_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })


async def fetch_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            USERINFO_URL,
            params={"fields": "open_id,display_name,avatar_url"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    body = resp.json()
    return (body.get("data") or {}).get("user", {}) if resp.status_code == 200 else {}


# ── Persistence ─────────────────────────────────────────────────

async def get_account(session: AsyncSession, workspace_id) -> TikTokAccount | None:
    return await session.scalar(
        select(TikTokAccount).where(TikTokAccount.workspace_id == workspace_id)
    )


async def save_from_token(session: AsyncSession, workspace_id, token: dict) -> TikTokAccount:
    """Persist (or update) the connected account from a token response."""
    open_id = token.get("open_id") or ""
    info = await fetch_user_info(token["access_token"])
    expires_at = datetime.utcnow() + timedelta(seconds=int(token.get("expires_in", 0) or 0))

    acct = await get_account(session, workspace_id)
    if acct is None:
        acct = TikTokAccount(workspace_id=workspace_id, open_id=open_id or info.get("open_id", ""))
        session.add(acct)
    acct.open_id = open_id or info.get("open_id", acct.open_id)
    acct.display_name = info.get("display_name")
    acct.avatar_url = info.get("avatar_url")
    acct.scope = token.get("scope")
    acct.encrypted_access_token = encrypt_secret(token["access_token"])
    if token.get("refresh_token"):
        acct.encrypted_refresh_token = encrypt_secret(token["refresh_token"])
    acct.expires_at = expires_at
    await session.flush()
    return acct


async def disconnect(session: AsyncSession, workspace_id) -> bool:
    acct = await get_account(session, workspace_id)
    if not acct:
        return False
    await session.delete(acct)
    await session.flush()
    return True


async def valid_access_token(session: AsyncSession, workspace_id) -> str:
    """Return a usable access token, refreshing it if expired. Used by posting/analytics."""
    acct = await get_account(session, workspace_id)
    if not acct:
        raise TikTokError("No TikTok account connected.")
    if acct.expires_at and acct.expires_at <= datetime.utcnow() + timedelta(minutes=2):
        if not acct.encrypted_refresh_token:
            raise TikTokError("TikTok token expired and no refresh token available — reconnect.")
        token = await refresh_access_token(decrypt_secret(acct.encrypted_refresh_token))
        await save_from_token(session, workspace_id, token)
        acct = await get_account(session, workspace_id)
    return decrypt_secret(acct.encrypted_access_token)
