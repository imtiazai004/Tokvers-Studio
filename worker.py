"""
Arq worker — executes long-running jobs (video generation) off the Redis queue,
in a process SEPARATE from the stateless web tier.

Run:  arq worker.WorkerSettings
"""
from core.queue import redis_settings


async def health(ctx, msg: str = "ping") -> str:
    """Trivial task to verify the queue round-trip works."""
    return f"pong:{msg}"


# Real generation task is wired in the walking-skeleton step (provider + R2 + jobs).
# async def generate_video_job(ctx, job_id): ...


class WorkerSettings:
    functions = [health]
    redis_settings = redis_settings()
    max_jobs = 10
    job_timeout = 60 * 30        # video generation can run for many minutes
    keep_result = 60 * 60        # keep job results for an hour
