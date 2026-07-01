"""
New Tokverse Studio app (multi-tenant, Neon-backed) — JSON API + served frontend.

Runs alongside legacy main.py until proven, then becomes the entrypoint.
Run:  uvicorn app.main:app --reload
"""
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.routes import admin, auth, billing, characters, credits, dashboard, jobs, providers, settings as settings_routes, team, tiktok
from core.config import settings
from core.db import SessionLocal
from core.models import User
from core.queue import get_pool

# Session cookie lifetime (also caps how long a stolen cookie stays valid).
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days

# Content-Security-Policy: scripts are all same-origin; only fonts are external
# (Fontshare). 'unsafe-inline' is kept for the hand-written inline styles/scripts;
# CSP here still blocks external script origins, framing, and base-tag hijacking.
_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "media-src 'self' https: blob:; "
    "style-src 'self' 'unsafe-inline' https://api.fontshare.com https://cdn.fontshare.com; "
    "font-src 'self' data: https://api.fontshare.com https://cdn.fontshare.com; "
    "script-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
)

# ── Error tracking (optional, env-gated) ────────────────────
if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment,
                        traces_sample_rate=0.1)
    except Exception:
        pass  # never let monitoring break startup

app = FastAPI(title="Tokverse Studio")


# ── Startup / shutdown: Arq pool for enqueueing jobs ────────
@app.on_event("startup")
async def _startup():
    # Never let a missing/misconfigured queue crash the web tier — generation
    # enqueue just degrades (and is gated by GENERATION_ENABLED anyway).
    app.state.arq = None
    if settings.redis_url:
        try:
            app.state.arq = await get_pool()
        except Exception as e:
            print(f"WARNING: Arq/Redis pool unavailable ({e}); job enqueue disabled.", flush=True)


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
app.include_router(characters.router)
app.include_router(billing.router)
app.include_router(tiktok.router)
app.include_router(settings_routes.router)
app.include_router(team.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "db_configured": settings.db_configured}


# ── Served frontend (app pages) ─────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

_PAGES = {
    "/": "static/create.html",
    "/dashboard": "static/dash.html",
    "/analytics": "static/analyt.html",
    "/settings-page": "static/settings.html",
    "/content-library": "static/lib.html",
    "/products": "static/prod.html",
    "/learnings": "static/learn.html",
    "/characters": "static/chars.html",
    "/billing": "static/billing.html",
    "/settings": "static/settings.html",
    "/guide": "static/guide.html",
}


@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")


@app.get("/signup")
async def signup_page():
    return FileResponse("static/signup.html")


@app.get("/forgot")
async def forgot_page():
    return FileResponse("static/forgot.html")


@app.get("/reset")
async def reset_page():
    return FileResponse("static/reset.html")


@app.get("/admin")
async def admin_page(request: Request):
    """Admin-only review console. Non-admins are bounced to the dashboard."""
    uid = request.session.get("user_id")
    if uid and SessionLocal is not None:
        async with SessionLocal() as s:
            user = await s.get(User, uuid.UUID(uid))
        if user and user.is_admin:
            return FileResponse("static/admin.html")
    return RedirectResponse("/dashboard", status_code=302)


def _page(file_path: str):
    async def _serve():
        return FileResponse(file_path)
    return _serve


for _route, _file in _PAGES.items():
    app.add_api_route(_route, _page(_file), methods=["GET"])


# ── Auth guard (inner) + session (outer) ────────────────────
APP_PAGES = set(_PAGES.keys())
PUBLIC_EXACT = {
    "/login", "/signup", "/forgot", "/reset", "/api/health", "/api/providers", "/api/billing/plans",
    "/api/auth/login", "/api/auth/signup", "/api/auth/logout", "/api/auth/me",
    "/api/auth/forgot-password", "/api/auth/reset-password", "/api/auth/verify",
}
PUBLIC_PREFIX = ("/static", "/favicon")


async def _session_still_valid(request: Request) -> bool:
    """Confirm the session's version still matches the user's — lets a password
    change/reset invalidate all previously issued cookies. Fails open on a
    transient DB error (defense-in-depth, not the primary auth check)."""
    if SessionLocal is None:
        return True
    uid = request.session.get("user_id")
    ver = request.session.get("sv", 0)
    try:
        async with SessionLocal() as s:
            current = await s.scalar(select(User.session_version).where(User.id == uuid.UUID(uid)))
    except Exception:
        return True
    if current is None:      # user no longer exists
        return False
    return current == ver


async def _auth_guard(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIX):
        return await call_next(request)
    if request.session.get("user_id"):
        if await _session_still_valid(request):
            return await call_next(request)
        request.session.clear()
    if path in APP_PAGES:
        return RedirectResponse("/login", status_code=302)
    return JSONResponse({"error": "Authentication required"}, status_code=401)


async def _limit_body(request: Request, call_next):
    """Reject oversized request bodies up front (memory-exhaustion guard)."""
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > settings.max_request_bytes:
                return JSONResponse({"error": "Request too large"}, status_code=413)
        except ValueError:
            return JSONResponse({"error": "Invalid Content-Length"}, status_code=400)
    return await call_next(request)


async def _security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    resp.headers["Content-Security-Policy"] = _CSP
    if settings.is_production:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


# Middleware order (added last = outermost = runs first on request):
#   security headers  ->  session  ->  auth guard  ->  app
# Session must populate request.session before the auth guard reads it.
app.add_middleware(BaseHTTPMiddleware, dispatch=_auth_guard)
app.add_middleware(
    SessionMiddleware, secret_key=settings.session_secret,
    same_site="lax", https_only=settings.is_production, max_age=SESSION_MAX_AGE,
)
app.add_middleware(BaseHTTPMiddleware, dispatch=_security_headers)
app.add_middleware(BaseHTTPMiddleware, dispatch=_limit_body)
