"""Central application settings — env-driven (12-factor)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── Core infra ──────────────────────────────────────────────
    database_url: str = ""          # Neon Postgres (postgresql://...)
    redis_url: str = ""             # Arq queue + cache + SSE pub/sub

    # ── Security ────────────────────────────────────────────────
    session_secret: str = "dev-only-insecure-change-me"
    encryption_key: str = ""        # Fernet key for per-workspace BYOK secrets
    environment: str = "development"  # "production" => secure cookies + HSTS
    app_base_url: str = "http://localhost:8001"  # for building email links
    sentry_dsn: str = ""            # optional error tracking (env-gated)

    # ── Email (password reset / verification) ───────────────────
    email_provider: str = "console"  # console | smtp (plug SMTP later)
    email_from: str = "Tokverse Studio <no-reply@tokverse.studio>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    # ── Limits / cost control ───────────────────────────────────
    max_workspace_monthly_spend: float = 0   # 0 = no cap (USD-equivalent credits/month)
    generation_enabled: bool = True          # global kill-switch for generation
    credits_per_scene: float = 1.0           # placeholder estimate until probe gives real cost

    # ── Billing ─────────────────────────────────────────────────
    billing_provider: str = "manual"         # manual | paddle | lemonsqueezy (plug gateway later)

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
