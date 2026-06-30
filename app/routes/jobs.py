"""Generation job API — create (with credit hold), list, and fetch (workspace-scoped)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_user_id, require_workspace_id
from core import credits, jobs
from core.config import settings
from core.db import get_session
from core.models import GenerationJob

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobIn(BaseModel):
    topic: str
    niche: str | None = None
    provider: str = "veo"           # video provider
    voice_provider: str = "elevenlabs"
    video_type: str = "product_demo"
    scenes: int = 6
    product_name: str | None = ""
    product_description: str | None = ""
    product_image: str | None = None   # base64 (no data-URI prefix) for image-to-video
    manual_script: str | None = None   # if set, skip the script agent
    character_id: str | None = None
    batch_count: int = 1               # generate N videos at once


def _job_dto(j: GenerationJob) -> dict:
    return {
        "job_id": str(j.id),
        "topic": (j.params or {}).get("topic"),
        "status": j.status,
        "step": j.step,
        "progress": j.progress,
        "provider": j.provider,
        "cost_estimate": float(j.cost_estimate) if j.cost_estimate is not None else None,
        "cost_actual": float(j.cost_actual) if j.cost_actual is not None else None,
        "error": j.error,
        "video_id": str(j.video_id) if j.video_id else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


@router.post("")
async def create(
    data: CreateJobIn,
    request: Request,
    ws=Depends(require_workspace_id),
    uid=Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
):
    scenes = max(1, min(12, data.scenes))
    estimate = scenes * settings.credits_per_scene
    batch = max(1, min(10, data.batch_count or 1))
    params = data.model_dump()
    pool = getattr(request.app.state, "arq", None)

    created = []
    for _ in range(batch):
        try:
            job = await jobs.create_job(
                session, ws, uid, params=params, cost_estimate=estimate, provider=data.provider,
            )
        except (credits.InsufficientCredits, credits.CapExceeded):
            break  # ran out mid-batch — return what we made
        except credits.GenerationDisabled as e:
            return JSONResponse({"error": str(e)}, status_code=503)
        if pool is not None:
            await pool.enqueue_job("generate_video_job", str(job.id))
        created.append(_job_dto(job))

    if not created:
        return JSONResponse({"error": "Not enough credits"}, status_code=402)
    return {"jobs": created}


@router.get("")
async def list_jobs(ws=Depends(require_workspace_id), session: AsyncSession = Depends(get_session)):
    return {"jobs": [_job_dto(j) for j in await jobs.list_jobs(session, ws)]}


@router.get("/{job_id}")
async def get_job(job_id: uuid.UUID, ws=Depends(require_workspace_id),
                  session: AsyncSession = Depends(get_session)):
    job = await jobs.get_job(session, ws, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_dto(job)
