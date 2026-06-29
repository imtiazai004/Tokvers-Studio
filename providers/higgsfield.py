"""
Higgsfield adapter (video) — OPTIONAL provider.

Contract is a best-effort from public docs (POST /v1/generations, Bearer auth,
poll /v1/generations/{id}); exact field names are confirmed on the first real
call once a key is supplied (our raise_http surfaces the API's own error, like it
did for Grok). Swapping/fixing this adapter changes nothing else — that's the
point of the provider abstraction.
"""
import asyncio
import base64
import os
import time

import aiofiles
import httpx

from .base import GenerationResult, VideoProvider, raise_http
from .settings import settings

HIGGSFIELD_BASE = "https://api.higgsfield.ai/v1"


class HiggsfieldProvider(VideoProvider):
    name = "higgsfield"

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 price_per_second: float | None = None):
        self.api_key = api_key or settings.higgsfield_api_key
        self.model = model or settings.higgsfield_model
        self.price_per_second = (
            price_per_second if price_per_second is not None else settings.higgsfield_price_per_second
        )

    async def generate(self, prompt, output_path, *, duration_seconds=8,
                       aspect_ratio="9:16", resolution="720p", reference_image_b64=None):
        if not self.api_key:
            raise RuntimeError("Higgsfield API key not set (HIGGSFIELD_API_KEY).")

        started = time.monotonic()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        body: dict = {
            "model": self.model,
            "prompt": prompt,
            "duration": duration_seconds,
            "fps": 30,
            "aspect_ratio": aspect_ratio,
        }
        if reference_image_b64:
            body["task"] = "image-to-video"
            body["input_image"] = f"data:image/png;base64,{reference_image_b64}"
        else:
            body["task"] = "text-to-video"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{HIGGSFIELD_BASE}/generations", headers=headers, json=body)
            raise_http(resp)
            data = resp.json()

        gen_id = data.get("generation_id") or data.get("id")
        if not gen_id:
            raise RuntimeError(f"Higgsfield: no generation id in response: {data}")

        video_url = await self._poll(gen_id, headers)
        await self._download(video_url, output_path)

        cost = self.price_per_second * duration_seconds if self.price_per_second else None
        return GenerationResult(
            output_path=output_path, provider=self.name, model=self.model,
            duration_seconds=duration_seconds, latency_seconds=time.monotonic() - started,
            cost_usd=cost, raw=data,
        )

    async def _poll(self, gen_id, headers, interval=10, max_attempts=60):
        url = f"{HIGGSFIELD_BASE}/generations/{gen_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(max_attempts):
                resp = await client.get(url, headers=headers)
                raise_http(resp)
                data = resp.json()
                status = (data.get("status") or "").lower()
                if status in ("completed", "succeeded", "done"):
                    out = data.get("output_url") or data.get("url") or (data.get("output", {}) or {}).get("url")
                    if not out:
                        raise RuntimeError(f"Higgsfield: completed but no output url: {data}")
                    return out
                if status in ("failed", "error"):
                    raise RuntimeError(f"Higgsfield: generation failed: {data}")
                await asyncio.sleep(interval)
        raise TimeoutError("Higgsfield: generation timed out")

    async def _download(self, url, output_path):
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url)
            raise_http(resp)
            content = resp.content
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(content)
