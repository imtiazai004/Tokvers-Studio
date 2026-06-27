import os
import httpx
import aiofiles
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

BASE_URL = "https://api.elevenlabs.io/v1"

def _api_key(): return get_key("elevenlabs_api_key")
def _voice_male(): return get_key("elevenlabs_voice_id_male") or "pNInz6obpgDQGcFmaJgB"
def _voice_female(): return get_key("elevenlabs_voice_id_female") or "EXAVITQu4vr4xnSDxMaL"

async def generate_voiceover(
    script: str,
    gender: str = "female",
    output_path: str = "output/audio/voice.mp3",
    stability: float = 0.4,
    style: float = 0.5,
) -> str:
    voice_id = _voice_female() if gender == "female" else _voice_male()

    headers = {
        "xi-api-key": _api_key(),
        "Content-Type": "application/json"
    }
    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": 0.8,
            "style": style,
            "use_speaker_boost": True
        }
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{BASE_URL}/text-to-speech/{voice_id}",
            headers=headers,
            json=payload
        )
        response.raise_for_status()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    async with aiofiles.open(output_path, "wb") as f:
        await f.write(response.content)

    return output_path

async def get_available_voices() -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/voices",
            headers={"xi-api-key": _api_key()}
        )
        response.raise_for_status()
        data = response.json()
        return [{"id": v["voice_id"], "name": v["name"]} for v in data.get("voices", [])]
