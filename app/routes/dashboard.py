"""Dashboard + library + analytics data — real, workspace-scoped (empty until you generate)."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
from core import billing, credits, storage
from core.config import settings
from core.db import get_session
from core.models import GenerationJob, Learning, ScriptPattern, Video

router = APIRouter(prefix="/api", tags=["dashboard"])

# Pipeline stages → the "agents" a creator sees working. Mirrors the real
# generation pipeline (script → voice → video → edit). Status is derived from
# actual running jobs, never faked.
_AGENTS = [
    ("script", "Script Agent"),
    ("voice", "Voice Agent"),
    ("video", "Video Agent"),
    ("editing", "Editing Agent"),
]


def _month_bounds():
    now = datetime.utcnow()
    this_start = datetime(now.year, now.month, 1)
    last_start = datetime(now.year - 1, 12, 1) if now.month == 1 else datetime(now.year, now.month - 1, 1)
    return this_start, last_start


def _pct(cur: int, prev: int):
    """Real month-over-month %, or None when there's no prior data to compare."""
    if prev <= 0:
        return None
    return round((cur - prev) / prev * 100)


@router.get("/dashboard")
async def dashboard(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    # Renew the plan's monthly credits if a new month has begun (idempotent).
    await billing.refresh_credits_if_due(session, ws)
    balance = float(await credits.get_balance(session, ws))

    # ── Jobs by status (real) ───────────────────────────────────
    rows = (
        await session.execute(
            select(GenerationJob.status, func.count())
            .where(GenerationJob.workspace_id == ws)
            .group_by(GenerationJob.status)
        )
    ).all()
    by_status = {s: c for s, c in rows}
    total = sum(by_status.values())
    done = by_status.get("done", 0)

    # ── Performance totals (real sums from tracked videos) ──────
    perf = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Video.views), 0),
                func.coalesce(func.sum(Video.likes), 0),
                func.coalesce(func.sum(Video.shares), 0),
            ).where(Video.workspace_id == ws)
        )
    ).one()
    videos_count, views, likes, shares = int(perf[0]), int(perf[1]), int(perf[2]), int(perf[3])

    # ── Real month-over-month trend for videos created ──────────
    this_start, last_start = _month_bounds()
    vids_this = await session.scalar(
        select(func.count()).select_from(Video)
        .where(Video.workspace_id == ws, Video.created_at >= this_start)
    ) or 0
    vids_last = await session.scalar(
        select(func.count()).select_from(Video)
        .where(Video.workspace_id == ws, Video.created_at >= last_start, Video.created_at < this_start)
    ) or 0

    # ── Agents: real status from currently running jobs ─────────
    run_rows = (
        await session.execute(
            select(GenerationJob.step, func.count())
            .where(GenerationJob.workspace_id == ws, GenerationJob.status == "running")
            .group_by(GenerationJob.step)
        )
    ).all()
    running_by_step = {s: c for s, c in run_rows}
    agents = [
        {
            "key": key, "name": name,
            "status": "active" if running_by_step.get(key) else "idle",
            "active": int(running_by_step.get(key, 0)),  # jobs at this stage right now
            "completed": int(done),                       # jobs this agent has finished (each done job used it)
        }
        for key, name in _AGENTS
    ]

    # ── Recent jobs (real) ──────────────────────────────────────
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
        "step": j.step,
        "provider": j.provider,
        "cost": float(j.cost_actual) if j.cost_actual is not None else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    } for j in recent]

    # ── Top videos by real performance ──────────────────────────
    top = list(
        await session.scalars(
            select(Video).where(Video.workspace_id == ws)
            .order_by(Video.performance_score.desc()).limit(5)
        )
    )
    top_dto = [{
        "topic": v.topic, "tool": v.tool,
        "views": v.views or 0, "likes": v.likes or 0, "shares": v.shares or 0,
    } for v in top if (v.views or v.likes or v.shares)]

    return {
        "balance": balance,
        "jobs": {"total": total, "queued": by_status.get("queued", 0),
                 "running": by_status.get("running", 0), "done": done,
                 "failed": by_status.get("failed", 0)},
        "videos": videos_count,
        "performance": {"views": views, "likes": likes, "shares": shares},
        "trends": {"videos": _pct(vids_this, vids_last)},   # real, or null
        "agents": agents,
        "system": {
            "generation_enabled": settings.generation_enabled,
            "running": by_status.get("running", 0),
        },
        "recent": recent_dto,
        "top_videos": top_dto,
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

