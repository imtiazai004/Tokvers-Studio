"""Dashboard + library + analytics data — real, workspace-scoped (empty until you generate)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
from core import billing, credits, storage
from core.db import get_session
from core.models import GenerationJob, Learning, ScriptPattern, Video

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    # Renew the plan's monthly credits if a new month has begun (idempotent).
    await billing.refresh_credits_if_due(session, ws)
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


@router.get("/products")
async def products(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(
                Video.topic, func.count(),
                func.coalesce(func.sum(Video.views), 0),
                func.coalesce(func.sum(Video.likes), 0),
                func.coalesce(func.sum(Video.shares), 0),
            )
            .where(Video.workspace_id == ws)
            .group_by(Video.topic)
            .order_by(func.count().desc())
        )
    ).all()
    return {"products": [
        {"product": r[0], "videos": r[1], "views": int(r[2]), "likes": int(r[3]), "shares": int(r[4])}
        for r in rows
    ]}


@router.get("/learnings")
async def learnings(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    ls = list(await session.scalars(
        select(Learning).where(Learning.workspace_id == ws).order_by(Learning.confidence.desc())
    ))
    ps = list(await session.scalars(
        select(ScriptPattern).where(ScriptPattern.workspace_id == ws)
    ))
    return {
        "learnings": [{"agent": l.agent_name, "key": l.learning_key, "value": l.learning_value,
                       "confidence": float(l.confidence)} for l in ls],
        "patterns": [{"niche": p.niche, "hook": p.hook_style, "length": p.script_length,
                      "voice": p.voice_gender, "perf": float(p.avg_performance),
                      "used": p.usage_count} for p in ps],
    }


@router.get("/analytics")
async def analytics(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    vids = list(await session.scalars(
        select(Video).where(Video.workspace_id == ws).order_by(Video.views.desc())
    ))
    return {
        "totals": {
            "videos": len(vids),
            "views": sum(v.views or 0 for v in vids),
            "likes": sum(v.likes or 0 for v in vids),
            "shares": sum(v.shares or 0 for v in vids),
        },
        "videos": [{"id": str(v.id), "topic": v.topic, "tool": v.tool,
                    "views": v.views or 0, "likes": v.likes or 0, "shares": v.shares or 0}
                   for v in vids],
    }


class MetricsIn(BaseModel):
    views: int = 0
    likes: int = 0
    shares: int = 0


@router.post("/videos/{video_id}/metrics")
async def set_metrics(video_id: uuid.UUID, data: MetricsIn,
                      ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    v = await session.scalar(select(Video).where(Video.id == video_id, Video.workspace_id == ws))
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    v.views, v.likes, v.shares = data.views, data.likes, data.shares
    v.performance_score = data.views + data.likes * 3 + data.shares * 5
    await session.commit()
    return {"status": "ok", "performance_score": float(v.performance_score)}

