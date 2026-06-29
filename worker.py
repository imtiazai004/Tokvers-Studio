"""
Arq worker — executes long-running generation jobs off the Redis queue, in a
process SEPARATE from the stateless web tier.

Run:  arq worker.WorkerSettings
"""
import os
import uuid

from core import jobs as jobs_svc
from core import storage
from core.db import SessionLocal
from core.models import GenerationJob, Video
from core.queue import redis_settings
from providers import get_provider


async def health(ctx, msg: str = "ping") -> str:
    """Trivial task to verify the queue round-trip works."""
    return f"pong:{msg}"


async def generate_video_job(ctx, job_id) -> dict:
    """
    Walking-skeleton generation: one clip via the chosen provider -> R2 -> done.

    Credit hold was already placed at job creation; here we settle on success or
    refund on failure. The full 6-agent pipeline replaces the single-clip step
    later — the surrounding job/credit/storage flow stays the same.
    """
    if SessionLocal is None:
        return {"error": "DATABASE_URL not configured"}
    jid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))

    async with SessionLocal() as session:
        job = await session.get(GenerationJob, jid)
        if not job:
            return {"error": "job not found"}

        await jobs_svc.mark_running(session, job.id, step="video")
        tmp = os.path.join("output", "gen", f"{job.id}.mp4")
        try:
            params = job.params or {}
            prompt = params.get("product_name") or params.get("topic") or "a short UGC clip"
            provider = get_provider(job.provider or "veo")

            result = await provider.generate(prompt, tmp)  # raises if key/setup missing

            key = f"{job.workspace_id}/videos/{job.id}.mp4"
            await storage.upload_file(key, tmp, content_type="video/mp4")
            try:
                os.remove(tmp)
            except OSError:
                pass

            video = Video(
                workspace_id=job.workspace_id, job_id=str(job.id),
                r2_key=key, topic=str(prompt)[:300], tool=job.provider,
            )
            session.add(video)
            await session.flush()

            cost = result.cost_usd if result.cost_usd is not None else float(job.cost_estimate or 0)
            await jobs_svc.complete_job(session, job.id, video_id=video.id, cost_actual=cost)
            return {"status": "done", "r2_key": key}

        except Exception as e:
            await jobs_svc.fail_job(session, job.id, str(e))
            return {"status": "failed", "error": str(e)[:200]}


class WorkerSettings:
    functions = [health, generate_video_job]
    redis_settings = redis_settings()
    max_jobs = 10
    job_timeout = 60 * 30        # video generation can run for many minutes
    keep_result = 60 * 60        # keep job results for an hour
