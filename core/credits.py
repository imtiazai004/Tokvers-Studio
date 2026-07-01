"""
Credit ledger — the metering backbone for usage-based billing.

Model: `workspaces.credit_balance` is the authoritative running balance; every
change is also written to the append-only `credit_ledger` (audit trail with
`balance_after`). A workspace row lock (SELECT ... FOR UPDATE) serializes
concurrent charges so balances can't race.

Generation lifecycle:
    place_hold(estimate)      # debit up-front so a job can't overspend
    ... run job ...
    settle(estimate, actual)  # reconcile to true cost   (on success)
    refund(estimate)          # give it back              (on failure)
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import CreditLedger, Workspace


class InsufficientCredits(Exception):
    """Raised when a workspace lacks the credits for a charge."""


class CapExceeded(Exception):
    """Raised when a charge would exceed the monthly spend cap."""


class GenerationDisabled(Exception):
    """Raised when the global generation kill-switch is off."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


async def get_balance(session: AsyncSession, workspace_id) -> Decimal:
    bal = await session.scalar(select(Workspace.credit_balance).where(Workspace.id == workspace_id))
    if bal is None:
        raise ValueError("workspace not found")
    return _dec(bal)


async def monthly_usage(session: AsyncSession, workspace_id) -> Decimal:
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    total = await session.scalar(
        select(func.coalesce(func.sum(-CreditLedger.amount), 0)).where(
            CreditLedger.workspace_id == workspace_id,
            CreditLedger.amount < 0,
            CreditLedger.created_at >= start,
        )
    )
    return _dec(total or 0)


async def _post(session, workspace_id, amount: Decimal, reason: str, job_id=None) -> CreditLedger:
    """Atomically adjust balance (row-locked) and append a ledger entry."""
    ws = await session.scalar(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    )
    if ws is None:
        raise ValueError("workspace not found")
    new_balance = _dec(ws.credit_balance) + amount
    ws.credit_balance = new_balance
    entry = CreditLedger(
        workspace_id=workspace_id, amount=amount, reason=reason,
        job_id=job_id, balance_after=new_balance,
    )
    session.add(entry)
    await session.flush()
    return entry


async def add_credits(session, workspace_id, amount, reason="purchase", job_id=None) -> CreditLedger:
    amount = _dec(amount)
    if amount <= 0:
        raise ValueError("amount must be positive")
    entry = await _post(session, workspace_id, amount, reason, job_id)
    await session.commit()
    return entry


async def charge(session, workspace_id, amount, reason="generation", job_id=None,
                 enforce_cap=True) -> CreditLedger:
    amount = _dec(amount)
    if amount <= 0:
        raise ValueError("amount must be positive")
    from . import appsettings  # local import avoids an import cycle at module load
    if not await appsettings.get_bool("generation_enabled", settings.generation_enabled):
        raise GenerationDisabled("Generation is temporarily disabled.")

    balance = await get_balance(session, workspace_id)
    if balance < amount:
        raise InsufficientCredits(f"balance {balance} < required {amount}")

    cap = _dec(settings.max_workspace_monthly_spend)
    if enforce_cap and cap > 0:
        used = await monthly_usage(session, workspace_id)
        if used + amount > cap:
            raise CapExceeded(f"monthly cap {cap} would be exceeded (used {used} + {amount})")

    entry = await _post(session, workspace_id, -amount, reason, job_id)
    await session.commit()
    return entry


# ── Generation job lifecycle helpers ────────────────────────────

async def place_hold(session, workspace_id, estimate, job_id) -> CreditLedger:
    """Pre-flight debit of the estimated cost before a job runs."""
    return await charge(session, workspace_id, estimate, reason="hold", job_id=job_id)


async def refund(session, workspace_id, amount, job_id, reason="refund") -> CreditLedger:
    """Give credits back (e.g. a failed job)."""
    return await add_credits(session, workspace_id, amount, reason=reason, job_id=job_id)


async def settle(session, workspace_id, estimate, actual, job_id) -> CreditLedger | None:
    """Reconcile a held estimate to the true cost once a job finishes."""
    diff = _dec(actual) - _dec(estimate)
    if diff > 0:
        # actual cost higher than held — charge the remainder (don't cap-block completion)
        return await charge(session, workspace_id, diff, reason="settle", job_id=job_id, enforce_cap=False)
    if diff < 0:
        return await refund(session, workspace_id, -diff, job_id=job_id, reason="settle_refund")
    return None
