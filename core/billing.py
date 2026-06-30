"""
Billing service — plans, subscriptions, and a pluggable payment-gateway interface.

Design: the *logic* (plan quota, monthly credit grants, enforcement) is fully
provider-agnostic and works today with NO payment account. A real gateway
(Paddle / LemonSqueezy / Stripe) is plugged in later behind `BillingProvider`
without touching this logic — its webhook just calls `activate_plan()`.

Credit grant model:
    subscribe(plan)            -> set plan + grant that month's credits (idempotent)
    refresh_credits_if_due()   -> on a new calendar month, grant again (once)
"""
from __future__ import annotations

import abc
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import credits as credit_svc
from .config import settings
from .models import Subscription
from .plans import DEFAULT_PLAN, get_plan, is_valid_plan


def _period_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return f"{dt.year:04d}-{dt.month:02d}"


# ── Subscription service (provider-agnostic core) ───────────────────

async def get_or_create_subscription(session: AsyncSession, workspace_id) -> Subscription:
    """Every workspace has exactly one subscription row; default = free, active."""
    sub = await session.scalar(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    )
    if sub is None:
        plan = get_plan(DEFAULT_PLAN)
        sub = Subscription(
            workspace_id=workspace_id, plan=DEFAULT_PLAN, status="active",
            provider="manual", monthly_credits=plan["monthly_credits"],
        )
        session.add(sub)
        await session.flush()
    return sub


async def activate_plan(
    session: AsyncSession, workspace_id, plan_id: str, *,
    provider: str = "manual", external_customer_id: str | None = None,
    external_subscription_id: str | None = None,
) -> Subscription:
    """Set a workspace's plan and grant this period's credits (idempotent per month).

    Called by the manual flow today, and by a gateway webhook later — same path.
    """
    if not is_valid_plan(plan_id):
        raise ValueError(f"unknown plan '{plan_id}'")
    plan = get_plan(plan_id)
    sub = await get_or_create_subscription(session, workspace_id)

    now = datetime.utcnow()
    plan_changed = sub.plan != plan_id
    sub.plan = plan_id
    sub.status = "active"
    sub.provider = provider
    sub.monthly_credits = plan["monthly_credits"]
    if external_customer_id:
        sub.external_customer_id = external_customer_id
    if external_subscription_id:
        sub.external_subscription_id = external_subscription_id
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=30)

    # Grant credits once per (plan change or new calendar month)
    period = _period_key(now)
    if plan_changed or sub.last_grant_period != period:
        if plan["monthly_credits"] > 0:
            await credit_svc.add_credits(
                session, workspace_id, plan["monthly_credits"], reason="plan_grant"
            )
        sub.last_grant_period = period

    await session.flush()
    return sub


async def refresh_credits_if_due(session: AsyncSession, workspace_id) -> bool:
    """Top up the plan's monthly credits when a new calendar month begins.

    Cheap to call on login/dashboard. Returns True if a grant happened.
    """
    sub = await get_or_create_subscription(session, workspace_id)
    period = _period_key()
    if sub.last_grant_period == period or sub.status != "active":
        return False
    plan = get_plan(sub.plan)
    if plan["monthly_credits"] > 0:
        await credit_svc.add_credits(
            session, workspace_id, plan["monthly_credits"], reason="plan_grant"
        )
    sub.last_grant_period = period
    sub.current_period_start = datetime.utcnow()
    sub.current_period_end = datetime.utcnow() + timedelta(days=30)
    await session.flush()
    return True


async def cancel_subscription(session: AsyncSession, workspace_id) -> Subscription:
    """Downgrade to free (no proration; credits already granted stay)."""
    sub = await get_or_create_subscription(session, workspace_id)
    sub.plan = DEFAULT_PLAN
    sub.status = "active"
    sub.provider = "manual"
    sub.external_subscription_id = None
    sub.monthly_credits = get_plan(DEFAULT_PLAN)["monthly_credits"]
    await session.flush()
    return sub


# ── Payment-gateway interface (plug a real provider in later) ───────

class CheckoutResult:
    """What a checkout attempt returns to the API layer."""
    def __init__(self, status: str, checkout_url: str | None = None):
        self.status = status              # "active" (manual) | "redirect" (gateway)
        self.checkout_url = checkout_url

    def as_dict(self) -> dict:
        return {"status": self.status, "checkout_url": self.checkout_url}


class BillingProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def start_checkout(self, session: AsyncSession, workspace_id, plan_id: str) -> CheckoutResult:
        ...


class ManualBillingProvider(BillingProvider):
    """No external gateway — activates the plan immediately (admin/dev/until a
    real gateway is wired). This is what makes billing fully testable today."""
    name = "manual"

    async def start_checkout(self, session, workspace_id, plan_id) -> CheckoutResult:
        await activate_plan(session, workspace_id, plan_id, provider="manual")
        return CheckoutResult(status="active")


# Future: PaddleBillingProvider / LemonSqueezyBillingProvider implement
# start_checkout() to return CheckoutResult(status="redirect", checkout_url=...)
# and their webhook handler calls activate_plan(provider="paddle", external_*=...).

_PROVIDERS: dict[str, BillingProvider] = {
    "manual": ManualBillingProvider(),
}


def get_billing_provider() -> BillingProvider:
    return _PROVIDERS.get(settings.billing_provider, _PROVIDERS["manual"])
