import uuid
import asyncio
from datetime import datetime
from typing import Callable

from agents.research_agent import run_research_agent
from agents.script_agent import run_script_agent, improve_script, MODE_REWRITE, MODE_NEW_ANGLE
from agents.voice_agent import run_voice_agent
from agents.video_agent import run_video_agent
from agents.editing_agent import run_editing_agent
from agents.quality_agent import run_quality_agent
from memory.database import save_video, init_db, get_character
from tools.video_types import get_video_type_script_instruction, get_video_type_visual_instruction

MAX_RETRIES = 2

async def run_pipeline(
    topic: str,
    niche: str,
    video_tool: str = "grok",
    video_type: str = "product_demo",
    product_name: str = "",
    product_description: str = "",
    script_mode: str = None,
    character_id: int = None,
    product_image: str = None,
    manual_script: str = None,
    batch_num: int = 1,
    batch_total: int = 1,
    progress_callback: Callable = None,
) -> dict:

    await init_db()
    job_id = str(uuid.uuid4())[:8]

    async def update(step: str, message: str, percent: int):
        if progress_callback:
            await progress_callback({
                "job_id": job_id,
                "step": step,
                "message": message,
                "percent": percent,
                "timestamp": datetime.now().isoformat()
            })

    try:
        # Step 1: Research - Top performing ads dhundho
        await update("research", "Research Agent top performing ads analyze kar raha hai...", 8)
        research = await run_research_agent(
            topic=topic,
            niche=niche,
            product_name=product_name,
            product_description=product_description,
        )

        if not research.get("should_proceed", True):
            return {
                "success": False,
                "job_id": job_id,
                "error": f"Research Agent: {research.get('reason', 'Topic suitable nahi')}",
                "research": research
            }

        # Character load karo agar select kiya hai
        character = None
        if character_id:
            character = await get_character(character_id)
            if character:
                await update("script", f"Character '{character['name']}' use ho raha hai...", 18)

        approach = research.get("recommended_approach", "new_angle")
        await update("research", f"Research complete - Approach: {approach}", 15)

        # Step 2: Script - Manual ya AI
        video_type_instruction = get_video_type_script_instruction(video_type)

        if manual_script:
            await update("script", "Using your provided script...", 25)
            script_data = {
                "hook": manual_script,
                "body": "",
                "cta": "",
                "full_script": manual_script,
                "approach": "manual",
                "video_type": video_type,
            }
        else:
            mode_label = "Rewriting top ad..." if approach == MODE_REWRITE else "Naya angle se script likh raha hai..."
            await update("script", f"Script Agent: {mode_label}", 25)
            script_data = await run_script_agent(
                topic=topic,
                niche=niche,
                research=research,
                product_name=product_name,
                product_description=product_description,
                script_mode=script_mode or approach,
                video_type=video_type,
                video_type_instruction=video_type_instruction,
            )

        # Step 3: Voice
        await update("voice", "Voice Agent voiceover bana raha hai...", 40)
        voice_result = await run_voice_agent(script_data, niche, job_id)

        # Step 4: Video - Grok ya Veo3
        video_type_visual_instruction = get_video_type_visual_instruction(video_type)
        await update("video", f"Video Agent {video_tool.upper()} se scenes bana raha hai...", 55)
        video_result = None
        for attempt in range(MAX_RETRIES):
            try:
                video_result = await run_video_agent(script_data, niche, video_tool, job_id, character, product_image, video_type, video_type_visual_instruction)
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                await update("video", f"Retry {attempt+1}: {str(e)[:60]}", 55)
                await asyncio.sleep(5)

        # Step 5: Editing - Compile karo
        await update("editing", "Editing Agent final ad video bana raha hai...", 75)
        edit_result = await run_editing_agent(
            video_result["video_paths"],
            voice_result["audio_path"],
            job_id
        )

        # Step 6: Quality Check
        await update("quality", "Quality Agent review kar raha hai...", 90)
        quality = await run_quality_agent(script_data, video_result, edit_result)

        # Low quality? Script improve karo aur voice/edit dobara
        if not quality.get("approved") and quality.get("quality_score", 0) < 5:
            await update("script", "Quality low hai - script improve ho rahi hai...", 92)
            feedback = "; ".join(quality.get("improvements", []))
            script_data = await improve_script(script_data, feedback)
            voice_result = await run_voice_agent(script_data, niche, f"{job_id}_v2")
            edit_result = await run_editing_agent(
                video_result["video_paths"],
                voice_result["audio_path"],
                f"{job_id}_v2"
            )
            quality = await run_quality_agent(script_data, video_result, edit_result)

        db_id = await save_video(
            topic=f"{product_name} - {topic}" if product_name else topic,
            niche=niche,
            script=script_data.get("full_script", ""),
            video_tool=video_tool,
            output_path=edit_result["final_video"],
            character_id=character_id,
        )

        await update("done", "Ad video ready hai!", 100)

        return {
            "success": True,
            "job_id": job_id,
            "final_video": edit_result["final_video"],
            "captions": edit_result["captions_file"],
            "quality_score": quality.get("quality_score", 0),
            "quality_report": quality,
            "research": research,
            "script": script_data,
            "script_mode": script_data.get("script_mode", "new_angle"),
            "approach_used": research.get("recommended_approach", "new_angle"),
            "tool_used": video_tool,
            "hook": script_data.get("hook", ""),
            "hashtags": script_data.get("hashtags", []),
            "character": character.get("name") if character else None,
            "db_id": db_id,
        }

    except Exception as e:
        await update("error", f"Error: {str(e)}", 0)
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e)
        }
