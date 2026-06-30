"""Per-workspace learning store — the self-improvement loop fills this as videos
generate. Upsert by (workspace, agent, key)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Learning


async def save_learning(session: AsyncSession, workspace_id, agent: str, key: str,
                        value, confidence: float = 0.6) -> None:
    existing = await session.scalar(
        select(Learning).where(
            Learning.workspace_id == workspace_id,
            Learning.agent_name == agent,
            Learning.learning_key == key,
        )
    )
    if existing:
        existing.learning_value = str(value)
        existing.confidence = confidence
    else:
        session.add(Learning(
            workspace_id=workspace_id, agent_name=agent,
            learning_key=key, learning_value=str(value), confidence=confidence,
        ))
    await session.commit()


async def record_pipeline_learnings(session, workspace_id, niche: str, result: dict) -> None:
    """A few learnings captured from a successful generation."""
    niche = niche or "general"
    if result.get("hook"):
        await save_learning(session, workspace_id, "Script Agent", f"winning_hook_{niche}", result["hook"], 0.7)
    if result.get("tool"):
        await save_learning(session, workspace_id, "Video Agent", f"preferred_tool_{niche}", result["tool"], 0.65)
    if result.get("hashtags"):
        await save_learning(session, workspace_id, "Research Agent", f"top_hashtags_{niche}",
                            " · ".join(result["hashtags"][:5]), 0.6)
