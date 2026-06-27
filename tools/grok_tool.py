import os
import httpx
import aiofiles
import asyncio
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

BASE_URL = "https://api.x.ai/v1"

def _api_key(): return get_key("grok_api_key")

async def generate_video_grok(prompt: str, output_path: str, duration: int = 10) -> str:
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-2-vision-1212",
        "prompt": prompt,
        "duration": duration,
        "resolution": "720p",
        "aspect_ratio": "9:16"
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{BASE_URL}/video/generations",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()

    generation_id = data.get("id")
    video_url = await _poll_grok_video(generation_id)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    async with httpx.AsyncClient(timeout=120) as client:
        video_response = await client.get(video_url)
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(video_response.content)

    return output_path

async def _poll_grok_video(generation_id: str, max_attempts: int = 30) -> str:
    headers = {"Authorization": f"Bearer {_api_key()}"}

    for attempt in range(max_attempts):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{BASE_URL}/video/generations/{generation_id}",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        status = data.get("status")
        if status == "completed":
            return data["url"]
        elif status == "failed":
            raise Exception(f"Grok video generation failed: {data.get('error')}")

        await asyncio.sleep(10)

    raise Exception("Grok video generation timeout")

async def generate_video_grok_with_image(prompt: str, image_base64: str, output_path: str, duration: int = 10) -> str:
    """Character reference image se video banao - consistent character ke liye."""
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-2-vision-1212",
        "prompt": prompt,
        "image": image_base64,
        "duration": duration,
        "resolution": "720p",
        "aspect_ratio": "9:16"
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{BASE_URL}/video/generations",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()

    generation_id = data.get("id")
    video_url = await _poll_grok_video(generation_id)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    async with httpx.AsyncClient(timeout=120) as client:
        video_response = await client.get(video_url)
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(video_response.content)

    return output_path

async def generate_scenes_grok(scene_prompts: list[str], output_dir: str, character_image_b64: str = None, product_image: str = None) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    video_paths = []
    reference_image = character_image_b64 or product_image
    for i, prompt in enumerate(scene_prompts):
        output_path = os.path.join(output_dir, f"scene_{i+1:02d}.mp4")
        if reference_image:
            path = await generate_video_grok_with_image(prompt, reference_image, output_path)
        else:
            path = await generate_video_grok(prompt, output_path)
        video_paths.append(path)
    return video_paths
