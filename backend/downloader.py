"""
downloader.py — yt-dlp wrapper for Sahhab Pro
Supports: YouTube, TikTok, Instagram, Snapchat, Twitter/X, Facebook, and 1000+ sites
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def _get_format_string(quality: str) -> str:
    formats = {
        "best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
        "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "480p":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
        "360p":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
        "audio": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio",
    }
    return formats.get(quality, formats["best"])


def _common_opts() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    }


async def download_url(
    url: str,
    job_id: str,
    quality: str = "best",
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Download a single video/image URL.
    Returns metadata dict including filepath.
    """
    loop = asyncio.get_event_loop()
    output_template = str(DOWNLOAD_DIR / f"{job_id}_%(title).60s.%(ext)s")

    def _progress_hook(d: dict):
        if progress_callback is None:
            return
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            percent = (downloaded / total * 100) if total else 0
            asyncio.run_coroutine_threadsafe(
                progress_callback(round(percent, 1), speed), loop
            )
        elif d["status"] == "finished":
            asyncio.run_coroutine_threadsafe(progress_callback(99.0, 0), loop)

    ydl_opts = {
        **_common_opts(),
        "format": _get_format_string(quality),
        "outtmpl": output_template,
        "progress_hooks": [_progress_hook],
        "noplaylist": True,
        "merge_output_format": "mp4",
        "postprocessors": [],
    }

    def _do_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    try:
        info = await loop.run_in_executor(None, _do_download)
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"فشل التحميل: {e}") from e
    except Exception as e:
        raise RuntimeError(f"خطأ غير متوقع: {e}") from e

    # Locate the actual file written to disk
    files = sorted(DOWNLOAD_DIR.glob(f"{job_id}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    filepath = str(files[0]) if files else None
    filesize = files[0].stat().st_size if files else 0

    return {
        "title":     info.get("title") or "بدون عنوان",
        "thumbnail": info.get("thumbnail"),
        "duration":  info.get("duration"),
        "uploader":  info.get("uploader") or info.get("channel"),
        "platform":  info.get("extractor_key") or info.get("extractor"),
        "filepath":  filepath,
        "filesize":  filesize,
        "ext":       info.get("ext") or (files[0].suffix.lstrip(".") if files else ""),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "webpage_url": info.get("webpage_url") or url,
    }


async def fetch_profile_videos(url: str, max_videos: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch video list from a user profile / channel / playlist.
    Returns list of video metadata (no download).
    """
    loop = asyncio.get_event_loop()

    ydl_opts = {
        **_common_opts(),
        "extract_flat": "in_playlist",
        "playlistend":  max_videos,
        "noplaylist":   False,
    }

    def _do_fetch():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await loop.run_in_executor(None, _do_fetch)
    except Exception as e:
        raise RuntimeError(f"فشل جلب الحساب: {e}") from e

    entries = info.get("entries") or []

    if not entries:
        # Possibly a single video URL
        return [{
            "url":       url,
            "title":     info.get("title") or "فيديو واحد",
            "thumbnail": info.get("thumbnail"),
            "duration":  info.get("duration"),
            "uploader":  info.get("uploader") or info.get("channel"),
            "id":        info.get("id"),
        }]

    result = []
    for e in entries:
        if not e:
            continue
        # Reconstruct full URL when only ID is available
        vid_url = (
            e.get("url")
            or e.get("webpage_url")
            or _build_url(e, info)
        )
        thumb = e.get("thumbnail")
        if not thumb and e.get("thumbnails"):
            thumb = e["thumbnails"][-1].get("url")

        result.append({
            "url":      vid_url,
            "title":    e.get("title") or "بدون عنوان",
            "thumbnail": thumb,
            "duration": e.get("duration"),
            "uploader": e.get("uploader") or info.get("uploader") or info.get("channel"),
            "id":       e.get("id"),
            "view_count": e.get("view_count"),
        })

    return result


def _build_url(entry: dict, parent_info: dict) -> str:
    extractor = parent_info.get("extractor_key", "").lower()
    vid_id = entry.get("id", "")
    if "youtube" in extractor:
        return f"https://www.youtube.com/watch?v={vid_id}"
    if "tiktok" in extractor:
        return f"https://www.tiktok.com/@/video/{vid_id}"
    return vid_id
