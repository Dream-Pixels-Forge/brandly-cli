"""Video backend protocol for pluggable video generation providers.

This module defines the VideoBackend protocol that all video generation
providers must implement. This enables the provider seam (G14) where
different backends (Agnes, Ark, local models, etc.) can be swapped
without changing the shot_runner or other pipeline code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class VideoBackendCapabilities:
    """Capability descriptor for a video backend.

    These capabilities drive:
    - G7's split_long_shots policy (uses reliable_duration_seconds)
    - G13's quota-aware planning (uses reliable_duration_seconds for avg_shot_duration)
    - G7's duration clamping (uses max_duration_seconds)
    """
    max_duration_seconds: int
    reliable_duration_seconds: int
    rate_limit_rpm: int
    supports_keyframe_mode: bool = True
    supports_reference_mode: bool = True
    supports_text_mode: bool = True


@dataclass(frozen=True)
class VideoTaskResult:
    """Result of a video generation task."""
    video_id: str
    status: str
    url: str | None = None
    progress: int = 0
    error: str | None = None
    metadata: dict[str, Any] | None = None


@runtime_checkable
class VideoBackend(Protocol):
    """Protocol for video generation backends.

    All video generation providers must implement this protocol.
    """

    def capabilities(self) -> VideoBackendCapabilities:
        """Return the capability descriptor for this backend."""
        ...

    async def submit(
        self,
        *,
        prompt: str,
        model: str,
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
        reference_roles: list[str] | None = None,
    ) -> VideoTaskResult:
        """Submit a video generation task."""
        ...

    async def poll(
        self,
        video_id: str,
        *,
        max_wait_seconds: int = 300,
        interval_seconds: int = 5,
        model_name: str | None = None,
    ) -> VideoTaskResult:
        """Poll until video generation completes or times out."""
        ...

    async def fetch(self, video_id: str) -> bytes:
        """Fetch the generated video clip as bytes."""
        ...


# ---------------------------------------------------------------------------
# Agnes implementation (the default backend)
# ---------------------------------------------------------------------------

class AgnesVideoBackend:
    """Agnes AI video backend implementation."""

    def capabilities(self) -> VideoBackendCapabilities:
        return VideoBackendCapabilities(
            max_duration_seconds=12,
            reliable_duration_seconds=8,
            rate_limit_rpm=1,
            supports_keyframe_mode=True,
            supports_reference_mode=True,
            supports_text_mode=True,
        )

    async def submit(
        self,
        *,
        prompt: str,
        model: str,
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
        reference_roles: list[str] | None = None,
    ) -> VideoTaskResult:
        from brandly_cli.agnes_client import create_video_task

        result = await create_video_task(
            prompt=prompt,
            model=model,
            mode=mode,
            duration=duration,
            aspect_ratio=aspect_ratio,
            size=size,
            seed=seed,
            negative_prompt=negative_prompt,
            first_frame=first_frame,
            last_frame=last_frame,
            reference_images=reference_images,
            reference_audios=reference_audios,
            reference_roles=reference_roles,
        )

        return VideoTaskResult(
            video_id=result.get("video_id", ""),
            status=result.get("status", "pending"),
            url=result.get("url"),
            progress=result.get("progress", 0),
            error=result.get("error"),
            metadata=result,
        )

    async def poll(
        self,
        video_id: str,
        *,
        max_wait_seconds: int = 300,
        interval_seconds: int = 5,
        model_name: str | None = None,
    ) -> VideoTaskResult:
        from brandly_cli.agnes_client import poll_video

        result = await poll_video(
            video_id,
            max_wait_seconds=max_wait_seconds,
            interval_seconds=interval_seconds,
            model_name=model_name,
        )

        return VideoTaskResult(
            video_id=result.get("video_id", video_id),
            status=result.get("status", "unknown"),
            url=result.get("url"),
            progress=result.get("progress", 0),
            error=result.get("error"),
            metadata=result,
        )

    async def fetch(self, video_id: str) -> bytes:
        from brandly_cli.agnes_client import get_video_status
        result = await get_video_status(video_id)
        url = result.get("url") or (result.get("metadata", {}) or {}).get("url")
        if not url:
            raise RuntimeError(f"No URL available for video {video_id}")

        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content


__all__ = [
    "VideoBackend",
    "VideoBackendCapabilities",
    "VideoTaskResult",
    "AgnesVideoBackend",
]
