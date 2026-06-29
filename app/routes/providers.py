"""Lists the user-selectable generation providers (so the UI can show the options)."""
from fastapi import APIRouter

from providers import available_providers, get_provider
from providers.voice import available_voice_providers, get_voice_provider

router = APIRouter(prefix="/api/providers", tags=["providers"])

LABELS = {
    "veo": "Veo 3",
    "grok": "Grok Imagine",
    "higgsfield": "Higgsfield",
    "elevenlabs": "ElevenLabs",
    "fish": "Fish Audio",
}


def _configured(getter, name: str) -> bool:
    try:
        return bool(getattr(getter(name), "api_key", ""))
    except Exception:
        return False


@router.get("")
async def list_providers():
    """All registered providers + whether each has a key configured (usable)."""
    return {
        "video": [
            {"id": p, "label": LABELS.get(p, p), "configured": _configured(get_provider, p)}
            for p in available_providers()
        ],
        "voice": [
            {"id": p, "label": LABELS.get(p, p), "configured": _configured(get_voice_provider, p)}
            for p in available_voice_providers()
        ],
    }
