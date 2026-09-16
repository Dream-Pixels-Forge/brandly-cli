"""Async HTTP client for the Agnes AI API (image + video generation).

Features:
- Exponential backoff retry for 429 (rate limit) and 503 (server error)
- Clear error messages for different failure modes
- Graceful fallback suggestions
"""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from brandly_cli.constants import DEFAULT_AGNES_IMAGE_MODEL
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


def _resolve_image_url(path_or_url: str) -> str:
    """Resolve an image input to a URL the Agnes API can consume.

    - HTTP(S) URLs are returned as-is.
    - Local file paths are base64-encoded into a data: URL.
    - stdin ('-') reads from stdin.
    """
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url

    p = Path(path_or_url)
    if not p.exists():
        console.print(f"[yellow]⚠ Image file not found:[/yellow] {path_or_url}")
        return path_or_url  # let API return a clear error

    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    data = base64.b64encode(p.read_bytes()).decode()
    console.print(f"[dim]Encoded local file: {p.name} ({mime}, {p.stat().st_size // 1024}KB)[/dim]")
    return f"data:{mime};base64,{data}"


def _resolve_image_urls(items: list[str] | None) -> list[str] | None:
    """Resolve a list of image paths/URLs."""
    if not items:
        return None
    return [_resolve_image_url(x) for x in items]


def _compute_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float | None = None,
    response: httpx.Response | None = None,
    *,
    jitter: bool = True,
) -> float:
    """Compute exponential backoff delay with jitter and Retry-After support.

    Args:
        attempt: Current attempt number (0-indexed).
        base_delay: Base delay in seconds (e.g. 1.0).
        max_delay: Maximum delay in seconds; None means no cap.
        response: httpx.Response (optional) — used to read Retry-After header.
        jitter: If True, add randomized variance to avoid thundering herd.

    Returns:
        Delay in seconds to wait before the next retry.
    """
    # Check for Retry-After header first (per RFC 7231)
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass  # fall through to computed delay

    # Exponential backoff: base * 2^attempt
    delay = base_delay * (2 ** attempt)

    # Cap at max_delay if provided
    if max_delay is not None:
        delay = min(delay, max_delay)

    # Add jitter to avoid coordinated retry storms
    if jitter:
        import random

        variance = random.uniform(0.5, 1.5)  # ±50% variance
        delay = delay * variance

    # Ensure at least a minimal wait
    delay = max(delay, 0.1)
    return delay


async def _retry_with_backoff(
    request_func,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
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

            # Compute next-wait using shared helper (jitter + Retry-After)
            wait_time = _compute_backoff_delay(
                attempt,
                base_delay,
                max_delay,
                e.response,
                jitter=jitter,
            )

            if status == 429:  # Rate limit
                # Check for Retry-After header (already handled in helper,
                # but we also print a helpful message)
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
            wait_time = _compute_backoff_delay(
                attempt,
                base_delay,
                max_delay,
                jitter=jitter,
            )
            console.print(
                f"[yellow]⚠ Request timeout. "
                f"Waiting {wait_time:.1f}s before retry "
                f"{attempt + 1}/{max_retries}...[/yellow]"
            )
            await asyncio.sleep(wait_time)
        except httpx.NetworkError as e:
            last_error = e
            wait_time = _compute_backoff_delay(
                attempt,
                base_delay,
                max_delay,
                jitter=jitter,
            )
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
    model: str = DEFAULT_AGNES_IMAGE_MODEL,
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
        body["extra_body"] = {"image": _resolve_image_urls(images), "response_format": "url"}

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
                "[dim]Tip: Agnes free keys allow ~10 RPM for 2K images "
                "(see `brandly rate-limits`). Switch to a smaller size tier "
                "or wait a minute before retrying.[/dim]"
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

    Supports three modes (API accepts these values directly):
    - text: plain text-to-video generation
    - keyframe: transition between first_frame and last_frame images
    - reference: use reference_images/audios to maintain character/object consistency
    """
    from brandly_cli.style_presets import apply_style_preset

    enhanced = apply_style_preset(prompt, "cinematic")
    is_v25_flash = "flash" in model or "2.5-flash" in model

    # API accepts mode values directly: "text", "keyframe", "reference"
    if mode not in ("text", "keyframe", "reference"):
        console.print(f"[yellow]⚠ Unknown mode '{mode}', falling back to 'text'[/yellow]")
        mode = "text"

    body: dict[str, Any] = {
        "model": model,
        "prompt": enhanced,
        "mode": mode,
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

    # Resolve local file paths to data: URLs
    if first_frame:
        first_frame = _resolve_image_url(first_frame)
    if last_frame:
        last_frame = _resolve_image_url(last_frame)
    if reference_images:
        reference_images = _resolve_image_urls(reference_images)

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
        data = await _retry_with_backoff(
            _request,
            max_retries=5,          # Video submission: more attempts for GPU backend
            base_delay=2.0,         # Longer initial wait for transient 503 recovery
            max_delay=120.0,        # Cap at 2min per retry attempt
            jitter=True,            # Avoid thundering herd on retries
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print(
                "[red]Error: Rate limit exceeded. Agnes video 2.5-flash has a 1 req/min rate limit.[/red]"
            )
            console.print(
                "[dim]Tip: Wait at least 60 seconds between requests, or switch to "
                "agnes-video-v2.0 for production use (higher cost, no rate limit).[/dim]"
            )
        elif e.response.status_code == 503:
            console.print(
                "[yellow]Warning: Agnes API returned 503 (service unavailable).[/yellow]"
            )
            console.print(
                "[dim]This is usually a transient issue. The retry logic will wait and retry.[/dim]"
            )
        raise

    return {
        "id": data.get("id"),
        "video_id": data.get("video_id") or data.get("task_id") or data.get("id"),
        "status": data.get("status", "pending"),
        "progress": data.get("progress", 0),
        "created_at": data.get("created_at"),
    }


async def get_video_status(
    video_id: str,
    *,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Poll video generation status with retry for rate limits.

    Args:
        video_id: The video ID to query.
        model_name: Model name for retrieval. Required for keyframe/reference
            modes; optional for text mode. E.g. "agnes-video-2.5-flash".
    """

    async def _request() -> Any:
        params: dict[str, Any] = {"video_id": video_id}
        if model_name:
            params["model_name"] = model_name
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{AGNES_BASE_URL}/agnesapi",
                headers=_headers(),
                params=params,
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
    model_name: str | None = None,
) -> dict[str, Any]:
    """Poll until video generation completes or times out.

    Handles rate limits gracefully by waiting and retrying.

    Args:
        video_id: The video ID to poll.
        model_name: Model name for retrieval (required for keyframe/reference modes).
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
            result = await get_video_status(video_id, model_name=model_name)

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


# ---------------------------------------------------------------------------
# Model catalog (Agnes text / image / video)
# ---------------------------------------------------------------------------

# Agnes text models are OpenAI-compatible: same base URL, /v1/chat/completions.
# The 2.5-flash model is recommended for tool calling / agent workflows
# (512K context, tool-calling support). 2.0-flash (256K) is the fallback.
AGNES_TEXT_MODELS: tuple[str, ...] = (
    "agnes-2.5-flash",
    "agnes-2.0-flash",
    "agnes-1.5-flash",
)
DEFAULT_TEXT_MODEL = "agnes-2.5-flash"


def list_text_models() -> list[dict[str, str]]:
    """Return the catalog of Agnes text/agent models with their specs.

    Mirrors the public model catalog (2026.07.30) so the CLI can surface them
    without a network round-trip.
    """
    return [
        {
            "id": "agnes-2.5-flash",
            "context": "512K",
            "max_output": "65.5K",
            "use": "tool calling, coding, agent workflows, multimodal",
        },
        {
            "id": "agnes-2.0-flash",
            "context": "256K",
            "max_output": "64K",
            "use": "coding, reasoning, agents, vision input, tool calling",
        },
        {
            "id": "agnes-1.5-flash",
            "context": "256K",
            "max_output": "64K",
            "use": "fast chat, low-latency content, simple multimodal",
        },
    ]


# ---------------------------------------------------------------------------
# Chat completion + tool calling (OpenAI-compatible /v1/chat/completions)
# ---------------------------------------------------------------------------

async def chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str = DEFAULT_TEXT_MODEL,
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_format: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a single OpenAI-compatible chat completion against Agnes.

    Args:
        messages: List of message dicts ({"role": "system"|"user"|"assistant", "content": ...}).
            Tool results are appended with role="tool" and the ``tool_call_id``.
        model: Agnes text model ID (defaults to agnes-2.5-flash).
        tools: Optional list of OpenAI-format tool definitions::

            [
                {"type": "function", "function": {
                    "name": ..., "description": ..., "parameters": {...}
                }}
            ]

        temperature: Sampling temperature (model default when None).
        max_tokens: Cap on generated tokens.
        response_format: Optional {"type": "json_object"} for structured output.

    Returns the raw completion dict (``choices[0].message`` and friends).
    """
    body: dict[str, Any] = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if response_format is not None:
        body["response_format"] = response_format

    async def _request() -> Any:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{AGNES_BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    try:
        return await _retry_with_backoff(_request, max_retries=3, base_delay=1.0)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[red]Error: Agnes chat rate limit exceeded. Retry shortly.[/red]")
        elif e.response.status_code == 503:
            console.print("[red]Error: Agnes chat API temporarily unavailable.[/red]")
        raise


def _build_tools_payload(
    tools: list[tuple[str, Any, dict[str, Any], str]] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalise a tool spec list into the OpenAI ``tools`` payload.

    Accepts either:
      - pre-shaped OpenAI tool dicts (pass through unchanged), or
      - 4-tuples ``(name, handler, json_schema, description)`` (handlers are
        ignored here; the loop keeps them separately).
    """
    out: list[dict[str, Any]] = []
    for t in tools:
        if isinstance(t, dict):
            # Already an OpenAI-format tool dict — but strip any "handler" key.
            out.append({k: v for k, v in t.items() if k != "handler"})
        else:
            name, _handler, schema, description = t
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": schema,
                    },
                }
            )
    return out


async def agent_tool_loop(
    messages: list[dict[str, Any]],
    tools: list[tuple[str, Any, dict[str, Any], str]],
    *,
    model: str = DEFAULT_TEXT_MODEL,
    max_iterations: int = 6,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Run a multi-turn agent loop where Agnes can call client-side tools.

    ``tools`` is a list of ``(name, handler, json_schema, description)``
    tuples — the shape produced by :func:`brandly_cli.agent_tools.get_builtin_tools`.
    The ``handler`` is invoked locally (sync or async) with JSON args; its
    result is JSON-stringified and appended as a ``tool``-role message so the
    model can reason over it.

    Returns the final assistant message dict plus metadata:
        {"content": ..., "tool_calls": [...], "iterations": N, "messages": [...]}
    """
    tools_payload = _build_tools_payload(tools)
    handlers: dict[str, Any] = {t[0]: t[1] for t in tools}

    working = list(messages)
    history: list[dict[str, Any]] = []
    last_message: dict[str, Any] = {}

    for iteration in range(1, max_iterations + 1):
        data = await chat_completion(
            working,
            model=model,
            tools=tools_payload or None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        last_message = msg
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            return {
                "content": content,
                "model": model,
                "iterations": iteration,
                "messages": working + [msg],
            }

        # Append the assistant's tool-calling turn
        working.append(msg)
        for call in tool_calls:
            fn = call.get("function") or {}
            fn_name = fn.get("name", "")
            raw_args = fn.get("arguments") or "{}"
            try:
                import json as _json

                args = _json.loads(raw_args) if raw_args else {}
            except ValueError:
                args = {"raw": raw_args}

            result: Any
            if fn_name in handlers:
                try:
                    result = handlers[fn_name](**args)
                    if hasattr(result, "__await__"):
                        result = await result
                except Exception as exc:  # pragma: no cover - defensive
                    result = {"error": str(exc)}
            else:
                result = {"error": f"unknown tool: {fn_name}"}

            # Stringify for the model
            from brandly_cli.agent_tools import to_json

            tool_payload = to_json(result)
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "name": fn_name,
                    "content": tool_payload,
                }
            )
            working.append(

                {
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": tool_payload,
                }
            )

    # Exhausted iterations — return the last assistant message.
    return {
        "content": last_message.get("content") or "(max tool iterations reached)",
        "model": model,
        "iterations": max_iterations,
        "messages": working,
    }
