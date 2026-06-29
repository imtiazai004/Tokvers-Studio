"""
Generation job lifecycle (DB layer) wired to the credit ledger.

create_job  -> insert job (queued) + place a credit HOLD for the estimate
mark_running / update_progress
complete_job -> SETTLE hold to actual cost, status=done, attach video
fail_job     -> REFUND the held estimate, status=failed

All reads are workspace-scoped. Credit holds guarantee a job can never run
without paying up-front (and a failed job gives the credits back).
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import credits
from .models import GenerationJob


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


async def create_job(
    session: AsyncSession,
    workspace_id,
    user_id,
    params: dict,
    cost_estimate,
    provider: str | None = None,
) -> GenerationJob:
    """Insert a queued job and hold its estimated cost. If the hold is rejected
    (insufficient credits / cap / kill-switch) the job is recorded as failed."""
    job = GenerationJob(
        workspace_id=workspace_id, user_id=user_id, params=params,
        provider=provider, cost_estimate=_dec(cost_estimate), status="queued",
    )
    session.add(job)
    await session.flush()  # assign job.id for the ledger FK

    try:
        await credits.place_hold(session, workspace_id, cost_estimate, job_id=job.id)
    except (credits.InsufficientCredits, credits.CapExceeded, credits.GenerationDisabled) as e:
        job.status = "failed"
        job.error = str(e)
        await session.commit()
        raise

    await session.commit()
    return job


async def mark_running(session, job_id, step: str | None = None) -> GenerationJob:
    job = await session.get(GenerationJob, job_id)
    job.status = "running"
    if step:
        job.step = step
    await session.commit()
    return job


async def update_progress(session, job_id, step: str, progress: int) -> None:
    job = await session.get(GenerationJob, job_id)
    job.step = step
    job.progress = max(0, min(100, progress))
    await session.commit()


async def complete_job(session, job_id, video_id, cost_actual) -> GenerationJob:
    job = await session.get(GenerationJob, job_id)
    # reconcile the up-front hold to the true cost
    await credits.settle(session, job.workspace_id, estimate=job.cost_estimate or 0,
                         actual=cost_actual, job_id=job.id)
    job.status = "done"
    job.step = "done"
    job.progress = 100
    job.cost_actual = _dec(cost_actual)
    job.video_id = video_id
    await session.commit()
    return job


async def fail_job(session, job_id, error) -> GenerationJob:
    job = await session.get(GenerationJob, job_id)
    if job.cost_estimate:
        await credits.refund(session, job.workspace_id, job.cost_estimate, job_id=job.id)
    job.status = "failed"
    job.error = str(error)[:2000]
    await session.commit()
    return job


async def get_job(session, workspace_id, job_id) -> GenerationJob | None:
    """Workspace-scoped fetch (a workspace can never read another's job)."""
    return await session.scalar(
        select(GenerationJob).where(
            GenerationJob.id == job_id, GenerationJob.workspace_id == workspace_id
        )
    )


async def list_jobs(session, workspace_id, limit: int = 50) -> list[GenerationJob]:
    return list(
        await session.scalars(
            select(GenerationJob)
            .where(GenerationJob.workspace_id == workspace_id)
            .order_by(GenerationJob.created_at.desc())
            .limit(limit)
        )
    )
