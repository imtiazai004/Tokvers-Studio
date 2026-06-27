import anthropic
import json
import os
import asyncio
from tools import apify_tool, google_trends_tool, web_search_tool
from memory.database import get_learnings, get_top_performing_patterns, save_learning
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _get_client():
    return anthropic.Anthropic(api_key=get_key("anthropic_api_key"))

async def run_research_agent(
    topic: str,
    niche: str,
    product_name: str = "",
    product_description: str = "",
) -> dict:
    """
    UGC Research Agent.
    Top performing organic creator videos dhundho - not ads.
    Analyze karo: kya hook, kya angle, kya tone viral hua.
    """

    learnings = await get_learnings("research_agent")
    top_patterns = await get_top_performing_patterns(niche, limit=5)
    product_keywords = _build_keywords(product_name, niche, topic)

    ugc_data = None
    trends_data = None
    search_data = None

    if apify_tool.is_available():
        print("[Research Agent] TikTok se top UGC creator videos fetch kar raha hoon...")
        ugc_data, trends_data, search_data = await asyncio.gather(
            _fetch_ugc_videos(product_keywords, niche),
            google_trends_tool.get_trending_topics(niche, topic),
            web_search_tool.search_tiktok_trends(niche, topic),
            return_exceptions=True
        )
    else:
        print("[Research Agent] Hybrid mode (Google Trends + Web Search + Claude)...")
        trends_data, search_data = await asyncio.gather(
            google_trends_tool.get_trending_topics(niche, topic),
            web_search_tool.search_tiktok_trends(niche, topic),
            return_exceptions=True
        )

    for name, val in [("ugc_data", ugc_data), ("trends_data", trends_data), ("search_data", search_data)]:
        if isinstance(val, Exception):
            print(f"[Research Agent] {name} error: {val}")
            if name == "ugc_data": ugc_data = None
            elif name == "trends_data": trends_data = None
            else: search_data = None

    analysis = await _analyze_with_claude(
        topic, niche, product_name, product_description,
        ugc_data, trends_data, search_data, learnings, top_patterns
    )

    await _save_learnings(analysis, niche)
    return analysis


async def _fetch_ugc_videos(keywords: list[str], niche: str) -> dict:
    """
    Organic UGC creator videos fetch karo - TikTok Shop affiliated content.
    #tiktokmademebuyit, #tiktokreview, product reviews etc.
    """
    ugc_hashtags = [
        "#tiktokmademebuyit",
        f"#{niche.replace('_', '')}review",
        "#ugccreator",
        "#productreview",
    ]

    videos, hashtag_videos = await asyncio.gather(
        apify_tool.search_trending_videos(keywords, max_videos=20),
        apify_tool.search_by_hashtag(ugc_hashtags, max_videos=15),
        return_exceptions=True
    )

    all_videos = []
    if not isinstance(videos, Exception): all_videos.extend(videos)
    if not isinstance(hashtag_videos, Exception): all_videos.extend(hashtag_videos)

    top = sorted(all_videos, key=lambda x: x.get("engagement_rate", 0), reverse=True)[:10]

    all_hashtags = []
    for v in all_videos:
        all_hashtags.extend(v.get("hashtags", []))
    tag_freq = {}
    for t in all_hashtags:
        if t: tag_freq[t] = tag_freq.get(t, 0) + 1
    top_tags = sorted(tag_freq, key=tag_freq.get, reverse=True)[:10]

    return {
        "source": "tiktok_organic_ugc",
        "total_analyzed": len(all_videos),
        "top_videos": top,
        "top_hashtags": top_tags,
        "avg_engagement": sum(v.get("engagement_rate", 0) for v in all_videos) / max(len(all_videos), 1),
    }


async def _analyze_with_claude(
    topic, niche, product_name, product_description,
    ugc_data, trends_data, search_data, learnings, top_patterns
) -> dict:

    data_summary = _build_data_summary(ugc_data, trends_data, search_data)
    memory_ctx = _build_memory_context(learnings, top_patterns)

    system_prompt = f"""Tu ek TikTok UGC content strategist hai jo {niche} niche mein expert hai.
Tera kaam: organic creator videos analyze karna aur best UGC content strategy decide karna.

UGC Content ke rules:
- Authentic lagna zaroori hai - scripted ya polished nahi
- Scroll-stopping hook in 3 seconds
- Product naturally integrate hona chahiye
- Creator ki genuine reaction ya story

{memory_ctx}

Sirf valid JSON respond karo."""

    product_ctx = f"\nProduct: {product_name}" if product_name else ""
    product_ctx += f"\nDetails: {product_description}" if product_description else ""

    response = _get_client().messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"""
Topic: {topic}{product_ctx}
Niche: {niche}

=== RESEARCH DATA ===
{data_summary}

UGC content strategy JSON mein do:
{{
  "data_source_used": "tiktok_organic / hybrid / claude_only",
  "should_proceed": true,
  "topic_trend_score": 0-100,

  "top_videos_analysis": {{
    "most_common_hook_style": "storytime/reaction/problem_solution/before_after/ranking",
    "most_common_ugc_style": "talking_head/voiceover/pov/day_in_life",
    "avg_video_duration": "seconds",
    "winning_formula": "top videos mein kya common tha - ek line mein",
    "authenticity_markers": ["jo cheezein real lagti hain - list"]
  }},

  "recommended_approach": "rewrite / new_angle",
  "approach_reason": "kyun",

  "rewrite_options": [
    {{
      "reference_ad": "konsa top video rewrite karna hai",
      "new_angle": "kya fresh karo ge",
      "why": "kyun better hoga"
    }}
  ],

  "new_angle_options": [
    {{
      "angle_name": "honest_review",
      "hook": "suggested opening line",
      "why": "kyun work karega"
    }},
    {{
      "angle_name": "storytime",
      "hook": "suggested opening line",
      "why": "kyun work karega"
    }},
    {{
      "angle_name": "problem_solution",
      "hook": "suggested opening line",
      "why": "kyun work karega"
    }}
  ],

  "recommended_scenes": 6,
  "hook_style": "storytime/reaction/problem_solution/before_after",
  "tone": "genuine_relatable/funny/educational/shocked",
  "top_hashtags": ["#tiktokmademebuyit", "#tiktokshop"],
  "key_selling_points": ["natural benefits jo mention ho sakte hain"],
  "avoid": ["kya avoid karna hai - salesy language etc"],
  "confidence_score": 0.0-1.0
}}"""}]
    )

    raw = _clean_json(response.content[0].text.strip())
    return json.loads(raw)


def _build_data_summary(ugc_data, trends_data, search_data) -> str:
    parts = []

    if ugc_data and not isinstance(ugc_data, Exception):
        top = ugc_data.get("top_videos", [])[:5]
        vids = "\n".join([
            f"  - \"{v.get('title','')[:65]}\" | Views: {v.get('views',0):,} | Engagement: {v.get('engagement_rate',0):.2f}%"
            for v in top
        ])
        parts.append(f"""[TikTok Organic UGC Videos - {ugc_data['total_analyzed']} analyzed]
Top Videos:
{vids}
Top Hashtags: {', '.join(['#'+t for t in ugc_data.get('top_hashtags',[])[:8]])}
Avg Engagement: {ugc_data.get('avg_engagement',0):.2f}%""")

    if trends_data and not isinstance(trends_data, Exception) and not trends_data.get("error"):
        parts.append(f"""[Google Trends]
Rising: {', '.join(trends_data.get('rising_topics',[])[:5])}
Top: {', '.join(trends_data.get('top_topics',[])[:5])}
Peak Interest: {trends_data.get('peak_interest',0)}/100""")

    if search_data and not isinstance(search_data, Exception):
        insights = search_data.get("insights", [])
        if insights:
            parts.append(f"[Web Insights]\n" + "\n".join([f"- {i}" for i in insights[:3]]))

    if not parts:
        parts.append("[No external data - Claude training knowledge use ho raha hai]")

    return "\n\n".join(parts)


def _build_memory_context(learnings, top_patterns) -> str:
    if not learnings and not top_patterns:
        return ""
    ctx = "\n=== HAMARE PAST RESULTS ===\n"
    for key, data in list(learnings.items())[:5]:
        ctx += f"- {key}: {data['value']} (confidence: {data['confidence']:.0%})\n"
    if top_patterns:
        ctx += "\nHamari Best Performing Videos:\n"
        for p in top_patterns[:3]:
            ctx += f"- \"{p['topic']}\" Score: {p['score']:.0f}\n"
    return ctx


def _build_keywords(product_name, niche, topic) -> list[str]:
    base = google_trends_tool.NICHE_KEYWORDS.get(niche, [niche])
    keywords = []
    if product_name: keywords.append(product_name)
    if topic: keywords.append(topic)
    keywords.extend(base[:2])
    return keywords[:4]


async def _save_learnings(analysis, niche):
    if analysis.get("confidence_score", 0) > 0.6:
        vids = analysis.get("top_videos_analysis", {})
        await asyncio.gather(
            save_learning("research_agent", f"best_hook_{niche}", vids.get("most_common_hook_style", ""), analysis.get("confidence_score", 0.5)),
            save_learning("research_agent", f"best_ugc_style_{niche}", vids.get("most_common_ugc_style", ""), analysis.get("confidence_score", 0.5)),
            save_learning("research_agent", f"winning_formula_{niche}", vids.get("winning_formula", ""), 0.7),
        )


def _clean_json(raw: str) -> str:
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"): part = part[4:].strip()
            if part.startswith("{"): return part
    return raw.strip()
