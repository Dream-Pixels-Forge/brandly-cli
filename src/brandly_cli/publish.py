"""G6: publish path (decision record DEV-G6-001) — dry-run first, live only
with explicitly stored credentials.

One platform at a time: YouTube shipped first (issue #97 PR 1); TikTok and
Instagram close the remaining adapters behind the same :data:`ADAPTERS`
interface (issue #97). The dry-run path builds the exact request payload and
never touches the network; live execution requires a credential stored via
``brandly config set`` (user-level store, never in project files or ``.env``
— see F2). Scheduling is only offered where the platform actually supports
it (YouTube ``publishAt``; TikTok direct-post has none and refuses it).
"""

from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path
from typing import Any, Protocol


class Adapter(Protocol):
    """A platform publish adapter: payload builder + live executor."""

    platform: str

    def build_payload(
        self,
        video: Path,
        *,
        title: str,
        description: str,
        schedule_iso: str | None,
        video_url: str | None = None,
    ) -> dict[str, Any]:
        """Build the exact request payload.

        Pure apart from ``stat()``-ing the video for size-sensitive platforms
        (TikTok's chunked-upload init needs the byte size).
        """
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
        video_url: str | None = None,
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
        return _post_json(payload["endpoint"], payload["request_body"], token)


#: TikTok chunked-upload init: chunks above this size split (64 MiB API cap).
TIKTOK_MAX_CHUNK_BYTES = 64 * 1024 * 1024


class TikTokAdapter:
    """TikTok direct-post (``/v2/post/publish/video/init/``) — SELF_ONLY default.

    TikTok's caption is a single field, so ``description`` folds into
    ``post_info.title``. Direct-post has no scheduled-publish equivalent, so a
    ``--schedule`` is refused (fail-closed, honest) instead of silently
    ignored: post private and publish from the app when it's ready.
    """

    platform = "tiktok"

    def build_payload(
        self,
        video: Path,
        *,
        title: str,
        description: str,
        schedule_iso: str | None,
        video_url: str | None = None,
    ) -> dict[str, Any]:
        if schedule_iso:
            raise ValueError(
                "TikTok direct-post does not support scheduled publishing - "
                "drop --schedule, post private (SELF_ONLY) and publish from "
                "the app when it's ready"
            )
        size = video.stat().st_size
        chunk = min(size, TIKTOK_MAX_CHUNK_BYTES) or 1
        return {
            "platform": self.platform,
            "method": "POST",
            "endpoint": "https://open.tiktokapis.com/v2/post/publish/video/init/",
            "video_file": str(video),
            "request_body": {
                "post_info": {
                    "title": f"{title}\n\n{description}".strip(),
                    "privacy_level": "SELF_ONLY",
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": chunk,
                    "total_chunk_count": max(1, math.ceil(size / chunk)),
                },
            },
        }

    def execute(self, payload: dict[str, Any], token: str) -> dict[str, Any]:
        return _post_json(payload["endpoint"], payload["request_body"], token)


class InstagramAdapter:
    """Instagram Reels via the Graph API — two-step container flow.

    The Graph API cannot fetch local files: a Reel needs a *publicly
    reachable* ``video_url`` — share the video first (``brandly share <id>``)
    and pass ``--video-url``. Without one the payload build fails closed.
    The create response's container id is published by the follow-up step.
    """

    platform = "instagram"

    def build_payload(
        self,
        video: Path,
        *,
        title: str,
        description: str,
        schedule_iso: str | None,
        video_url: str | None = None,
    ) -> dict[str, Any]:
        if not video_url:
            raise ValueError(
                "Instagram needs a publicly reachable video URL (the Graph API "
                "cannot fetch local files) - share the video first "
                "(`brandly share <id>`) and pass --video-url"
            )
        caption = f"{title}\n\n{description}".strip()
        return {
            "platform": self.platform,
            "method": "POST",
            "endpoint": "https://graph.facebook.com/v21.0/me/media",
            "video_file": str(video),
            "request_body": {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
            },
            "follow_up": {
                "method": "POST",
                "endpoint": "https://graph.facebook.com/v21.0/me/media_publish",
                "body": {"creation_id": "<container id from the create response>"},
            },
        }

    def execute(self, payload: dict[str, Any], token: str) -> dict[str, Any]:
        # Two-step flow: create the media container, then publish it.
        create = _post_json(payload["endpoint"], payload["request_body"], token)
        container = str(create.get("id") or "")
        if not container:
            return create  # create failed — nothing to publish
        return _post_json(
            payload["follow_up"]["endpoint"], {"creation_id": container}, token
        )


def _post_json(endpoint: str, body: dict[str, Any], token: str) -> dict[str, Any]:
    """POST a JSON body with a Bearer credential (the shared live executor)."""
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


#: All three F9 platforms (DEV-G6-001): YouTube shipped in G6 PR 1, TikTok/IG
#: close the set (issue #97). Scheduling: YouTube only (publishAt).
ADAPTERS: dict[str, Adapter] = {
    "youtube": YouTubeAdapter(),
    "tiktok": TikTokAdapter(),
    "instagram": InstagramAdapter(),
}


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


def build_social_copy(
    title: str,
    *,
    description: str = "",
    hashtags: list[str] | None = None,
    platform: str | None = None,
    subject: str | None = None,
    style: str | None = None,
    category: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Compose copy-ready social text for a platform: description + hashtags.

    * ``description`` is seeded from ``subject``/``title`` when absent - only
      known metadata is used, nothing is fabricated.
    * ``hashtags``: an explicit list wins (hash-prefixed, de-whitened);
      ``None`` auto-generates from ``category``/``subject``/``style``/``platform``
      via :func:`brandly_cli.trends.build_hashtags`; an explicit empty list
      means "no hashtags".
    * ``caption`` is a single copy-paste block (title, description, hashtags);
      ``description_with_tags`` is what feeds the platform payload's
      description/caption field (hashtags appended to the description).
    """
    from brandly_cli import trends

    base_desc = (description or "").strip()
    if not base_desc:
        base_desc = (subject or title or "").strip()

    if hashtags is None:
        tags = trends.build_hashtags(
            category, subject=subject, style=style, platform=platform, limit=limit
        )
    else:
        tags: list[str] = []
        for raw in hashtags:
            cleaned = str(raw).strip()
            if not cleaned:
                continue
            if not cleaned.startswith("#"):
                cleaned = f"#{cleaned}"
            tags.append(cleaned)

    tag_line = " ".join(tags)
    description_with_tags = (
        f"{base_desc}\n\n{tag_line}".strip() if tag_line else base_desc
    )
    caption = "\n\n".join(part for part in (title.strip(), description_with_tags) if part)

    return {
        "platform": platform,
        "title": title,
        "subject": subject,
        "description": base_desc,
        "hashtags": tags,
        "description_with_tags": description_with_tags,
        "caption": caption,
    }
