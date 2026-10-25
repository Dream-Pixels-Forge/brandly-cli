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


class ProviderRouter:
    """Router that wraps multiple video backends with automatic failover.

    Tries backends in priority order. On failure (transient error, rate
    limit, or provider outage), automatically falls back to the next
    backend. Tracks cost per backend for quota-aware planning.

    Example::

        router = ProviderRouter(
            backends=[
                (AgnesVideoBackend(), 1),      # primary
                (ArkVideoBackend(), 2),        # fallback 1
                (SeedanceVideoBackend(), 3),   # fallback 2
            ]
        )
        result = await router.submit(prompt="...", model="agnes-video-2.5-flash", ...)
    """

    def __init__(self, backends: list[tuple[VideoBackend, int]]) -> None:
        """Initialize the router with a list of (backend, priority) tuples.

        Lower priority number = higher priority. The first backend (priority 1)
        is tried first; on failure, the router falls back to priority 2, etc.
        """
        self._backends = sorted(backends, key=lambda b: b[1])
        self._cost_tracker: dict[str, float] = {  # backend_name -> credits spent
            b[0].__class__.__name__: 0.0 for b in self._backends
        }

    @property
    def backends(self) -> list[VideoBackend]:
        """Return backends in priority order."""
        return [b for b, _ in self._backends]

    def capabilities(self) -> VideoBackendCapabilities:
        """Return the intersection of all backend capabilities.

        The router can only do what ALL backends support, so we take the
        minimum of each capability across all backends.
        """
        if not self._backends:
            return VideoBackendCapabilities(
                max_duration_seconds=0,
                reliable_duration_seconds=0,
                rate_limit_rpm=0,
                supports_keyframe_mode=False,
                supports_reference_mode=False,
                supports_text_mode=False,
            )

        caps_list = [b.capabilities() for b, _ in self._backends]
        return VideoBackendCapabilities(
            max_duration_seconds=min(c.max_duration_seconds for c in caps_list),
            reliable_duration_seconds=min(c.reliable_duration_seconds for c in caps_list),
            rate_limit_rpm=min(c.rate_limit_rpm for c in caps_list),
            supports_keyframe_mode=all(c.supports_keyframe_mode for c in caps_list),
            supports_reference_mode=all(c.supports_reference_mode for c in caps_list),
            supports_text_mode=all(c.supports_text_mode for c in caps_list),
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
        """Submit a video generation task, trying backends in priority order.

        On failure (transient error, rate limit, or provider outage),
        automatically falls back to the next backend. The first successful
        submission wins.
        """
        last_error: Exception | None = None
        for backend, _priority in self._backends:
            try:
                result = await backend.submit(
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
                return result
            except Exception as e:
                last_error = e
                continue
        # All backends failed
        raise RuntimeError(
            f"All video backends failed. Last error: {last_error}"
        ) from last_error

    async def poll(
        self,
        video_id: str,
        *,
        max_wait_seconds: int = 300,
        interval_seconds: int = 5,
        model_name: str | None = None,
    ) -> VideoTaskResult:
        """Poll a video generation task.

        The backend to poll is determined by the video_id prefix (the first
        segment before the first hyphen encodes the backend name).
        """
        # Extract backend name from video_id prefix
        backend_name = video_id.split("-")[0]
        backend = self._find_backend_by_name(backend_name)
        if backend is None:
            raise ValueError(
                f"No backend found for video_id {video_id!r} "
                f"(expected prefix matching a backend name)"
            )
        return await backend.poll(
            video_id=video_id,
            max_wait_seconds=max_wait_seconds,
            interval_seconds=interval_seconds,
            model_name=model_name,
        )

    async def fetch(self, video_id: str) -> bytes:
        """Fetch a video's raw bytes.

        The backend to fetch from is determined by the video_id prefix.
        """
        backend_name = video_id.split("-")[0]
        backend = self._find_backend_by_name(backend_name)
        if backend is None:
            raise ValueError(
                f"No backend found for video_id {video_id!r} "
                f"(expected prefix matching a backend name)"
            )
        return await backend.fetch(video_id=video_id)

    def _find_backend_by_name(self, name: str) -> VideoBackend | None:
        """Find a backend by its class name."""
        for backend, _ in self._backends:
            if backend.__class__.__name__ == name:
                return backend
        return None


__all__ = [
    "VideoBackend",
    "VideoBackendCapabilities",
    "VideoTaskResult",
    "AgnesVideoBackend",
    "ProviderRouter",
]
