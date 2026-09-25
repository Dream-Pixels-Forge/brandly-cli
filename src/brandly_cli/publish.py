"""G6: publish path (decision record DEV-G6-001) — dry-run first, live only
with explicitly stored credentials.

One platform at a time: YouTube is the first adapter; TikTok/Instagram are
follow-ups behind the same :data:`ADAPTERS` interface. The dry-run path
builds the exact request payload and never touches the network; live
execution requires a credential stored via ``brandly config set``
(user-level store, never in project files or ``.env`` — see F2).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Protocol


class Adapter(Protocol):
    """A platform publish adapter: pure payload builder + live executor."""

    platform: str

    def build_payload(
        self,
        video: Path,
        *,
        title: str,
        description: str,
        schedule_iso: str | None,
    ) -> dict[str, Any]:
        """Build the exact request payload (pure — no I/O)."""
        ...

    def execute(self, payload: dict[str, Any], token: str) -> dict[str, Any]:
        """POST the payload live. Only called when a credential is present."""
        ...


def _schedule_zulu(schedule_iso: str | None) -> str | None:
    """Normalize an ISO-8601 time to Zulu for YouTube's ``publishAt``."""
    if not schedule_iso:
        return None
    return schedule_iso.replace("+00:00", "Z")


class YouTubeAdapter:
    """YouTube uploads (``youtube/v3/videos``) — private by default.

    An optional ``publishAt`` schedules a private post; un-scheduled uploads
    stay private until the owner publishes them.
    """

    platform = "youtube"

    def build_payload(
        self,
        video: Path,
        *,
        title: str,
        description: str,
        schedule_iso: str | None,
    ) -> dict[str, Any]:
        status: dict[str, str] = {"privacyStatus": "private"}
        zulu = _schedule_zulu(schedule_iso)
        if zulu:
            status["publishAt"] = zulu
        return {
            "platform": self.platform,
            "method": "POST",
            "endpoint": "https://www.googleapis.com/upload/youtube/v3/videos",
            "video_file": str(video),
            "request_body": {
                "snippet": {"title": title, "description": description},
                "status": status,
            },
        }

    def execute(self, payload: dict[str, Any], token: str) -> dict[str, Any]:
        req = urllib.request.Request(
            payload["endpoint"],
            data=json.dumps(payload["request_body"]).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))


#: One platform at a time — TikTok/Instagram adapters join this map in
#: follow-up PRs (DEV-G6-001 bounds the first release to one adapter).
ADAPTERS: dict[str, Adapter] = {"youtube": YouTubeAdapter()}


def get_adapter(platform: str) -> Adapter:
    """Return the adapter for ``platform`` (KeyError if unimplemented)."""
    if platform not in ADAPTERS:
        raise KeyError(f"no publish adapter for {platform!r} (available: {sorted(ADAPTERS)})")
    return ADAPTERS[platform]


def youtube_payload(
    video: Path,
    *,
    title: str,
    description: str = "",
    schedule_iso: str | None = None,
) -> dict[str, Any]:
    """Convenience wrapper: the YouTube payload builder, directly testable."""
    return ADAPTERS["youtube"].build_payload(
        video, title=title, description=description, schedule_iso=schedule_iso
    )
