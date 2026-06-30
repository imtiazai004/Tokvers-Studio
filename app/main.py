"""
New Tokverse Studio app (multi-tenant, Neon-backed) — JSON API + served frontend.

Runs alongside legacy main.py until proven, then becomes the entrypoint.
Run:  uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, credits, dashboard, jobs, providers
from core.config import settings
from core.queue import get_pool

app = FastAPI(title="Tokverse Studio")


# ── Startup / shutdown: Arq pool for enqueueing jobs ────────
@app.on_event("startup")
async def _startup():
    app.state.arq = await get_pool() if settings.redis_url else None


@app.on_event("shutdown")
async def _shutdown():
    pool = getattr(app.state, "arq", None)
    if pool is not None:
        await pool.aclose()


# ── API routers ─────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(credits.router)
app.include_router(jobs.router)
app.include_router(providers.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "db_configured": settings.db_configured}


# ── Served frontend (app pages) ─────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

_PAGES = {
    "/": "static/create.html",
    "/dashboard": "static/dash.html",
    "/analytics": "static/analytics.html",
    "/settings-page": "static/settings.html",
    "/content-library": "static/content-library.html",
    "/products": "static/products.html",
    "/learnings": "static/learnings.html",
    "/guide": "static/guide.html",
}


@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")


@app.get("/signup")
async def signup_page():
    return FileResponse("static/signup.html")


def _page(file_path: str):
    async def _serve():
        return FileResponse(file_path)
    return _serve


for _route, _file in _PAGES.items():
    app.add_api_route(_route, _page(_file), methods=["GET"])


# ── Auth guard (inner) + session (outer) ────────────────────
APP_PAGES = set(_PAGES.keys())
PUBLIC_EXACT = {
    "/login", "/signup", "/api/health", "/api/providers",
    "/api/auth/login", "/api/auth/signup", "/api/auth/logout", "/api/auth/me",
}
PUBLIC_PREFIX = ("/static", "/favicon")


async def _auth_guard(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIX):
        return await call_next(request)
    if request.session.get("user_id"):
        return await call_next(request)
    if path in APP_PAGES:
        return RedirectResponse("/login", status_code=302)
    return JSONResponse({"error": "Authentication required"}, status_code=401)


# Order: SessionMiddleware added last => outermost => runs first, so request.session
# is populated before the auth guard runs.
app.add_middleware(BaseHTTPMiddleware, dispatch=_auth_guard)
app.add_middleware(
    SessionMiddleware, secret_key=settings.session_secret,
    same_site="lax", https_only=False,
)
