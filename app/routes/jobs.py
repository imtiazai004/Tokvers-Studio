"""Generation job API — create (with credit hold), list, and fetch (workspace-scoped)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
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
    provider: str = "veo"
    video_type: str = "product_demo"
    scenes: int = 6
    product_name: str | None = ""
    product_description: str | None = ""
    character_id: str | None = None


def _job_dto(j: GenerationJob) -> dict:
    return {
        "job_id": str(j.id),
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
    ws=Depends(require_workspace_id),
    uid=Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
):
    scenes = max(1, min(12, data.scenes))
    estimate = scenes * settings.credits_per_scene
    try:
        job = await jobs.create_job(
            session, ws, uid, params=data.model_dump(),
            cost_estimate=estimate, provider=data.provider,
        )
    except credits.InsufficientCredits as e:
        return JSONResponse({"error": str(e)}, status_code=402)
    except credits.CapExceeded as e:
        return JSONResponse({"error": str(e)}, status_code=402)
    except credits.GenerationDisabled as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    # TODO(walking-skeleton): enqueue generate_video_job(job.id) to Arq once
    # provider keys + R2 are configured. The credit hold is already placed.
    return _job_dto(job)


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
