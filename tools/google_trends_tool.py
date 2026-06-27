import asyncio
from datetime import datetime

# Niche se Google Trends keywords ka map
NICHE_KEYWORDS = {
    "food_and_beverage": ["food tiktok", "food review", "recipe tiktok", "mukbang", "restaurant review"],
    "fashion": ["fashion tiktok", "outfit ideas", "ootd tiktok", "fashion haul", "style tiktok"],
    "beauty": ["beauty tiktok", "makeup tutorial", "skincare routine", "beauty hack", "glow up"],
    "fitness": ["fitness tiktok", "workout tiktok", "gym motivation", "weight loss tiktok", "home workout"],
    "tech": ["tech tiktok", "tech review", "gadget review", "iphone tips", "ai tools"],
    "travel": ["travel tiktok", "travel vlog", "hidden gems", "travel tips", "solo travel"],
    "lifestyle": ["lifestyle tiktok", "day in my life", "productivity tiktok", "morning routine", "life hack"],
}

async def get_trending_topics(niche: str, topic: str) -> dict:
    """Google Trends se trending data lo."""
    keywords = NICHE_KEYWORDS.get(niche, ["tiktok trending"])
    if topic:
        keywords = [topic] + keywords[:2]

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch_trends, keywords, niche)
    return result

def _fetch_trends(keywords: list[str], niche: str) -> dict:
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload(keywords[:5], cat=0, timeframe="now 7-d", geo="US")

        interest_df = pytrends.interest_over_time()
        related_df = pytrends.related_queries()

        # Interest scores
        trend_scores = {}
        if not interest_df.empty:
            for kw in keywords[:5]:
                if kw in interest_df.columns:
                    trend_scores[kw] = int(interest_df[kw].mean())

        # Related rising queries
        rising_topics = []
        for kw in keywords[:3]:
            if kw in related_df and related_df[kw].get("rising") is not None:
                rising_df = related_df[kw]["rising"]
                if rising_df is not None and not rising_df.empty:
                    rising_topics.extend(rising_df["query"].tolist()[:5])

        # Top queries
        top_topics = []
        for kw in keywords[:3]:
            if kw in related_df and related_df[kw].get("top") is not None:
                top_df = related_df[kw]["top"]
                if top_df is not None and not top_df.empty:
                    top_topics.extend(top_df["query"].tolist()[:5])

        return {
            "source": "google_trends",
            "trend_scores": trend_scores,
            "rising_topics": list(set(rising_topics))[:8],
            "top_topics": list(set(top_topics))[:8],
            "best_keyword": max(trend_scores, key=trend_scores.get) if trend_scores else keywords[0],
            "peak_interest": max(trend_scores.values()) if trend_scores else 0,
        }

    except Exception as e:
        return {
            "source": "google_trends",
            "error": str(e),
            "trend_scores": {},
            "rising_topics": [],
            "top_topics": [],
            "best_keyword": keywords[0] if keywords else niche,
            "peak_interest": 0,
        }

async def get_niche_keywords(niche: str) -> list[str]:
    return NICHE_KEYWORDS.get(niche, ["tiktok", "viral", "trending"])
