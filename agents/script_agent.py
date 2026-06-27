import anthropic
import json
import os
from memory.database import get_learnings, save_learning
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _get_client():
    return anthropic.Anthropic(api_key=get_key("anthropic_api_key"))

MODE_REWRITE = "rewrite"
MODE_NEW_ANGLE = "new_angle"

# UGC video angles jo TikTok pe best perform karte hain
UGC_ANGLES = {
    "honest_review": "Main ne ye try kiya aur honestly...",
    "problem_solution": "Mujhe ye problem thi, phir ye mila...",
    "before_after": "Pehle aisa tha, ab aisa hai...",
    "storytime": "Okay so ye baat hai...",
    "ranking": "Maine 5 cheezein try ki, ye number 1 hai...",
    "reaction": "Ye dekh ke main shocked tha...",
}

async def run_script_agent(
    topic: str,
    niche: str,
    research: dict,
    product_name: str = "",
    product_description: str = "",
    script_mode: str = None,
    video_type: str = "product_demo",
    video_type_instruction: str = "",
) -> dict:
    """
    UGC Script Agent.

    Ye scripts aisi lagni chahiye jaise ek real creator ne
    genuinely product try kiya aur apne followers ko bata raha hai.

    NOT: polished ad copy
    YES: authentic, first-person, relatable storytelling
    """

    learnings = await get_learnings("script_agent")
    if not script_mode:
        script_mode = research.get("recommended_approach", MODE_NEW_ANGLE)

    print(f"[Script Agent] UGC Mode: {script_mode}")

    if script_mode == MODE_REWRITE:
        script_data = await _write_ugc_rewrite(topic, niche, research, product_name, product_description, learnings)
    else:
        script_data = await _write_ugc_new_angle(topic, niche, research, product_name, product_description, learnings)

    await _save_learnings(script_data, niche, script_mode)
    return script_data


async def _write_ugc_rewrite(
    topic: str, niche: str, research: dict,
    product_name: str, product_description: str, learnings: dict
) -> dict:
    """
    Top performing UGC video ki style le aur fresh script likho.
    Same vibe, naya content - creator ki apni voice mein.
    """

    top_videos = research.get("top_videos_analysis", {})
    rewrite_ref = research.get("rewrite_options", [{}])[0]

    system_prompt = f"""Tu ek TikTok UGC creator hai jo {niche} niche mein kaam karta hai.
Tu authentic, relatable content banata hai jo real lagta hai - not an ad.

UGC Script ke Golden Rules:
1. FIRST PERSON hamesha - "I", "Maine", "Mujhe"
2. Hook 3 seconds mein - aise shuru karo jaise beech ki baat ho
3. Product naturally aaye - "...aur phir maine ye try kiya" style
4. Honest lagne chahiye - ek chhoti si problem ya doubt bhi mention karo
5. CTA casual ho - "link bio mein hai" ya "comment karo main share karunga"
6. Total 25-40 seconds - TikTok ki sweet spot

AVOID:
- "Amazing product!", "Buy now!", "Limited offer!" - ye sab ad lagta hai
- Formal language - casual raho
- Over-excitement - real reactions realistic hoti hain

Past learnings: {json.dumps({k: v['value'] for k, v in list(learnings.items())[:3]}, ensure_ascii=False)}"""

    product_ctx = f"Product: {product_name}\n" if product_name else ""
    product_ctx += f"Details: {product_description}\n" if product_description else ""

    ref_ctx = f"\nReference video style: {rewrite_ref.get('reference_ad', '')}\nNaya twist: {rewrite_ref.get('new_angle', '')}" if rewrite_ref else ""

    video_type_note = f"\nVIDEO TYPE: {video_type}\n{video_type_instruction}\n" if video_type_instruction else ""

    response = _get_client().messages.create(
        model="claude-opus-4-8",
        max_tokens=2500,
        system=system_prompt,
        messages=[{"role": "user", "content": f"""
Topic: {topic}
{product_ctx}{ref_ctx}{video_type_note}
Hook style: {research.get('hook_style', 'storytime')}
Tone: {research.get('tone', 'genuine_and_relatable')}
Scenes: {research.get('recommended_scenes', 6)}

Ek authentic UGC script likho jaise creator apni real experience share kar raha ho.
JSON mein do:
{{
  "script_mode": "rewrite",
  "ugc_angle": "honest_review/storytime/problem_solution/etc",
  "product_name": "{product_name or topic}",
  "full_script": "poora script jo voiceover mein use hoga - conversational language mein",
  "hook": "pehli line - scroll ruk jaye",
  "scenes": [
    {{
      "scene_number": 1,
      "scene_type": "hook/context/product_intro/reaction/cta",
      "narration": "is scene mein jo bolna hai - natural language",
      "visual_prompt": "casual, authentic scene ka description for video generation - real life setting",
      "duration_seconds": 6,
      "on_screen_text": "optional caption ya text overlay"
    }}
  ],
  "cta": "casual call to action - not salesy",
  "hashtags": ["#tiktokmademebuyit", "#productreview"],
  "total_duration": "seconds",
  "authenticity_notes": "ye script real kyun lagegi"
}}"""}]
    )

    raw = _clean_json(response.content[0].text.strip())
    return json.loads(raw)


async def _write_ugc_new_angle(
    topic: str, niche: str, research: dict,
    product_name: str, product_description: str, learnings: dict
) -> dict:
    """
    Fresh UGC angle se original script - research ke best angle se.
    """

    angles = research.get("new_angle_options", [])
    chosen = angles[0] if angles else {"angle_name": "honest_review", "hook": ""}

    selling_points = research.get("key_selling_points", [])
    hashtags = research.get("top_hashtags", ["#tiktokmademebuyit", "#tiktokshop"])
    winning_formula = research.get("top_videos_analysis", {}).get("winning_formula", "")

    system_prompt = f"""Tu ek real TikTok creator hai jo {niche} content banata hai.
Tujhe aaj ek product review/UGC video banana hai jo genuinely helpful lagni chahiye.

Jo kaam karta hai TikTok pe:
- Relatable opening: "okay so", "POV:", "tell me why I...", "no bc why does this actually work"
- Real moment share karna - jab product ne genuinely help ki
- Ek chhoti si hesitation ya doubt jo resolve ho - credibility badhti hai
- Friends ko bataane wala tone - not selling

Winning formula from top videos: {winning_formula}

Angles jo best perform karte hain:
{json.dumps(UGC_ANGLES, ensure_ascii=False, indent=2)}

Past learnings: {json.dumps({k: v['value'] for k, v in list(learnings.items())[:3]}, ensure_ascii=False)}"""

    product_ctx = f"Product: {product_name}\n" if product_name else ""
    product_ctx += f"Details: {product_description}\n" if product_description else ""
    product_ctx += f"Key benefits: {', '.join(selling_points)}\n" if selling_points else ""

    response = _get_client().messages.create(
        model="claude-opus-4-8",
        max_tokens=2500,
        system=system_prompt,
        messages=[{"role": "user", "content": f"""
Topic: {topic}
{product_ctx}
Chosen angle: {chosen.get('angle_name', 'honest_review')}
Suggested hook: {chosen.get('hook', '')}
Tone: {research.get('tone', 'genuine_relatable')}
Scenes: {research.get('recommended_scenes', 6)}
Hashtags to use: {', '.join(hashtags)}

Ek authentic UGC creator video script likho.
JSON mein do:
{{
  "script_mode": "new_angle",
  "ugc_angle": "{chosen.get('angle_name', 'honest_review')}",
  "product_name": "{product_name or topic}",
  "full_script": "poora voiceover script - jaise real banda bol raha ho",
  "hook": "pehli 3 second ki line - must stop the scroll",
  "scenes": [
    {{
      "scene_number": 1,
      "scene_type": "hook/context/product_intro/reaction/social_proof/cta",
      "narration": "is scene mein jo bolna hai",
      "visual_prompt": "real life casual setting - bedroom, kitchen, outdoor etc - for AI video generation",
      "duration_seconds": 6,
      "on_screen_text": "text overlay if needed"
    }}
  ],
  "cta": "casual bio link mention ya comment CTA",
  "hashtags": {json.dumps(hashtags)},
  "total_duration": "estimated seconds",
  "why_authentic": "ye script real kyun lagegi audience ko"
}}"""}]
    )

    raw = _clean_json(response.content[0].text.strip())
    return json.loads(raw)


async def improve_script(script_data: dict, feedback: str) -> dict:
    response = _get_client().messages.create(
        model="claude-opus-4-8",
        max_tokens=2500,
        messages=[{"role": "user", "content": f"""Is UGC script ko improve karo. More authentic, less salesy.

Feedback: {feedback}

Original:
{json.dumps(script_data, ensure_ascii=False, indent=2)}

Same JSON structure mein improved version do."""}]
    )
    raw = _clean_json(response.content[0].text.strip())
    return json.loads(raw)


async def _save_learnings(script_data: dict, niche: str, mode: str):
    angle = script_data.get("ugc_angle", "")
    hook = script_data.get("hook", "")
    if angle:
        await save_learning("script_agent", f"best_ugc_angle_{niche}", angle, 0.6)
    if hook:
        await save_learning("script_agent", f"successful_hook_{niche}", hook[:80], 0.6)
    await save_learning("script_agent", f"preferred_mode_{niche}", mode, 0.5)


def _clean_json(raw: str) -> str:
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                return part
    return raw.strip()
