"""Central application settings — env-driven (12-factor)."""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SESSION_SECRET = "dev-only-insecure-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── Core infra ──────────────────────────────────────────────
    database_url: str = ""          # Neon Postgres (postgresql://...)
    redis_url: str = ""             # Arq queue + cache + SSE pub/sub

    # ── Security ────────────────────────────────────────────────
    session_secret: str = _INSECURE_SESSION_SECRET
    encryption_key: str = ""        # Fernet key for per-workspace BYOK secrets
    environment: str = "development"  # "production" => secure cookies + HSTS
    app_base_url: str = "http://localhost:8001"  # for building email links
    sentry_dsn: str = ""            # optional error tracking (env-gated)
    # Number of trusted reverse proxies in front of the app (Render LB = 1;
    # set to 2 if you later put Cloudflare in front). Used to derive the real
    # client IP from X-Forwarded-For safely (rightmost hop is unspoofable).
    trusted_proxy_hops: int = 1
    # Reject request bodies larger than this (base64 product images inflate ~33%,
    # so 8 MB covers a ~6 MB source image while blocking memory-exhaustion payloads).
    max_request_bytes: int = 8 * 1024 * 1024

    # ── Email (password reset / verification) ───────────────────
    email_provider: str = "console"  # console | smtp | resend
    email_from: str = "Tokverse Studio <no-reply@tokverse.studio>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""         # https://resend.com — set email_provider=resend

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def _fail_closed_in_production(self):
        """In production, refuse to boot with a forgeable session secret or a
        missing encryption key — fail closed rather than run insecurely."""
        if self.is_production:
            if not self.session_secret or self.session_secret == _INSECURE_SESSION_SECRET:
                raise ValueError(
                    "SESSION_SECRET must be set to a strong random value in production "
                    "(the insecure default would let sessions be forged)."
                )
            if not self.encryption_key:
                raise ValueError("ENCRYPTION_KEY must be set in production (used to encrypt stored secrets).")
        return self

    # ── Limits / cost control ───────────────────────────────────
    max_workspace_monthly_spend: float = 0   # 0 = no cap (USD-equivalent credits/month)
    generation_enabled: bool = True          # global kill-switch for generation
    credits_per_scene: float = 1.0           # placeholder estimate until probe gives real cost

    # ── Billing ─────────────────────────────────────────────────
    billing_provider: str = "manual"         # manual | paddle | lemonsqueezy (plug gateway later)

    # ── TikTok integration (Login Kit + Content Posting API) ────
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = ""            # must match the app's registered redirect
    tiktok_scopes: str = "user.info.basic,video.list,video.upload,video.publish"

    @property
    def tiktok_configured(self) -> bool:
        return bool(self.tiktok_client_key and self.tiktok_client_secret and self.tiktok_redirect_uri)

    # ── Cloudflare R2 (object storage) ──────────────────────────
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""    # CDN/public base for serving objects

    @property
    def db_configured(self) -> bool:
        return bool(self.database_url)


settings = Settings()
