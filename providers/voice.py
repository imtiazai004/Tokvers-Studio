"""
Voice (TTS) provider abstraction — mirrors the video VideoProvider pattern.

Adapters: ElevenLabs and Fish Audio. The app/pipeline picks one via
get_voice_provider(name); adding another TTS backend is just one more adapter.
"""
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import aiofiles
import httpx

from .base import raise_http
from .settings import settings


@dataclass
class VoiceResult:
    output_path: str
    provider: str
    latency_seconds: float
    raw: dict = field(default_factory=dict)


class VoiceProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, output_path: str, *, gender: str = "female",
                         **opts) -> VoiceResult:
        raise NotImplementedError


class ElevenLabsVoice(VoiceProvider):
    name = "elevenlabs"
    BASE = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.elevenlabs_api_key

    async def synthesize(self, text, output_path, *, gender="female", stability=0.4, style=0.5, **_):
        if not self.api_key:
            raise RuntimeError("ElevenLabs API key not set (ELEVENLABS_API_KEY).")
        started = time.monotonic()
        voice_id = settings.elevenlabs_voice_female if gender == "female" else settings.elevenlabs_voice_male
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        body = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": stability, "similarity_boost": 0.8,
                               "style": style, "use_speaker_boost": True},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.BASE}/text-to-speech/{voice_id}", headers=headers, json=body)
            raise_http(resp)
            audio = resp.content
        await _write(output_path, audio)
        return VoiceResult(output_path, self.name, time.monotonic() - started)


class FishAudioVoice(VoiceProvider):
    name = "fish"
    BASE = "https://api.fish.audio/v1"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.fish_audio_api_key
        self.model = model or settings.fish_model

    async def synthesize(self, text, output_path, *, gender="female", **_):
        if not self.api_key:
            raise RuntimeError("Fish Audio API key not set (FISH_AUDIO_API_KEY).")
        started = time.monotonic()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                   "model": self.model}
        body: dict = {"text": text, "format": "mp3"}
        if settings.fish_voice_id:
            body["reference_id"] = settings.fish_voice_id
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.BASE}/tts", headers=headers, json=body)
            raise_http(resp)
            audio = resp.content
        await _write(output_path, audio)
        return VoiceResult(output_path, self.name, time.monotonic() - started)


async def _write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)


_VOICE_PROVIDERS: dict[str, type[VoiceProvider]] = {
    "elevenlabs": ElevenLabsVoice,
    "fish": FishAudioVoice,
}


def get_voice_provider(name: str, **kwargs) -> VoiceProvider:
    key = (name or "").lower()
    if key not in _VOICE_PROVIDERS:
        raise ValueError(f"Unknown voice provider '{name}'. Available: {list(_VOICE_PROVIDERS)}")
    return _VOICE_PROVIDERS[key](**kwargs)


def available_voice_providers() -> list[str]:
    return list(_VOICE_PROVIDERS)
