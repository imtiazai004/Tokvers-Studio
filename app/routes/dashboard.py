"""Dashboard + library data — real, workspace-scoped (empty until you generate)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
from core import credits, storage
from core.db import get_session
from core.models import GenerationJob, Video

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    balance = float(await credits.get_balance(session, ws))

    rows = (
        await session.execute(
            select(GenerationJob.status, func.count())
            .where(GenerationJob.workspace_id == ws)
            .group_by(GenerationJob.status)
        )
    ).all()
    by_status = {s: c for s, c in rows}
    total = sum(by_status.values())

    videos_count = await session.scalar(
        select(func.count()).select_from(Video).where(Video.workspace_id == ws)
    ) or 0

    recent = list(
        await session.scalars(
            select(GenerationJob)
            .where(GenerationJob.workspace_id == ws)
            .order_by(GenerationJob.created_at.desc())
            .limit(8)
        )
    )
    recent_dto = [{
        "topic": (j.params or {}).get("topic"),
        "status": j.status,
        "provider": j.provider,
        "cost": float(j.cost_actual) if j.cost_actual is not None else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    } for j in recent]

    return {
        "balance": balance,
        "jobs": {"total": total, "queued": by_status.get("queued", 0),
                 "running": by_status.get("running", 0), "done": by_status.get("done", 0),
                 "failed": by_status.get("failed", 0)},
        "videos": videos_count,
        "recent": recent_dto,
    }


@router.get("/library")
async def library(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    vids = list(
        await session.scalars(
            select(Video).where(Video.workspace_id == ws).order_by(Video.created_at.desc()).limit(60)
        )
    )
    out = []
    for v in vids:
        url = None
        if v.r2_key and storage.is_configured():
            try:
                url = await storage.signed_url(v.r2_key, expires=3600)
            except Exception:
                url = None
        out.append({"id": str(v.id), "topic": v.topic, "tool": v.tool,
                    "url": url, "created_at": v.created_at.isoformat() if v.created_at else None})
    return {"videos": out}
