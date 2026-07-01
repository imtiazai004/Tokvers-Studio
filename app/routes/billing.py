"""Billing API — plans, current subscription, checkout (provider-agnostic)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
from core import billing, credits
from core.config import settings
from core.db import get_session
from core.plans import get_plan, is_valid_plan, list_plans

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/webhook")
async def stripe_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    """Stripe webhook. PUBLIC but authenticated by signature — we verify the
    Stripe-Signature header against STRIPE_WEBHOOK_SECRET before trusting anything."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    import stripe
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception:
        # Bad signature / malformed — reject (could be a forged request).
        return JSONResponse({"error": "invalid signature"}, status_code=400)
    await billing.handle_stripe_event(session, event)
    return {"received": True}


@router.get("/plans")
async def plans():
    """Public plan catalog for the pricing UI."""
    return {"plans": list_plans()}


@router.get("/subscription")
async def subscription(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    # Top up monthly credits if a new month has started, then report status.
    await billing.refresh_credits_if_due(session, ws)
    sub = await billing.get_or_create_subscription(session, ws)
    await session.commit()
    plan = get_plan(sub.plan)
    return {
        "plan": sub.plan,
        "plan_name": plan["name"],
        "status": sub.status,
        "provider": sub.provider,
        "monthly_credits": sub.monthly_credits,
        "balance": float(await credits.get_balance(session, ws)),
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


class CheckoutIn(BaseModel):
    plan_id: str


@router.post("/checkout")
async def checkout(data: CheckoutIn, ws=Depends(require_workspace_id),
                   session: AsyncSession = Depends(get_session)):
    """Start a plan change. With the manual provider this activates immediately;
    a real gateway returns a checkout_url to redirect to."""
    if not is_valid_plan(data.plan_id):
        raise HTTPException(status_code=400, detail="Unknown plan")
    provider = billing.get_billing_provider()
    result = await provider.start_checkout(session, ws, data.plan_id)
    await session.commit()
    return result.as_dict()


@router.post("/cancel")
async def cancel(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    sub = await billing.cancel_subscription(session, ws)
    await session.commit()
    return {"plan": sub.plan, "status": sub.status}
