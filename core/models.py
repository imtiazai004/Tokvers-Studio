"""
Multi-tenant ORM models (SQLAlchemy 2.0).

Tenancy rule: every tenant-owned row carries `workspace_id`. A workspace owns all
data; users belong to a workspace via `Membership`. Every data-access query MUST
filter by `workspace_id` — this is enforced in the repository/service layer.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _ws_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)


# ── Tenancy & identity ──────────────────────────────────────────

class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(120))
    plan: Mapped[str] = mapped_column(String(40), default="free")
    credit_balance: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    # Per-workspace generation defaults (pre-fill the Create form). e.g.
    # {"provider","voice_provider","video_type","scenes","niche"}.
    gen_defaults: Mapped[dict] = mapped_column(JSON, default=dict)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Platform staff — gates admin-only endpoints (e.g. manual credit top-up).
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Bumped on password change/reset to invalidate all existing sessions.
    session_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Anti-abuse signals captured at signup. `flagged` accounts (e.g. same device
    # as an existing account) are allowed in but withheld free credits + generation
    # until reviewed — never hard-blocked, to avoid locking out shared-device users.
    signup_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signup_fp: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    flag_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)


class AuthToken(Base, TimestampMixin):
    """Single-use tokens for password reset / email verification.

    Only the SHA-256 hash is stored; the raw token travels in the emailed link.
    """
    __tablename__ = "auth_tokens"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(20))          # reset | verify
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_member_ws_user"),)
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")  # owner/admin/member


class WorkspaceInvite(Base, TimestampMixin):
    """Pending invite to join a workspace. Claimed automatically when the invited
    email signs up (or applied instantly if that user already exists)."""
    __tablename__ = "workspace_invites"
    __table_args__ = (UniqueConstraint("workspace_id", "email", name="uq_invite_ws_email"),)
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WorkspaceApiKey(Base, TimestampMixin):
    """Per-workspace BYOK secrets (encrypted at rest)."""
    __tablename__ = "workspace_api_keys"
    __table_args__ = (UniqueConstraint("workspace_id", "provider", name="uq_apikey_ws_provider"),)
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    provider: Mapped[str] = mapped_column(String(40))   # veo/grok/elevenlabs/...
    encrypted_key: Mapped[str] = mapped_column(Text)


# ── Billing / metering ──────────────────────────────────────────

class CreditLedger(Base, TimestampMixin):
    """Append-only ledger: +amount = top-up, -amount = usage/refund."""
    __tablename__ = "credit_ledger"
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    amount: Mapped[float] = mapped_column(Numeric(12, 4))
    reason: Mapped[str] = mapped_column(String(40))     # purchase/generation/refund/adjustment
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True
    )
    balance_after: Mapped[float] = mapped_column(Numeric(12, 4))


class Subscription(Base, TimestampMixin):
    """Provider-agnostic subscription. `provider` + `external_*` map to whatever
    payment gateway is plugged in later (manual/paddle/lemonsqueezy/stripe)."""
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(40), default="free")
    status: Mapped[str] = mapped_column(String(30), default="active")  # active/canceled/past_due

    # Payment-gateway link (generic — set when a real gateway is wired)
    provider: Mapped[str] = mapped_column(String(40), default="manual")
    external_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Plan quota + billing period
    monthly_credits: Mapped[int] = mapped_column(Integer, default=0)
    current_period_start: Mapped[datetime | None] = mapped_column(nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(nullable=True)
    last_grant_period: Mapped[str | None] = mapped_column(String(7), nullable=True)  # "YYYY-MM"


# ── TikTok integration (official OAuth — no password storage) ───

class TikTokAccount(Base, TimestampMixin):
    """A workspace's connected TikTok account (Login Kit). Tokens encrypted at rest."""
    __tablename__ = "tiktok_accounts"
    __table_args__ = (UniqueConstraint("workspace_id", "open_id", name="uq_tiktok_ws_open"),)
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    open_id: Mapped[str] = mapped_column(String(120))            # TikTok user id
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)


# ── Generation pipeline ─────────────────────────────────────────

class GenerationJob(Base, TimestampMixin):
    __tablename__ = "generation_jobs"
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued/running/done/failed/canceled
    step: Mapped[str | None] = mapped_column(String(30), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cost_estimate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_actual: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )


class Video(Base, TimestampMixin):
    __tablename__ = "videos"
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    job_id: Mapped[uuid.UUID | None] = mapped_column(String(40), nullable=True)
    r2_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    topic: Mapped[str] = mapped_column(String(300))
    niche: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tool: Mapped[str | None] = mapped_column(String(40), nullable=True)
    character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    performance_score: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class Character(Base, TimestampMixin):
    __tablename__ = "characters"
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    appearance: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_r2_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    niche: Mapped[str | None] = mapped_column(String(80), nullable=True)
    voice_gender: Mapped[str] = mapped_column(String(20), default="female")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    videos_created: Mapped[int] = mapped_column(Integer, default=0)
    avg_performance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


# ── Learning (per-workspace, no cross-tenant leakage) ───────────

class Learning(Base, TimestampMixin):
    __tablename__ = "agent_learnings"
    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_name", "learning_key", name="uq_learning_ws_agent_key"),
    )
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    agent_name: Mapped[str] = mapped_column(String(60))
    learning_key: Mapped[str] = mapped_column(String(120))
    learning_value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)


class ScriptPattern(Base, TimestampMixin):
    __tablename__ = "script_patterns"
    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _ws_fk()
    niche: Mapped[str] = mapped_column(String(80))
    hook_style: Mapped[str | None] = mapped_column(String(120), nullable=True)
    script_length: Mapped[str | None] = mapped_column(String(40), nullable=True)
    voice_gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avg_performance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
