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

        # Higgsfield (video) — optional provider; contract confirmed on first real call
        self.higgsfield_api_key = os.getenv("HIGGSFIELD_API_KEY") or ""
        self.higgsfield_model = os.getenv("HIGGSFIELD_MODEL", "higgsfield_v1")
        self.higgsfield_price_per_second = _float_or_none(os.getenv("HIGGSFIELD_PRICE_PER_SECOND"))

        # Voice providers
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY") or ""
        self.elevenlabs_voice_male = os.getenv("ELEVENLABS_VOICE_ID_MALE", "pNInz6obpgDQGcFmaJgB")
        self.elevenlabs_voice_female = os.getenv("ELEVENLABS_VOICE_ID_FEMALE", "EXAVITQu4vr4xnSDxMaL")
        self.fish_audio_api_key = os.getenv("FISH_AUDIO_API_KEY") or ""
        self.fish_model = os.getenv("FISH_MODEL", "speech-1.6")
        self.fish_voice_id = os.getenv("FISH_VOICE_ID", "")  # reference_id of a Fish voice model


settings = ProviderSettings()
