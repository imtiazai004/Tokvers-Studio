"""
Veo 3 adapter — Google Gemini API (generativelanguage.googleapis.com).

Verified contract (official docs):
  POST /v1beta/models/{model}:predictLongRunning
    body: {"instances":[{"prompt": ...}], "parameters":{...}}
  poll: GET /v1beta/{operation_name}  until {"done": true}
  video: response.generateVideoResponse.generatedSamples[0].video.uri
  auth: header "x-goog-api-key: <key>"
"""
import asyncio
import os
import time

import aiofiles
import httpx

from .base import GenerationResult, VideoProvider, raise_http
from .settings import settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class VeoProvider(VideoProvider):
    name = "veo"

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 price_per_second: float | None = None):
        self.api_key = api_key or settings.veo_api_key
        self.model = model or settings.veo_model
        self.price_per_second = (
            price_per_second if price_per_second is not None else settings.veo_price_per_second
        )

    async def generate(self, prompt, output_path, *, duration_seconds=8,
                       aspect_ratio="9:16", resolution="720p", reference_image_b64=None):
        if not self.api_key:
            raise RuntimeError("Veo API key not set (VEO_API_KEY / GEMINI_API_KEY).")

        started = time.monotonic()
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        instance: dict = {"prompt": prompt}
        if reference_image_b64:
            instance["image"] = {"inlineData": {"mimeType": "image/png", "data": reference_image_b64}}

        body = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration_seconds,
                "resolution": resolution,
                "personGeneration": "allow_adult",
            },
        }

        url = f"{GEMINI_BASE}/models/{self.model}:predictLongRunning"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
            raise_http(resp)
            operation = resp.json()

        op_name = operation.get("name")
        if not op_name:
            raise RuntimeError(f"Veo: no operation name in response: {operation}")

        video_uri = await self._poll(op_name, headers)
        await self._download(video_uri, output_path, headers)

        cost = self.price_per_second * duration_seconds if self.price_per_second else None
        return GenerationResult(
            output_path=output_path, provider=self.name, model=self.model,
            duration_seconds=duration_seconds, latency_seconds=time.monotonic() - started,
            cost_usd=cost, raw=operation,
        )

    async def _poll(self, op_name: str, headers: dict, interval: int = 10,
                    max_attempts: int = 60) -> str:
        url = f"{GEMINI_BASE}/{op_name}"
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(max_attempts):
                resp = await client.get(url, headers=headers)
                raise_http(resp)
                data = resp.json()
                if data.get("done"):
                    samples = (
                        data.get("response", {})
                        .get("generateVideoResponse", {})
                        .get("generatedSamples", [])
                    )
                    if not samples:
                        raise RuntimeError(f"Veo: completed but no samples: {data}")
                    uri = samples[0].get("video", {}).get("uri")
                    if not uri:
                        raise RuntimeError(f"Veo: no video uri in sample: {data}")
                    return uri
                await asyncio.sleep(interval)
        raise TimeoutError("Veo: generation timed out")

    async def _download(self, uri: str, output_path: str, headers: dict) -> None:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(uri, headers=headers)
            raise_http(resp)
            content = resp.content
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(content)
