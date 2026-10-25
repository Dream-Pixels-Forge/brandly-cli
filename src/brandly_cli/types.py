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
    attempts: int = 0


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
    product_category: str | None = None
    """Issue #273: the product category is the trend-research axis — style
    and category are different axes (TREND_DATABASE is keyed by category)."""
    target_duration: int | None = None
    """Issue #276: the requested film duration in seconds — drives the
    script phase's shot plan and the film-level duration truth report."""
    storyboards: bool = False
    """Issue #281: when true, the asset phase runs the keyframe pass first —
    a failing storyboard gate blocks that shot's video spend."""
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


# ---------------------------------------------------------------------------
# .brandly Documents — Bible & Screenplay (foundation layer)
# ---------------------------------------------------------------------------


class BibleContent(BaseModel):
    """Production bible content — the single source of truth that informs
    every downstream tool (cast, wardrobe, location, sound, director, DP)."""

    project_id: str
    title: str
    logline: str
    tone: str = ""
    genre: str = ""
    visual_style: str = "cinematic"
    color_palette: str = ""
    characters: list[dict[str, Any]] = Field(default_factory=list)
    locations: list[dict[str, Any]] = Field(default_factory=list)
    props: list[dict[str, Any]] = Field(default_factory=list)
    wardrobe_notes: str = ""
    sound_notes: str = ""
    camera_notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class ScreenplayContent(BaseModel):
    """Screenplay / beat sheet — drives shot generation and scheduling."""

    project_id: str
    title: str
    logline: str
    acts: list[dict[str, Any]] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    total_duration: int = 0
    tone: str = ""
    pacing: str = ""
    created_at: str = ""
    updated_at: str = ""


# ---------------------------------------------------------------------------
# Pre-production — Cast, Wardrobe, Sheets, Location, Sound, Spatial
# ---------------------------------------------------------------------------


class CastMember(BaseModel):
    """A cast member with identity anchor and reference plates."""

    name: str
    role: str  # lead, supporting, extra
    description: str = ""
    reference_images: list[str] = Field(default_factory=list)
    wardrobe: list[str] = Field(default_factory=list)
    voice_notes: str = ""
    created_at: str = ""


class WardrobeTry(BaseModel):
    """Wardrobe variation for a character."""

    character_name: str
    outfit_name: str
    description: str = ""
    image_path: str = ""
    category: str = ""  # casual, formal, period, tactical, etc.
    created_at: str = ""


class ReferenceSheet(BaseModel):
    """Generated reference sheet for a subject (character, location, prop, etc.)."""

    subject_type: str  # character, location, prop, vehicle, mecha, animal, plant
    subject_name: str
    image_path: str
    category: str = ""
    prompt: str = ""
    created_at: str = ""


class LocationDesign(BaseModel):
    """Location / set design with visual reference."""

    name: str
    description: str = ""
    image_path: str = ""
    category: str = ""  # interior, exterior, studio, practical
    lighting_notes: str = ""
    created_at: str = ""


class SoundTrack(BaseModel):
    """Audio track design (soundtrack, sfx, foley, voiceover)."""

    id: str
    type: str  # music | sfx | foley | voiceover
    description: str = ""
    prompt: str = ""
    duration: int | None = None
    output_path: str = ""
    category: str = "general"
    created_at: str = ""


class SpatialFrame(BaseModel):
    """3D spatial reference frame from Blender (camera position, angle, blocking)."""

    shot_id: str
    camera_position: list[float] = Field(default_factory=list)  # [x, y, z]
    camera_rotation: list[float] = Field(default_factory=list)  # [x, y, z]
    lens_mm: str = ""
    aspect_ratio: str = "16:9"
    depth_map_path: str = ""
    keyframe_path: str = ""
    blocking_notes: str = ""
    created_at: str = ""


# ---------------------------------------------------------------------------
# Production — Director, DoP, Cascade, Editor
# ---------------------------------------------------------------------------


class ShotDirection(BaseModel):
    """Director's direction for a single shot."""

    shot_id: str
    scene_id: str
    prompt: str
    model: str = "agnes-video-2.5-flash"
    style: str = "cinematic"
    duration: int = 5
    aspect_ratio: str = "16:9"
    first_frame: str | None = None
    last_frame: str | None = None
    reference_images: list[str] = Field(default_factory=list)
    reference_roles: list[str] = Field(default_factory=list)
    camera_notes: str = ""
    lighting_notes: str = ""
    sound_notes: str = ""
    created_at: str = ""


class CascadeStage(BaseModel):
    """One stage in a cinematic high-end cascade pipeline."""

    name: str
    phase: str  # trends, concept, bible, casting, screenplay, script, asset, audio, re_edit, validate, publish
    tool: str  # which brandly tool to invoke
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    gate_passed: bool | None = None
    created_at: str = ""


class DirectorOfPhotography(BaseModel):
    """DoP specifications for a shot or scene."""

    shot_id: str
    lens: str = "50mm"
    aperture: str = "f/2.8"
    lighting_setup: str = "three_point"  # three_point, natural, dramatic, golden_hour
    color_grade: str = "cinematic"
    composition: str = "rule_of_thirds"
    camera_move: str = "static"
    notes: str = ""


class EditDecision(BaseModel):
    """Editor's cut decision for a clip."""

    clip_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    transition: str = "cut"  # cut, fade, wipe, dissolve
    transition_duration: float = 0.5
    color_grade: str = "none"
    volume: float = 1.0
    created_at: str = ""


# ---------------------------------------------------------------------------
# Film Action / Fight Choreography (higgsfield-fight-scene integration)
#
# The cascade pipeline handles film action by breaking fights into beats
# (1–2 seconds each). Each beat: position → action (limb, trajectory,
# target) → opponent's physical reaction → new position. JKD logic:
# intercept rather than block, shortest line, minimal movement.
#
# Prompts are Seedance-proof: pure body geometry, zero martial-arts
# terminology, zero prohibitions, physics of consequences. Every fight
# prompt ends with the identical FIGHT STYLE LOCK.
# ---------------------------------------------------------------------------


class Fighter(BaseModel):
    """A fighter in an action scene — hero, opponent, master, student."""

    name: str
    role: str  # hero, opponent, master, student
    lead_hand: str = "right"  # right or left — strong side forward in JKD
    style: str = "jkd"  # jkd, wing_chun, classical, street
    description: str = ""
    reference_images: list[str] = Field(default_factory=list)


class FightBeat(BaseModel):
    """One beat of a fight — roughly 1–2 seconds of screen time.

    An 8-second shot holds 4–6 beats maximum, including 1–2 beats of
    stance/pause. The pause is part of the fight: broken rhythm requires
    written stop-stills.
    """

    beat_number: int
    start_time: float
    end_time: float
    position: str  # stance/geometry description (e.g. S1 bai-jong geometry)
    action: str  # which limb, from where, along which path, to where
    reaction: str  # opponent's physical response following the strike vector
    new_position: str  # position after the beat resolves
    camera_angle: str = "profile"  # profile, three_quarter, front
    shot_size: str = "medium"  # wide, medium, close — legs visible for kicks


class FightChoreography(BaseModel):
    """A complete fight scene choreography — beats, pattern, style lock.

    Written in Seedance-proof prompt language: pure body geometry, zero
    martial-arts terminology, zero prohibitions, physics of consequences.
    """

    project_id: str
    scene_id: str
    fighters: list[Fighter] = Field(default_factory=list)
    opponents: list[Fighter] = Field(default_factory=list)
    weapons: list[str] = Field(default_factory=list)
    location: str = ""
    emotion: str = ""
    shot_duration: int = 6  # seconds — beats = duration / 1.5, max 4-6
    winner: str = ""
    pattern: str = "P1"  # P1-P6 or custom
    beats: list[FightBeat] = Field(default_factory=list)
    style_lock: str = ""
    created_at: str = ""
    updated_at: str = ""


class CascadeFightStage(BaseModel):
    """A cascade stage that carries fight choreography for film action."""

    name: str
    phase: str  # trends, concept, bible, casting, screenplay, script, asset, audio, re_edit, validate, publish
    tool: str  # which brandly tool to invoke
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    gate_passed: bool | None = None
    fight_choreography: FightChoreography | None = None
    created_at: str = ""
