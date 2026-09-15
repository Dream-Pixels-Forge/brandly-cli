"""MiniMax AI API client — images, video, and job management."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from rich.console import Console

console = Console()

MINIMAX_BASE_URL = os.getenv(
    "MINIMAX_BASE_URL",
    "https://api.minimax.io",
)


def _get_api_key() -> str:
    key = os.getenv("MINIMAX_API_KEY")
    if not key:
        raise OSError(
            "MINIMAX_API_KEY environment variable is not set. "
            "Get your API key from https://platform.minimax.io and set it:\n"
            "  export MINIMAX_API_KEY=your_key"
        )
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------


async def generate_image(
    prompt: str,
    *,
    model: str = "image-01",
    aspect_ratio: str = "16:9",
    width: int | None = None,
    height: int | None = None,
    response_format: str = "url",
    n: int = 1,
    subject_reference: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Generate image(s) via MiniMax API.

    Args:
        prompt: Text description of the image (max 1500 chars).
        model: Model ID — "image-01" or "image-01-live".
        aspect_ratio: One of 1:1, 16:9, 4:3, 3:2, 2:3, 3:4, 9:16, 21:9.
        width: Image width in px (512-2048, divisible by 8). Required with height.
        height: Image height in px. Required with width.
        response_format: "url" or "base64".
        n: Number of images to generate (1-9).
        subject_reference: List of subject reference dicts for i2i.
            [{"type": "character", "image_file": "<url>"}]
    """
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt[:1500],
        "aspect_ratio": aspect_ratio,
        "response_format": response_format,
        "n": n,
    }
    if width and height:
        body["width"] = width
        body["height"] = height
    if subject_reference:
        body["subject_reference"] = subject_reference

    async def _request() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{MINIMAX_BASE_URL}/v1/image_generation",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: MiniMax API key invalid or expired.[/red]")
        elif e.response.status_code == 429:
            console.print("[red]Error: MiniMax rate limit exceeded. Please wait and retry.[/red]")
        else:
            console.print(f"[red]Error: MiniMax API error ({e.response.status_code})[/red]")
        raise

    image_urls = data.get("data", {}).get("image_urls", [])
    failed_count = int(data.get("metadata", {}).get("failed_count", 0))
    success_count = int(data.get("metadata", {}).get("success_count", 0))

    return {
        "id": data.get("id", ""),
        "model": model,
        "urls": image_urls,
        "success_count": success_count,
        "failed_count": failed_count,
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------


async def create_video_task(
    prompt: str,
    *,
    model: str = "MiniMax-H3",
    resolution: str = "768P",
    duration: int = 5,
    ratio: str = "adaptive",
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    reference_videos: list[str] | None = None,
    reference_audios: list[str] | None = None,
) -> dict[str, Any]:
    """Create a video generation task via MiniMax API.

    MiniMax H3 generates video with **synchronized native stereo audio** in the
    same inference pass — no separate audio flag is needed. Direct sound via
    the prompt's [sound] element (e.g. "footsteps on wet concrete, rain, no
    dialogue"). Reference audio (voice clone / music) goes in via
    ``reference_audios``.

    Models:
        MiniMax-H3: Full multimodal input (first/last frame, reference
            video/audio) | Resolution: 480P, 768P, 2K | Duration: 4-15s
        MiniMax-H3-Max: Fast; first/last frame only (no reference video/audio)
            Resolution: 480P, 768P | Duration: 5-15s

    Args:
        prompt: Text prompt (max 7000 chars). Include a [sound] element to
            direct native audio.
        model: "MiniMax-H3" or "MiniMax-H3-Max".
        resolution: "480P", "768P", or "2K" (H3-Max caps at 768P).
        duration: Video duration in seconds (H3: 4-15, H3-Max: 5-15).
        ratio: Aspect ratio — adaptive, 21:9, 16:9, 4:3, 1:1, 3:4, 9:16.
        first_frame: URL for first frame image.
        last_frame: URL for last frame image.
        reference_images: URLs for reference images.
        reference_videos: URLs for reference videos (H3 only, not H3-Max).
        reference_audios: URLs for reference audio (H3 only, not H3-Max).
    """
    is_h3_max = "H3-Max" in model
    valid_resolutions = {"480P", "768P", "2K"} if not is_h3_max else {"480P", "768P"}
    if resolution not in valid_resolutions:
        resolution = "768P"

    # H3-Max supports only T2V + first/last-frame I2V — no reference video/audio
    effective_ref_vids: list[str] | None = None if is_h3_max else reference_videos
    effective_ref_auds: list[str] | None = None if is_h3_max else reference_audios

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt[:7000]}]

    if first_frame:
        content.append({"type": "image_url", "url": first_frame, "role": "first_frame"})
    if last_frame:
        content.append({"type": "image_url", "url": last_frame, "role": "last_frame"})
    if reference_images:
        for img_url in reference_images:
            content.append({"type": "image_url", "url": img_url, "role": "reference_image"})
    if effective_ref_vids:
        for vid_url in effective_ref_vids:
            content.append({"type": "video_url", "url": vid_url, "role": "reference_video"})
    if effective_ref_auds:
        for aud_url in effective_ref_auds:
            content.append({"type": "audio_url", "url": aud_url, "role": "reference_audio"})

    # Clamp duration to model-specific range
    min_dur = 5 if is_h3_max else 4
    max_dur = 15
    clamped_dur = max(min_dur, min(max_dur, duration))

    body: dict[str, Any] = {
        "model": model,
        "content": content,
        "resolution": resolution,
        "duration": clamped_dur,
    }
    if ratio:
        body["ratio"] = ratio

    async def _request() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{MINIMAX_BASE_URL}/v2/video_generation",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: MiniMax API key invalid or expired.[/red]")
        elif e.response.status_code == 429:
            console.print("[red]Error: MiniMax rate limit exceeded. Please wait and retry.[/red]")
        else:
            console.print(f"[red]Error: MiniMax API error ({e.response.status_code})[/red]")
        raise

    task_id = data.get("task_id", "")
    return {
        "task_id": task_id,
        "model": model,
        "status": "pending",
        "created_at": _now_iso(),
    }


async def get_video_status(task_id: str) -> dict[str, Any]:
    """Poll video generation status via MiniMax API."""
    async def _request() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{MINIMAX_BASE_URL}/v2/query/video_generation/{task_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {
                "task_id": task_id,
                "status": "not_found",
                "error": "Task not found or expired (tasks older than 7 days are not queryable)",
            }
        raise

    task = data.get("task", {})
    status = task.get("status", "unknown")
    content = task.get("content", {})

    return {
        "task_id": task_id,
        "status": status,
        "progress": 100 if status in ("succeeded", "failed", "cancelled") else 0,
        "url": content.get("url"),
        "model": task.get("model"),
        "resolution": task.get("resolution"),
        "duration": task.get("duration"),
        "ratio": task.get("ratio"),
        "error": _format_error(task),
        "created_at": _timestamp_to_iso(task.get("created_at")),
        "updated_at": _timestamp_to_iso(task.get("updated_at")),
    }


async def poll_video(
    task_id: str,
    *,
    max_wait_seconds: int = 600,
    interval_seconds: int = 5,
) -> dict[str, Any]:
    """Poll until MiniMax video generation completes or times out."""
    console.print(
        f"[dim]Polling MiniMax video status every {interval_seconds}s "
        f"(max {max_wait_seconds}s)...[/dim]"
    )

    deadline = asyncio.get_event_loop().time() + max_wait_seconds
    attempts = 0

    while asyncio.get_event_loop().time() < deadline:
        attempts += 1
        try:
            result = await get_video_status(task_id)
            status = result["status"]

            if status == "succeeded":
                console.print(f"[green]✓ Video generated after {attempts} polls[/green]")
                return result
            if status in ("failed", "cancelled"):
                raise RuntimeError(
                    f"MiniMax video generation {status}: {result.get('error')}"
                )

            console.print(f"  Progress: {result.get('progress', 0)}% | Status: {status}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429,):
                wait_time = min(10 * (2 ** (attempts % 3)), 60)
                console.print(f"[yellow]⚠ Rate limited, waiting {wait_time}s...[/yellow]")
                await asyncio.sleep(wait_time)
                continue
            raise
        except Exception as e:
            console.print(f"[yellow]⚠ Poll error: {e}, retrying...[/yellow]")
            await asyncio.sleep(interval_seconds)
            continue

        await asyncio.sleep(interval_seconds)

    raise TimeoutError(
        f"MiniMax video generation timed out after {max_wait_seconds}s. "
        f"Task ID: {task_id}"
    )


async def list_jobs(
    *,
    status: str | None = None,
    limit: int = 20,
    page: int = 1,
) -> list[dict[str, Any]]:
    """List recent MiniMax video generation jobs."""
    async def _request() -> dict[str, Any]:
        params: dict[str, Any] = {"page_num": page, "page_size": limit}
        if status:
            params["filter.status"] = status
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{MINIMAX_BASE_URL}/v2/query/video_generation",
                headers=_headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
        items = data.get("items", [])
        return [
            {
                "task_id": item.get("id", ""),
                "status": item.get("status", "unknown"),
                "progress": (
                    100 if item.get("status") in ("succeeded", "failed", "cancelled")
                    else 0
                ),
                "model": item.get("model", ""),
                "resolution": item.get("resolution", ""),
                "duration": item.get("duration"),
                "url": (item.get("content") or {}).get("url", ""),
                "created_at": _timestamp_to_iso(item.get("created_at")),
            }
            for item in items
        ]
    except Exception as e:
        console.print(f"[yellow]⚠ Could not fetch MiniMax jobs: {e}[/yellow]")
        return []


def _format_error(task: dict[str, Any]) -> str | None:
    """Extract error message from task response."""
    error = task.get("error")
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        return error.get("message")
    return None


def _timestamp_to_iso(ts: int | None) -> str:
    """Convert Unix timestamp to ISO format string."""
    if not ts:
        return ""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc).isoformat()
