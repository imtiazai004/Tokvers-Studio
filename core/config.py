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

    # ── Limits / cost control ───────────────────────────────────
    max_workspace_monthly_spend: float = 0   # 0 = no cap (USD-equivalent credits/month)
    generation_enabled: bool = True          # global kill-switch for generation

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
