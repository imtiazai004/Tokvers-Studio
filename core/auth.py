"""
Workspace-aware authentication & account provisioning.

Signing up creates a User, a Workspace, and an owner Membership in one step — so
every account is multi-tenant from the first login (no single-tenant data sharing).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Membership, User, Workspace
from .security import hash_password, verify_password


class AuthError(Exception):
    """Raised for signup/login problems surfaced to the user."""


async def create_account(
    session: AsyncSession,
    email: str,
    password: str,
    name: str = "",
    workspace_name: str | None = None,
) -> tuple[User, Workspace]:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise AuthError("Please enter a valid email.")
    if len(password or "") < 8:
        raise AuthError("Password must be at least 8 characters.")

    if await session.scalar(select(User).where(User.email == email)):
        raise AuthError("An account with this email already exists.")

    user = User(email=email, password_hash=hash_password(password), name=(name or None))
    session.add(user)
    await session.flush()  # assign user.id

    ws_label = workspace_name or f"{(name or email.split('@')[0])}'s workspace"
    workspace = Workspace(name=ws_label)
    session.add(workspace)
    await session.flush()  # assign workspace.id

    session.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await session.flush()

    # Provision the free plan + grant its starter credits, so a brand-new
    # workspace can generate immediately. (activate_plan commits internally.)
    from . import billing  # local import avoids any import-time cycle
    await billing.activate_plan(session, workspace.id, "free")

    await session.commit()
    return user, workspace


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    email = (email or "").strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def get_primary_workspace(session: AsyncSession, user_id) -> Workspace | None:
    membership = await session.scalar(
        select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
    )
    if not membership:
        return None
    return await session.get(Workspace, membership.workspace_id)
