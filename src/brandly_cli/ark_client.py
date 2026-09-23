"""BytePlus Ark API client — Seedream images and Seedance videos.

Features:
- Seedream for image generation (text-to-image, style transfer)
- Seedance for video generation (text-to-video, image-to-video)
- Exponential backoff retry for 429 (rate limit) and 503 (server error)
- Clear error messages for different failure modes
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from rich.console import Console

from brandly_cli.utils import now_iso

console = Console()

ARK_BASE_URL = os.getenv(
    "ARK_BASE_URL",
    "https://ark.cn-beijing.volces.com/api/v3",
)


def _get_api_key() -> str:
    key = os.getenv("ARK_API_KEY")
    if not key:
        raise OSError(
            "ARK_API_KEY environment variable is not set. "
            "Get your API key from BytePlus Ark console and set it:\n"
            "  export ARK_API_KEY=your_key"
        )
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _retry_with_backoff(
    request_func,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Any:
    """Retry an async request with exponential backoff for 429/503 errors."""
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await request_func()
        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code

            if status == 429:  # Rate limit
                wait_time = min(base_delay * (2**attempt), max_delay)
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        pass

                console.print(
                    f"[yellow]⚠ Rate limited (429). "
                    f"Waiting {wait_time:.1f}s before retry "
                    f"{attempt + 1}/{max_retries}...[/yellow]"
                )
                await asyncio.sleep(wait_time)

            elif status == 503:  # Service unavailable
                wait_time = min(base_delay * (2**attempt), max_delay)
                console.print(
                    f"[yellow]⚠ Service unavailable (503). "
                    f"Waiting {wait_time:.1f}s before retry "
                    f"{attempt + 1}/{max_retries}...[/yellow]"
                )
                await asyncio.sleep(wait_time)

            else:
                raise

        except httpx.TimeoutException as e:
            last_error = e
            wait_time = min(base_delay * (2**attempt), max_delay)
            console.print(
                f"[yellow]⚠ Request timeout. "
                f"Waiting {wait_time:.1f}s before retry "
                f"{attempt + 1}/{max_retries}...[/yellow]"
            )
            await asyncio.sleep(wait_time)
        except httpx.NetworkError as e:
            last_error = e
            wait_time = min(base_delay * (2**attempt), max_delay)
            console.print(
                f"[yellow]⚠ Network error: {e}. "
                f"Waiting {wait_time:.1f}s before retry "
                f"{attempt + 1}/{max_retries}...[/yellow]"
            )
            await asyncio.sleep(wait_time)

    if last_error:
        raise last_error


# ---------------------------------------------------------------------------
# Image generation (Seedream)
# ---------------------------------------------------------------------------


async def generate_image(
    prompt: str,
    *,
    model: str = "seedream-4.0",
    size: str = "16:9",
    ratio: str | None = None,
    n: int = 1,
) -> dict[str, Any]:
    """Generate image(s) via BytePlus Ark API (Seedream).

    Args:
        prompt: Text description of the image (apply style presets in the
            caller — this provider stays a dumb transport).
        model: Model ID — "seedream-4.0" or "seedream-3.5".
        size: Aspect ratio — "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3".
        ratio: Alternative aspect ratio format.
        n: Number of images to generate (1-4).
    """

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
    }
    if size:
        body["size"] = size
    if ratio:
        body["ratio"] = ratio

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ARK_BASE_URL}/images/generations",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_with_backoff(_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[red]Error: Rate limit exceeded. Please wait and retry.[/red]")
        elif e.response.status_code == 401:
            console.print("[red]Error: Invalid API key.[/red]")
        elif e.response.status_code == 503:
            console.print("[red]Error: Service temporarily unavailable.[/red]")
        raise

    # Handle response — may be direct URLs or task-based
    results: list[dict[str, Any]] = []
    if "data" in data:
        for item in data["data"]:
            results.append({
                "url": item.get("url"),
                "b64_json": item.get("b64_json"),
                "revised_prompt": item.get("revised_prompt"),
                "model": model,
                "generated_at": now_iso(),
            })
    elif "output" in data and "result" in data["output"]:
        # Some APIs return nested structure
        result_data = data["output"]["result"]
        if isinstance(result_data, list):
            for item in result_data:
                results.append({
                    "url": item.get("url"),
                    "b64_json": item.get("b64_json"),
                    "model": model,
                    "generated_at": now_iso(),
                })
        else:
            results.append({
                "url": result_data.get("url"),
                "b64_json": result_data.get("b64_json"),
                "model": model,
                "generated_at": now_iso(),
            })

    return {
        "urls": [r["url"] for r in results],
        "model": model,
        "results": results,
        "generated_at": now_iso(),
    }


# ---------------------------------------------------------------------------
# Video generation (Seedance)
# ---------------------------------------------------------------------------


async def create_video_task(
    prompt: str,
    *,
    model: str = "seedance-1.0-t2v",
    duration: int = 5,
    aspect_ratio: str = "16:9",
    size: str = "720P",
    seed: int | None = None,
    negative_prompt: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    reference_audios: list[str] | None = None,
) -> dict[str, Any]:
    """Create a video generation task via BytePlus Ark API (Seedance).

    Models:
        seedance-1.0-t2v: Text-to-video generation
        seedance-1.0-i2v: Image-to-video generation

    Args:
        prompt: Text prompt describing the video.
        model: Model ID — "seedance-1.0-t2v" or "seedance-1.0-i2v".
        duration: Video duration in seconds (4-15s typical).
        aspect_ratio: Aspect ratio — "16:9", "9:16", "1:1", "4:3".
        size: Resolution — "720P", "1080P".
        seed: Optional random seed for reproducibility.
        negative_prompt: What to avoid in the video.
        first_frame: URL for first frame image (i2v mode).
        last_frame: URL for last frame image.
        reference_images: URLs for reference images.
        reference_audios: URLs for reference audio.

    Style presets are applied by the caller (prompt layer); historically this
    provider hard-coded the "cinematic" preset — callers now do that explicitly.
    """

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
    }

    # Add aspect ratio
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio

    # Add seed if provided
    if seed is not None:
        body["seed"] = seed

    # Add negative prompt
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    # Add reference images for i2v mode
    if reference_images:
        body["images"] = reference_images

    # Add first/last frame for keyframe mode
    if first_frame:
        body["first_frame"] = first_frame
    if last_frame:
        body["last_frame"] = last_frame

    # Add reference audio
    if reference_audios:
        body["audios"] = reference_audios

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{ARK_BASE_URL}/videos",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_with_backoff(_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[red]Error: Rate limit exceeded. Please wait and retry.[/red]")
        elif e.response.status_code == 401:
            console.print("[red]Error: Invalid API key.[/red]")
        elif e.response.status_code == 503:
            console.print("[red]Error: Service temporarily unavailable.[/red]")
        raise

    return {
        "task_id": data.get("id") or data.get("task_id"),
        "model": model,
        "status": data.get("status", "pending"),
        "progress": data.get("progress", 0),
        "created_at": data.get("created_at"),
    }


async def get_video_status(task_id: str) -> dict[str, Any]:
    """Poll video generation status via BytePlus Ark API."""

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ARK_BASE_URL}/videos/{task_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_with_backoff(_request, max_retries=2, base_delay=2.0, max_delay=10.0)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {
                "task_id": task_id,
                "status": "not_found",
                "error": "Task not found or expired",
            }
        raise

    result: dict[str, Any] = {
        "task_id": data.get("id") or data.get("task_id"),
        "status": data.get("status"),
        "progress": data.get("progress", 0),
        "url": data.get("url") or (data.get("output") or {}).get("url"),
        "model": data.get("model"),
        "duration": data.get("duration"),
    }
    error = data.get("error")
    if isinstance(error, dict):
        result["error"] = error.get("message")
    elif error:
        result["error"] = error
    result["created_at"] = data.get("created_at")
    result["completed_at"] = data.get("completed_at")
    return result


async def poll_video(
    task_id: str,
    *,
    max_wait_seconds: int = 300,
    interval_seconds: int = 5,
) -> dict[str, Any]:
    """Poll until video generation completes or times out."""
    console.print(
        f"[dim]Polling Seedance video status every {interval_seconds}s "
        f"(max {max_wait_seconds}s)...[/dim]"
    )

    deadline = asyncio.get_event_loop().time() + max_wait_seconds
    attempts = 0

    while asyncio.get_event_loop().time() < deadline:
        attempts += 1
        try:
            result = await get_video_status(task_id)

            if result["status"] == "completed":
                console.print(f"[green]✓ Video generated after {attempts} polls[/green]")
                return result
            if result["status"] == "failed":
                raise RuntimeError(
                    f"Seedance video generation failed: {result.get('error') or 'unknown error'}"
                )

            progress = result.get("progress", 0)
            status = result.get("status", "processing")
            console.print(f"  Progress: {progress}% | Status: {status}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                wait_time = min(10 * (2 ** (attempts % 3)), 60)
                console.print(f"[yellow]⚠ API issue, waiting {wait_time}s...[/yellow]")
                await asyncio.sleep(wait_time)
                continue
            raise
        except RuntimeError:
            # Re-raise generated-failure RuntimeError
            raise
        except Exception as e:
            console.print(f"[yellow]⚠ Poll error: {e}, retrying...[/yellow]")
            await asyncio.sleep(interval_seconds)
            continue

        await asyncio.sleep(interval_seconds)

    raise TimeoutError(
        f"Seedance video generation timed out after {max_wait_seconds}s. "
        f"Task ID: {task_id}. Check status manually."
    )


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------


async def list_jobs(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent video generation jobs from BytePlus Ark."""
    async def _request() -> Any:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ARK_BASE_URL}/videos",
                headers=_headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
        jobs = data.get("data", data if isinstance(data, list) else [])
        if isinstance(jobs, dict):
            jobs = jobs.get("jobs", [])
        return [
            {
                "task_id": j.get("id", ""),
                "status": j.get("status", "unknown"),
                "progress": j.get("progress", 0),
                "model": j.get("model", "unknown"),
                "prompt": (j.get("prompt") or "")[:100],
                "created_at": j.get("created_at", ""),
                "completed_at": j.get("completed_at", ""),
            }
            for j in jobs
        ]
    except Exception as e:
        console.print(f"[yellow]⚠ Could not fetch Ark jobs: {e}[/yellow]")
        return []


async def cancel_job(task_id: str) -> dict[str, Any]:
    """Cancel a pending/in-progress video generation job."""
    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{ARK_BASE_URL}/videos/{task_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
        console.print(f"[green]✓ Job {task_id} cancelled.[/green]")
        return {"task_id": task_id, "status": "cancelled", "result": data}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Job {task_id} not found.[/red]")
        elif e.response.status_code == 409:
            console.print(f"[yellow]⚠ Job {task_id} already completed or cancelled.[/yellow]")
        else:
            console.print(f"[red]Error cancelling job: {e}[/red]")
        return {"task_id": task_id, "status": "error", "error": str(e)}
    except Exception as e:
        console.print(f"[red]Error cancelling job: {e}[/red]")
        return {"task_id": task_id, "status": "error", "error": str(e)}
