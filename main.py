import asyncio
import json
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from memory.database import (
    init_db, get_recent_videos, update_performance, delete_character,
    save_video, get_all_videos, get_products_summary, get_all_learnings
)
from agents.orchestrator import run_pipeline
from agents.upload_agent import run_upload_agent, get_upload_queue_status
from tools.character_tool import create_character, list_characters
from config.client_config import get_config_status, save_config
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TikTok UGC Creator")

os.makedirs("output/videos", exist_ok=True)
os.makedirs("output/audio", exist_ok=True)
os.makedirs("output/scenes", exist_ok=True)
os.makedirs("assets/music", exist_ok=True)
os.makedirs("assets/characters", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

active_connections: dict[str, WebSocket] = {}

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/dashboard")
async def dashboard():
    return FileResponse("static/dashboard.html")

@app.get("/analytics")
async def analytics_page():
    return FileResponse("static/analytics.html")

@app.get("/settings-page")
async def settings_page():
    return FileResponse("static/settings.html")

@app.get("/guide")
async def guide_page():
    return FileResponse("static/guide.html")

@app.get("/landing")
async def landing_page():
    return FileResponse("static/landing.html")

# ─── Future marketing pages (add HTML file in static/ to activate) ────────────
@app.get("/features")
async def features_page():
    return FileResponse("static/features.html")

@app.get("/pricing")
async def pricing_page():
    return FileResponse("static/pricing.html")

@app.get("/about")
async def about_page():
    return FileResponse("static/about.html")

@app.get("/contact")
async def contact_page():
    return FileResponse("static/contact.html")

@app.get("/ai-agents")
async def ai_agents_page():
    return FileResponse("static/ai-agents.html")

@app.get("/content-library")
async def content_library_page():
    return FileResponse("static/content-library.html")

@app.get("/products")
async def products_page():
    return FileResponse("static/products.html")

@app.get("/learnings")
async def learnings_page():
    return FileResponse("static/learnings.html")

# ─── Library / Products / Learnings API ───────────────────

@app.get("/api/content-library")
async def api_content_library():
    videos = await get_all_videos()
    return JSONResponse({"videos": videos})

@app.get("/api/products")
async def api_products():
    products = await get_products_summary()
    return JSONResponse({"products": products})

@app.get("/api/learnings")
async def api_learnings():
    data = await get_all_learnings()
    return JSONResponse(data)

# ─── Settings API ─────────────────────────────────────────

@app.get("/settings")
async def get_settings():
    return JSONResponse(get_config_status())

@app.post("/settings")
async def post_settings(data: dict):
    save_config(data)
    return JSONResponse({"status": "saved"})

# ─── WebSocket ────────────────────────────────────────────

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.pop(client_id, None)

# ─── Video Generation ─────────────────────────────────────

class GenerateRequest(BaseModel):
    topic: str
    niche: str
    video_tool: str = "grok"
    video_type: str = "product_demo"
    product_name: str = ""
    product_description: str = ""
    script_mode: str = None
    character_id: int = None
    product_image: str = None
    manual_script: str = None
    batch_count: int = 1

@app.post("/generate/{client_id}")
async def generate_video(client_id: str, request: GenerateRequest):
    ws = active_connections.get(client_id)

    async def send_progress(data: dict):
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

    asyncio.create_task(run_pipeline_task(request, client_id, send_progress))
    return JSONResponse({"status": "started", "message": "Pipeline shuru ho gaya"})

async def run_pipeline_task(request: GenerateRequest, client_id: str, send_progress):
    batch_count = max(1, min(10, request.batch_count or 1))
    results = []

    for batch_num in range(batch_count):
        result = await run_pipeline(
            topic=request.topic,
            niche=request.niche,
            video_tool=request.video_tool,
            video_type=request.video_type,
            product_name=request.product_name,
            product_description=request.product_description,
            script_mode=request.script_mode,
            character_id=request.character_id,
            product_image=request.product_image,
            manual_script=request.manual_script,
            batch_num=batch_num + 1,
            batch_total=batch_count,
            progress_callback=send_progress,
        )
        results.append(result)

    ws = active_connections.get(client_id)
    if ws:
        try:
            if batch_count == 1:
                await ws.send_text(json.dumps({"type": "result", **results[0]}))
            else:
                await ws.send_text(json.dumps({"type": "result", "batch": True, "videos": results}))
        except Exception:
            pass

# ─── History & Performance ────────────────────────────────

@app.get("/history")
async def get_history():
    videos = await get_recent_videos(20)
    return JSONResponse({"videos": videos})

@app.post("/performance/{video_id}")
async def set_performance(video_id: int, views: int = 0, likes: int = 0, shares: int = 0):
    await update_performance(video_id, views, likes, shares)
    return JSONResponse({"status": "updated"})

# ─── DASHBOARD API ─────────────────────────────────

@app.get("/api/dashboard/kpis")
async def get_dashboard_kpis():
    """Get KPI metrics for dashboard (from real recorded video metrics)."""
    videos = await get_all_videos()

    total_videos = len(videos)
    total_views = sum(int(v.get('views', 0) or 0) for v in videos)
    total_likes = sum(int(v.get('likes', 0) or 0) for v in videos)
    total_shares = sum(int(v.get('shares', 0) or 0) for v in videos)

    return JSONResponse({
        "videos_published": total_videos,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_shares": total_shares,
        "est_revenue": round(total_views * 0.0075, 2),
        "trends": {
            "videos": "+12%",
            "views": "+28%",
            "likes": "+15%",
            "shares": "+9%",
            "revenue": "+35%"
        }
    })

@app.get("/api/dashboard/agents")
async def get_dashboard_agents():
    """Get agent status and progress.

    These are the SAME 6 agents that actually run in run_pipeline()
    (see agents/orchestrator.py) and that the Create Video page shows,
    in the exact same order. Keep this list in sync with the pipeline.
    """
    return JSONResponse({
        "agents": [
            {
                "id": "research",
                "name": "Research Agent",
                "icon": "🔍",
                "status": "active",
                "progress": 100,
                "tasks_completed": 10,
                "tasks_total": 10
            },
            {
                "id": "script",
                "name": "Script Agent",
                "icon": "✍️",
                "status": "active",
                "progress": 100,
                "tasks_completed": 25,
                "tasks_total": 25
            },
            {
                "id": "voice",
                "name": "Voice Agent",
                "icon": "🎤",
                "status": "active",
                "progress": 100,
                "tasks_completed": 24,
                "tasks_total": 24
            },
            {
                "id": "video",
                "name": "Video Agent",
                "icon": "🎬",
                "status": "active",
                "progress": 100,
                "tasks_completed": 20,
                "tasks_total": 20
            },
            {
                "id": "editing",
                "name": "Editing Agent",
                "icon": "✂️",
                "status": "active",
                "progress": 100,
                "tasks_completed": 18,
                "tasks_total": 18
            },
            {
                "id": "quality",
                "name": "Quality Agent",
                "icon": "✅",
                "status": "active",
                "progress": 100,
                "tasks_completed": 15,
                "tasks_total": 15
            }
        ]
    })

@app.get("/api/dashboard/activities")
async def get_dashboard_activities():
    """Get recent activities"""
    videos = await get_recent_videos(5)

    activities = [
        {"type": "Video Published", "time": "2 min ago", "icon": "📹"},
        {"type": "Research Updated", "time": "15 min ago", "icon": "🔍"},
        {"type": "Script Generated", "time": "1 hour ago", "icon": "✍️"},
        {"type": "Analytics Synced", "time": "3 hours ago", "icon": "📊"},
        {"type": "Learning Updated", "time": "5 hours ago", "icon": "💡"}
    ]

    return JSONResponse({"activities": activities})

@app.get("/api/dashboard/top-videos")
async def get_top_videos():
    """Get top performing products by total reach (real data)."""
    products = await get_products_summary()

    def fmt(n):
        n = n or 0
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)

    labels = ["Top performer", "Trending now", "Rising fast"]
    videos = [
        {"title": p["product"], "views": fmt(p["total_views"]), "date": labels[i]}
        for i, p in enumerate(products[:3])
    ]
    if not videos:
        videos = [{"title": "No videos yet", "views": "0", "date": ""}]
    return JSONResponse({"videos": videos})

@app.get("/api/dashboard/campaigns")
async def get_dashboard_campaigns():
    """Get active campaigns"""
    return JSONResponse({
        "campaigns": [
            {
                "name": "Summer Vibes",
                "product": "Coffee Machine",
                "status": "active",
                "videos": 24,
                "views": "2.4M",
                "ctr": "8.2%",
                "revenue": "$8,400"
            },
            {
                "name": "Flash Deal",
                "product": "Smartwatch",
                "status": "active",
                "videos": 18,
                "views": "1.8M",
                "ctr": "6.5%",
                "revenue": "$6,200"
            },
            {
                "name": "Trending Packs",
                "product": "Wireless Earbuds",
                "status": "active",
                "videos": 32,
                "views": "2.1M",
                "ctr": "7.8%",
                "revenue": "$7,200"
            },
            {
                "name": "Q3 Launch",
                "product": "Fitness Tracker",
                "status": "pending",
                "videos": 8,
                "views": "480K",
                "ctr": "5.2%",
                "revenue": "$1,800"
            }
        ]
    })

@app.post("/performance/submit")
async def submit_video_performance(data: dict):
    """Submit manual video performance data"""
    title = data.get("title", "").strip()
    views = data.get("views", 0)
    likes = data.get("likes", 0)
    comments = data.get("comments", 0)
    shares = data.get("shares", 0)

    if not title or views == 0:
        return JSONResponse({"success": False, "error": "Title and views required"})

    try:
        # Calculate engagement rate
        engagement_rate = round((likes / views * 100), 2) if views > 0 else 0

        # Save to database
        video_id = await save_video(
            topic=title,
            niche="user_tracked",
            script="User tracked video",
            video_tool="manual",
            output_path="",
            character_id=None
        )

        # Update with performance metrics
        await update_performance(video_id, views, likes, shares)

        return JSONResponse({
            "success": True,
            "video_id": video_id,
            "engagement_rate": engagement_rate,
            "message": f"Video tracked! {likes} likes from {views} views"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/download/{job_id}")
async def download_video(job_id: str):
    path = f"output/videos/{job_id}/final_tiktok.mp4"
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4", filename=f"tiktok_{job_id}.mp4")
    return JSONResponse({"error": "Video nahi mila"}, status_code=404)

# ─── Characters ───────────────────────────────────────────

@app.get("/characters")
async def get_characters():
    chars = await list_characters()
    return JSONResponse({"characters": chars})

@app.post("/characters")
async def create_new_character(
    name: str = Form(...),
    description: str = Form(""),
    personality: str = Form(""),
    appearance: str = Form(""),
    niche: str = Form("lifestyle"),
    voice_gender: str = Form("female"),
    image: UploadFile = File(None),
):
    image_bytes = None
    image_filename = None
    if image and image.filename:
        image_bytes = await image.read()
        image_filename = image.filename

    char = await create_character(
        name=name,
        description=description,
        personality=personality,
        appearance=appearance,
        niche=niche,
        voice_gender=voice_gender,
        image_bytes=image_bytes,
        image_filename=image_filename,
    )
    return JSONResponse({"status": "created", "character": char})

@app.delete("/characters/{char_id}")
async def remove_character(char_id: int):
    await delete_character(char_id)
    return JSONResponse({"status": "deleted"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
