"""
Subscription plans — provider-agnostic catalog.

Credits are the unit of metering (≈ `settings.credits_per_scene` per scene, so a
6-scene video ≈ 6 credits). Prices/quotas below are PLACEHOLDERS to be calibrated
after Phase 4 (one real generation → true cost per video). Changing money/credits
here needs no gateway and no schema change.
"""
from __future__ import annotations

PLANS: dict[str, dict] = {
    "free": {
        "id": "free",
        "name": "Free",
        "price_usd": 0,
        "monthly_credits": 30,          # ~5 short videos to try the product
        "tagline": "Try it out",
        "features": [
            "30 credits / month",
            "All video types incl. UGC",
            "Watermark-free downloads",
            "1 workspace",
        ],
    },
    "starter": {
        "id": "starter",
        "name": "Starter",
        "price_usd": 29,
        "monthly_credits": 300,         # ~50 short videos
        "tagline": "For solo creators",
        "features": [
            "300 credits / month",
            "Consistent characters",
            "Batch generation",
            "Performance analytics",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_usd": 99,
        "monthly_credits": 1200,        # ~200 short videos
        "tagline": "For brands & agencies",
        "features": [
            "1,200 credits / month",
            "Priority generation queue",
            "All providers (Veo / Grok / Higgsfield)",
            "Everything in Starter",
        ],
    },
}

DEFAULT_PLAN = "free"


def get_plan(plan_id: str | None) -> dict:
    """Return a plan dict, falling back to the free plan for unknown ids."""
    return PLANS.get(plan_id or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def list_plans() -> list[dict]:
    """Ordered list (cheapest → priciest) for the pricing UI."""
    return sorted(PLANS.values(), key=lambda p: p["price_usd"])


def is_valid_plan(plan_id: str) -> bool:
    return plan_id in PLANS
