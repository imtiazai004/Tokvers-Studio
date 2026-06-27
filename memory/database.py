import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "memory/agent_memory.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS video_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                niche TEXT,
                script TEXT,
                video_tool TEXT,
                output_path TEXT,
                character_id INTEGER DEFAULT NULL,
                tiktok_views INTEGER DEFAULT 0,
                tiktok_likes INTEGER DEFAULT 0,
                tiktok_shares INTEGER DEFAULT 0,
                performance_score REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                learning_key TEXT NOT NULL,
                learning_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS script_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche TEXT NOT NULL,
                hook_style TEXT,
                script_length TEXT,
                voice_gender TEXT,
                avg_performance REAL DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Character profiles table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                personality TEXT,
                appearance TEXT,
                image_path TEXT,
                niche TEXT,
                voice_gender TEXT DEFAULT 'female',
                is_active INTEGER DEFAULT 1,
                videos_created INTEGER DEFAULT 0,
                avg_performance REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # TikTok Account credentials table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_tiktok_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tiktok_username TEXT UNIQUE NOT NULL,
                tiktok_password_encrypted TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_sync TEXT
            )
        """)
        # TikTok Videos metrics table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_tiktok_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                title TEXT,
                url TEXT,
                synced_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrations - purani DB mein naye columns add karo
        try:
            await db.execute("ALTER TABLE video_history ADD COLUMN character_id INTEGER DEFAULT NULL")
        except Exception:
            pass  # Column already exists
        try:
            await db.execute("ALTER TABLE video_history ADD COLUMN performance_score REAL DEFAULT 0")
        except Exception:
            pass

        await db.commit()

# ─── Video History ───────────────────────────────────────

async def save_video(topic: str, niche: str, script: str, video_tool: str, output_path: str, character_id: int = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO video_history (topic, niche, script, video_tool, output_path, character_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (topic, niche, script, video_tool, output_path, character_id, datetime.now().isoformat()))
        await db.commit()
        return cursor.lastrowid

async def update_performance(video_id: int, views: int, likes: int, shares: int):
    score = (views * 1) + (likes * 3) + (shares * 5)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE video_history
            SET tiktok_views=?, tiktok_likes=?, tiktok_shares=?, performance_score=?
            WHERE id=?
        """, (views, likes, shares, score, video_id))
        # Character ki avg performance bhi update karo
        row = await (await db.execute("SELECT character_id FROM video_history WHERE id=?", (video_id,))).fetchone()
        if row and row[0]:
            await _update_character_performance(db, row[0])
        await db.commit()

async def _update_character_performance(db, character_id: int):
    result = await db.execute("""
        SELECT AVG(performance_score), COUNT(*) FROM video_history
        WHERE character_id=? AND performance_score > 0
    """, (character_id,))
    row = await result.fetchone()
    if row:
        await db.execute("""
            UPDATE characters SET avg_performance=?, videos_created=(
                SELECT COUNT(*) FROM video_history WHERE character_id=?
            ) WHERE id=?
        """, (row[0] or 0, character_id, character_id))

# ─── Agent Learnings ─────────────────────────────────────

async def save_learning(agent_name: str, key: str, value: str, confidence: float = 0.5):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute(
            "SELECT id FROM agent_learnings WHERE agent_name=? AND learning_key=?",
            (agent_name, key)
        )
        row = await existing.fetchone()
        if row:
            await db.execute("""
                UPDATE agent_learnings
                SET learning_value=?, confidence=?, updated_at=?
                WHERE agent_name=? AND learning_key=?
            """, (value, confidence, datetime.now().isoformat(), agent_name, key))
        else:
            await db.execute("""
                INSERT INTO agent_learnings (agent_name, learning_key, learning_value, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_name, key, value, confidence, datetime.now().isoformat()))
        await db.commit()

async def get_learnings(agent_name: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT learning_key, learning_value, confidence FROM agent_learnings WHERE agent_name=? ORDER BY confidence DESC",
            (agent_name,)
        )
        rows = await cursor.fetchall()
        return {row[0]: {"value": row[1], "confidence": row[2]} for row in rows}

async def get_top_performing_patterns(niche: str, limit: int = 5) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT topic, script, video_tool, performance_score
            FROM video_history
            WHERE niche=? AND performance_score > 0
            ORDER BY performance_score DESC
            LIMIT ?
        """, (niche, limit))
        rows = await cursor.fetchall()
        return [{"topic": r[0], "script": r[1], "tool": r[2], "score": r[3]} for r in rows]

async def get_recent_videos(limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT v.id, v.topic, v.niche, v.video_tool, v.performance_score, v.created_at,
                   c.name as character_name
            FROM video_history v
            LEFT JOIN characters c ON v.character_id = c.id
            ORDER BY v.created_at DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [{"id": r[0], "topic": r[1], "niche": r[2], "tool": r[3],
                 "score": r[4], "date": r[5], "character": r[6]} for r in rows]

async def get_all_videos() -> list:
    """Full video list with metrics — for the Content Library page."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT v.id, v.topic, v.niche, v.video_tool, v.output_path,
                   v.tiktok_views, v.tiktok_likes, v.tiktok_shares,
                   v.performance_score, v.created_at, c.name as character_name
            FROM video_history v
            LEFT JOIN characters c ON v.character_id = c.id
            ORDER BY v.created_at DESC
        """)
        rows = await cursor.fetchall()
        return [{
            "id": r[0], "topic": r[1], "niche": r[2], "tool": r[3],
            "output_path": r[4], "views": r[5] or 0, "likes": r[6] or 0,
            "shares": r[7] or 0, "score": r[8] or 0, "date": r[9],
            "character": r[10]
        } for r in rows]

async def get_products_summary() -> list:
    """Aggregate videos by product (topic) — for the Products page."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT topic, niche,
                   COUNT(*) as video_count,
                   SUM(tiktok_views) as total_views,
                   SUM(tiktok_likes) as total_likes,
                   SUM(tiktok_shares) as total_shares,
                   AVG(performance_score) as avg_score,
                   MAX(created_at) as last_used
            FROM video_history
            GROUP BY topic
            ORDER BY total_views DESC, video_count DESC
        """)
        rows = await cursor.fetchall()
        return [{
            "product": r[0], "niche": r[1], "video_count": r[2],
            "total_views": r[3] or 0, "total_likes": r[4] or 0,
            "total_shares": r[5] or 0, "avg_score": round(r[6] or 0, 1),
            "last_used": r[7]
        } for r in rows]

async def get_all_learnings() -> dict:
    """All agent learnings + script patterns — for the Learnings page."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT agent_name, learning_key, learning_value, confidence, updated_at
            FROM agent_learnings
            ORDER BY confidence DESC, updated_at DESC
        """)
        learning_rows = await cursor.fetchall()
        learnings = [{
            "agent": r[0], "key": r[1], "value": r[2],
            "confidence": round(r[3] or 0, 2), "updated_at": r[4]
        } for r in learning_rows]

        cursor = await db.execute("""
            SELECT niche, hook_style, script_length, voice_gender, avg_performance, usage_count
            FROM script_patterns
            ORDER BY avg_performance DESC
        """)
        pattern_rows = await cursor.fetchall()
        patterns = [{
            "niche": r[0], "hook_style": r[1], "script_length": r[2],
            "voice_gender": r[3], "avg_performance": round(r[4] or 0, 1),
            "usage_count": r[5] or 0
        } for r in pattern_rows]

        return {"learnings": learnings, "patterns": patterns}

# ─── Characters ──────────────────────────────────────────

async def save_character(
    name: str, description: str, personality: str,
    appearance: str, image_path: str, niche: str, voice_gender: str = "female"
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO characters (name, description, personality, appearance, image_path, niche, voice_gender, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description, personality, appearance, image_path, niche, voice_gender, datetime.now().isoformat()))
        await db.commit()
        return cursor.lastrowid

async def get_all_characters() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, name, description, personality, appearance, image_path,
                   niche, voice_gender, videos_created, avg_performance
            FROM characters WHERE is_active=1
            ORDER BY avg_performance DESC, created_at DESC
        """)
        rows = await cursor.fetchall()
        return [{
            "id": r[0], "name": r[1], "description": r[2],
            "personality": r[3], "appearance": r[4], "image_path": r[5],
            "niche": r[6], "voice_gender": r[7],
            "videos_created": r[8], "avg_performance": r[9]
        } for r in rows]

async def get_character(character_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, name, description, personality, appearance, image_path, niche, voice_gender FROM characters WHERE id=?",
            (character_id,)
        )
        r = await cursor.fetchone()
        if not r:
            return None
        return {
            "id": r[0], "name": r[1], "description": r[2],
            "personality": r[3], "appearance": r[4], "image_path": r[5],
            "niche": r[6], "voice_gender": r[7]
        }

async def delete_character(character_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE characters SET is_active=0 WHERE id=?", (character_id,))
        await db.commit()

# ─── TikTok Integration ───────────────────────────────────

async def save_tiktok_credentials(username: str, password_encrypted: str):
    """Save user's encrypted TikTok credentials"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO user_tiktok_accounts
               (tiktok_username, tiktok_password_encrypted, enabled)
               VALUES (?, ?, 1)""",
            (username, password_encrypted)
        )
        await db.commit()

async def get_tiktok_credentials() -> dict:
    """Get user's encrypted TikTok credentials"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT tiktok_username, tiktok_password_encrypted FROM user_tiktok_accounts WHERE enabled=1 LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            return {"username": row[0], "password_encrypted": row[1]}
        return None

async def save_tiktok_videos(videos: list):
    """Save/update TikTok video metrics"""
    async with aiosqlite.connect(DB_PATH) as db:
        for video in videos:
            await db.execute(
                """INSERT OR REPLACE INTO user_tiktok_videos
                   (video_id, views, likes, comments, shares, engagement_rate, title, url, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    video.get("video_id"),
                    video.get("views", 0),
                    video.get("likes", 0),
                    video.get("comments", 0),
                    video.get("shares", 0),
                    video.get("engagement_rate", 0),
                    video.get("title", ""),
                    video.get("url", ""),
                    datetime.now().isoformat()
                )
            )
        await db.commit()

async def get_tiktok_videos() -> list:
    """Get all stored TikTok videos"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT video_id, views, likes, comments, shares, engagement_rate, title FROM user_tiktok_videos ORDER BY synced_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "video_id": r[0],
                "views": r[1],
                "likes": r[2],
                "comments": r[3],
                "shares": r[4],
                "engagement_rate": r[5],
                "title": r[6],
            }
            for r in rows
        ]

async def update_tiktok_sync_time():
    """Update last sync time"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_tiktok_accounts SET last_sync=? WHERE enabled=1",
            (datetime.now().isoformat(),)
        )
        await db.commit()
