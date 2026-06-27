import os
import httpx
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _brave_key(): return get_key("brave_search_api_key")
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

def is_available() -> bool:
    return bool(_brave_key())

async def search_tiktok_trends(niche: str, topic: str) -> dict:
    """Web search se TikTok trends dhundho."""
    queries = [
        f"trending TikTok {niche.replace('_', ' ')} videos {_current_month()}",
        f"viral TikTok {topic} content ideas",
        f"TikTok {niche.replace('_', ' ')} trending hashtags",
    ]

    all_results = []
    for query in queries:
        results = await _brave_search(query)
        all_results.extend(results)

    return {
        "source": "brave_search",
        "results": all_results[:12],
        "queries_used": queries,
        "insights": _extract_insights(all_results),
    }

async def search_competitor_content(niche: str, topic: str) -> list[dict]:
    """Similar content ke baare mein search karo."""
    query = f"best performing TikTok {topic} {niche} content strategy 2025"
    results = await _brave_search(query, count=5)
    return results

async def _brave_search(query: str, count: int = 5) -> list[dict]:
    if not _brave_key():
        return _fallback_search(query)

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": _brave_key(),
    }
    params = {
        "q": query,
        "count": count,
        "search_lang": "en",
        "country": "US",
        "text_decorations": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(BRAVE_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
            })
        return results
    except Exception:
        return _fallback_search(query)

def _fallback_search(query: str) -> list[dict]:
    """Brave API na hone par Claude khud context se analyze kare."""
    return [{
        "title": f"Analysis: {query}",
        "description": "No web search API - Claude will analyze from training knowledge",
        "url": "",
    }]

def _extract_insights(results: list[dict]) -> list[str]:
    insights = []
    keywords = ["viral", "trending", "hook", "engage", "views", "million", "popular"]
    for r in results:
        text = f"{r.get('title', '')} {r.get('description', '')}".lower()
        if any(kw in text for kw in keywords):
            desc = r.get("description", "")
            if desc and len(desc) > 30:
                insights.append(desc[:150])
    return insights[:5]

def _current_month() -> str:
    from datetime import datetime
    return datetime.now().strftime("%B %Y")
