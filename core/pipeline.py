"""
Full generation pipeline, wired onto the new architecture (async, multi-tenant).

Flow:  script (Claude) -> voiceover (voice provider) -> scene clips (video provider)
       -> edit (ffmpeg: merge + voice + captions) -> upload to R2 -> learnings.

It's provider-agnostic (video: veo/grok/higgsfield, voice: elevenlabs/fish) and
uses the same job/credit/storage flow as the walking skeleton. Builds without any
keys; each external call raises a clear error until its key is set (then it runs
for real). Progress is reported via the async `progress(step, percent)` callback
so the Dashboard/Create pages reflect live status.
"""
import json
import os

from anthropic import AsyncAnthropic

from config.client_config import get_key
from core import storage
from providers import get_provider
from providers.voice import get_voice_provider
from tools.ffmpeg_tool import (
    add_audio_to_video,
    burn_captions,
    convert_to_tiktok_format,
    merge_video_clips,
)
from tools.whisper_tool import generate_captions

WORK_DIR = "output/gen"


def _anthropic() -> AsyncAnthropic:
    key = get_key("anthropic_api_key")
    if not key:
        raise RuntimeError("Anthropic API key not set (ANTHROPIC_API_KEY).")
    return AsyncAnthropic(api_key=key)


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                return part
    return raw


async def write_script(topic, niche, product_name, product_description, scenes_n) -> dict:
    """UGC script with per-scene narration + visual prompts (async Claude)."""
    client = _anthropic()
    system = (
        f"You are a TikTok UGC creator in the {niche or 'lifestyle'} niche. Write authentic, "
        "first-person, non-salesy short-form scripts that feel like a real person sharing an "
        "honest experience. Hook in the first 3 seconds. Respond ONLY with valid JSON."
    )
    prod = f"\nProduct: {product_name}" if product_name else ""
    prod += f"\nDetails: {product_description}" if product_description else ""
    user = f"""Topic: {topic}{prod}
Niche: {niche or 'lifestyle'}
Scenes: {scenes_n}

Return JSON:
{{
  "hook": "first line that stops the scroll",
  "full_script": "the complete voiceover narration, conversational",
  "scenes": [
    {{"narration": "what is said in this scene",
      "visual_prompt": "a realistic, candid 9:16 scene description for AI video generation",
      "duration_seconds": 8}}
  ],
  "hashtags": ["#tiktokmademebuyit", "#fyp"]
}}"""
    resp = await client.messages.create(
        model="claude-sonnet-4-6", max_tokens=2000,
        system=system, messages=[{"role": "user", "content": user}],
    )
    data = json.loads(_clean_json(resp.content[0].text))
    if not data.get("scenes"):
        raise RuntimeError("Script agent returned no scenes")
    return data


async def run_pipeline(*, job_id, params, workspace_id, progress) -> dict:
    """Run the full pipeline. `progress` is an async fn(step:str, percent:int)."""
    topic = params.get("topic") or "a short UGC clip"
    niche = params.get("niche")
    product_name = params.get("product_name") or topic
    video_provider_name = params.get("provider") or "veo"
    voice_provider_name = params.get("voice_provider") or "elevenlabs"
    scenes_n = max(1, min(8, int(params.get("scenes") or 4)))

    out_dir = os.path.join(WORK_DIR, str(job_id))
    os.makedirs(out_dir, exist_ok=True)
    cost = 0.0

    # 1) Script
    await progress("script", 12)
    script = await write_script(topic, niche, product_name, params.get("product_description"), scenes_n)
    scenes = script["scenes"][:scenes_n]

    # 2) Voiceover (full narration)
    await progress("voice", 32)
    voice = get_voice_provider(voice_provider_name)
    audio_path = os.path.join(out_dir, "voice.mp3")
    await voice.synthesize(script.get("full_script", topic), audio_path)

    # 3) Video — one clip per scene
    video = get_provider(video_provider_name)
    clip_paths = []
    for i, scene in enumerate(scenes):
        pct = 40 + int(35 * (i / max(1, len(scenes))))
        await progress("video", pct)
        clip = os.path.join(out_dir, f"scene_{i+1:02d}.mp4")
        res = await video.generate(scene.get("visual_prompt", topic), clip,
                                   duration_seconds=int(scene.get("duration_seconds", 8)))
        if res.cost_usd:
            cost += res.cost_usd
        clip_paths.append(clip)

    # 4) Edit — merge clips, add voice, burn captions, format for TikTok
    await progress("editing", 82)
    merged = os.path.join(out_dir, "merged.mp4")
    await merge_video_clips(clip_paths, merged)
    with_voice = os.path.join(out_dir, "with_voice.mp4")
    await add_audio_to_video(merged, audio_path, with_voice)
    final_in = with_voice
    try:
        srt = os.path.join(out_dir, "captions.srt")
        await generate_captions(audio_path, srt)
        with_caps = os.path.join(out_dir, "with_caps.mp4")
        await burn_captions(with_voice, srt, with_caps)
        final_in = with_caps
    except Exception:
        pass  # captions are best-effort
    final_path = os.path.join(out_dir, "final.mp4")
    await convert_to_tiktok_format(final_in, final_path)

    # 5) Store in R2
    await progress("store", 94)
    key = f"{workspace_id}/videos/{job_id}.mp4"
    await storage.upload_file(key, final_path, content_type="video/mp4")

    return {
        "r2_key": key,
        "cost": cost,
        "topic": topic,
        "hook": script.get("hook", ""),
        "hashtags": script.get("hashtags", []),
        "tool": video_provider_name,
    }
