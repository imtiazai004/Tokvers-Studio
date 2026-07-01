"""Credit API — balance, ledger, and admin-only manual top-up. Real end-user
top-ups are created by the payment-gateway webhook, not here."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_admin, require_workspace_id
from core import credits
from core.db import get_session
from core.models import CreditLedger

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/balance")
async def balance(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    return {"balance": float(await credits.get_balance(session, ws))}


@router.get("/ledger")
async def ledger(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    rows = list(
        await session.scalars(
            select(CreditLedger)
            .where(CreditLedger.workspace_id == ws)
            .order_by(CreditLedger.created_at.desc())
            .limit(100)
        )
    )
    return {
        "entries": [
            {
                "amount": float(r.amount),
                "reason": r.reason,
                "balance_after": float(r.balance_after),
                "at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


class TopUpIn(BaseModel):
    amount: float
    workspace_id: str | None = None   # admin may top up any workspace; default = own


@router.post("/topup")
async def topup(
    data: TopUpIn,
    ws=Depends(require_workspace_id),
    _admin=Depends(require_admin),          # ADMIN-ONLY: real top-ups come via the billing webhook
    session: AsyncSession = Depends(get_session),
):
    # Manual credit grant — restricted to platform staff (see require_admin).
    # End-user top-ups are created by the payment-gateway webhook, never here.
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    target_ws = uuid.UUID(data.workspace_id) if data.workspace_id else ws
    entry = await credits.add_credits(session, target_ws, data.amount, reason="adjustment")
    return {"balance": float(entry.balance_after)}
