import anthropic
import json
import os
import asyncio
from tools.grok_tool import generate_scenes_grok
from tools.veo3_tool import generate_scenes_veo3
from tools.character_tool import get_character_image_base64, build_character_prompt
from memory.database import get_learnings, save_learning
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _get_client():
    return anthropic.Anthropic(api_key=get_key("anthropic_api_key"))

async def run_video_agent(
    script_data: dict,
    niche: str,
    video_tool: str,
    job_id: str,
    character: dict = None,
    product_image: str = None,
    video_type: str = "product_demo",
    video_type_visual_instruction: str = "",
) -> dict:
    learnings = await get_learnings("video_agent")
    scenes = script_data.get("scenes", [])

    # Character image load karo agar hai
    character_image_b64 = None
    character_prompt_ext = ""
    if character:
        character_image_b64 = await get_character_image_base64(character)
        character_prompt_ext = build_character_prompt(character)
        if character_image_b64:
            print(f"[Video Agent] Character '{character['name']}' ki image reference use ho rahi hai")
        else:
            print(f"[Video Agent] Character '{character['name']}' - sirf description use hogi (no image)")

    enhanced_prompts = await _enhance_ugc_prompts(
        scenes, niche, video_tool, script_data, learnings, character_prompt_ext, product_image, video_type_visual_instruction
    )

    output_dir = f"output/scenes/{job_id}"
    os.makedirs(output_dir, exist_ok=True)

    if video_tool == "grok":
        video_paths = await generate_scenes_grok(
            enhanced_prompts, output_dir, character_image_b64, product_image
        )
    elif video_tool == "veo3":
        video_paths = await generate_scenes_veo3(
            enhanced_prompts, output_dir, character_image_b64, product_image
        )
    else:
        raise ValueError(f"Unknown video tool: {video_tool}")

    await save_learning("video_agent", f"preferred_tool_{niche}", video_tool, 0.6)

    return {
        "video_paths": video_paths,
        "tool_used": video_tool,
        "scene_count": len(video_paths),
        "character_used": character.get("name") if character else None,
    }


async def _enhance_ugc_prompts(
    scenes: list, niche: str, tool: str,
    script_data: dict, learnings: dict, character_prompt_ext: str = "", product_image: str = None, video_type_instruction: str = ""
) -> list[str]:

    ugc_angle = script_data.get("ugc_angle", "honest_review")
    scene_list = "\n".join([
        f"Scene {s['scene_number']} ({s.get('scene_type','')}):\n"
        f"  Narration: {s.get('narration','')[:80]}\n"
        f"  Visual: {s.get('visual_prompt','')}"
        for s in scenes
    ])

    char_note = ""
    if character_prompt_ext:
        char_note = f"\nCHARACTER (har scene mein consistent rahna chahiye):\n{character_prompt_ext}\n"

    video_type_note = ""
    if video_type_instruction:
        video_type_note = f"\nVIDEO TYPE VISUAL GUIDELINES:\n{video_type_instruction}\n"

    style_note = (
        "Veo3: realistic, natural lighting, handheld feel. NOT studio quality."
        if tool == "veo3" else
        "Grok: real-life setting, candid feel, natural colors."
    )

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""
TikTok UGC video ke liye scene prompts enhance karo.
Niche: {niche} | UGC Angle: {ugc_angle}
{style_note}
{char_note}{video_type_note}
UGC Rules: real locations, natural lighting, casual clothing, candid expressions, vertical 9:16.
NO studio/corporate/over-produced look.

Original Scenes:
{scene_list}

Har scene ka enhanced prompt do. JSON array (sirf prompts):
["prompt 1", "prompt 2", ...]"""}]
    )

    raw = response.content[0].text.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"): part = part[4:].strip()
            if part.startswith("["): raw = part; break
    return json.loads(raw.strip())
