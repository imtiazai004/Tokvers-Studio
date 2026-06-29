"""New Tokverse Studio API app (multi-tenant, Neon-backed).

Run:  uvicorn app.main:app --reload
Currently exposes auth; job/credit routes and the static frontend are wired in
as the cutover proceeds.
"""
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, credits, jobs
from core.config import settings

app = FastAPI(title="Tokverse Studio API")

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
