"""Async HTTP client for the Agnes AI API (image + video generation).

Features:
- Exponential backoff retry for 429 (rate limit) and 503 (server error)
- Clear error messages for different failure modes
- Graceful fallback suggestions
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from rich.console import Console

from brandly_cli.utils import now_iso

console = Console()

AGNES_BASE_URL = os.getenv(
    "AGNES_BASE_URL",
    "https://apihub.agnes-ai.com/v1",
)


def _get_api_key() -> str:
    key = os.getenv("AGNES_API_KEY")
    if not key:
        raise OSError(
            "AGNES_API_KEY environment variable is not set. "
            "Get your API key from https://apihub.agnes-ai.com and set it:\n"
            "  export AGNES_API_KEY=your_key"
        )
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


async def _retry_with_backoff(
    request_func,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Any:
    """Retry an async request with exponential backoff for 429/503 errors.

    Non-retryable conditions (4xx with semantic error codes like
    ``model_not_found``) are raised immediately so the user gets a clear
    error rather than burning 4 attempts on something that will never work.

    Returns the response on success or raises the last error.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await request_func()
        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code
            body_text = e.response.text or ""

            # Agnes quirk: model_not_found / invalid_request / etc. are
            # returned as 503 with a JSON body containing the real reason.
            # Detect these and don't waste retries on them.
            is_permanent = False
            permanent_hint = ""
            if status in (400, 403, 404, 422):
                is_permanent = True
                permanent_hint = f"HTTP {status}"
            elif status == 503:
                # Try to detect "not actually a transient outage" bodies
                try:
                    import json as _json

                    payload = _json.loads(body_text)
                    err = payload.get("error", {}) if isinstance(payload, dict) else {}
                    code = (err.get("code") or "").lower() if isinstance(err, dict) else ""
                    msg = err.get("message") or "" if isinstance(err, dict) else ""
                    if code in (
                        "model_not_found",
                        "invalid_request",
                        "authentication_error",
                        "permission_error",
                        "billing_error",
                    ):
                        is_permanent = True
                        permanent_hint = f"Agnes error code={code!r}: {msg[:200]}"
                except (ValueError, AttributeError):
                    pass

            if is_permanent:
                # Real semantic error, not a transient outage
                console.print(
                    f"[red]✗ Permanent error ({permanent_hint}) — not retrying.[/red]"
                )
                raise

            if status == 429:  # Rate limit
                wait_time = min(base_delay * (2**attempt), max_delay)
                # Check for Retry-After header
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

            elif status == 503:  # Service unavailable (genuine)
                wait_time = min(base_delay * (2**attempt), max_delay)
                console.print(
                    f"[yellow]⚠ Service unavailable (503). "
                    f"Waiting {wait_time:.1f}s before retry "
                    f"{attempt + 1}/{max_retries}...[/yellow]"
                )
                await asyncio.sleep(wait_time)

            else:
                # Other 5xx, or other status — raise immediately
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

    # All retries exhausted
    if last_error:
        raise last_error


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------


async def generate_image(
    prompt: str,
    *,
    model: str = "agnes-image-2.1-flash",
    size: str = "2K",
    ratio: str = "16:9",
    images: list[str] | None = None,
    style_preset: str | None = None,
) -> dict[str, Any]:
    """Generate an image via Agnes AI and return {url, revised_prompt}.

    Note: The Agnes API does not support negative_prompt — accuracy is
    achieved through prompt engineering via style presets.
    """
    from brandly_cli.style_presets import apply_style_preset

    enhanced = apply_style_preset(prompt, style_preset) if style_preset else prompt

    body: dict[str, Any] = {
        "model": model,
        "prompt": enhanced,
        "size": size,
    }
    if ratio:
        body["ratio"] = ratio
    if images:
        body["extra_body"] = {"image": images, "response_format": "url"}

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{AGNES_BASE_URL}/images/generations",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_with_backoff(_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print(
                "[red]Error: Rate limit exceeded. Please wait a moment and try again.[/red]"
            )
            console.print(
                "[dim]Tip: Use v2.0 model for production (2.5-flash is rate-limited)[/dim]"
            )
        elif e.response.status_code == 503:
            console.print(
                "[red]Error: Agnes API is temporarily unavailable. Please try again later.[/red]"
            )
        raise

    item = data.get("data", [{}])[0]
    return {
        "url": item.get("url"),
        "b64_json": item.get("b64_json"),
        "revised_prompt": item.get("revised_prompt"),
        "model": model,
        "generated_at": now_iso(),
    }


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------


async def create_video_task(
    prompt: str,
    *,
    model: str = "agnes-video-v2.0",
    mode: str = "text",
    duration: int | None = None,
    aspect_ratio: str = "16:9",
    size: str = "720P",
    seed: int | None = None,
    negative_prompt: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    reference_audios: list[str] | None = None,
) -> dict[str, Any]:
    """Create a video generation task and return {id, video_id, status, progress}.

    Supports three modes:
    - text: plain text-to-video generation (maps to API mode 'ti2vid')
    - keyframe: transition between first_frame and last_frame images (maps to 'keyframes')
    - reference: use reference_images to maintain character/object consistency
      (maps to 'multi_reference')
    """
    from brandly_cli.style_presets import apply_style_preset

    enhanced = apply_style_preset(prompt, "cinematic")
    is_v25_flash = "flash" in model or "2.5-flash" in model

    # Map CLI modes to API modes
    mode_map = {"text": "ti2vid", "keyframe": "keyframes", "reference": "multi_reference"}
    api_mode = mode_map.get(mode, "ti2vid")

    body: dict[str, Any] = {
        "model": model,
        "prompt": enhanced,
        "mode": api_mode,
    }
    if seed is not None:
        body["seed"] = seed

    # Build style suffix to enforce consistency
    consistency_hint = (
        "\n\nCharacter consistency notes: Maintain identical appearance, clothing, "
        "and physical features across all shots. No identity drift. Same object "
        "properties (color, texture, size) in every frame."
    )
    body["prompt"] = enhanced + consistency_hint

    if is_v25_flash:
        # Video 2.5 Flash: duration 4-12s, size fixed at 720P
        body["seconds"] = str(max(4, min(12, duration or 5)))
        body["size"] = "720P"
        body["aspect_ratio"] = aspect_ratio
        if mode == "keyframe":
            if first_frame:
                body["first_frame"] = first_frame
            if last_frame:
                body["last_frame"] = last_frame
        elif mode == "reference":
            if reference_images:
                body["images"] = reference_images
            if reference_audios:
                body["audios"] = reference_audios
            # Add reference hint for consistency
            body["prompt"] += (
                "\n\nReference image anchored: Preserve exact appearance, lighting, "
                "and composition from the provided reference image(s)."
            )
    else:
        # v2.0 style (legacy)
        frame_count = min(441, (duration or 5) * 24) + 1 if duration else 121
        body["num_frames"] = frame_count
        body["frame_rate"] = 24
        if aspect_ratio:
            body["ratio"] = aspect_ratio
        if mode == "keyframe" and reference_images:
            body["extra_body"] = {"image": reference_images, "mode": "keyframes"}
        elif mode == "reference" and reference_images:
            body["extra_body"] = {"image": reference_images, "mode": "multi_reference"}
        elif reference_images:
            body["image"] = reference_images[0]
            body["prompt"] += (
                "\n\nReference image anchored: Preserve exact appearance, lighting, "
                "and composition from the provided reference image."
            )

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{AGNES_BASE_URL}/videos",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_with_backoff(_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[red]Error: Rate limit exceeded. Using v2.0 model recommended.[/red]")
            console.print("[dim]Tip: Switch to agnes-video-v2.0 for production use[/dim]")
        elif e.response.status_code == 503:
            console.print(
                "[red]Error: Agnes API is temporarily unavailable. Please try again later.[/red]"
            )
        raise

    return {
        "id": data.get("id"),
        "video_id": data.get("video_id") or data.get("task_id") or data.get("id"),
        "status": data.get("status", "pending"),
        "progress": data.get("progress", 0),
        "created_at": data.get("created_at"),
    }


async def get_video_status(video_id: str) -> dict[str, Any]:
    """Poll video generation status with retry for rate limits."""

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{AGNES_BASE_URL}/agnesapi",
                headers=_headers(),
                params={"video_id": video_id},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_with_backoff(_request, max_retries=2, base_delay=2.0, max_delay=10.0)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[yellow]⚠ Rate limited while polling. Will retry shortly...[/yellow]")
        elif e.response.status_code == 503:
            console.print("[yellow]⚠ Service unavailable. Will retry shortly...[/yellow]")
        raise

    error_obj = data.get("error")
    error_msg = (
        error_obj
        if isinstance(error_obj, str)
        else (error_obj or {}).get("message")
        if isinstance(error_obj, dict)
        else None
    )

    return {
        "id": data.get("id"),
        "video_id": data.get("video_id") or data.get("task_id") or data.get("id"),
        "status": data.get("status"),
        "progress": data.get("progress", 0),
        "url": data.get("url") or (data.get("metadata") or {}).get("url"),
        "error": error_msg,
        "created_at": data.get("created_at"),
        "completed_at": data.get("completed_at"),
    }


async def poll_video(
    video_id: str,
    *,
    max_wait_seconds: int = 300,
    interval_seconds: int = 5,
) -> dict[str, Any]:
    """Poll until video generation completes or times out.

    Handles rate limits gracefully by waiting and retrying.
    """
    import asyncio

    console.print(
        f"[dim]Polling video status every {interval_seconds}s (max {max_wait_seconds}s)...[/dim]"
    )

    deadline = asyncio.get_event_loop().time() + max_wait_seconds
    attempts = 0

    while asyncio.get_event_loop().time() < deadline:
        attempts += 1
        try:
            result = await get_video_status(video_id)

            if result["status"] == "completed":
                console.print(f"[green]✓ Video generated after {attempts} polls[/green]")
                return result
            if result["status"] == "failed":
                raise RuntimeError(
                    f"Agnes video generation failed: {result.get('error') or 'unknown error'}"
                )

            # Show progress
            progress = result.get("progress", 0)
            status = result.get("status", "processing")
            console.print(f"  Progress: {progress}% | Status: {status}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                # Rate limit or service error - wait and continue
                wait_time = min(10 * (2 ** (attempts % 3)), 60)
                console.print(f"[yellow]⚠ API issue, waiting {wait_time}s...[/yellow]")
                await asyncio.sleep(wait_time)
                continue
            raise
        except RuntimeError:
            # Re-raise generated-failure RuntimeError from above; don't swallow it
            raise
        except Exception as e:
            # Other errors - wait and retry
            console.print(f"[yellow]⚠ Poll error: {e}, retrying...[/yellow]")
            await asyncio.sleep(interval_seconds)
            continue

        # Normal progression - wait for next poll
        await asyncio.sleep(interval_seconds)

    raise TimeoutError(
        f"Agnes video generation timed out after {max_wait_seconds}s. "
        f"Task ID: {video_id}. Check status manually with: brandly status {video_id}"
    )


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------

async def list_jobs(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent video generation jobs from the Agnes API."""
    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            params: dict[str, Any] = {"limit": limit}
            if status:
                params["status"] = status
            resp = await client.get(
                f"{AGNES_BASE_URL}/videos",
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
                "id": j.get("id", ""),
                "video_id": j.get("video_id") or j.get("task_id") or j.get("id", ""),
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
        console.print(f"[yellow]⚠ Could not fetch jobs: {e}[/yellow]")
        return []


async def cancel_job(video_id: str) -> dict[str, Any]:
    """Cancel a pending/in-progress video generation job."""
    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{AGNES_BASE_URL}/videos/{video_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _request()
        console.print(f"[green]✓ Job {video_id} cancelled.[/green]")
        return {"video_id": video_id, "status": "cancelled", "result": data}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Job {video_id} not found.[/red]")
        elif e.response.status_code == 409:
            console.print(f"[yellow]⚠ Job {video_id} already completed or cancelled.[/yellow]")
        else:
            console.print(f"[red]Error cancelling job: {e}[/red]")
        return {"video_id": video_id, "status": "error", "error": str(e)}
    except Exception as e:
        console.print(f"[red]Error cancelling job: {e}[/red]")
        return {"video_id": video_id, "status": "error", "error": str(e)}
