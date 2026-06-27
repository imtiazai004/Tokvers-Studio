import os
import asyncio
import aiofiles
import httpx
from config.client_config import get_key

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "veo-3.0-generate-preview"

def _api_key():
    return get_key("google_ai_studio_api_key")

async def generate_video_veo3(prompt: str, output_path: str, duration: int = 8, model: str = DEFAULT_MODEL) -> str:
    api_key = _api_key()

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{BASE_URL}/models/{model}:generateVideo",
            params={"key": api_key},
            json={
                "prompt": {"text": prompt},
                "videoConfig": {
                    "durationSeconds": duration,
                    "aspectRatio": "9:16",
                    "personGeneration": "allow_adult"
                }
            }
        )
        response.raise_for_status()
        operation = response.json()

    video_bytes = await _poll_operation(operation.get("name"), api_key)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    async with aiofiles.open(output_path, "wb") as f:
        await f.write(video_bytes)
    return output_path

async def generate_video_veo3_with_image(prompt: str, image_base64: str, output_path: str, duration: int = 8, model: str = DEFAULT_MODEL) -> str:
    """Character reference image se video — Veo3 image-to-video."""
    api_key = _api_key()

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{BASE_URL}/models/{model}:generateVideo",
            params={"key": api_key},
            json={
                "prompt": {"text": prompt},
                "image": {
                    "imageBytes": image_base64,
                    "mimeType": "image/jpeg"
                },
                "videoConfig": {
                    "durationSeconds": duration,
                    "aspectRatio": "9:16",
                    "personGeneration": "allow_adult"
                }
            }
        )
        response.raise_for_status()
        operation = response.json()

    video_bytes = await _poll_operation(operation.get("name"), api_key)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    async with aiofiles.open(output_path, "wb") as f:
        await f.write(video_bytes)
    return output_path

async def _poll_operation(operation_name: str, api_key: str, max_attempts: int = 60) -> bytes:
    poll_url = f"{BASE_URL}/{operation_name}"

    for _ in range(max_attempts):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(poll_url, params={"key": api_key})
            response.raise_for_status()
            data = response.json()

        if data.get("done"):
            samples = data.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
            if not samples:
                raise Exception("Veo3: No video samples in response")
            video_uri = samples[0].get("video", {}).get("uri", "")
            if not video_uri:
                raise Exception("Veo3: No video URI in response")
            return await _download_video(video_uri, api_key)

        await asyncio.sleep(10)

    raise Exception("Veo3 generation timed out")

async def _download_video(uri: str, api_key: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.get(uri, params={"key": api_key})
            r.raise_for_status()
            return r.content
        except Exception:
            r = await client.get(uri)
            r.raise_for_status()
            return r.content

async def generate_scenes_veo3(scene_prompts: list[str], output_dir: str, character_image_b64: str = None, product_image: str = None) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    video_paths = []
    reference_image = character_image_b64 or product_image
    for i, prompt in enumerate(scene_prompts):
        output_path = os.path.join(output_dir, f"scene_{i+1:02d}.mp4")
        if reference_image:
            path = await generate_video_veo3_with_image(prompt, reference_image, output_path)
        else:
            path = await generate_video_veo3(prompt, output_path)
        video_paths.append(path)
    return video_paths
