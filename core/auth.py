"""
Workspace-aware authentication & account provisioning.

Signing up creates a User, a Workspace, and an owner Membership in one step — so
every account is multi-tenant from the first login (no single-tenant data sharing).
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .email_policy import is_disposable, is_valid_format, normalize_email
from .models import AuthToken, Membership, User, Workspace
from .security import hash_password, verify_password


class AuthError(Exception):
    """Raised for signup/login problems surfaced to the user."""


async def _flag_reason(session: AsyncSession, fingerprint: str | None) -> str | None:
    """Return a flag reason if this signup looks like a duplicate. Fingerprint
    only (IP is too noisy behind NAT/mobile to flag on) — and this only flags,
    never blocks, so a shared-device false positive just triggers review."""
    if fingerprint:
        seen = await session.scalar(select(User.id).where(User.signup_fp == fingerprint).limit(1))
        if seen:
            return "duplicate_device"
    return None


async def create_account(
    session: AsyncSession,
    email: str,
    password: str,
    name: str = "",
    workspace_name: str | None = None,
    *,
    signup_ip: str | None = None,
    fingerprint: str | None = None,
) -> tuple[User, Workspace]:
    email = normalize_email(email)
    if not is_valid_format(email):
        raise AuthError("Please enter a valid email.")
    if is_disposable(email):
        raise AuthError("Please use a permanent email address — temporary email providers aren't allowed.")
    if len(password or "") < 8:
        raise AuthError("Password must be at least 8 characters.")

    if await session.scalar(select(User).where(User.email == email)):
        raise AuthError("An account with this email already exists.")

    reason = await _flag_reason(session, fingerprint)
    user = User(
        email=email, password_hash=hash_password(password), name=(name or None),
        signup_ip=signup_ip, signup_fp=fingerprint,
        flagged=bool(reason), flag_reason=reason,
    )
    session.add(user)
    await session.flush()  # assign user.id

    ws_label = workspace_name or f"{(name or email.split('@')[0])}'s workspace"
    workspace = Workspace(name=ws_label)
    session.add(workspace)
    await session.flush()  # assign workspace.id

    session.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await session.flush()

    # Provision the free plan. Flagged (suspected-duplicate) accounts get the plan
    # row but NO free credits until reviewed — so device abuse yields nothing.
    from . import billing  # local import avoids any import-time cycle
    if user.flagged:
        await billing.get_or_create_subscription(session, workspace.id)
    else:
        await billing.activate_plan(session, workspace.id, "free")

    # Auto-join any workspaces this email was invited to.
    from . import team
    await team.claim_invites(session, user)

    await session.commit()
    return user, workspace


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    email = (email or "").strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


# ── Single-use tokens (password reset / email verification) ─────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_token(session: AsyncSession, user_id, purpose: str, ttl_minutes: int) -> str:
    """Create a single-use token; returns the RAW token (only the hash is stored)."""
    raw = secrets.token_urlsafe(32)
    session.add(AuthToken(
        user_id=user_id, purpose=purpose, token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
    ))
    await session.commit()
    return raw


async def consume_token(session: AsyncSession, raw: str, purpose: str) -> User | None:
    """Validate + burn a token. Returns the owning user, or None if invalid/expired/used."""
    tok = await session.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == _hash_token(raw),
            AuthToken.purpose == purpose,
        )
    )
    if not tok or tok.used_at is not None or tok.expires_at < datetime.utcnow():
        return None
    tok.used_at = datetime.utcnow()
    return await session.get(User, tok.user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == (email or "").strip().lower()))


async def reset_password(session: AsyncSession, raw_token: str, new_password: str) -> bool:
    if len(new_password or "") < 8:
        raise AuthError("Password must be at least 8 characters.")
    user = await consume_token(session, raw_token, "reset")
    if not user:
        return False
    user.password_hash = hash_password(new_password)
    user.session_version += 1   # invalidate every existing session after a reset
    await session.commit()
    return True


async def verify_email(session: AsyncSession, raw_token: str) -> bool:
    user = await consume_token(session, raw_token, "verify")
    if not user:
        return False
    user.email_verified = True
    await session.commit()
    return True


async def get_primary_workspace(session: AsyncSession, user_id) -> Workspace | None:
    membership = await session.scalar(
        select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
    )
    if not membership:
        return None
    return await session.get(Workspace, membership.workspace_id)
