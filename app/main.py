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

from app.routes import auth, billing, characters, credits, dashboard, jobs, providers, tiktok
from core.config import settings
from core.queue import get_pool

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


async def _auth_guard(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIX):
        return await call_next(request)
    if request.session.get("user_id"):
        return await call_next(request)
    if path in APP_PAGES:
        return RedirectResponse("/login", status_code=302)
    return JSONResponse({"error": "Authentication required"}, status_code=401)


async def _security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.is_production:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


# Middleware order (added last = outermost = runs first on request):
#   security headers  ->  session  ->  auth guard  ->  app
# Session must populate request.session before the auth guard reads it.
app.add_middleware(BaseHTTPMiddleware, dispatch=_auth_guard)
app.add_middleware(
    SessionMiddleware, secret_key=settings.session_secret,
    same_site="lax", https_only=settings.is_production,
)
app.add_middleware(BaseHTTPMiddleware, dispatch=_security_headers)
