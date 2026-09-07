"""Pydantic models for Brandly data structures."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Project models
# ---------------------------------------------------------------------------


class PhaseResult(BaseModel):
    status: str = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    output: str | None = None
    error: str | None = None


class ProjectData(BaseModel):
    id: str
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    status: str = "pending"
    style: str = "cinematic"
    shot_count: int = 5
    budget: int = 500
    spent: int = 0
    current_phase: str = "init"
    phases: dict[str, PhaseResult] = Field(default_factory=dict)
    hooks: list[str] = Field(default_factory=list)
    settings: list[str] = Field(default_factory=list)
    target_platforms: list[str] = Field(default_factory=lambda: ["tiktok", "instagram"])
    image_analysis: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""

    model_config = {"extra": "allow"}

    def to_dict(self) -> dict[str, Any]:
        # Include unset fields with defaults so round-tripping preserves the
        # full project shape. Extras (via ``extra="allow"``) are also included.
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectData:
        # Normalize keys
        normalized = {}
        for k, v in data.items():
            key = k.replace("-", "_").replace(" ", "_")
            normalized[key] = v
        return cls(**normalized)


# ---------------------------------------------------------------------------
# Trend / Concept / Script models
# ---------------------------------------------------------------------------


class TrendFormat(BaseModel):
    name: str
    description: str
    example_hooks: list[str] = Field(default_factory=list)
    pacing: str = "moderate"
    avg_duration: int = 15
    virality_potential: float = 0.0
    best_for: str = ""


class TrendReport(BaseModel):
    trending_formats: list[TrendFormat] = Field(default_factory=list)
    recommended_style: str = "cinematic"
    key_insight: str = ""
    platform_notes: dict[str, str] = Field(default_factory=dict)
    timestamp: str = ""


class VideoConcept(BaseModel):
    id: int = 1
    name: str = ""
    hook: str = ""
    narrative_arc: str = ""
    visual_style: str = ""
    cta: str = ""
    shots: int = 5
    estimated_duration: int = 15
    estimated_credits: int = 100
    virality_score: float = 0.0
    best_for: str = ""


class ConceptResult(BaseModel):
    concepts: list[VideoConcept] = Field(default_factory=list)
    recommended: int = 1
    reasoning: str = ""


class ScriptScene(BaseModel):
    id: int = 1
    description: str = ""
    duration: int = 3
    dialogue: str | None = None
    visual_notes: str | None = None
    prompt: str = ""


class ScriptResult(BaseModel):
    scenes: list[ScriptScene] = Field(default_factory=list)
    duration: int = 15
    tone: str = ""
    pacing: str = ""


class AssetItem(BaseModel):
    shot_id: int = 1
    model: str = ""
    prompt: str = ""
    aspect_ratio: str = "9:16"
    resolution: str = "720p"
    duration: int = 3
    estimated_credits: int = 2
    status: str = "pending"


class AssetPlan(BaseModel):
    asset_plan: list[AssetItem] = Field(default_factory=list)
    total_estimated_credits: int = 0
    preview_assets: list[dict[str, Any]] = Field(default_factory=list)


class AudioTrack(BaseModel):
    id: str = ""
    type: str = "music"  # music | sfx | voiceover
    description: str = ""
    prompt: str = ""
    duration: int | None = None


class AudioPlan(BaseModel):
    tracks: list[AudioTrack] = Field(default_factory=list)
    style: str = ""
    mood: str = ""


class ValidationResult(BaseModel):
    passed: bool = False
    score: float = 0.0
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CostEstimate(BaseModel):
    style: str = "cinematic"
    shot_count: int = 5
    base_cost: int = 0
    shot_cost: int = 0
    total_cost: int = 0
    phase_estimates: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent command models (for orchestrator)
# ---------------------------------------------------------------------------


class AgentCommand(BaseModel):
    """A command that an agent sub-process should execute."""

    tool: str
    params: dict[str, Any] = Field(default_factory=dict)


class ToolCall(AgentCommand):
    pass


# ---------------------------------------------------------------------------
# Export manifest
# ---------------------------------------------------------------------------


class ExportManifest(BaseModel):
    project_id: str = ""
    project_name: str | None = None
    description: str | None = None
    style: str = "cinematic"
    shot_count: int = 5
    budget: int = 500
    spent: int = 0
    target_platforms: list[str] = Field(default_factory=list)
    created_at: str = ""
    exported_at: str = ""
    phases: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    artifact_count: int = 0
    media_files: list[str] = Field(default_factory=list)
    media_count: int = 0
    total_files: int = 0
