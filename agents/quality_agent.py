import anthropic
import json
import os
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _get_client():
    return anthropic.Anthropic(api_key=get_key("anthropic_api_key"))

async def run_quality_agent(script_data: dict, video_result: dict, edit_result: dict) -> dict:
    """
    UGC Quality Agent.
    Ad quality se alag - UGC ke liye alag standards hain.

    Good UGC video:
    - Authentic lagti hai, scripted nahi
    - Hook strong hai
    - Product naturally integrate hua
    - CTA forced nahi lagta
    - Length TikTok ke liye theek hai (25-40 sec)
    """

    final_video = edit_result.get("final_video", "")
    video_exists = os.path.exists(final_video)
    video_size_mb = os.path.getsize(final_video) / (1024 * 1024) if video_exists else 0

    hook = script_data.get("hook", "")
    cta = script_data.get("cta", "")
    full_script = script_data.get("full_script", "")
    ugc_angle = script_data.get("ugc_angle", "")
    scene_count = video_result.get("scene_count", 0)
    word_count = len(full_script.split())

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""
UGC TikTok video quality check karo:

Hook: "{hook}"
CTA: "{cta}"
UGC Angle: {ugc_angle}
Script word count: {word_count} words
Scene count: {scene_count}
Video exists: {video_exists}
Video size: {video_size_mb:.1f} MB

UGC Quality Checklist:
1. Hook scroll rokne wali hai? (3 sec rule)
2. Script authentic lagti hai ya scripted/salesy?
3. Product naturally integrate hua?
4. CTA casual hai ya forced?
5. Length appropriate hai? (25-40 sec ideal)
6. Angle clearly execute hua ({ugc_angle})?

JSON mein do:
{{
  "approved": true/false,
  "quality_score": 0-10,
  "ugc_authenticity_score": 0-10,
  "hook_strength": "weak/medium/strong",
  "feels_like_ad": true/false,
  "issues": ["specific issues"],
  "improvements": ["specific improvements"],
  "cta_natural": true/false,
  "ready_to_upload": true/false,
  "estimated_performance": "low/medium/high"
}}"""}]
    )

    raw = response.content[0].text.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"): part = part[4:].strip()
            if part.startswith("{"): raw = part; break

    report = json.loads(raw.strip())

    if not video_exists:
        report["approved"] = False
        report["issues"] = report.get("issues", []) + ["Video file missing"]

    if report.get("feels_like_ad"):
        report["approved"] = False
        report["issues"] = report.get("issues", []) + ["Too salesy - UGC feel nahi hai"]

    if not report.get("ugc_authenticity_score"):
        report["ugc_authenticity_score"] = report.get("quality_score", 5)

    return report
