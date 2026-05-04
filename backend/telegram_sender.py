"""
telegram_sender.py — Direct Telegram upload for Sahhab Pro
Sends video/audio/photo directly from server to Telegram chat/channel.
No download required on the user's device.
"""

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_FILE_LIMIT = 50 * 1024 * 1024  # 50 MB Telegram bot limit

VIDEO_EXTS  = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp"}
PHOTO_EXTS  = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUDIO_EXTS  = {".mp3", ".m4a", ".ogg", ".wav", ".flac", ".aac"}
GIF_EXTS    = {".gif"}


async def verify_bot(token: str) -> dict:
    """Returns bot info or raises on bad token."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
    data = r.json()
    if not data.get("ok"):
        raise ValueError(f"توكن خاطئ: {data.get('description', 'Unknown')}")
    return data["result"]


async def send_to_telegram(
    token: str,
    chat_id: str,
    filepath: str,
    caption: str = "",
) -> bool:
    """
    Upload a local file to a Telegram chat/channel.
    Automatically picks the right method (sendVideo / sendPhoto / sendAudio / sendDocument).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError("الملف غير موجود على السيرفر")

    size = path.stat().st_size
    if size > TELEGRAM_FILE_LIMIT:
        raise ValueError(
            f"حجم الملف {_fmt_size(size)} يتجاوز الحد المسموح به (50 MB) لبوتات تيليجرام"
        )

    ext = path.suffix.lower()
    safe_caption = (caption or "")[:1024]

    base_url = f"https://api.telegram.org/bot{token}"
    common_data = {"chat_id": chat_id, "caption": safe_caption}

    async with httpx.AsyncClient(timeout=180) as client:
        with open(filepath, "rb") as fh:
            if ext in VIDEO_EXTS:
                endpoint = f"{base_url}/sendVideo"
                files = {"video": (path.name, fh, "video/mp4")}
                data = {**common_data, "supports_streaming": "true"}
            elif ext in GIF_EXTS:
                endpoint = f"{base_url}/sendAnimation"
                files = {"animation": (path.name, fh, "image/gif")}
                data = common_data
            elif ext in PHOTO_EXTS:
                endpoint = f"{base_url}/sendPhoto"
                files = {"photo": (path.name, fh, "image/jpeg")}
                data = common_data
            elif ext in AUDIO_EXTS:
                endpoint = f"{base_url}/sendAudio"
                files = {"audio": (path.name, fh, "audio/mpeg")}
                data = common_data
            else:
                endpoint = f"{base_url}/sendDocument"
                files = {"document": (path.name, fh, "application/octet-stream")}
                data = common_data

            response = await client.post(endpoint, data=data, files=files)

    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"خطأ تيليجرام: {result.get('description', 'Unknown error')}")

    logger.info(f"Telegram send OK → chat={chat_id} file={path.name}")
    return True


def _fmt_size(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024**3:.1f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024**2:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"
