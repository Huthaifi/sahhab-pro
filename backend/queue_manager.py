"""
queue_manager.py — Async download queue with real-time WebSocket updates
Handles sequential processing, progress tracking, and Telegram forwarding.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import WebSocket

from downloader import download_url
from telegram_sender import send_to_telegram

logger = logging.getLogger(__name__)


class DownloadQueue:
    def __init__(self):
        self.jobs: Dict[str, dict] = {}          # job_id → job dict
        self._queue: asyncio.Queue = asyncio.Queue()
        self._ws_clients: Dict[str, WebSocket] = {}
        self.active_job_id: Optional[str] = None

    # ──────────────────────────────── Public API ──────────────────────────────

    async def add(self, job_id: str, data: dict) -> dict:
        position = self._queue.qsize() + (1 if self.active_job_id else 0)
        job = {
            "id":          job_id,
            "url":         data["url"],
            "status":      "queued",
            "progress":    0,
            "speed":       0,
            "title":       None,
            "thumbnail":   None,
            "uploader":    None,
            "platform":    None,
            "filepath":    None,
            "filesize":    0,
            "ext":         None,
            "error":       None,
            "position":    position,
            "created_at":  time.time(),
            "completed_at": None,
            "telegram_sent":  False,
            "telegram_error": None,
            "_data":       data,           # private: original request data
        }
        self.jobs[job_id] = job
        await self._queue.put(job_id)
        await self._broadcast({"type": "queue_update", "jobs": self._public_jobs()})
        return job

    def get_status(self, job_id: str) -> Optional[dict]:
        return self.jobs.get(job_id)

    def get_all(self) -> List[dict]:
        return self._public_jobs()

    def cancel(self, job_id: str):
        job = self.jobs.get(job_id)
        if job and job["status"] == "queued":
            job["status"] = "cancelled"

    def clear_completed(self):
        done = [jid for jid, j in self.jobs.items()
                if j["status"] in ("completed", "failed", "cancelled")]
        for jid in done:
            self.jobs.pop(jid, None)

    # ────────────────────────── WebSocket management ──────────────────────────

    def register_ws(self, client_id: str, ws: WebSocket):
        self._ws_clients[client_id] = ws

    def unregister_ws(self, client_id: str):
        self._ws_clients.pop(client_id, None)

    # ──────────────────────────── Background loop ─────────────────────────────

    async def process_loop(self):
        """Main worker loop — runs as a background task."""
        while True:
            job_id = await self._queue.get()

            job = self.jobs.get(job_id)
            if not job:
                continue
            if job["status"] == "cancelled":
                self._queue.task_done()
                continue

            self.active_job_id = job_id
            await self._update_job(job_id, status="downloading")

            data = job["_data"]
            try:
                # ── Download ──────────────────────────────────────────────
                async def _progress(percent: float, speed: float):
                    await self._update_job(
                        job_id,
                        progress=percent,
                        speed=speed,
                        _broadcast_type="progress",
                    )

                result = await download_url(
                    url=data["url"],
                    job_id=job_id,
                    quality=data.get("quality", "best"),
                    progress_callback=_progress,
                )

                await self._update_job(
                    job_id,
                    status="completed",
                    progress=100,
                    speed=0,
                    title=result["title"],
                    thumbnail=result["thumbnail"],
                    uploader=result["uploader"],
                    platform=result["platform"],
                    filepath=result["filepath"],
                    filesize=result["filesize"],
                    ext=result["ext"],
                    completed_at=time.time(),
                )

                # ── Optional: Send to Telegram ────────────────────────────
                if data.get("send_to_telegram") and data.get("telegram_token"):
                    await self._update_job(job_id, status="sending_telegram")
                    try:
                        await send_to_telegram(
                            token=data["telegram_token"],
                            chat_id=data["telegram_chat_id"],
                            filepath=result["filepath"],
                            caption=f"📥 {result['title']}",
                        )
                        await self._update_job(job_id, status="completed", telegram_sent=True)
                    except Exception as tg_err:
                        logger.warning(f"Telegram send failed: {tg_err}")
                        await self._update_job(
                            job_id,
                            status="completed",
                            telegram_error=str(tg_err),
                        )

            except Exception as err:
                logger.error(f"Job {job_id} failed: {err}")
                await self._update_job(job_id, status="failed", error=str(err))

            finally:
                self.active_job_id = None
                self._queue.task_done()
                await self._broadcast({"type": "queue_update", "jobs": self._public_jobs()})

    # ──────────────────────────── Helpers ─────────────────────────────────────

    async def _update_job(self, job_id: str, _broadcast_type: str = "job_update", **fields):
        job = self.jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        await self._broadcast({"type": _broadcast_type, "job": self._strip_private(job)})

    async def _broadcast(self, message: dict):
        dead = []
        payload = json.dumps(message, ensure_ascii=False, default=str)
        for cid, ws in self._ws_clients.items():
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self._ws_clients.pop(cid, None)

    def _public_jobs(self) -> List[dict]:
        return [self._strip_private(j) for j in self.jobs.values()]

    @staticmethod
    def _strip_private(job: dict) -> dict:
        return {k: v for k, v in job.items() if not k.startswith("_")}
