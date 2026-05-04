"""
main.py — Sahhab Pro Backend API
FastAPI application with WebSocket support for real-time download progress.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from downloader import fetch_profile_videos
from queue_manager import DownloadQueue
from telegram_sender import send_to_telegram, verify_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

queue = DownloadQueue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = asyncio.create_task(queue.process_loop())
    logger.info("✅ Sahhab Pro started — queue worker running")
    yield
    worker.cancel()
    try:
        await worker
    except asyncio.CancelledError:
        pass
    logger.info("🛑 Sahhab Pro stopped")


app = FastAPI(
    title="Sahhab Pro API",
    description="محمّل الوسائط الاحترافي — Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────── Schemas ────────────────────────────────────

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"
    send_to_telegram: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class BulkDownloadRequest(BaseModel):
    urls: list[str]
    quality: str = "best"
    send_to_telegram: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class ProfileRequest(BaseModel):
    url: str
    max_videos: int = 50


class TelegramSendRequest(BaseModel):
    job_id: str
    token: str
    chat_id: str


class TelegramVerifyRequest(BaseModel):
    token: str


# ─────────────────────────────── Routes ─────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "service": "Sahhab Pro"}


@app.post("/api/download")
async def add_single_download(req: DownloadRequest):
    """Add one URL to the download queue."""
    if not req.url.strip():
        raise HTTPException(400, "الرابط فارغ")
    job_id = str(uuid.uuid4())[:8]
    job = await queue.add(job_id, req.model_dump())
    return {"job_id": job_id, "status": "queued", "position": job["position"]}


@app.post("/api/download/bulk")
async def add_bulk_downloads(req: BulkDownloadRequest):
    """Add multiple URLs to the download queue at once."""
    if not req.urls:
        raise HTTPException(400, "قائمة الروابط فارغة")
    if len(req.urls) > 50:
        raise HTTPException(400, "الحد الأقصى 50 رابطاً دفعة واحدة")

    job_ids = []
    base = req.model_dump()
    for url in req.urls:
        if not url.strip():
            continue
        job_id = str(uuid.uuid4())[:8]
        data = {**base, "url": url}
        await queue.add(job_id, data)
        job_ids.append(job_id)

    return {"job_ids": job_ids, "count": len(job_ids)}


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    job = queue.get_status(job_id)
    if not job:
        raise HTTPException(404, "المهمة غير موجودة")
    return job


@app.get("/api/queue")
async def get_queue():
    return {"jobs": queue.get_all()}


@app.delete("/api/queue/{job_id}")
async def cancel_job(job_id: str):
    queue.cancel(job_id)
    return {"status": "cancelled", "job_id": job_id}


@app.delete("/api/queue")
async def clear_completed():
    queue.clear_completed()
    return {"status": "cleared"}


@app.post("/api/profile")
async def fetch_profile(req: ProfileRequest):
    """Fetch all videos from a profile / channel / playlist URL."""
    try:
        videos = await fetch_profile_videos(req.url, max_videos=min(req.max_videos, 100))
        return {"count": len(videos), "videos": videos}
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@app.get("/api/download/{job_id}/file")
async def serve_file(job_id: str):
    """Serve the downloaded file for browser download."""
    job = queue.get_status(job_id)
    if not job:
        raise HTTPException(404, "المهمة غير موجودة")
    if job["status"] not in ("completed", "sending_telegram"):
        raise HTTPException(400, f"الملف غير جاهز — الحالة: {job['status']}")
    filepath = job.get("filepath")
    if not filepath or not Path(filepath).exists():
        raise HTTPException(404, "الملف غير موجود على السيرفر")
    return FileResponse(
        path=filepath,
        filename=Path(filepath).name,
        media_type="application/octet-stream",
    )


@app.post("/api/telegram/send")
async def send_job_to_telegram(req: TelegramSendRequest):
    """Manually send an already-downloaded file to Telegram."""
    job = queue.get_status(req.job_id)
    if not job:
        raise HTTPException(404, "المهمة غير موجودة")
    if job["status"] != "completed":
        raise HTTPException(400, "يجب اكتمال التحميل أولاً")
    filepath = job.get("filepath")
    if not filepath or not Path(filepath).exists():
        raise HTTPException(404, "الملف غير موجود")
    try:
        await send_to_telegram(
            token=req.token,
            chat_id=req.chat_id,
            filepath=filepath,
            caption=f"📥 {job.get('title', '')}",
        )
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/telegram/verify")
async def telegram_verify(req: TelegramVerifyRequest):
    """Verify a Telegram bot token."""
    try:
        info = await verify_bot(req.token)
        return {"ok": True, "bot_name": info.get("first_name"), "username": info.get("username")}
    except Exception as e:
        raise HTTPException(400, str(e))


# ─────────────────────────── WebSocket endpoint ──────────────────────────────

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    queue.register_ws(client_id, websocket)
    logger.info(f"WebSocket connected: {client_id}")

    # Send current state immediately on connect
    import json
    await websocket.send_text(
        json.dumps({"type": "init", "jobs": queue.get_all()}, ensure_ascii=False, default=str)
    )

    try:
        while True:
            # Keep connection alive with ping
            await asyncio.sleep(30)
            try:
                await websocket.send_text('{"type":"ping"}')
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        queue.unregister_ws(client_id)
        logger.info(f"WebSocket disconnected: {client_id}")


# ─────────────────────────── Entry point ─────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
