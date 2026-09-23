"""Pydantic models for the web API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Clip models
# ---------------------------------------------------------------------------

TransitionType = Literal["fade", "dissolve", "wipe", "slide"]
ClipStatus = Literal["pending", "generating", "generated", "failed"]


class Clip(BaseModel):
    """A single video clip on the timeline."""

    id: str
    shot_id: str
    scene: int = 1
    index_in_scene: int = 1
    clip_path: str  # relative to project root, e.g. "videos/scenes/Scene-01-Shot-1.mp4"
    prompt: str
    duration: float = 5.0  # seconds, user-editable
    actual_duration: float | None = None  # from ffprobe on load
    style: str = "cinematic"
    transition_in: TransitionType | None = None
    transition_duration: float = 0.5
    volume: float = 1.0
    status: ClipStatus = "pending"
    aspect_ratio: str = "16:9"
    created_at: str = ""
    updated_at: str = ""

    @property
    def start_time(self) -> float:
        """Computed start time on the timeline (set by caller)."""
        return getattr(self, "_start_time", 0.0)

    @start_time.setter
    def start_time(self, value: float) -> None:
        self._start_time = value

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration

    @property
    def thumbnail_path(self) -> str | None:
        """Derived thumbnail path from clip path."""
        if not self.clip_path:
            return None
        stem = self.clip_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return f"thumbnails/{stem}.png"


class ClipUpdate(BaseModel):
    """PATCH payload for a single clip."""

    duration: float | None = None
    transition_in: TransitionType | None = None
    transition_duration: float | None = None
    volume: float | None = None
    prompt: str | None = None


class ClipRegenerateResponse(BaseModel):
    clip_id: str
    status: str
    file_path: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Timeline models
# ---------------------------------------------------------------------------

ColorGrade = Literal["cinematic", "warm", "cool", "desaturated", "none"]


class ProjectTimeline(BaseModel):
    """The canonical timeline for one project."""

    project_id: str
    clips: list[Clip] = Field(default_factory=list)
    aspect_ratio: str = "16:9"
    fps: int = 24
    color_grade: ColorGrade = "cinematic"
    created_at: str = ""
    updated_at: str = ""

    @property
    def total_duration(self) -> float:
        if not self.clips:
            return 0.0
        return sum(c.duration for c in self.clips)


class TimelinePatch(BaseModel):
    """Full timeline replacement payload."""

    clips: list[Clip]
    color_grade: ColorGrade | None = None


# ---------------------------------------------------------------------------
# Project models
# ---------------------------------------------------------------------------

class ProjectSummary(BaseModel):
    id: str
    name: str | None = None
    slug: str | None = None
    status: str = "pending"
    style: str = "cinematic"
    shot_count: int = 0
    current_phase: str = "init"
    has_timeline: bool = False


class ProjectDetail(ProjectSummary):
    description: str | None = None
    budget: int = 500
    spent: int = 0
    target_platforms: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


# ---------------------------------------------------------------------------
# Export model
# ---------------------------------------------------------------------------

class ExportResult(BaseModel):
    output_path: str
    duration_seconds: float
    file_size_bytes: int
    error: str | None = None


# ---------------------------------------------------------------------------
# API response wrappers
# ---------------------------------------------------------------------------

class ApiResponse(BaseModel):
    ok: bool = True
    error: str | None = None


class ProjectListResponse(ApiResponse):
    projects: list[ProjectSummary] = Field(default_factory=list)


class TimelineResponse(ApiResponse):
    timeline: ProjectTimeline | None = None


class ClipResponse(ApiResponse):
    clip: Clip | None = None
