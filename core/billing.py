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
import asyncio
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


# ── Stripe ──────────────────────────────────────────────────────────

def _stripe_price_for(plan_id: str) -> str:
    """Stripe Price ID for a paid plan (empty for free / unmapped)."""
    return {
        "starter": settings.stripe_price_starter,
        "pro": settings.stripe_price_pro,
    }.get(plan_id, "")


class StripeBillingProvider(BillingProvider):
    """Stripe Checkout (subscription mode). The plan is activated by the webhook
    (`handle_stripe_event`) after payment succeeds — never client-side."""
    name = "stripe"

    async def start_checkout(self, session, workspace_id, plan_id) -> CheckoutResult:
        price_id = _stripe_price_for(plan_id)
        print(f"DEBUG checkout: provider={settings.billing_provider!r} plan={plan_id!r} price_id={price_id!r} pro_env={settings.stripe_price_pro!r}", flush=True)
        if not price_id:
            # Free/unpriced plan — no payment needed, activate immediately.
            await activate_plan(session, workspace_id, plan_id, provider="stripe")
            return CheckoutResult(status="active")

        import stripe
        stripe.api_key = settings.stripe_secret_key
        sub = await get_or_create_subscription(session, workspace_id)

        def _create():
            return stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=f"{settings.app_base_url}/billing?checkout=success",
                cancel_url=f"{settings.app_base_url}/billing?checkout=cancel",
                client_reference_id=str(workspace_id),
                metadata={"workspace_id": str(workspace_id), "plan_id": plan_id},
                **({"customer": sub.external_customer_id} if sub.external_customer_id else {}),
            )

        cs = await asyncio.to_thread(_create)
        return CheckoutResult(status="redirect", checkout_url=cs.url)


async def _sub_by_stripe(session, *, subscription_id=None, customer_id=None) -> Subscription | None:
    if subscription_id:
        s = await session.scalar(select(Subscription).where(Subscription.external_subscription_id == subscription_id))
        if s:
            return s
    if customer_id:
        return await session.scalar(select(Subscription).where(Subscription.external_customer_id == customer_id))
    return None


async def handle_stripe_event(session: AsyncSession, event: dict) -> None:
    """Apply a verified Stripe webhook event to our billing state. Idempotent
    (activate_plan only grants once per plan-change / calendar month)."""
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        workspace_id = meta.get("workspace_id") or obj.get("client_reference_id")
        plan_id = meta.get("plan_id")
        if workspace_id and plan_id:
            await activate_plan(
                session, workspace_id, plan_id, provider="stripe",
                external_customer_id=obj.get("customer"),
                external_subscription_id=obj.get("subscription"),
            )

    elif etype in ("invoice.paid", "invoice.payment_succeeded"):
        sub = await _sub_by_stripe(session, subscription_id=obj.get("subscription"),
                                   customer_id=obj.get("customer"))
        if sub:  # recurring renewal — top up this period's credits (idempotent)
            await activate_plan(session, sub.workspace_id, sub.plan, provider="stripe")

    elif etype == "customer.subscription.deleted":
        sub = await _sub_by_stripe(session, subscription_id=obj.get("id"),
                                   customer_id=obj.get("customer"))
        if sub:
            await cancel_subscription(session, sub.workspace_id)

    await session.commit()


# Future gateways implement start_checkout() the same way and route their webhook
# through a handler like handle_stripe_event().

_PROVIDERS: dict[str, BillingProvider] = {
    "manual": ManualBillingProvider(),
    "stripe": StripeBillingProvider(),
}


def get_billing_provider() -> BillingProvider:
    return _PROVIDERS.get(settings.billing_provider, _PROVIDERS["manual"])
