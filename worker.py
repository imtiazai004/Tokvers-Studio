"""
Arq worker — runs the full generation pipeline off the Redis queue, in a process
SEPARATE from the stateless web tier.

Run:  arq worker.WorkerSettings
"""
import uuid

from core import jobs as jobs_svc
from core.db import SessionLocal
from core.learnings import record_pipeline_learnings
from core.models import GenerationJob, Video
from core.pipeline import run_pipeline
from core.queue import redis_settings


async def health(ctx, msg: str = "ping") -> str:
    return f"pong:{msg}"


async def generate_video_job(ctx, job_id) -> dict:
    """
    Full pipeline: script -> voice -> scene clips -> edit -> R2, with the credit
    hold settled on success and refunded on failure. Uses short-lived DB sessions
    (the pipeline itself runs for minutes, so we don't hold a connection open).
    """
    if SessionLocal is None:
        return {"error": "DATABASE_URL not configured"}
    jid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))

    # load job basics + mark running
    async with SessionLocal() as s:
        job = await s.get(GenerationJob, jid)
        if not job:
            return {"error": "job not found"}
        params = dict(job.params or {})
        workspace_id = job.workspace_id
        cost_estimate = float(job.cost_estimate or 0)
        await jobs_svc.mark_running(s, jid, step="script")

    async def progress(step: str, percent: int):
        async with SessionLocal() as ps:
            await jobs_svc.update_progress(ps, jid, step, percent)

    try:
        result = await run_pipeline(
            job_id=jid, params=params, workspace_id=workspace_id, progress=progress
        )
        async with SessionLocal() as s:
            video = Video(
                workspace_id=workspace_id, job_id=str(jid),
                r2_key=result["r2_key"], topic=str(result.get("topic", ""))[:300],
                tool=result.get("tool"),
            )
            s.add(video)
            await s.flush()
            cost_actual = result.get("cost") or cost_estimate
            await jobs_svc.complete_job(s, jid, video_id=video.id, cost_actual=cost_actual)
        async with SessionLocal() as s:
            await record_pipeline_learnings(s, workspace_id, params.get("niche"), result)
        return {"status": "done", "r2_key": result["r2_key"]}
    except Exception as e:
        async with SessionLocal() as s:
            await jobs_svc.fail_job(s, jid, str(e))
        return {"status": "failed", "error": str(e)[:200]}


class WorkerSettings:
    functions = [health, generate_video_job]
    redis_settings = redis_settings()
    max_jobs = 10
    job_timeout = 60 * 30        # video generation can run for many minutes
    keep_result = 60 * 60
