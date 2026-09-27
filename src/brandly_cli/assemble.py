"""Issue #121: ordered final assembly from the deterministic clip naming.

The produce runner already names clips ``Scene-<scene:02d>-Shot-<scene>-<shot>-<act>.mp4``;
assembling a film meant hand-listing every path into ``brandly stitch``.
``brandly assemble`` derives the order from the shot list + naming
convention, concatenates each scene (hard cuts within a scene), then
stitches the scene segments with the between-scenes transition, color grade
and the G4 ratio policy (crop happens here, never in production).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brandly_cli import edit, stitch


@dataclass
class AssemblyPlan:
    """Ordered per-scene clip groups + the shots missing a clip."""

    scene_clips: list[list[Path]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def plan_assembly(shots: list, scenes_dir: Path) -> AssemblyPlan:  # type: ignore[type-arg]
    """Group clips per scene in shot-list order; collect missing shot ids.

    A shot's clips are found by the deterministic naming convention: glob
    ``<clip-stem>*.mp4`` under ``scenes_dir`` (the -<act> suffix and any
    extra takes match the prefix glob).
    """
    scenes_dir = Path(scenes_dir)
    by_scene: dict[int, list[Path]] = {}
    order: list[int] = []
    missing: list[str] = []
    for shot in shots:
        stem = Path(shot.clip_name).stem
        takes = sorted(scenes_dir.glob(stem + "*.mp4")) if scenes_dir.is_dir() else []
        if not takes:
            missing.append(shot.id)
            continue
        if shot.scene not in by_scene:
            by_scene[shot.scene] = []
            order.append(shot.scene)
        by_scene[shot.scene].append(takes[0])
    return AssemblyPlan(
        scene_clips=[by_scene[s] for s in order],
        missing=missing,
    )


async def assemble_project(
    plan: AssemblyPlan,
    output: Path,
    *,
    transition: str = "fade",
    transition_duration: float = 1.0,
    color_grade: str = "cinematic",
    ratio: str | None = None,
    fit: str = "crop",
    say=lambda _m: None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Execute an assembly plan: concat per scene, stitch between scenes."""
    if plan.missing:
        lines = ", ".join(plan.missing)
        say(f"missing {len(plan.missing)} shot(s): {lines}")
        return {"error": f"Missing {len(plan.missing)} shot(s): {lines}"}

    output = Path(output)
    tmp_dir = output.parent / ".assemble_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        segments: list[Path] = []
        for idx, clips in enumerate(plan.scene_clips, start=1):
            if len(clips) == 1:
                segments.append(clips[0])
                say(f"scene {idx}: single clip -> {clips[0].name}")
                continue
            segment = tmp_dir / f"scene-{idx:02d}.mp4"
            result = await edit.concatenate_videos(
                [str(c) for c in clips], str(segment)
            )
            if "error" in result:
                return result
            segments.append(segment)
            say(f"scene {idx}: concatenated {len(clips)} clips -> {segment.name}")

        if not segments:
            return {"error": "No clips to assemble."}
        return await stitch.stitch_videos(
            segments,
            output,
            transition=transition,
            transition_duration=transition_duration,
            color_grade=color_grade,
            ratio=ratio,
            fit=fit,
        )
    finally:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)
