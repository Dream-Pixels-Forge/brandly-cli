"""Timeline state management — load/save/sync for brandly timeline editor."""

from __future__ import annotations

import json
from pathlib import Path

from brandly_cli import layout
from brandly_cli.web.models import (
    Clip,
    ClipUpdate,
    ProjectTimeline,
)

TIMELINE_FILENAME = "timeline.json"

#: Flat shot list mirrored alongside the timeline so `brandly produce
#: --shots .brandly/{id}/shots.json` sees the editor's edits (plan line 60).
SHOTS_FILENAME = "shots.json"

#: Agnes' effective per-shot clamp, enforced on PATCH and PUT alike.
MIN_CLIP_DURATION = 1.0
MAX_CLIP_DURATION = 12.0  # Agnes model limit


class TimelineState:
    """In-memory timeline state synced to timeline.json on disk."""

    def __init__(self, project_id: str, root: Path) -> None:
        self.project_id = project_id
        self.root = root
        self._timeline: ProjectTimeline | None = None

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self) -> ProjectTimeline:
        """Load timeline from disk, building from existing clips if needed."""
        path = self._timeline_path()
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            self._timeline = ProjectTimeline.model_validate(raw)
            return self._timeline

        # Build from project files
        self._timeline = self._build_from_project()
        self.save()
        return self._timeline

    def save(self) -> None:
        """Persist the timeline and mirror it as ``shots.json`` (plan line 60)."""
        if self._timeline is None:
            return
        path = self._timeline_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._timeline.model_dump()
        # Remove internal _start_time fields
        for clip in data.get("clips", []):
            clip.pop("_start_time", None)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._write_shots()

    def _write_shots(self) -> None:
        """Mirror the timeline as a flat shot list for ``brandly produce``.

        ``timeline.json`` stays the editor's source of truth; ``shots.json`` is
        regenerated from it so reordered/trimmed/retimed clips reach the CLI.
        Empty timelines write nothing — produce rejects a 0-shot flat list.
        """
        assert self._timeline is not None
        shots = [
            {"name": c.id, "prompt": c.prompt, "duration": c.duration, "style": c.style}
            for c in self._timeline.clips
        ]
        if not shots:
            return
        proj_dir = layout.project_dir(self.root, self.project_id)
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / SHOTS_FILENAME).write_text(
            json.dumps(shots, indent=2), encoding="utf-8"
        )

    def reload(self) -> ProjectTimeline:
        """Discard in-memory state and reload from disk."""
        self._timeline = None
        return self.load()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def timeline(self) -> ProjectTimeline:
        if self._timeline is None:
            return self.load()
        return self._timeline

    def get_clip(self, clip_id: str) -> Clip | None:
        for clip in self.timeline.clips:
            if clip.id == clip_id:
                return clip
        return None

    def clip_index(self, clip_id: str) -> int:
        for i, c in enumerate(self.timeline.clips):
            if c.id == clip_id:
                return i
        return -1

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def reorder_clips(self, order: list[str]) -> None:
        """Reorder clips by ID list. Recalculates start times."""
        clips = self.timeline.clips
        by_id = {c.id: c for c in clips}
        new_order = [by_id[i] for i in order if i in by_id]
        # Actually keep all clips, just reorder the ones specified
        all_ids = {c.id for c in clips}
        for cid in order:
            if cid in all_ids and cid not in {c.id for c in new_order}:
                new_order.append(by_id[cid])
        extra = [c for c in clips if c not in new_order]
        self.timeline.clips = new_order + extra
        self._recalculate_start_times()
        self.save()

    def update_clip(self, clip_id: str, updates: ClipUpdate) -> Clip | None:
        """Apply partial update to a clip."""
        clip = self.get_clip(clip_id)
        if clip is None:
            return None
        if updates.duration is not None:
            clip.duration = max(MIN_CLIP_DURATION, min(MAX_CLIP_DURATION, updates.duration))
        if updates.transition_in is not None:
            clip.transition_in = updates.transition_in  # type: ignore[assignment]
        if updates.transition_duration is not None:
            clip.transition_duration = updates.transition_duration
        if updates.volume is not None:
            clip.volume = updates.volume
        if updates.prompt is not None:
            clip.prompt = updates.prompt
        clip.updated_at = _now_iso()
        self._recalculate_start_times()
        self.save()
        return clip

    def replace_clips(self, clips: list[Clip]) -> None:
        """Replace the whole clip list, clamping durations to the model limit."""
        for clip in clips:
            clip.duration = max(MIN_CLIP_DURATION, min(MAX_CLIP_DURATION, clip.duration))
        self.timeline.clips = clips
        self._recalculate_start_times()
        self.save()

    def set_color_grade(self, grade: str) -> None:
        self.timeline.color_grade = grade  # type: ignore[assignment]
        self.save()

    def regenerate_clip_status(self, clip_id: str, status: str) -> None:
        clip = self.get_clip(clip_id)
        if clip:
            clip.status = status  # type: ignore[assignment]
            clip.updated_at = _now_iso()
            self.save()

    def set_clip_file(self, clip_id: str, clip_path: str) -> None:
        clip = self.get_clip(clip_id)
        if clip:
            clip.clip_path = clip_path
            clip.status = "generated"  # type: ignore[assignment]
            clip.updated_at = _now_iso()
            self.save()

    def compute_quality_status(self, clip_id: str) -> str | None:
        """Run the deterministic quality gate on a clip and persist the result."""
        clip = self.get_clip(clip_id)
        if clip is None or not clip.clip_path:
            return None
        proj_dir = layout.project_dir(self.root, self.project_id)
        from brandly_cli.web.security import safe_join
        full_path = safe_join(proj_dir, clip.clip_path)
        if full_path is None or not full_path.is_file():
            return None
        import asyncio

        from brandly_cli.quality_gate import PASS, verify_element
        try:
            result = asyncio.run(
                verify_element(
                    full_path,
                    use_ai=False,
                    root=self.root,
                    project_id=self.project_id,
                    write_report=False,
                )
            )
            q = result.status
            if q != PASS:
                clip.quality_status = q  # type: ignore[assignment]
                clip.updated_at = _now_iso()
                self.save()
            return q
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Time recalculation
    # ------------------------------------------------------------------

    def _recalculate_start_times(self) -> None:
        """Set start_time on each clip based on cumulative duration."""
        t = 0.0
        for clip in self.timeline.clips:
            clip.start_time = t
            t += clip.duration

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _timeline_path(self) -> Path:
        proj_dir = layout.project_dir(self.root, self.project_id)
        return layout.docs_dir(proj_dir, "tmp") / TIMELINE_FILENAME

    def _build_from_project(self) -> ProjectTimeline:
        """Build initial timeline from existing project files."""
        proj_dir = layout.project_dir(self.root, self.project_id)
        clips: list[Clip] = []

        # Scan for generated video clips
        videos_dir = layout.media_dir(proj_dir, "videos", "scenes")
        if videos_dir.exists():
            for mp4 in sorted(videos_dir.glob("*.mp4")):
                stem = mp4.stem  # e.g. "Scene-01-Shot-1-1"
                clip = self._parse_clip_filename(stem, mp4, proj_dir)
                if clip:
                    clips.append(clip)

        # Also check transition clips
        trans_dir = layout.media_dir(proj_dir, "videos", "transition")
        if trans_dir.exists():
            for mp4 in sorted(trans_dir.glob("*.mp4")):
                stem = mp4.stem
                clip = self._parse_clip_filename(stem, mp4, proj_dir)
                if clip:
                    clips.append(clip)

        timeline = ProjectTimeline(
            project_id=self.project_id,
            clips=clips,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        timeline._recalculate_start_times = lambda: None  # type: ignore
        # Set start times manually
        t = 0.0
        for c in timeline.clips:
            c.start_time = t
            t += c.duration
        return timeline

    def _parse_clip_filename(
        self, stem: str, path: Path, proj_dir: Path
    ) -> Clip | None:
        """Parse Scene-01-Shot-1-1.mp4 into a Clip."""
        try:
            parts = stem.split("-")
            if len(parts) < 4:
                return None
            scene = int(parts[1])
            shot_idx = int(parts[3])
        except (ValueError, IndexError):
            return None

        rel_path = f"videos/scenes/{path.name}"
        duration = _get_clip_duration(path)

        return Clip(
            id=stem,
            shot_id=f"shot-{scene}-{shot_idx}",
            scene=scene,
            index_in_scene=shot_idx,
            clip_path=rel_path,
            prompt=f"Shot {scene}-{shot_idx}",
            duration=duration or 5.0,
            actual_duration=duration,
            status="generated",
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _get_clip_duration(path: Path) -> float | None:
    """Get clip duration via ffprobe (sync), or None when unavailable."""
    from brandly_cli.web.utils.ffprobe import get_clip_duration

    return get_clip_duration(path) or None
