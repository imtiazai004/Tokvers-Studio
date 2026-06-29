"""Credit API — balance, ledger, and (dev) top-up. Real top-ups go via Stripe later."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
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


@router.post("/topup")
async def topup(data: TopUpIn, ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    # NOTE: dev/admin convenience. Production top-ups are created by the Stripe webhook.
    entry = await credits.add_credits(session, ws, data.amount, reason="purchase")
    return {"balance": float(entry.balance_after)}
