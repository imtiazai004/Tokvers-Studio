"""
Team / workspace-membership logic. A workspace can have multiple members.

Invite model: if the invited email already has an account, they're added
instantly; otherwise a pending invite is stored and claimed automatically when
that email signs up (see auth.create_account -> claim_invites).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Membership, User, Workspace, WorkspaceInvite


async def get_role(session: AsyncSession, workspace_id, user_id) -> str | None:
    return await session.scalar(
        select(Membership.role).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    )


async def list_members(session: AsyncSession, workspace_id) -> list[dict]:
    rows = (
        await session.execute(
            select(User.id, User.name, User.email, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.workspace_id == workspace_id)
            .order_by(Membership.created_at)
        )
    ).all()
    return [{"user_id": str(r[0]), "name": r[1], "email": r[2], "role": r[3]} for r in rows]


async def list_invites(session: AsyncSession, workspace_id) -> list[dict]:
    invs = list(
        await session.scalars(
            select(WorkspaceInvite).where(
                WorkspaceInvite.workspace_id == workspace_id,
                WorkspaceInvite.accepted_at.is_(None),
            )
        )
    )
    return [{"email": i.email, "role": i.role,
             "created_at": i.created_at.isoformat() if i.created_at else None} for i in invs]


async def invite(session: AsyncSession, workspace_id, email: str, role: str, invited_by) -> dict:
    """Add an existing user instantly, else store a pending invite. Returns a status."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return {"status": "invalid"}
    role = "member" if role not in ("member", "admin") else role

    user = await session.scalar(select(User).where(User.email == email))
    if user:
        existing = await session.scalar(
            select(Membership).where(
                Membership.workspace_id == workspace_id, Membership.user_id == user.id
            )
        )
        if existing:
            return {"status": "already_member"}
        session.add(Membership(workspace_id=workspace_id, user_id=user.id, role=role))
        await session.commit()
        return {"status": "added"}

    inv = await session.scalar(
        select(WorkspaceInvite).where(
            WorkspaceInvite.workspace_id == workspace_id, WorkspaceInvite.email == email
        )
    )
    if inv:
        inv.role, inv.accepted_at = role, None
    else:
        session.add(WorkspaceInvite(workspace_id=workspace_id, email=email, role=role, invited_by=invited_by))
    await session.commit()
    return {"status": "invited"}


async def claim_invites(session: AsyncSession, user: User) -> int:
    """On signup: join any workspaces this email was invited to. Caller commits."""
    invs = list(
        await session.scalars(
            select(WorkspaceInvite).where(
                WorkspaceInvite.email == user.email, WorkspaceInvite.accepted_at.is_(None)
            )
        )
    )
    n = 0
    for inv in invs:
        already = await session.scalar(
            select(Membership).where(
                Membership.workspace_id == inv.workspace_id, Membership.user_id == user.id
            )
        )
        if not already:
            session.add(Membership(workspace_id=inv.workspace_id, user_id=user.id, role=inv.role))
            n += 1
        inv.accepted_at = datetime.utcnow()
    return n


async def remove_member(session: AsyncSession, workspace_id, user_id) -> dict:
    mem = await session.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    )
    if not mem:
        return {"status": "not_found"}
    if mem.role == "owner":
        return {"status": "cannot_remove_owner"}
    await session.delete(mem)
    await session.commit()
    return {"status": "removed"}


async def list_workspaces(session: AsyncSession, user_id) -> list[dict]:
    rows = (
        await session.execute(
            select(Workspace.id, Workspace.name, Membership.role)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user_id)
            .order_by(Workspace.created_at)
        )
    ).all()
    return [{"id": str(r[0]), "name": r[1], "role": r[2]} for r in rows]


async def is_member(session: AsyncSession, workspace_id, user_id) -> bool:
    return await get_role(session, workspace_id, user_id) is not None
