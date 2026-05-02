"""Local media storage helpers for Telegram-admin uploads."""

import asyncio
import hashlib
import inspect
from mimetypes import guess_extension
from os import getenv
from pathlib import Path
from shutil import copyfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from aiogram.types import Message

from src.shared.errors import ValidationError


_DEFAULT_CONTENT_TYPE = "image/png"


def _data_dir() -> Path:
    """Return the configured data directory."""

    return Path(getenv("YUQA_DATA_DIR", "data/yuqa")).expanduser()


def _extension(content_type: str, original_name: str | None = None) -> str:
    """Choose a filesystem extension for a stored media file."""

    if original_name:
        suffix = Path(original_name).suffix
        if suffix:
            return suffix.lower()
    if content_type == "image/jpeg":
        return ".jpg"
    return guess_extension(content_type.partition(";")[0].strip()) or ".bin"


def _stored_relative_path(
    folder: str,
    source_key: str,
    content_type: str,
    original_name: str | None = None,
) -> Path:
    """Build a deterministic relative storage path for one media source."""

    digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:24]
    return Path("media") / folder / f"{digest}{_extension(content_type, original_name)}"


def _existing_local_path(source: str) -> Path | None:
    """Resolve an existing local path from absolute, cwd-relative, or data-dir-relative input."""

    path = Path(source).expanduser()
    candidates = [path]
    if not path.is_absolute():
        candidates.append(_data_dir() / path)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    parsed = urlparse(source)
    if parsed.scheme == "file":
        candidate = Path(parsed.path)
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _download_url(url: str, destination: Path) -> str | None:
    """Download a URL into a local destination and return its content type."""

    request = Request(url, headers={"User-Agent": "yuqa-bot/1.0"})
    with urlopen(request, timeout=20) as response:
        content_type = response.headers.get_content_type()
        destination.write_bytes(response.read())
        return content_type


async def _maybe_await(value):
    """Await aiogram APIs while keeping fake test bots simple."""

    if inspect.isawaitable(value):
        return await value
    return value


async def _download_telegram_file(bot, file_id: str, destination: Path) -> None:
    """Download a Telegram file id using the available bot API shape."""

    if bot is None:
        raise RuntimeError("Telegram bot is not available for media download")
    if hasattr(bot, "download"):
        await _maybe_await(bot.download(file_id, destination=destination))
        return
    if hasattr(bot, "get_file") and hasattr(bot, "download_file"):
        file_info = await _maybe_await(bot.get_file(file_id))
        file_path = getattr(file_info, "file_path", None)
        if not file_path:
            raise RuntimeError("Telegram file path is missing")
        await _maybe_await(bot.download_file(file_path, destination=destination))
        return
    raise RuntimeError("Telegram bot does not support file downloads")


async def _store_media_source(
    source: str,
    folder: str,
    *,
    content_type: str = _DEFAULT_CONTENT_TYPE,
    original_name: str | None = None,
    bot=None,
) -> tuple[str, str]:
    """Persist one media source locally and return its relative storage key."""

    parsed = urlparse(source)
    local_source = _existing_local_path(source)
    relative_path = _stored_relative_path(folder, source, content_type, original_name)
    destination = _data_dir() / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if local_source is not None:
        if local_source.resolve() != destination.resolve():
            copyfile(local_source, destination)
        return relative_path.as_posix(), content_type
    if parsed.scheme in {"http", "https"}:
        try:
            downloaded_type = await asyncio.to_thread(
                _download_url, source, destination
            )
        except OSError as error:
            raise ValidationError("could not store media locally") from error
        return relative_path.as_posix(), downloaded_type or content_type
    try:
        await _download_telegram_file(bot, source, destination)
    except RuntimeError as error:
        if bot is not None:
            raise ValidationError("could not store media locally") from error
        return source, content_type
    return relative_path.as_posix(), content_type


async def local_media_from_message(
    message: Message,
    folder: str,
) -> tuple[str | None, str]:
    """Extract media from a message and store it under the local data directory."""

    bot = getattr(message, "bot", None)
    photo = getattr(message, "photo", None) or []
    if photo:
        item = photo[-1]
        file_id = getattr(item, "file_id", None)
        if file_id:
            return await _store_media_source(
                file_id,
                folder,
                content_type="image/jpeg",
                bot=bot,
            )
    video = getattr(message, "video", None)
    if video is not None:
        file_id = getattr(video, "file_id", None)
        if file_id:
            content_type = getattr(video, "mime_type", "video/mp4")
            return await _store_media_source(
                file_id,
                folder,
                content_type=content_type,
                original_name=getattr(video, "file_name", None),
                bot=bot,
            )
    document = getattr(message, "document", None)
    if document is not None:
        file_id = getattr(document, "file_id", None)
        if file_id:
            content_type = getattr(document, "mime_type", "application/octet-stream")
            return await _store_media_source(
                file_id,
                folder,
                content_type=content_type,
                original_name=getattr(document, "file_name", None),
                bot=bot,
            )
    text = (message.text or "").strip()
    if not text:
        return None, _DEFAULT_CONTENT_TYPE
    content_type = (
        "video/mp4"
        if text.lower().endswith((".mp4", ".mov", ".webm"))
        else _DEFAULT_CONTENT_TYPE
    )
    return await _store_media_source(text, folder, content_type=content_type, bot=bot)


__all__ = ["local_media_from_message"]
