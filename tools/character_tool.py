import os
import shutil
import base64
import aiofiles
from memory.database import save_character, get_character, get_all_characters

CHARACTERS_DIR = "assets/characters"

def ensure_dir():
    os.makedirs(CHARACTERS_DIR, exist_ok=True)

async def create_character(
    name: str,
    description: str,
    personality: str,
    appearance: str,
    niche: str,
    voice_gender: str = "female",
    image_bytes: bytes = None,
    image_filename: str = None,
) -> dict:
    """
    Naya character create karo aur save karo.
    Image optional hai - agar hai toh image-to-video use hoga.
    """
    ensure_dir()

    image_path = ""
    if image_bytes and image_filename:
        safe_name = name.lower().replace(" ", "_")
        ext = os.path.splitext(image_filename)[1] or ".jpg"
        image_path = os.path.join(CHARACTERS_DIR, f"{safe_name}{ext}")
        async with aiofiles.open(image_path, "wb") as f:
            await f.write(image_bytes)

    char_id = await save_character(
        name=name,
        description=description,
        personality=personality,
        appearance=appearance,
        image_path=image_path,
        niche=niche,
        voice_gender=voice_gender,
    )

    return {
        "id": char_id,
        "name": name,
        "description": description,
        "personality": personality,
        "appearance": appearance,
        "image_path": image_path,
        "niche": niche,
        "voice_gender": voice_gender,
    }

async def load_character(character_id: int) -> dict | None:
    """Character data load karo."""
    return await get_character(character_id)

async def get_character_image_base64(character: dict) -> str | None:
    """Character ki image base64 mein do - API ke liye."""
    image_path = character.get("image_path", "")
    if not image_path or not os.path.exists(image_path):
        return None
    async with aiofiles.open(image_path, "rb") as f:
        data = await f.read()
    return base64.b64encode(data).decode("utf-8")

def build_character_prompt(character: dict) -> str:
    """
    Character description se video prompt extension banao.
    Ye har scene ke prompt mein add hoga.
    """
    name = character.get("name", "")
    appearance = character.get("appearance", "")
    personality = character.get("personality", "")

    parts = []
    if name:
        parts.append(f"Main character: {name}")
    if appearance:
        parts.append(f"Appearance: {appearance}")
    if personality:
        parts.append(f"Vibe/personality: {personality}")

    parts.append("Consistent character appearance across all scenes")
    parts.append("Same person throughout the video")

    return ". ".join(parts)

async def list_characters() -> list:
    """Saare active characters lo."""
    return await get_all_characters()
