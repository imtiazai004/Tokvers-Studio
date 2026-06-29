"""New Tokverse Studio API app (multi-tenant, Neon-backed).

Run:  uvicorn app.main:app --reload
Currently exposes auth; job/credit routes and the static frontend are wired in
as the cutover proceeds.
"""
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, credits, jobs
from core.config import settings
from core.queue import get_pool

app = FastAPI(title="Tokverse Studio API")


@app.on_event("startup")
async def _startup():
    app.state.arq = await get_pool() if settings.redis_url else None


@app.on_event("shutdown")
async def _shutdown():
    pool = getattr(app.state, "arq", None)
    if pool is not None:
        await pool.aclose()

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,  # set True in production (HTTPS)
)

app.include_router(auth.router)
app.include_router(credits.router)
app.include_router(jobs.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "db_configured": settings.db_configured}
