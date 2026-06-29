"""
Env-driven provider settings (keys, model ids, pricing).

Pricing is intentionally NOT hard-coded — exact per-second prices change and must
be verified. Set `*_PRICE_PER_SECOND` to have the probe report real cost; if unset,
cost is reported as "unknown" rather than a fabricated number.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _float_or_none(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


class ProviderSettings:
    def __init__(self) -> None:
        # Veo 3 (Google Gemini API)
        self.veo_api_key = (
            os.getenv("VEO_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
            or ""
        )
        self.veo_model = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
        self.veo_price_per_second = _float_or_none(os.getenv("VEO_PRICE_PER_SECOND"))

        # Grok Imagine (xAI)
        self.grok_api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY") or ""
        self.grok_model = os.getenv("GROK_MODEL", "grok-imagine-video")
        self.grok_price_per_second = _float_or_none(os.getenv("GROK_PRICE_PER_SECOND"))


settings = ProviderSettings()
