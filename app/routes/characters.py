"""Characters API — recurring creators for face/style consistency across scenes."""
import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import require_workspace_id
from core import storage
from core.db import get_session
from core.models import Character

router = APIRouter(prefix="/api/characters", tags=["characters"])


class CharacterIn(BaseModel):
    name: str
    description: str | None = ""
    personality: str | None = ""
    appearance: str | None = ""
    niche: str | None = "lifestyle"
    voice_gender: str = "female"
    image: str | None = None   # base64 (no data-URI prefix)


def _dto(ch: Character) -> dict:
    return {
        "id": str(ch.id), "name": ch.name, "description": ch.description,
        "personality": ch.personality, "appearance": ch.appearance,
        "niche": ch.niche, "voice_gender": ch.voice_gender,
        "has_image": bool(ch.image_r2_key), "videos_created": ch.videos_created,
    }


@router.post("")
async def create(data: CharacterIn, ws=Depends(require_workspace_id),
                 session: AsyncSession = Depends(get_session)):
    ch = Character(
        workspace_id=ws, name=data.name, description=data.description or None,
        personality=data.personality or None, appearance=data.appearance or None,
        niche=data.niche, voice_gender=data.voice_gender,
    )
    session.add(ch)
    await session.flush()
    if data.image:
        key = f"{ws}/characters/{ch.id}.png"
        await storage.upload_bytes(key, base64.b64decode(data.image), content_type="image/png")
        ch.image_r2_key = key
    await session.commit()
    return _dto(ch)


@router.get("")
async def list_characters(ws=Depends(require_workspace_id),
                          session: AsyncSession = Depends(get_session)):
    chs = list(await session.scalars(
        select(Character)
        .where(Character.workspace_id == ws, Character.is_active.is_(True))
        .order_by(Character.created_at.desc())
    ))
    return {"characters": [_dto(c) for c in chs]}


@router.delete("/{character_id}")
async def delete_character(character_id: uuid.UUID, ws=Depends(require_workspace_id),
                           session: AsyncSession = Depends(get_session)):
    ch = await session.scalar(
        select(Character).where(Character.id == character_id, Character.workspace_id == ws)
    )
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")
    ch.is_active = False
    await session.commit()
    return {"status": "deleted"}
