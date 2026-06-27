import anthropic
import json
import os
from tools.elevenlabs_tool import generate_voiceover
from memory.database import get_learnings, save_learning
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _get_client():
    return anthropic.Anthropic(api_key=get_key("anthropic_api_key"))

async def run_voice_agent(script_data: dict, niche: str, job_id: str) -> dict:
    """
    UGC Voice Agent.
    Natural, conversational voice chahiye - not a professional announcer.
    Jaise real banda apne dost ko bata raha ho.
    """

    learnings = await get_learnings("voice_agent")
    ugc_angle = script_data.get("ugc_angle", "honest_review")
    full_script = script_data.get("full_script", "")

    decision = await _decide_voice(ugc_angle, niche, full_script, learnings)

    gender = decision.get("gender", "female")
    stability = decision.get("stability", 0.4)
    style = decision.get("style", 0.5)

    output_path = f"output/audio/{job_id}_voice.mp3"
    audio_path = await generate_voiceover(
        full_script, gender, output_path,
        stability=stability, style=style
    )

    await save_learning("voice_agent", f"best_gender_{niche}", gender, 0.6)
    await save_learning("voice_agent", f"best_ugc_angle_voice_{ugc_angle}", gender, 0.6)

    return {
        "audio_path": audio_path,
        "gender": gender,
        "script": full_script,
        "voice_style": decision.get("reasoning", "")
    }


async def _decide_voice(ugc_angle: str, niche: str, script: str, learnings: dict) -> dict:
    """UGC angle aur niche ke hisab se best voice decide karo."""

    past = {k: v['value'] for k, v in list(learnings.items())[:3]}

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": f"""
UGC TikTok video ke liye best voice decide karo.

UGC Angle: {ugc_angle}
Niche: {niche}
Script preview: "{script[:150]}..."
Past learnings: {json.dumps(past, ensure_ascii=False)}

UGC voice guidelines:
- "honest_review" → warm, genuine, slightly casual
- "storytime" → engaging, expressive, conversational
- "problem_solution" → relatable, empathetic
- "reaction" → energetic, surprised
- "ranking" → confident, clear

JSON mein do:
{{
  "gender": "male/female",
  "stability": 0.3-0.5,
  "style": 0.4-0.7,
  "reasoning": "kyun ye voice is UGC angle ke liye best hai"
}}"""}]
    )

    raw = response.content[0].text.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"): part = part[4:].strip()
            if part.startswith("{"): raw = part; break
    try:
        return json.loads(raw.strip())
    except Exception:
        return {"gender": "female", "stability": 0.4, "style": 0.5, "reasoning": "default"}
