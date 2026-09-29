"""Async HTTP client for the Agnes AI API (image + video generation).

Features:
- Backoff retry for transient errors (429 + docs "retry later" 5xx)
- 503 body classification (permanent vs routing vs transient, issue #148)
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

from brandly_cli.constants import DEFAULT_AGNES_IMAGE_MODEL, DEFAULT_AGNES_VIDEO_MODEL
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

    # Issue #24/#20: shrink large local images (PNG plates, multi-MB files)
    # to webp/jpeg before base64-encoding. No-op for small/remote files;
    # disable with BRANDLY_IMAGE_CONVERT=off.
    from brandly_cli.image_convert import maybe_convert

    converted = maybe_convert(path_or_url)
    if converted.startswith("data:"):
        console.print(f"[dim]Converted to smaller format: {p.name}[/dim]")
        return converted

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


#: Agnes error codes that are request problems dressed up as a 503 — waiting
#: never fixes them (docs + observed gateway bodies, issue #148).
_PERMANENT_503_CODES = frozenset(
    {"invalid_request", "authentication_error", "permission_error", "billing_error"}
)

#: 503 bodies that only state gateway ROUTING state ("no available channel
#: for model"). Live probes (2026-09-29): a WRONG model name and a CHANNEL
#: OUTAGE for a correct model produce the same body — disambiguate against
#: GET /v1/models (issue #148).
_ROUTING_503_CODES = frozenset({"model_not_found"})

#: GET /v1/models cache TTL in seconds.
_MODEL_CATALOG_TTL_SECONDS = 300.0
_model_catalog_cache: tuple[float, list[str]] | None = None


def _parse_error_body(text: str) -> dict[str, Any]:
    """Normalize every observed Agnes/gateway error body shape.

    Returns ``{"code": str | None, "message": str, "request_id": str | None}``.

    Observed shapes (live probes, 2026-09-29):
    - nested:    ``{"error": {"code": "model_not_found", "message": "..."}}``
    - top level: ``{"code": "invalid_request", "message": "...", "data": {...}}``
    - FastAPI:   ``{"detail": "..."}`` (no code)
    - non-JSON gateway pages -> ``code=None``, message = raw text

    ``code`` may arrive as an int (the 404 probe returned ``"code": 404``)
    and is normalized to a lowercase string so callers can do membership
    checks without an AttributeError.
    """
    import json as _json
    import re as _re

    if not isinstance(text, str):  # defensive: mock/partial responses
        text = str(text)
    code: Any = None
    message: Any = text
    request_id: str | None = None
    try:
        payload = _json.loads(text)
    except (ValueError, TypeError):
        payload = None
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            message = err.get("message") or message
        elif "code" in payload:
            code = payload.get("code")
            message = payload.get("message") or message
        elif "detail" in payload:
            detail = payload.get("detail")
            message = detail if isinstance(detail, str) else _json.dumps(detail)
        elif "message" in payload:
            message = payload.get("message") or message
    msg = message if isinstance(message, str) else _json.dumps(message)
    m = _re.search(r"request id:\s*([A-Za-z0-9]+)", msg, _re.IGNORECASE)
    if m:
        request_id = m.group(1)
    return {
        "code": str(code).lower() if code is not None else None,
        "message": msg,
        "request_id": request_id,
    }


async def _model_catalog() -> list[str] | None:
    """Model ids from ``GET /v1/models``, cached for ~5 minutes.

    Returns ``None`` when the catalog cannot be fetched — callers fail open
    to "transient" (the docs list "failed to fetch the model list" as a 503
    cause, so a failed lookup must not itself fail the run).
    """
    global _model_catalog_cache
    import time as _time

    if (
        _model_catalog_cache is not None
        and _time.monotonic() - _model_catalog_cache[0] < _MODEL_CATALOG_TTL_SECONDS
    ):
        return _model_catalog_cache[1]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{AGNES_BASE_URL}/models", headers=_headers())
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None  # fail-open by design
    items = data.get("data") if isinstance(data, dict) else data
    ids: list[str] = []
    if isinstance(items, list):
        ids = [i["id"] for i in items if isinstance(i, dict) and isinstance(i.get("id"), str)]
    _model_catalog_cache = (_time.monotonic(), ids)
    return ids


def _classify_status(status: int, parsed: dict[str, Any]) -> str:
    """Route an HTTP error: "retry", "permanent" or "check_catalog".

    - 503 with a semantic request code -> permanent (never retryable).
    - 503 with routing state (model_not_found / "no available channel" /
      no code at all) -> verify the model against GET /v1/models.
    - 429 and every 5xx -> transient "retry later" per the docs (issue #150).
    - everything else (4xx and below) -> permanent.
    """
    if status == 503:
        code = parsed["code"]
        if code in _PERMANENT_503_CODES:
            return "permanent"
        if (
            code in _ROUTING_503_CODES
            or code is None
            or "no available channel" in parsed["message"].lower()
        ):
            return "check_catalog"
        return "retry"  # unknown 503 code (e.g. service_unavailable)
    if status == 429 or status >= 500:
        return "retry"
    return "permanent"


def _print_exhausted(error: Exception, attempts: int, elapsed: float) -> None:
    """Final line after the budget is spent: attempts, elapsed, body, request id."""
    if isinstance(error, httpx.HTTPStatusError):
        resp = error.response
        body = (resp.text or "").strip()
        detail = body[:500] if body else "(empty body)"
        request_id = _parse_error_body(body).get("request_id")
        rid = f"; request id: {request_id}" if request_id else ""
        console.print(
            f"[red]✗ HTTP {resp.status_code}: {detail}{rid} — "
            f"gave up after {attempts} attempts over {elapsed:.1f}s.[/red]"
        )
    else:
        console.print(
            f"[red]✗ {error} — gave up after {attempts} attempts "
            f"over {elapsed:.1f}s.[/red]"
        )


async def _retry_with_backoff(
    request_func,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    min_429_delay: float = 0.0,
    model: str | None = None,
) -> Any:
    """Retry an async request with exponential backoff for transient errors.

    Retries 429 and every 5xx the docs classify as "retry later"
    (500/502/503/504/520/522/524). Non-retryable 4xx — and 503 bodies
    carrying a semantic request error (``invalid_request`` etc.) — raise
    immediately with the response body surfaced.

    Routing-class 503s ("no available channel for model") are checked
    against ``GET /v1/models`` when ``model`` is given: in the catalog =>
    transient outage (retry), not in the catalog => permanent, with the
    available models in the message. No model, or a failed catalog fetch =>
    fail open to transient (issue #148).

    Waits only BETWEEN attempts — never after the final one — and the
    exhaustion line reports attempts, elapsed time, body and request id
    (issue #149).

    ``min_429_delay`` floors the wait on 429 (e.g. 60.0 for 1 req/min).
    """
    last_error: Exception | None = None
    attempts = 0
    import time as _time

    started = _time.monotonic()

    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        try:
            return await request_func()
        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code
            body_text = e.response.text or ""
            parsed = _parse_error_body(body_text)
            verdict = _classify_status(status, parsed)

            if verdict == "check_catalog":
                if model is None:
                    verdict = "retry"  # no model to check against -> fail open
                else:
                    catalog = await _model_catalog()
                    if catalog is not None and model not in catalog:
                        hint = (
                            f"model {model!r} is not offered by this endpoint "
                            f"(available: {', '.join(catalog[:12]) or 'none'})"
                        )
                        if parsed["request_id"]:
                            hint += f"; request id: {parsed['request_id']}"
                        detail = body_text.strip()[:500] or "(empty body)"
                        console.print(
                            f"[red]✗ Permanent error ({hint}): {detail} — not retrying.[/red]"
                        )
                        raise
                    verdict = "retry"  # in catalog, or catalog unknown -> transient

            if verdict == "permanent":
                detail = body_text.strip()[:500] or "(empty body)"
                hint = (
                    f"Agnes error code={parsed['code']!r}: {parsed['message'][:200]}"
                    if parsed["code"]
                    else f"HTTP {status}"
                )
                console.print(
                    f"[red]✗ Permanent error ({hint}): {detail} — not retrying.[/red]"
                )
                raise

            # Retryable HTTP status.
            wait_time = _compute_backoff_delay(
                attempt, base_delay, max_delay, e.response, jitter=jitter
            )
            if status == 429:
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        pass
                if min_429_delay > 0 and wait_time < min_429_delay:
                    wait_time = min_429_delay
                label = "Rate limited (429)"
            else:
                label = f"Transient server error (HTTP {status})"

            if attempt >= max_retries:
                break  # budget spent — never sleep after the final attempt
            console.print(
                f"[yellow]⚠ {label}. Waiting {wait_time:.1f}s before retry "
                f"{attempt + 1}/{max_retries}...[/yellow]"
            )
            await asyncio.sleep(wait_time)

        except httpx.TimeoutException as e:
            last_error = e
            if attempt >= max_retries:
                break
            wait_time = _compute_backoff_delay(
                attempt, base_delay, max_delay, jitter=jitter
            )
            console.print(
                f"[yellow]⚠ Request timeout. Waiting {wait_time:.1f}s before retry "
                f"{attempt + 1}/{max_retries}...[/yellow]"
            )
            await asyncio.sleep(wait_time)
        except httpx.NetworkError as e:
            last_error = e
            if attempt >= max_retries:
                break
            wait_time = _compute_backoff_delay(
                attempt, base_delay, max_delay, jitter=jitter
            )
            console.print(
                f"[yellow]⚠ Network error: {e}. Waiting {wait_time:.1f}s before retry "
                f"{attempt + 1}/{max_retries}...[/yellow]"
            )
            await asyncio.sleep(wait_time)

    # All retries exhausted
    if last_error:
        _print_exhausted(last_error, attempts, _time.monotonic() - started)
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
) -> dict[str, Any]:
    """Generate an image via Agnes AI and return {url, revised_prompt}.

    Note: The Agnes API does not support negative_prompt — accuracy is
    achieved through prompt engineering via style presets. Style presets are
    applied by the caller (prompt layer, ``style_presets.apply_style_preset``);
    this provider stays a dumb transport.
    """

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
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
        data = await _retry_with_backoff(_request, model=model)
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


def infer_video_mode(
    *,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    reference_audios: list[str] | None = None,
) -> str:
    """Infer the video generation mode from the inputs actually provided.

    - ``keyframe``  — a start/first frame (or end/last frame) is provided.
    - ``reference`` — reference image(s) and/or audio(s) are provided
      (character/object consistency; the API accepts either or both).
    - ``text``      — plain text-to-video, no image inputs.
    """
    if first_frame or last_frame:
        return "keyframe"
    if reference_images or reference_audios:
        return "reference"
    return "text"


#: Issue #124: monotonic timestamp of the last video create POST. The
#: provider counts every create against its 1 request/minute window - even
#: failed ones - so short internal 503 backoffs self-saturate the limiter.
_LAST_VIDEO_CREATE_AT: float | None = None

#: Agnes video create endpoint: 1 request/minute (matches --interval default).
MIN_VIDEO_CREATE_GAP_SECONDS = 60.0


async def _enforce_video_create_spacing(gap: float | None = None) -> None:
    """Wait until the provider's create window has room (issue #124).

    Called before EVERY video create POST - including internal 503 retries
    and shot-level retries - so two creates can never land inside the
    1 req/min window. A fresh process (no prior create) never waits.
    """
    global _LAST_VIDEO_CREATE_AT
    import time

    min_gap = MIN_VIDEO_CREATE_GAP_SECONDS if gap is None else gap
    now = time.monotonic()
    if _LAST_VIDEO_CREATE_AT is not None and now - _LAST_VIDEO_CREATE_AT < min_gap:
        wait = min_gap - (now - _LAST_VIDEO_CREATE_AT)
        await asyncio.sleep(wait)
    _LAST_VIDEO_CREATE_AT = time.monotonic()


#: Issue #160: Flash create constraints (Agnes Video 2.5 Flash docs,
#: 2026-09-29). The server validates these BEFORE task creation, queueing,
#: and billing - mirroring them client-side gives a clear error and never
#: burns a slot in the 1-req/min create window (issue #124).
AGNES_VIDEO_ASPECT_RATIOS = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
MAX_REFERENCE_IMAGES = 5
MAX_REFERENCE_AUDIOS = 3


def _validate_flash_create(
    *,
    model: str,
    size: str | None,
    aspect_ratio: str | None,
    reference_images: list[str] | None,
    reference_audios: list[str] | None,
) -> None:
    """Raise ``ValueError`` naming the exact violated Flash rule.

    Checks run in the server's documented precedence: size -> images ->
    audios, then the common aspect_ratio constraint. Non-Flash models are
    left untouched so future models are not constrained by Flash limits.
    """
    if model != "agnes-video-2.5-flash":
        return
    if size and size != "720P":
        raise ValueError(f"size must be 720P (Agnes Video 2.5 Flash got {size!r})")
    if reference_images and len(reference_images) > MAX_REFERENCE_IMAGES:
        raise ValueError(
            f"images length must not exceed {MAX_REFERENCE_IMAGES} "
            f"(got {len(reference_images)})"
        )
    if reference_audios and len(reference_audios) > MAX_REFERENCE_AUDIOS:
        raise ValueError(
            f"audios length must not exceed {MAX_REFERENCE_AUDIOS} "
            f"(got {len(reference_audios)})"
        )
    if aspect_ratio and aspect_ratio not in AGNES_VIDEO_ASPECT_RATIOS:
        raise ValueError(
            f"aspect_ratio {aspect_ratio!r} is not supported; "
            f"use one of: {', '.join(AGNES_VIDEO_ASPECT_RATIOS)}"
        )


async def create_video_task(
    prompt: str,
    *,
    model: str = DEFAULT_AGNES_VIDEO_MODEL,
    mode: str = "auto",
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

    Supported modes (the API accepts these values directly):
    - text: plain text-to-video generation (no image inputs)
    - keyframe: transition between first_frame and last_frame images
    - reference: use reference_images/audios to maintain character/object consistency

    ``mode="auto"`` (the default) infers the mode from the inputs:
    keyframe when a start/end frame is provided, reference when reference
    images are provided, otherwise text.

    Style presets (issue #21) are applied by the caller — e.g. the CLI passes
    ``"cinematic"`` only when the requested style is cinematic; this provider
    no longer imports the prompt layer.
    """
    _validate_flash_create(
        model=model,
        size=size,
        aspect_ratio=aspect_ratio,
        reference_images=reference_images,
        reference_audios=reference_audios,
    )
    if mode == "auto":
        mode = infer_video_mode(
            first_frame=first_frame,
            last_frame=last_frame,
            reference_images=reference_images,
            reference_audios=reference_audios,
        )
    if mode not in ("text", "keyframe", "reference"):
        console.print(f"[yellow]⚠ Unknown mode '{mode}', falling back to 'text'[/yellow]")
        mode = "text"

    # Guard: warn if the chosen mode is missing its required inputs, and
    # degrade to text so the task can still be created.
    if mode == "keyframe" and not first_frame and not last_frame:
        console.print(
            "[yellow]⚠ Keyframe mode needs --first-frame or --last-frame; "
            "falling back to text mode.[/yellow]"
        )
        mode = "text"
    elif mode == "reference" and not reference_images and not reference_audios:
        console.print(
            "[yellow]⚠ Reference mode needs reference images or audios; "
            "falling back to text mode.[/yellow]"
        )
        mode = "text"

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
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
    body["prompt"] = prompt + consistency_hint

    # Video 2.5 Flash workflow: duration 4-12s, 720P
    body["seconds"] = str(max(4, min(12, duration or 5)))
    body["size"] = size or "720P"
    body["aspect_ratio"] = aspect_ratio

    # Resolve local file paths to data: URLs
    if first_frame:
        first_frame = _resolve_image_url(first_frame)
    if last_frame:
        last_frame = _resolve_image_url(last_frame)
    if reference_images:
        reference_images = _resolve_image_urls(reference_images)

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
        # Issue #158: the API binds reference media through <Picture N> /
        # <Audio N> tokens referenced from the prompt (1-based, array order;
        # doc examples: "Use ... in <Picture 1> as reference",
        # "Use <Audio 1> as the rhythm and ambience reference").
        binding_sentences: list[str] = []
        if reference_images:
            pictures = ", ".join(
                f"<Picture {i}>" for i in range(1, len(reference_images) + 1)
            )
            binding_sentences.append(
                f"Use {pictures} as reference: preserve exact appearance, "
                "lighting, and composition from the provided reference image(s)."
            )
        if reference_audios:
            audios = ", ".join(f"<Audio {i}>" for i in range(1, len(reference_audios) + 1))
            binding_sentences.append(
                f"Use {audios} as reference: match rhythm, ambience, and sound "
                "character from the provided reference audio(s)."
            )
        if binding_sentences:
            body["prompt"] += "\n\n" + " ".join(binding_sentences)

    async def _request() -> Any:
        # Issue #124: space every create attempt >= MIN_VIDEO_CREATE_GAP_SECONDS
        # apart - across shot retries AND internal attempts.
        await _enforce_video_create_spacing()
        # 180s: large reference payloads (even after webp/jpeg conversion)
        # need headroom on the slow create endpoint (issue #24).
        async with httpx.AsyncClient(timeout=180) as client:
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
            # Issue #151: fail fast + park — 3 spaced attempts (~3 min max);
            # long outages are handled by --park-after, not by burning the
            # whole run inside the client (60s spacing x 6 attempts was 6+ min).
            max_retries=2,          # => 3 attempts total
            base_delay=2.0,         # Longer initial wait for transient 503 recovery
            max_delay=120.0,        # Cap at 2min per retry attempt
            jitter=True,            # Avoid thundering herd on retries
            min_429_delay=60.0,     # 1 req/min limit on create endpoint
            model=model,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print(
                "[red]Error: Rate limit exceeded. Agnes video 2.5-flash has a 1 req/min rate limit.[/red]"
            )
            console.print(
                "[dim]Tip: Wait at least 60 seconds between requests.[/dim]"
            )
            raise
        elif e.response.status_code == 503:
            # Advice only — no claims about attempts (a 503 may be permanent
            # and fail after a single POST, see issue #148).
            console.print(
                "[dim]For a long outage, rerun with --continue-on-fail "
                "--park-after 3: the run parks after 3 consecutive failed shots "
                "with a resume hint (brandly job-resume).[/dim]"
            )
        raise

    return {
        "id": data.get("id"),
        "video_id": data.get("video_id") or data.get("task_id") or data.get("id"),
        "status": data.get("status", "pending"),
        "progress": data.get("progress", 0),
        "mode": mode,
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
        data = await _retry_with_backoff(
            _request, max_retries=2, base_delay=2.0, max_delay=10.0, model=model_name
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[yellow]⚠ Rate limited while polling. Will retry shortly...[/yellow]")
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
            # 429 and any 5xx are transient per the docs (issue #150) — a
            # 500/502/504 mid-poll must not kill --wait/produce while the
            # async task keeps running server-side.
            if e.response.status_code == 429 or 500 <= e.response.status_code <= 599:
                # Monotonic backoff, capped: 10, 20, 40, 60, 60, ... (was a
                # non-monotonic 10 * 2 ** (attempts % 3) cycle).
                wait_time = min(10 * (2 ** min(attempts - 1, 3)), 60)
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
        f"Task ID: {video_id}. Check status manually with: brandly job-resume {video_id}"
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
    except httpx.HTTPStatusError as e:
        # Issue #19: the default Agnes base URL does not expose GET /videos
        # — degrade gracefully instead of warning about a 404.
        if e.response.status_code == 404:
            console.print(
                "[dim]Job listing is not supported on this Agnes endpoint "
                f"({AGNES_BASE_URL}). Use 'brandly job-resume <video_id>' "
                "instead.[/dim]"
            )
            return []
        console.print(f"[yellow]⚠ Could not fetch jobs: {e}[/yellow]")
        return []
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
        return await _retry_with_backoff(_request, max_retries=3, base_delay=1.0, model=model)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            console.print("[red]Error: Agnes chat rate limit exceeded. Retry shortly.[/red]")
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
            from brandly_cli.job_polling import to_json

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
