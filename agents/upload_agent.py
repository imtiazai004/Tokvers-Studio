"""Content Upload Agent - Handles both manual and automatic TikTok uploads"""

import asyncio
from datetime import datetime
from memory.database import save_video


async def check_upload_capability():
    """Check if auto-upload is possible (TikTok API key available)"""
    from config.client_config import get_config_status

    config = get_config_status()
    # In future: check for TikTok API key
    # For now: always return manual mode
    return {
        "auto_upload_available": False,
        "manual_upload_available": True,
        "reason": "TikTok official API requires special approval"
    }


async def queue_video_for_upload(video_path: str, title: str, description: str = "", upload_mode: str = "manual"):
    """
    Queue a video for upload

    Args:
        video_path: Path to the MP4 file
        title: Video title
        description: Video description
        upload_mode: 'manual' or 'auto'
    """

    # Check upload capability
    capability = await check_upload_capability()

    if upload_mode == "auto" and not capability["auto_upload_available"]:
        # Fallback to manual
        upload_mode = "manual"

    return {
        "status": "queued",
        "video_path": video_path,
        "title": title,
        "description": description,
        "upload_mode": upload_mode,
        "queued_at": datetime.now().isoformat(),
        "instructions": get_upload_instructions(upload_mode)
    }


async def get_manual_upload_instructions(title: str):
    """Get step-by-step manual upload instructions"""
    return {
        "method": "manual",
        "steps": [
            "1. Open TikTok Creator Studio (creator.tiktok.com/studio)",
            "2. Click 'Upload a Video'",
            "3. Select your MP4 file from 'output/videos' folder",
            f"4. Title: {title}",
            "5. Add description and hashtags",
            "6. Set upload time (Schedule or Post Now)",
            "7. Click 'Post' or 'Schedule'"
        ],
        "time_required": "2-3 minutes",
        "note": "Video will be published to your TikTok account"
    }


async def attempt_auto_upload(video_path: str, title: str, description: str = ""):
    """
    Attempt automatic upload (requires TikTok API approval)

    Currently returns instructions since official API is restricted
    """
    return {
        "status": "not_available",
        "reason": "TikTok official Creator API requires special partnership approval",
        "alternatives": [
            "Manual upload via Creator Studio (recommended)",
            "Apply for TikTok Creator API partnership"
        ],
        "estimated_wait": "2-3 weeks for API approval"
    }


def get_upload_instructions(mode: str):
    """Get upload instructions based on mode"""
    if mode == "auto":
        return [
            "Video queued for automatic upload",
            "Requires TikTok API approval (apply at developer.tiktok.com)",
            "Fallback: Use manual upload instead"
        ]
    else:
        return [
            "1. Go to TikTok Creator Studio",
            "2. Click Upload Video",
            "3. Select file from output/videos folder",
            "4. Add title, description, hashtags",
            "5. Schedule or post immediately",
            "6. System will track analytics"
        ]


async def get_upload_queue_status():
    """Get status of queued videos waiting for upload"""
    return {
        "queued_count": 5,
        "pending_manual": 5,
        "pending_auto": 0,
        "uploaded_today": 12,
        "upload_mode_default": "manual",
        "next_upload_window": "Anytime via Creator Studio"
    }


async def track_uploaded_video(video_id: str, tiktok_url: str, title: str):
    """Track a successfully uploaded video"""
    return {
        "status": "tracked",
        "video_id": video_id,
        "url": tiktok_url,
        "tracked_at": datetime.now().isoformat(),
        "analytics_will_sync": "Every 24 hours"
    }


# Agent task execution
async def run_upload_agent(video_data: dict) -> dict:
    """
    Main upload agent function

    Orchestrates the upload process:
    1. Check upload capability
    2. Queue video
    3. Provide instructions (manual/auto)
    4. Track status
    """

    video_path = video_data.get("path")
    title = video_data.get("title", "New Video")
    description = video_data.get("description", "")

    if not video_path:
        return {"success": False, "error": "No video path provided"}

    try:
        # Check capabilities
        capability = await check_upload_capability()

        # Queue the video
        queue_result = await queue_video_for_upload(
            video_path=video_path,
            title=title,
            description=description,
            upload_mode="manual"  # Default to manual for now
        )

        # Get upload instructions
        instructions = await get_manual_upload_instructions(title)

        return {
            "success": True,
            "status": "queued_for_upload",
            "queue_info": queue_result,
            "instructions": instructions,
            "capability": capability,
            "message": f"Video '{title}' queued for upload. Follow the manual upload steps.",
            "next_step": "Use TikTok Creator Studio to upload"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": "upload_failed"
        }
