import os
import asyncio
import httpx
from dotenv import load_dotenv
from config.client_config import get_key

load_dotenv()

def _apify_token(): return get_key("apify_api_token")
ACTOR_ID = "clockworks~tiktok-scraper"
CREATIVE_CENTER_ACTOR_ID = "tiktok~creative-center-ads-scraper"
BASE_URL = "https://api.apify.com/v2"

def is_available() -> bool:
    return bool(_apify_token())

# ─────────────────────────────────────────────
# TikTok Shop AD Research - Main new feature
# ─────────────────────────────────────────────

async def get_top_product_ads(niche: str, product_keywords: list[str], max_ads: int = 15) -> dict:
    """
    TikTok Creative Center se top performing product ads fetch karo.
    Ye publicly available data hai - TikTok khud dikhata hai konse ads achhe chal rahe hain.
    """
    ads_by_keyword = []
    for kw in product_keywords[:3]:
        ads = await _scrape_creative_center(kw, niche, max_ads // 3)
        ads_by_keyword.extend(ads)

    # Duplicate hata do, engagement se sort karo
    seen = set()
    unique_ads = []
    for ad in ads_by_keyword:
        key = ad.get("title", "")[:40]
        if key not in seen:
            seen.add(key)
            unique_ads.append(ad)

    top_ads = sorted(unique_ads, key=lambda x: x.get("ctr", 0), reverse=True)

    return {
        "source": "tiktok_creative_center",
        "total_ads_analyzed": len(unique_ads),
        "top_ads": top_ads[:10],
        "common_hooks": _extract_hooks(top_ads),
        "common_ctas": _extract_ctas(top_ads),
        "avg_duration": _avg_duration(top_ads),
        "top_ad_styles": _identify_ad_styles(top_ads),
    }

async def search_shop_ads_by_niche(niche: str, max_results: int = 20) -> list[dict]:
    """Niche ke hisab se TikTok Shop ads search karo."""
    niche_map = {
        "food_and_beverage": ["food product", "snack", "beverage", "drink", "health food"],
        "beauty": ["skincare", "makeup", "beauty product", "cosmetic"],
        "fashion": ["clothing", "outfit", "fashion accessories", "shoes"],
        "fitness": ["fitness equipment", "supplement", "workout gear", "protein"],
        "tech": ["gadget", "tech accessory", "phone case", "earbuds"],
        "lifestyle": ["home decor", "kitchen gadget", "lifestyle product"],
    }
    keywords = niche_map.get(niche, [niche])
    results = []
    for kw in keywords[:2]:
        ads = await _scrape_creative_center(kw, niche, max_results // 2)
        results.extend(ads)
    return results

async def _scrape_creative_center(keyword: str, niche: str, max_items: int = 10) -> list[dict]:
    """
    TikTok Creative Center scrape karo.
    Creative Center URL: https://ads.tiktok.com/business/creativecenter/inspiration/topads/
    Apify ka dedicated actor use karta hai.
    """
    input_data = {
        "keyword": keyword,
        "industry": niche,
        "period": "7",
        "maxItems": max_items,
        "orderBy": "ctr",
    }
    try:
        raw = await _run_actor_by_id(CREATIVE_CENTER_ACTOR_ID, input_data)
        return _extract_ad_data(raw)
    except Exception:
        # Fallback: regular TikTok search with shop hashtags
        shop_query = f"{keyword} #tiktokmademebuyit #tiktokshop"
        videos = await _run_tiktok_search(shop_query, max_items)
        return _convert_videos_to_ads(videos)

async def search_trending_videos(niche_keywords: list[str], max_videos: int = 20) -> list[dict]:
    """TikTok pe niche keywords se trending videos dhundho."""
    results = []
    for keyword in niche_keywords[:3]:
        videos = await _run_tiktok_search(keyword, max_videos // len(niche_keywords[:3]))
        results.extend(videos)
    return results

async def search_by_hashtag(hashtags: list[str], max_videos: int = 15) -> list[dict]:
    """Specific hashtags ke videos lo."""
    results = []
    for tag in hashtags[:3]:
        tag_clean = tag.lstrip("#")
        videos = await _run_tiktok_search(f"#{tag_clean}", max_videos // 3)
        results.extend(videos)
    return results

async def get_creator_analytics(username: str) -> dict:
    """Kisi creator ki analytics lo."""
    input_data = {
        "profiles": [username],
        "resultsPerPage": 10,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }
    raw = await _run_actor(input_data)
    if not raw:
        return {}

    profile = raw[0] if raw else {}
    return {
        "username": profile.get("authorMeta", {}).get("name", username),
        "followers": profile.get("authorMeta", {}).get("fans", 0),
        "following": profile.get("authorMeta", {}).get("following", 0),
        "total_likes": profile.get("authorMeta", {}).get("heart", 0),
        "video_count": profile.get("authorMeta", {}).get("video", 0),
        "recent_videos": _extract_video_data(raw[:10])
    }

async def _run_tiktok_search(query: str, max_items: int = 10) -> list[dict]:
    input_data = {
        "searchQueries": [query],
        "maxVideos": max_items,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
    }
    raw = await _run_actor(input_data)
    return _extract_video_data(raw)

def _extract_ad_data(raw: list) -> list[dict]:
    ads = []
    for item in raw:
        try:
            ads.append({
                "title": item.get("adTitle", item.get("desc", "")),
                "script": item.get("adScript", item.get("desc", "")),
                "hook": item.get("hook", item.get("desc", "")[:80]),
                "cta": item.get("callToAction", "Shop Now"),
                "ctr": item.get("ctr", item.get("clickRate", 0)),
                "views": item.get("impressions", item.get("playCount", 0)),
                "likes": item.get("likes", item.get("diggCount", 0)),
                "duration": item.get("duration", 0),
                "ad_style": item.get("adType", "ugc"),
                "hashtags": [t.get("name", "") for t in item.get("textExtra", [])],
                "product_name": item.get("productName", ""),
                "author": item.get("advertiserName", item.get("authorMeta", {}).get("name", "")),
            })
        except Exception:
            continue
    return ads

def _convert_videos_to_ads(videos: list[dict]) -> list[dict]:
    """Regular TikTok videos ko ad format mein convert karo."""
    return [{
        "title": v.get("title", ""),
        "script": v.get("title", ""),
        "hook": v.get("title", "")[:80],
        "cta": "Shop Now",
        "ctr": v.get("engagement_rate", 0),
        "views": v.get("views", 0),
        "likes": v.get("likes", 0),
        "duration": v.get("duration", 0),
        "ad_style": "organic",
        "hashtags": v.get("hashtags", []),
        "product_name": "",
        "author": v.get("author", ""),
    } for v in videos]

def _extract_hooks(ads: list[dict]) -> list[str]:
    hooks = [ad.get("hook", "") for ad in ads if ad.get("hook")]
    return list(set(hooks))[:5]

def _extract_ctas(ads: list[dict]) -> list[str]:
    ctas = [ad.get("cta", "") for ad in ads if ad.get("cta")]
    freq = {}
    for c in ctas:
        freq[c] = freq.get(c, 0) + 1
    return sorted(freq, key=freq.get, reverse=True)[:5]

def _avg_duration(ads: list[dict]) -> float:
    durations = [ad.get("duration", 0) for ad in ads if ad.get("duration")]
    return sum(durations) / max(len(durations), 1)

def _identify_ad_styles(ads: list[dict]) -> dict:
    styles = {}
    for ad in ads:
        style = ad.get("ad_style", "unknown")
        styles[style] = styles.get(style, 0) + 1
    return dict(sorted(styles.items(), key=lambda x: x[1], reverse=True))

async def _run_actor_by_id(actor_id: str, input_data: dict) -> list:
    return await _run_actor(input_data, actor_id=actor_id)

async def _run_actor(input_data: dict, actor_id: str = None) -> list:
    headers = {"Content-Type": "application/json"}
    params = {"token": _apify_token()}
    use_actor = actor_id or ACTOR_ID

    # Actor run shuru karo
    async with httpx.AsyncClient(timeout=30) as client:
        run_resp = await client.post(
            f"{BASE_URL}/acts/{use_actor}/runs",
            headers=headers,
            params=params,
            json={"input": input_data}
        )
        run_resp.raise_for_status()
        run_id = run_resp.json()["data"]["id"]

    # Run complete hone ka wait karo
    await _wait_for_run(run_id)

    # Results lo
    async with httpx.AsyncClient(timeout=30) as client:
        items_resp = await client.get(
            f"{BASE_URL}/actor-runs/{run_id}/dataset/items",
            params={"token": _apify_token(), "format": "json"}
        )
        items_resp.raise_for_status()
        return items_resp.json()

async def _wait_for_run(run_id: str, max_wait: int = 120):
    params = {"token": _apify_token()}
    for _ in range(max_wait // 5):
        await asyncio.sleep(5)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/actor-runs/{run_id}",
                params=params
            )
            status = resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise Exception(f"Apify actor failed: {status}")
    raise Exception("Apify actor timeout")

def _extract_video_data(raw: list) -> list[dict]:
    videos = []
    for item in raw:
        try:
            videos.append({
                "title": item.get("desc", ""),
                "views": item.get("playCount", 0),
                "likes": item.get("diggCount", 0),
                "comments": item.get("commentCount", 0),
                "shares": item.get("shareCount", 0),
                "hashtags": [t.get("name", "") for t in item.get("textExtra", [])],
                "author": item.get("authorMeta", {}).get("name", ""),
                "duration": item.get("videoMeta", {}).get("duration", 0),
                "engagement_rate": _calc_engagement(item),
            })
        except Exception:
            continue
    return sorted(videos, key=lambda x: x["engagement_rate"], reverse=True)

def _calc_engagement(item: dict) -> float:
    views = item.get("playCount", 1) or 1
    likes = item.get("diggCount", 0)
    comments = item.get("commentCount", 0)
    shares = item.get("shareCount", 0)
    return ((likes + comments * 2 + shares * 3) / views) * 100
