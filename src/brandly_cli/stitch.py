"""Multi-shot video assembly — concatenate clips with transitions and color grading."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# FFmpeg availability helpers (mirrors edit.py conventions)
# ---------------------------------------------------------------------------

def _ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ffprobe_available() -> bool:
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Transitions & color grades
# ---------------------------------------------------------------------------

TRANSITIONS = ("fade", "dissolve", "wipe", "slide")

COLOR_GRADES: dict[str, str] = {
    "cinematic": "eq=brightness=0.02:contrast=1.1:saturation=1.2",
    "warm": "colorbalance=rs=0.05:gs=0.02:bs=-0.02",
    "cool": "colorbalance=rs=-0.02:gs=-0.01:bs=0.05",
    "desaturated": "eq=saturation=0.5",
    "none": "",
}


def get_clip_duration(path: Path) -> float:
    """Return the duration of a clip in seconds using ffprobe."""
    if not _ffprobe_available():
        return 0.0
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    if proc.returncode != 0:
        return 0.0
    try:
        data = json.loads(proc.stdout.decode())
        return float(data.get("format", {}).get("duration", 0.0))
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Core stitch
# ---------------------------------------------------------------------------

async def stitch_videos(
    clips: list[Path],
    output: Path,
    *,
    transition: str = "fade",
    transition_duration: float = 0.5,
    color_grade: str = "cinematic",
    root: Path | None = None,
) -> dict[str, Any]:
    """Concatenate video clips with transitions and color grading.

    Args:
        clips: Ordered list of input video paths.
        output: Destination file path.
        transition: One of fade | dissolve | wipe | slide.
        transition_duration: Duration of each transition in seconds.
        color_grade: One of cinematic | warm | cool | desaturated | none.
        root: Optional project root (used for resolving relative outputs).

    Returns:
        Dict with output metadata, or an ``{"error": ...}`` dict on failure.
    """
    clips = [Path(c) for c in clips]
    output = Path(output)

    # --- validation ---------------------------------------------------------
    for clip in clips:
        if not clip.exists():
            return {"error": f"Input file not found: {clip}"}
    if not clips:
        return {"error": "No clips provided."}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}
    if transition not in TRANSITIONS:
        return {"error": f"Unknown transition: {transition}. Choose from {TRANSITIONS}."}
    if color_grade not in COLOR_GRADES:
        return {"error": f"Unknown color grade: {color_grade}. Choose from {list(COLOR_GRADES)}."}

    output.parent.mkdir(parents=True, exist_ok=True)

    # --- single clip: pass-through ------------------------------------------
    if len(clips) == 1:
        grade_filter = COLOR_GRADES.get(color_grade, "")
        # grade_filter applied in cmd
        cmd = [
            "ffmpeg", "-y", "-i", str(clips[0]),
            "-vf", grade_filter if grade_filter else "null",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(output),
        ]
        rc, stderr = await _run(cmd)
        if rc != 0:
            return {"error": stderr[:500]}
        return _result(output, clips, [], color_grade)

    # --- multi-clip: simple concat -------------------------------------------
    # Write concat file
    concat_file = output.parent / f"_concat_{output.name}.txt"
    concat_lines = []
    durations: list[float] = []
    for c in clips:
        d = get_clip_duration(c) or 1.0
        durations.append(d)
        concat_lines.append(f"file '{c.resolve()}'")
        concat_lines.append(f"duration {d}")
    concat_lines.append("file ''")  # final empty line
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    # Build filter complex for crossfade transitions
    grade_filter = COLOR_GRADES.get(color_grade, "")
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]

    # Use xfade for video and acrossfade for audio
    n = len(clips)
    offsets: list[float] = []
    offset = durations[0] - transition_duration
    for i in range(n - 1):
        offsets.append(max(offset, 0.1))
        offset += durations[i + 1] - transition_duration

    # Build video filter chain
    vf_chain = "[0:v]"
    for i in range(1, n):
        offset_val = offsets[i - 1]
        vf_chain += (
            f"[{i}:v]xfade=transition={transition}"
            f":duration={transition_duration}"
            f":offset={offset_val}"
        )
        if i < n - 1:
            vf_chain += f"[v{i}];"
        else:
            vf_chain += "[vout];"

    if grade_filter:
        vf_chain += f"[vout]{grade_filter}[final_v]"
    else:
        vf_chain += "[vout]"

    # Build audio filter chain with acrossfade
    af_chain = "[0:a]"
    for i in range(1, n):
        af_chain += f"[{i}:a]acrossfade=d={transition_duration}:c1=tri:c2=tri"
        if i < n - 1:
            af_chain += f"[a{i}];"
        else:
            af_chain += "[aout]"

    filter_complex = f"{vf_chain};{af_chain}"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[final_v]" if grade_filter else "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output),
    ]

    rc, stderr = await _run(cmd)
    concat_file.unlink(missing_ok=True)

    if rc != 0:
        return {"error": stderr[:500]}

    transitions_applied = [transition] * (n - 1)
    return _result(output, clips, transitions_applied, color_grade)


async def _run(cmd: list[str]) -> tuple[int | None, str]:
    """Run an FFmpeg command, returning (returncode, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    return proc.returncode, stderr.decode()


def _result(
    output: Path,
    clips: list[Path],
    transitions_applied: list[str],
    color_grade: str,
) -> dict[str, Any]:
    """Build the standardized result dict."""
    size = output.stat().st_size if output.exists() else 0
    duration = get_clip_duration(output)
    return {
        "output_path": str(output),
        "duration_seconds": duration,
        "size_bytes": size,
        "transitions_applied": transitions_applied,
        "color_grade": color_grade,
        "clips_count": len(clips),
    }


# ---------------------------------------------------------------------------
# Scene graph — long-form continuity management
# ---------------------------------------------------------------------------

class SceneNode:
    """A single scene in the scene graph."""

    def __init__(
        self,
        scene_id: str,
        title: str,
        location: str,
        time_of_day: str = "day",
        mood: str = "neutral",
        characters: list[str] | None = None,
        props: list[str] | None = None,
        duration_seconds: float = 0.0,
    ) -> None:
        self.scene_id = scene_id
        self.title = title
        self.location = location
        self.time_of_day = time_of_day
        self.mood = mood
        self.characters = characters or []
        self.props = props or []
        self.duration_seconds = duration_seconds
        self.transitions_from: list[str] = []
        self.transitions_to: list[str] = []
        self.visual_theme: dict[str, str] = {}

    def add_transition_from(self, scene_id: str) -> None:
        """Add a scene that transitions into this one."""
        if scene_id not in self.transitions_from:
            self.transitions_from.append(scene_id)

    def add_transition_to(self, scene_id: str) -> None:
        """Add a scene this one transitions to."""
        if scene_id not in self.transitions_to:
            self.transitions_to.append(scene_id)

    def set_visual_theme(self, theme: dict[str, str]) -> None:
        """Set the visual theme for this scene."""
        self.visual_theme = theme

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "mood": self.mood,
            "characters": self.characters,
            "props": self.props,
            "duration_seconds": self.duration_seconds,
            "transitions_from": self.transitions_from,
            "transitions_to": self.transitions_to,
            "visual_theme": self.visual_theme,
        }


class SceneGraph:
    """Manages scene transitions and visual themes for long-form content.

    Maintains continuity by tracking:
    - Scene relationships and transitions
    - Character appearances across scenes
    - Visual theme consistency
    - Time-of-day continuity
    - Prop persistence
    """

    def __init__(self, title: str = "Untitled Project") -> None:
        self.title = title
        self._scenes: dict[str, SceneNode] = {}
        self._scene_order: list[str] = []
        self._global_visual_theme: dict[str, str] = {}
        self._character_registry: dict[str, dict[str, str]] = {}

    def add_scene(
        self,
        scene_id: str,
        title: str,
        location: str,
        *,
        time_of_day: str = "day",
        mood: str = "neutral",
        characters: list[str] | None = None,
        props: list[str] | None = None,
        duration_seconds: float = 0.0,
        auto_transition: bool = True,
    ) -> SceneNode:
        """Add a scene to the graph."""
        if scene_id in self._scenes:
            raise ValueError(f"Scene '{scene_id}' already exists")

        node = SceneNode(
            scene_id=scene_id,
            title=title,
            location=location,
            time_of_day=time_of_day,
            mood=mood,
            characters=characters,
            props=props,
            duration_seconds=duration_seconds,
        )

        # Apply global visual theme
        if self._global_visual_theme:
            node.set_visual_theme(self._global_visual_theme.copy())

        self._scenes[scene_id] = node
        self._scene_order.append(scene_id)

        # Auto-transition from previous scene
        if auto_transition and len(self._scene_order) > 1:
            prev_id = self._scene_order[-2]
            self.connect_scenes(prev_id, scene_id, "cut")

        # Register characters
        for char in (characters or []):
            if char not in self._character_registry:
                self._character_registry[char] = {"first_seen": scene_id}

        return node

    def connect_scenes(
        self,
        from_id: str,
        to_id: str,
        transition_type: str = "cut",
    ) -> None:
        """Connect two scenes with a transition."""
        if from_id not in self._scenes:
            raise ValueError(f"Scene '{from_id}' not found")
        if to_id not in self._scenes:
            raise ValueError(f"Scene '{to_id}' not found")

        self._scenes[from_id].add_transition_to(to_id)
        self._scenes[to_id].add_transition_from(from_id)

    def set_global_visual_theme(self, theme: dict[str, str]) -> None:
        """Set a global visual theme applied to all scenes."""
        self._global_visual_theme = theme
        for scene in self._scenes.values():
            scene.set_visual_theme(theme.copy())

    def register_character(
        self,
        character_name: str,
        description: str,
        key_traits: list[str] | None = None,
    ) -> None:
        """Register a character with their description for consistency."""
        self._character_registry[character_name] = {
            "description": description,
            "key_traits": ", ".join(key_traits or []),
        }

    def get_scene(self, scene_id: str) -> SceneNode | None:
        """Get a scene by ID."""
        return self._scenes.get(scene_id)

    def get_previous_scene(self, scene_id: str) -> SceneNode | None:
        """Get the scene that comes before the given scene."""
        idx = self._scene_order.index(scene_id) if scene_id in self._scene_order else -1
        if idx > 0:
            return self._scenes[self._scene_order[idx - 1]]
        return None

    def get_next_scene(self, scene_id: str) -> SceneNode | None:
        """Get the scene that comes after the given scene."""
        idx = self._scene_order.index(scene_id) if scene_id in self._scene_order else -1
        if 0 <= idx < len(self._scene_order) - 1:
            return self._scenes[self._scene_order[idx + 1]]
        return None

    def get_character_scenes(self, character_name: str) -> list[str]:
        """Get all scene IDs where a character appears."""
        return [
            sid for sid, scene in self._scenes.items()
            if character_name in scene.characters
        ]

    def validate_continuity(self) -> list[str]:
        """Validate continuity across the scene graph.

        Returns a list of issues found.
        """
        issues: list[str] = []

        for i, scene_id in enumerate(self._scene_order):
            scene = self._scenes[scene_id]

            # Check time-of-day continuity
            if i > 0:
                prev = self._scenes[self._scene_order[i - 1]]
                time_progression = {
                    "dawn": 0, "morning": 1, "day": 2, "afternoon": 3,
                    "evening": 4, "dusk": 5, "night": 6,
                }
                prev_time = time_progression.get(prev.time_of_day, 2)
                curr_time = time_progression.get(scene.time_of_day, 2)
                if curr_time < prev_time - 1:
                    issues.append(
                        f"Scene '{scene_id}': Time jumps backward from "
                        f"'{prev.time_of_day}' to '{scene.time_of_day}'"
                    )

            # Check character consistency
            for char in scene.characters:
                if char in self._character_registry:
                    # Character should maintain consistent appearance
                    pass  # Visual consistency checked by prompt system

            # Check location transitions
            if i > 0:
                prev = self._scenes[self._scene_order[i - 1]]
                if prev.location != scene.location:
                    # Location change should have a transition
                    if scene_id not in prev.transitions_to:
                        issues.append(
                            f"Scene '{scene_id}': Location change from "
                            f"'{prev.location}' without explicit transition"
                        )

        return issues

    def generate_assembly_plan(self) -> dict[str, Any]:
        """Generate an assembly plan for video stitching."""
        total_duration = sum(
            self._scenes[sid].duration_seconds
            for sid in self._scene_order
        )

        scene_sequence = []
        for i, scene_id in enumerate(self._scene_order):
            scene = self._scenes[scene_id]
            transition_type = "cut"
            if i > 0:
                prev_id = self._scene_order[i - 1]
                # Determine transition from mood
                if scene.mood == "dramatic":
                    transition_type = "dissolve"
                elif scene.mood == "tense":
                    transition_type = "wipe"
                else:
                    transition_type = "fade"

            scene_sequence.append({
                "scene_id": scene_id,
                "title": scene.title,
                "duration_seconds": scene.duration_seconds,
                "transition_to_next": transition_type if i < len(self._scene_order) - 1 else None,
                "characters": scene.characters,
                "location": scene.location,
            })

        return {
            "title": self.title,
            "total_scenes": len(self._scene_order),
            "total_duration_seconds": total_duration,
            "scenes": scene_sequence,
            "characters": list(self._character_registry.keys()),
            "issues": self.validate_continuity(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Export the entire scene graph as a dictionary."""
        return {
            "title": self.title,
            "scenes": [self._scenes[sid].to_dict() for sid in self._scene_order],
            "global_visual_theme": self._global_visual_theme,
            "character_registry": self._character_registry,
        }
