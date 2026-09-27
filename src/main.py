from asyncio import create_task, gather, sleep
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from os import getenv
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory, gettempdir
from time import time
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, RedirectResponse
from loguru import logger
from starlette.background import BackgroundTask
from yt_dlp import YoutubeDL, match_filter_func

load_dotenv()

DEFAULT_MAX_DURATION = getenv("MAX_DURATION")
DEFAULT_MAX_FILESIZE = getenv("MAX_FILESIZE")
DEFAULT_FORMAT = getenv("FORMAT")
DEFAULT_FORMAT_SORT = getenv("FORMAT_SORT")

TEMP_ROOT = Path(gettempdir()) / "ytdlp-rest-api"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
MAX_TEMP_AGE = 24 * 60 * 60
CLEANUP_INTERVAL = 24 * 60 * 60


def remove_expired_downloads() -> None:
    cutoff = time() - MAX_TEMP_AGE
    for path in TEMP_ROOT.iterdir():
        if path.is_dir() and path.stat().st_mtime < cutoff:
            rmtree(path, ignore_errors=True)


async def cleanup_loop() -> None:
    while True:
        remove_expired_downloads()
        await sleep(CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    cleanup_task = create_task(cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        await gather(cleanup_task, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


@app.get("/download")
def download(
    video_url: str,
    max_duration: int | None = DEFAULT_MAX_DURATION,
    max_filesize_mb: int | None = DEFAULT_MAX_FILESIZE,
    format: str | None = DEFAULT_FORMAT,
    format_sort: str | None = DEFAULT_FORMAT_SORT,
) -> Response:
    logger.info(f"[{video_url}] Received request")
    request_id = str(uuid4())
    target_dir = TemporaryDirectory(prefix=f"{request_id}-", dir=TEMP_ROOT)
    target_path = Path(target_dir.name) / request_id
    try:
        params = video_params(max_duration, max_filesize_mb, format, format_sort)
        result = download_file(video_url, target_path, params, max_filesize_mb)
        return prepare_response(video_url, result, target_dir)
    except Exception:
        target_dir.cleanup()
        raise


def prepare_response(
    video_url: str,
    result: Path | str | None,
    target_dir: TemporaryDirectory,
) -> Response:
    if not result:
        raise HTTPException(status_code=404, detail="No media found")
    if isinstance(result, Path):
        logger.info(f"[{video_url}] Sending file response [{result}]")
        return FileResponse(result, background=BackgroundTask(target_dir.cleanup))
    logger.info(f"[{video_url}] Redirecting to thumbnail [{result}]")
    target_dir.cleanup()
    return RedirectResponse(url=result) if result else None


def video_params(
    max_duration: int | None,
    max_filesize_mb: int | None,
    format: str | None,
    format_sort: str | None,
) -> dict[str, Any]:
    params = {}
    if match_filter := prepare_match_filter(max_duration, max_filesize_mb):
        params["match_filter"] = match_filter_func(match_filter)
    if format is not None:
        params["format"] = format
    if format_sort is not None:
        params["format_sort"] = [format_sort]
    return params


def prepare_match_filter(max_duration: int | None, max_filesize_mb: int | None) -> str:
    match_filter = [
        f"duration<={max_duration}" if max_duration else None,
        f"filesize<={max_filesize_mb}M?" if max_filesize_mb else None,
        # "filesize" only applies to individual downloaded files.
        # If final file is merged from multiple others, then it can exceed this limit.
        # However, this is handled by a file size check after the download.
        # It's still useful to avoid downloading obviously too large files.
    ]
    return " & ".join(filter(None, match_filter))


def download_file(
    video_url: str,
    target_path: Path,
    params: dict[str, Any],
    max_filesize_mb: int | None = None,
) -> Path | str | None:
    result: Path | None = None

    def capture_path(path: str) -> None:
        nonlocal result
        result = Path(path)

    final_params = {
        "outtmpl": f"{target_path}.%(ext)s",
        "post_hooks": [capture_path],
        **params,
    }
    with YoutubeDL(final_params) as ytdl:
        info = ytdl.extract_info(video_url, download=True)
    if result and result.is_file() and size_matches(result, max_filesize_mb):
        return result
    return info.get("thumbnail")


def size_matches(file: Path, max_size: int | None) -> bool:
    return max_size is None or (file.stat().st_size / 1_000_000) <= max_size
