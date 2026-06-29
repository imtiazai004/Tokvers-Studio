"""
Grok Imagine adapter — xAI (api.x.ai).

Verified contract (official docs):
  POST /v1/videos/generations
    body: {"model":"grok-imagine-video","prompt":...,"duration":...,
           "aspect_ratio":...,"resolution":..., optional "image":{"url":...}}
  response: {"request_id": ...}
  poll: GET /v1/videos/{request_id}  -> status pending|done|failed
  video: video.url  (or video.file_output.public_url)
  auth: header "Authorization: Bearer <key>"
"""
import asyncio
import os
import time

import aiofiles
import httpx

from .base import GenerationResult, VideoProvider, raise_http
from .settings import settings

XAI_BASE = "https://api.x.ai/v1"


class GrokProvider(VideoProvider):
    name = "grok"

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 price_per_second: float | None = None):
        self.api_key = api_key or settings.grok_api_key
        self.model = model or settings.grok_model
        self.price_per_second = (
            price_per_second if price_per_second is not None else settings.grok_price_per_second
        )

    async def generate(self, prompt, output_path, *, duration_seconds=8,
                       aspect_ratio="9:16", resolution="720p", reference_image_b64=None):
        if not self.api_key:
            raise RuntimeError("Grok API key not set (XAI_API_KEY).")

        started = time.monotonic()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        body: dict = {
            "model": self.model,
            "prompt": prompt,
            "duration": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        }
        if reference_image_b64:
            body["image"] = {"url": f"data:image/png;base64,{reference_image_b64}"}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{XAI_BASE}/videos/generations", headers=headers, json=body)
            raise_http(resp)
            data = resp.json()

        request_id = data.get("request_id")
        if not request_id:
            raise RuntimeError(f"Grok: no request_id in response: {data}")

        video_url = await self._poll(request_id, headers)
        await self._download(video_url, output_path)

        cost = self.price_per_second * duration_seconds if self.price_per_second else None
        return GenerationResult(
            output_path=output_path, provider=self.name, model=self.model,
            duration_seconds=duration_seconds, latency_seconds=time.monotonic() - started,
            cost_usd=cost, raw=data,
        )

    async def _poll(self, request_id: str, headers: dict, interval: int = 10,
                    max_attempts: int = 60) -> str:
        url = f"{XAI_BASE}/videos/{request_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(max_attempts):
                resp = await client.get(url, headers=headers)
                raise_http(resp)
                data = resp.json()
                status = data.get("status")
                if status == "done":
                    video = data.get("video", {}) or {}
                    out = video.get("url") or video.get("file_output", {}).get("public_url")
                    if not out:
                        raise RuntimeError(f"Grok: done but no video url: {data}")
                    return out
                if status == "failed":
                    raise RuntimeError(f"Grok: generation failed: {data}")
                await asyncio.sleep(interval)
        raise TimeoutError("Grok: generation timed out")

    async def _download(self, url: str, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url)
            raise_http(resp)
            content = resp.content
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(content)
