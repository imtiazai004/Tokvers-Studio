"""
seed_demo.py — populate the database with realistic demo data so the whole app
(Dashboard, Analytics, Content Library, Products, Learnings, Characters) looks
and behaves like a live, successful TikTok-automation operation.

Safe to re-run: it wipes the demo tables and reseeds deterministically.

    python seed_demo.py
"""
import asyncio
import random
from datetime import datetime, timedelta

import aiosqlite

from memory.database import init_db, DB_PATH

random.seed(7)  # deterministic — same data every run

# ── products (these become the "topic" = product identifier) ──────────────
PRODUCTS = [
    ("Spicy Ramen Kit",            "food_and_beverage"),
    ("Cold Brew Coffee Maker",     "food_and_beverage"),
    ("Matcha Starter Kit",         "food_and_beverage"),
    ("Vitamin C Glow Serum",       "beauty"),
    ("Collagen Glow Powder",       "beauty"),
    ("Hydrating Lip Mask",         "beauty"),
    ("Scalp Massager Brush",       "beauty"),
    ("Smart Fitness Watch",        "tech"),
    ("Wireless Earbuds Pro",       "tech"),
    ("Mini Portable Blender",      "lifestyle"),
    ("LED Sunset Lamp",            "lifestyle"),
    ("Oversized Vintage Hoodie",   "fashion"),
    ("Resistance Band Set",        "fitness"),
    ("Posture Corrector",          "fitness"),
    ("Travel Packing Cubes",       "travel"),
]

# ── recurring creator characters ──────────────────────────────────────────
CHARACTERS = [
    # name, description, personality, appearance, niche, voice_gender
    ("Sara",  "Relatable beauty creator",   "warm, energetic",    "South Asian woman, 20s, dark wavy hair", "beauty",            "female"),
    ("Maya",  "Cozy lifestyle host",        "calm, aesthetic",    "East Asian woman, late 20s, soft style", "lifestyle",         "female"),
    ("Alex",  "Tech reviewer",              "confident, clear",   "White man, 30s, casual modern",          "tech",              "male"),
    ("Liam",  "Fitness coach",              "high-energy, direct","Athletic Black man, 20s",                "fitness",           "male"),
    ("Zoe",   "Fashion stylist",            "playful, trendy",    "Latina woman, 20s, bold style",          "fashion",           "female"),
    ("Noah",  "Foodie storyteller",         "fun, expressive",    "Middle Eastern man, 20s",                "food_and_beverage", "male"),
    ("Aria",  "Travel vlogger",             "adventurous, bright","White woman, late 20s",                  "travel",            "female"),
]

# ── agent learnings (Learnings page · Agent Insights) ─────────────────────
LEARNINGS = [
    ("Research Agent", "best_posting_time",  "6–9 PM weekdays",                       0.88),
    ("Research Agent", "top_hashtag_cluster","#tiktokmademebuyit · #amazonfinds",     0.82),
    ("Research Agent", "trending_format",    "POV: problem → product reveal",         0.79),
    ("Research Agent", "competitor_gap",     "Under-served angle: ASMR unboxing",     0.68),
    ("Script Agent",   "winning_hook",       "\"I was today years old when…\"",       0.91),
    ("Script Agent",   "optimal_length",     "21–27 seconds",                         0.86),
    ("Script Agent",   "cta_style",          "\"Link in bio — selling out fast\"",    0.80),
    ("Script Agent",   "emoji_use",          "1–2 emojis lift CTR",                   0.70),
    ("Voice Agent",    "best_voice",         "Female · upbeat · US accent",           0.84),
    ("Voice Agent",    "pacing",             "150–165 words per minute",              0.77),
    ("Voice Agent",    "music_pairing",      "Trending audio + low VO bed",           0.73),
    ("Video Agent",    "hook_visual",        "First frame = product in motion",       0.87),
    ("Video Agent",    "best_tool_food",     "Veo3 for close-up texture shots",       0.83),
    ("Video Agent",    "scene_count",        "3 scenes converts best",                0.74),
    ("Editing Agent",  "caption_style",      "Word-by-word, bottom-center",           0.85),
    ("Editing Agent",  "broll_ratio",        "60% product / 40% lifestyle",           0.72),
    ("Quality Agent",  "min_score",          "Reject anything below 78",              0.90),
    ("Quality Agent",  "retry_rate",         "Auto-retry improves score ~12%",        0.76),
]

# ── winning script patterns (Learnings page · Script Patterns) ────────────
PATTERNS = [
    ("beauty",            "Before / After reveal", "22s", "female", 91.4, 64),
    ("food_and_beverage", "POV craving",           "24s", "female", 88.7, 52),
    ("fashion",           "Get ready with me",     "21s", "female", 87.1, 41),
    ("tech",              "3 reasons why",         "27s", "male",   85.2, 47),
    ("lifestyle",         "This changed my…",      "23s", "female", 84.5, 33),
    ("fitness",           "Day 1 vs Day 30",       "26s", "male",   83.9, 38),
    ("travel",            "Don't go until you…",   "28s", "female", 81.6, 22),
]


def sample_views():
    """Long-tail view distribution — most modest, a few viral."""
    r = random.random()
    if r < 0.58:
        return random.randint(6_000, 65_000)
    if r < 0.84:
        return random.randint(65_000, 290_000)
    if r < 0.96:
        return random.randint(290_000, 900_000)
    return random.randint(1_000_000, 2_300_000)


async def main():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        # wipe demo tables for a clean, deterministic reseed
        for t in ("video_history", "agent_learnings", "script_patterns", "characters"):
            await db.execute(f"DELETE FROM {t}")
            try:
                await db.execute("DELETE FROM sqlite_sequence WHERE name=?", (t,))
            except Exception:
                pass

        # characters
        char_by_niche = {}
        for (name, desc, persona, appearance, niche, voice) in CHARACTERS:
            cur = await db.execute(
                """INSERT INTO characters
                   (name, description, personality, appearance, image_path, niche, voice_gender, is_active, created_at)
                   VALUES (?,?,?,?,?,?,?,1,?)""",
                (name, desc, persona, appearance, "", niche, voice,
                 (datetime.now() - timedelta(days=random.randint(120, 200))).isoformat()),
            )
            char_by_niche.setdefault(niche, []).append(cur.lastrowid)

        # videos per product
        now = datetime.now()
        total_videos = total_views = total_likes = total_shares = 0
        for (product, niche) in PRODUCTS:
            n = random.randint(12, 22)
            for _ in range(n):
                views = sample_views()
                likes = int(views * random.uniform(0.07, 0.13))
                shares = int(views * random.uniform(0.010, 0.025))
                score = random.randint(74, 98)                  # quality score
                tool = random.choices(["grok", "veo3"], weights=[0.6, 0.4])[0]
                # assign a recurring character ~55% of the time (niche-matched)
                char_id = None
                pool = char_by_niche.get(niche)
                if pool and random.random() < 0.55:
                    char_id = random.choice(pool)
                created = (now - timedelta(
                    days=random.randint(0, 178),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )).isoformat()
                await db.execute(
                    """INSERT INTO video_history
                       (topic, niche, script, video_tool, output_path, character_id,
                        tiktok_views, tiktok_likes, tiktok_shares, performance_score, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (product, niche, f"UGC script for {product}", tool, "", char_id,
                     views, likes, shares, score, created),
                )
                total_videos += 1
                total_views += views
                total_likes += likes
                total_shares += shares

        # roll up character stats
        await db.execute("""
            UPDATE characters SET
              videos_created = (SELECT COUNT(*) FROM video_history WHERE character_id = characters.id),
              avg_performance = (SELECT COALESCE(AVG(performance_score), 0) FROM video_history WHERE character_id = characters.id)
        """)

        # learnings
        for (agent, key, value, conf) in LEARNINGS:
            await db.execute(
                """INSERT INTO agent_learnings (agent_name, learning_key, learning_value, confidence, updated_at)
                   VALUES (?,?,?,?,?)""",
                (agent, key, value, conf,
                 (now - timedelta(days=random.randint(0, 40))).isoformat()),
            )

        # script patterns
        for (niche, hook, length, voice, perf, used) in PATTERNS:
            await db.execute(
                """INSERT INTO script_patterns
                   (niche, hook_style, script_length, voice_gender, avg_performance, usage_count, updated_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (niche, hook, length, voice, perf, used, now.isoformat()),
            )

        await db.commit()

    print("[OK] Demo data seeded")
    print(f"   Products : {len(PRODUCTS)}")
    print(f"   Videos   : {total_videos}")
    print(f"   Views    : {total_views:,}")
    print(f"   Likes    : {total_likes:,}")
    print(f"   Shares   : {total_shares:,}")
    print(f"   Revenue  : ${round(total_views * 0.0075):,}")
    print(f"   Chars    : {len(CHARACTERS)}  ·  Learnings: {len(LEARNINGS)}  ·  Patterns: {len(PATTERNS)}")


if __name__ == "__main__":
    asyncio.run(main())
