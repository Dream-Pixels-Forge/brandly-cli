"""Production tools — director, cascade, DoP, editor.

Tools map to skills:

* ``director`` → ``brandly-film-director``
* ``cascade`` → ``brandly-storyboard`` (plus fight choreography for film action)
* ``director_of_photography`` → ``brandly-camera``
* ``editor`` → ``dpf-senior-editor``
* ``fight_choreography`` → fight-scene skill (JKD combat for AI video)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brandly_cli.agnes_client import create_video_task
from brandly_cli.async_compat import run_async
from brandly_cli.io import now_iso, write_json
from brandly_cli.layout import project_dir
from brandly_cli.types import (
    CascadeFightStage,
    CascadeStage,
    DirectorOfPhotography,
    EditDecision,
    FightBeat,
    FightChoreography,
    Fighter,
    ShotDirection,
)

# ---------------------------------------------------------------------------
# Film-action fight choreography — beat patterns for AI video.
#
# Every fight is broken into beats of roughly 1-2 seconds. An 8-second shot
# holds 4-6 beats maximum, including 1-2 beats of stance/pause. Prompts are
# Seedance-proof: pure body geometry, zero martial-arts terminology, zero
# prohibitions, physics of consequences. Every fight prompt ends with the
# identical FIGHT STYLE LOCK.
# ---------------------------------------------------------------------------

#: Style lock appended verbatim to every fight prompt. Identical wording across
#: all scenes so the model learns the style by repetition.
FIGHT_STYLE_LOCK = (
    "FIGHT STYLE LOCK: every kick stays below belt height; every punch travels "
    "a short straight line launched from where the hands already rest at guard "
    "— the first visible motion of a limb IS the strike itself; between "
    "exchanges the fighter is completely still in his narrow side-on stance; "
    "the fight is short straight lines and long stillness."
)

#: Beat patterns — ready-to-use structures translated from choreography theory
#: into prompt language. Each beat: (position, action, reaction, new_position,
#: start_seconds, end_seconds).
BEAT_PATTERNS: dict[str, list[tuple[str, str, str, str, float, float]]] = {
    # P1: Intercepting a Single Attack — 4-6 sec
    "P1": [
        ("side-on stance, weight on balls of feet, lead hand half-extended",
         "opponent throws a sweeping haymaker",
         "straight lead lands on the jaw at the moment of the windup, opponent's strike dies halfway",
         "opponent staggers back, hero returns to stance", 0.0, 1.5),
        ("opponent reeling backward",
         "hero settles back into the narrow side-on stance and goes completely still",
         "stillness holds a full second",
         "hero motionless", 1.5, 3.0),
        ("hero still in stance",
         "opponent lunges again with a wide right swing",
         "stop-hit straight lead mid-motion, opponent's own punch dying halfway",
         "opponent's head whips back, staggers two steps", 3.0, 4.5),
        ("opponent falling backward",
         "hero remains still in stance",
         "stillness holds",
         "hero motionless", 4.5, 6.0),
    ],
    # P2: Kick-to-Punch Entry (Long → Medium Range) — 6-8 sec
    "P2": [
        ("side-on stance, circling in an arc on small fencing steps",
         "opponent steps forward",
         "low side kick from the lead leg spears into the knee; leg buckles, opponent pitches forward",
         "opponent pitching forward", 0.0, 1.5),
        ("opponent pitching forward",
         "straight lead or lead hook to the jaw",
         "head snaps back hard, two steps backward",
         "opponent falls past the hero", 1.5, 3.0),
        ("opponent falling past",
         "hero settles back into stance and goes completely still",
         "stillness holds a full second",
         "hero motionless", 3.0, 4.5),
    ],
    # P3: Trap-Combo (Medium → Close Range) — 6-8 sec
    "P3": [
        ("side-on stance",
         "opponent throws a straight punch",
         "left palm slaps the guard down while the right fist fires through the opening in the same beat",
         "opponent sways", 0.0, 1.5),
        ("opponent sways, attempts a second strike",
         "wrist pull jerks the man forward into a short punch — pull and hit landing as one motion",
         "opponent jerked forward and down",
         "opponent falling past", 1.5, 3.0),
        ("opponent falling past",
         "hero releases the hand, stillness",
         "stillness holds",
         "hero motionless", 3.0, 4.5),
    ],
    # P4: Straight Blast Finish (Pressure) — 4-6 sec
    "P4": [
        ("opponent stunned, losing structure",
         "chain of vertical-fist punches piston down the centerline, hero surging forward",
         "opponent retreats without time to recover structure",
         "opponent stumbling backward", 0.0, 1.5),
        ("opponent retreating",
         "side kick slams into the sternum",
         "entire body flies backward 2-3 meters into an obstacle",
         "opponent against obstacle", 1.5, 3.0),
        ("opponent against obstacle",
         "hero remains still in stance",
         "stillness holds",
         "hero motionless", 3.0, 4.5),
    ],
}

#: Camera rules for action — profile/three-quarter for straight punches, wide
#: enough to show legs for kicks, long fixed shots instead of montage cuts.
CAMERA_RULES: dict[str, str] = {
    "punch": "profile or three-quarter view, chest-up close-up, long fixed shot",
    "kick": "wide shot showing the legs, profile view, long fixed shot",
    "exchange": "three-quarter view, long fixed shot, no montage cuts",
}

#: Per-strike reaction physics — mandatory in prompts so the model registers contact.
STRIKE_REACTIONS: dict[str, str] = {
    "straight_lead_to_jaw": "head snaps backward, one or two steps back, sinking down",
    "side_kick_to_body": "entire body flies backward, 2-3 meters, into an obstacle",
    "finger_jab_to_eyes": "flinches back, both hands flying to his face, eyes screwed shut",
    "low_kick_to_knee": "leg buckles, he pitches forward",
    "backfist_to_temple": "head snaps sideways",
    "hook_to_jaw": "head jerks to the side, stumbling",
}


def build_fight_prompt(
    project_id: str,
    scene_id: str,
    fighters: list[dict[str, Any]],
    pattern: str = "P1",
    duration: int = 6,
    location: str = "",
    emotion: str = "",
    winner: str = "",
) -> dict[str, Any]:
    """Build a Seedance-proof fight-choreography prompt from beat patterns.

    Returns a dict with ``beats`` (list of beat dicts), ``prompt`` (the full
    packaged prompt), ``style_lock``, and ``shots`` (camera notes per beat).
    """
    pattern_beats = BEAT_PATTERNS.get(pattern, BEAT_PATTERNS["P1"])
    num_beats = min(len(pattern_beats), max(2, int(round(duration / 1.5))))

    beats: list[dict[str, Any]] = []
    prompt_parts: list[str] = []

    hero = fighters[0] if fighters else {}
    hero_desc = hero.get("description", "the fighter")
    hero_lead = hero.get("lead_hand", "right")

    # Opening stance — full body geometry in the first frame (no terminology).
    stance_line = (
        f"{hero_desc} stands almost side-on, {hero_lead} shoulder and "
        f"{hero_lead} foot leading, feet just past shoulder width, rear heel "
        f"floating off the ground, knees softly bent, weight riding the balls "
        f"of both feet with a light constant spring. His lead hand floats "
        f"half-extended at shoulder height, rear fist rests at his chin, "
        f"elbows close to the ribs, chin tucked, eyes steady over the lead "
        f"shoulder, face calm and unreadable."
    )

    for i in range(num_beats):
        position, action, reaction, new_position, start_t, end_t = pattern_beats[min(i, len(pattern_beats) - 1)]
        beat_num = i + 1
        camera = CAMERA_RULES["kick"] if "kick" in action.lower() else CAMERA_RULES["punch"]

        beats.append({
            "beat_number": beat_num,
            "start_time": start_t,
            "end_time": end_t,
            "position": position,
            "action": action,
            "reaction": reaction,
            "new_position": new_position,
            "camera_angle": "profile" if "kick" in action.lower() else "three_quarter",
            "shot_size": "wide" if "kick" in action.lower() else "medium",
        })

        prompt_parts.append(
            f"BEAT {beat_num} ({start_t}-{end_t}s): {position}. {action}. "
            f"{reaction}. {new_position}. {camera}."
        )

    prompt_parts.insert(0, stance_line)
    prompt_parts.append(FIGHT_STYLE_LOCK)
    prompt = " ".join(prompt_parts)

    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "pattern": pattern,
        "duration": duration,
        "beats": beats,
        "prompt": prompt,
        "style_lock": FIGHT_STYLE_LOCK,
        "location": location,
        "emotion": emotion,
        "winner": winner,
        "fighters": fighters,
    }


# ---------------------------------------------------------------------------
# Tool: director
# ---------------------------------------------------------------------------

def _director(
    project_id: str,
    shot_id: str,
    scene_id: str,
    prompt: str,
    model: str = "agnes-video-2.5-flash",
    style: str = "cinematic",
    duration: int = 5,
    aspect_ratio: str = "16:9",
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    reference_roles: list[str] | None = None,
    camera_notes: str = "",
    lighting_notes: str = "",
    sound_notes: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Director's shot-by-shot direction — creates a video task with full
    directorial control (camera, lighting, sound, references, style).

    Cinematic style defaults to 21:9 aspect ratio.
    """
    # Cinematic-category styles enforce 21:9 by default.
    if style in ("cinematic", "short-film") and aspect_ratio == "16:9":
        aspect_ratio = "21:9"

    try:
        direction = ShotDirection(
            shot_id=shot_id,
            scene_id=scene_id,
            prompt=prompt,
            model=model,
            style=style,
            duration=duration,
            aspect_ratio=aspect_ratio,
            first_frame=first_frame,
            last_frame=last_frame,
            reference_images=reference_images or [],
            reference_roles=reference_roles or [],
            camera_notes=camera_notes,
            lighting_notes=lighting_notes,
            sound_notes=sound_notes,
            created_at=now_iso(),
        )
        result = run_async(
            create_video_task(
                prompt,
                model=model,
                mode="reference" if reference_images else "text",
                duration=duration,
                aspect_ratio=aspect_ratio,
                size="720P",
                first_frame=first_frame,
                last_frame=last_frame,
                reference_images=reference_images,
            )
        )
        return {
            "project_id": project_id,
            "shot_id": shot_id,
            "scene_id": scene_id,
            "video_id": result.get("video_id"),
            "status": result.get("status"),
            "mode": result.get("mode"),
            "aspect_ratio": aspect_ratio,
            "direction": direction.model_dump(),
        }
    except Exception as e:
        return {"error": f"director: {e}"}


# ---------------------------------------------------------------------------
# Tool: cascade
# ---------------------------------------------------------------------------

def _cascade(
    project_id: str,
    stages: list[dict[str, Any]],
    root: str | None = None,
) -> dict[str, Any]:
    """Run a cinematic high-end cascade pipeline.

    Executes stages sequentially through the phase chain
    (trends → concept → bible → casting → screenplay → script → asset
    → audio → re_edit → validate → publish), with per-stage gates.
    """
    try:
        from brandly_cli.io import now_iso as _now_iso

        proj_dir = project_dir(Path(root or "."), project_id)
        general_dir = proj_dir / "docs" / "general"
        general_dir.mkdir(parents=True, exist_ok=True)

        cascade_stages: list[dict[str, Any]] = []
        stage: Any
        for s in stages:
            fight = s.get("fight_choreography")
            if fight:
                choreo = build_fight_prompt(
                    project_id=project_id,
                    scene_id=s.get("scene_id", ""),
                    fighters=fight.get("fighters", []),
                    pattern=fight.get("pattern", "P1"),
                    duration=fight.get("duration", 6),
                    location=fight.get("location", ""),
                    emotion=fight.get("emotion", ""),
                    winner=fight.get("winner", ""),
                )
                s["input"]["fight_prompt"] = choreo["prompt"]
                s["input"]["beats"] = choreo["beats"]
                s["input"]["style_lock"] = choreo["style_lock"]
                stage = CascadeFightStage(
                    name=s.get("name", ""),
                    phase=s.get("phase", "init"),
                    tool=s.get("tool", ""),
                    input=s.get("input", {}),
                    output={},
                    status="pending",
                    gate_passed=None,
                    fight_choreography=FightChoreography(
                        project_id=project_id,
                        scene_id=s.get("scene_id", ""),
                        fighters=[Fighter(**f) for f in fight.get("fighters", [])],
                        pattern=fight.get("pattern", "P1"),
                        shot_duration=fight.get("duration", 6),
                        location=fight.get("location", ""),
                        emotion=fight.get("emotion", ""),
                        winner=fight.get("winner", ""),
                        beats=[
                            FightBeat(
                                beat_number=b["beat_number"],
                                start_time=b["start_time"],
                                end_time=b["end_time"],
                                position=b["position"],
                                action=b["action"],
                                reaction=b["reaction"],
                                new_position=b["new_position"],
                                camera_angle=b["camera_angle"],
                                shot_size=b["shot_size"],
                            )
                            for b in choreo["beats"]
                        ],
                        created_at=_now_iso(),
                        updated_at=_now_iso(),
                    ),
                    created_at=_now_iso(),
                )
            else:
                stage = CascadeStage(
                    name=s.get("name", ""),
                    phase=s.get("phase", "init"),
                    tool=s.get("tool", ""),
                    input=s.get("input", {}),
                    output={},
                    status="pending",
                    gate_passed=None,
                    created_at=_now_iso(),
                )
            cascade_stages.append(stage.model_dump())

        path = general_dir / f"cascade_{project_id}.json"
        write_json(path, {
            "project_id": project_id,
            "stages": cascade_stages,
            "updated_at": _now_iso(),
        })
        return {
            "project_id": project_id,
            "stage_count": len(cascade_stages),
            "path": str(path),
            "phases": [s.get("phase", "") for s in stages],
        }
    except Exception as e:
        return {"error": f"cascade: {e}"}


# ---------------------------------------------------------------------------
# Tool: director_of_photography
# ---------------------------------------------------------------------------

def _director_of_photography(
    project_id: str,
    shot_id: str,
    lens: str = "50mm",
    aperture: str = "f/2.8",
    lighting_setup: str = "three_point",
    color_grade: str = "cinematic",
    composition: str = "rule_of_thirds",
    camera_move: str = "static",
    notes: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """DoP specifications for a shot — lens, aperture, lighting, grade,
    composition, camera move."""
    try:
        proj_dir = project_dir(Path(root or "."), project_id)
        dop_dir = proj_dir / "docs" / "general"
        dop_dir.mkdir(parents=True, exist_ok=True)

        dop = DirectorOfPhotography(
            shot_id=shot_id,
            lens=lens,
            aperture=aperture,
            lighting_setup=lighting_setup,
            color_grade=color_grade,
            composition=composition,
            camera_move=camera_move,
            notes=notes,
        )
        path = dop_dir / f"dop_{shot_id}.json"
        write_json(path, dop.model_dump())
        return {
            "project_id": project_id,
            "shot_id": shot_id,
            "lens": lens,
            "lighting_setup": lighting_setup,
            "color_grade": color_grade,
            "composition": composition,
            "camera_move": camera_move,
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"director_of_photography: {e}"}


# ---------------------------------------------------------------------------
# Tool: editor
# ---------------------------------------------------------------------------

def _editor(
    project_id: str,
    clip_id: str,
    start_time: float = 0.0,
    end_time: float = 0.0,
    transition: str = "cut",
    transition_duration: float = 0.5,
    color_grade: str = "none",
    volume: float = 1.0,
    root: str | None = None,
) -> dict[str, Any]:
    """Editor's cut decision for a clip — trim, transition, grade, volume."""
    try:
        proj_dir = project_dir(Path(root or "."), project_id)
        edit_dir = proj_dir / "docs" / "tmp"
        edit_dir.mkdir(parents=True, exist_ok=True)

        decision = EditDecision(
            clip_id=clip_id,
            start_time=start_time,
            end_time=end_time,
            transition=transition,
            transition_duration=transition_duration,
            color_grade=color_grade,
            volume=volume,
            created_at=now_iso(),
        )
        path = edit_dir / f"edit_{clip_id}.json"
        write_json(path, decision.model_dump())
        return {
            "project_id": project_id,
            "clip_id": clip_id,
            "start_time": start_time,
            "end_time": end_time,
            "transition": transition,
            "color_grade": color_grade,
            "volume": volume,
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"editor: {e}"}


# ---------------------------------------------------------------------------
# Tool registry — production domain
# ---------------------------------------------------------------------------

# Tool: fight_choreography
# ---------------------------------------------------------------------------


def _fight_choreography(
    project_id: str,
    scene_id: str,
    fighters: list[dict[str, Any]],
    pattern: str = "P1",
    duration: int = 6,
    location: str = "",
    emotion: str = "",
    winner: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Build a Seedance-proof fight-choreography prompt from beat patterns.

    JKD-derived: interception over blocking, economy of motion, non-telegraphed
    strikes, low kicks, broken rhythm. Prompts use pure body geometry, zero
    martial-arts terminology, zero prohibitions, physics of consequences.
    """
    try:
        from brandly_cli.io import now_iso as _now_iso

        choreo = build_fight_prompt(
            project_id=project_id,
            scene_id=scene_id,
            fighters=fighters,
            pattern=pattern,
            duration=duration,
            location=location,
            emotion=emotion,
            winner=winner,
        )

        # Persist to docs/general for the cascade pipeline to consume.
        proj_dir = project_dir(Path(root or "."), project_id)
        general_dir = proj_dir / "docs" / "general"
        general_dir.mkdir(parents=True, exist_ok=True)
        path = general_dir / f"fight_choreography_{scene_id}.json"
        write_json(
            path,
            {
                "project_id": project_id,
                "scene_id": scene_id,
                "pattern": pattern,
                "duration": duration,
                "location": location,
                "emotion": emotion,
                "winner": winner,
                "prompt": choreo["prompt"],
                "beats": choreo["beats"],
                "style_lock": choreo["style_lock"],
                "created_at": _now_iso(),
            },
        )

        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "pattern": pattern,
            "duration": duration,
            "prompt": choreo["prompt"],
            "beats": choreo["beats"],
            "style_lock": choreo["style_lock"],
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"fight_choreography: {e}"}


BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "director": {
        "handler": _director,
        "schema": {
            "type": "object",
            "title": "Director",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shot_id": {"type": "string", "description": "Shot id."},
                "scene_id": {"type": "string", "description": "Scene id."},
                "prompt": {"type": "string", "description": "Shot direction prompt."},
                "model": {
                    "type": "string",
                    "default": "agnes-video-2.5-flash",
                    "description": "Video model.",
                },
                "style": {
                    "type": "string",
                    "default": "cinematic",
                    "description": "Video style (cinematic, short-film, ugc, ...).",
                },
                "duration": {"type": "integer", "default": 5, "description": "Shot duration in seconds."},
                "aspect_ratio": {
                    "type": "string",
                    "default": "16:9",
                    "description": "Aspect ratio (cinematic style defaults to 21:9).",
                },
                "first_frame": {"type": "string", "description": "First frame image path (keyframe mode)."},
                "last_frame": {"type": "string", "description": "Last frame image path (keyframe mode)."},
                "reference_images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reference images for consistency.",
                },
                "reference_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reference image roles (character, environment, prop, ...).",
                },
                "camera_notes": {"type": "string", "description": "DoP camera notes."},
                "lighting_notes": {"type": "string", "description": "Lighting notes."},
                "sound_notes": {"type": "string", "description": "Sound notes."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "shot_id", "scene_id", "prompt"],
        },
        "description": "Director's shot-by-shot direction — creates a video task with full directorial control.",
    },
    "cascade": {
        "handler": _cascade,
        "schema": {
            "type": "object",
            "title": "Cascade",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phase": {"type": "string"},
                            "tool": {"type": "string"},
                            "input": {"type": "object"},
                        },
                        "required": ["name", "phase", "tool"],
                    },
                    "description": "Cascade stages mapped to brandly tools and phases.",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "stages"],
        },
        "description": (
            "Run a cinematic high-end cascade pipeline through the phase chain "
            "(trends → concept → bible → casting → screenplay → script → asset "
            "→ audio → re_edit → validate → publish) with per-stage gates."
        ),
    },
    "director_of_photography": {
        "handler": _director_of_photography,
        "schema": {
            "type": "object",
            "title": "Director of Photography",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shot_id": {"type": "string", "description": "Shot id."},
                "lens": {"type": "string", "default": "50mm", "description": "Lens focal length."},
                "aperture": {"type": "string", "default": "f/2.8", "description": "Aperture."},
                "lighting_setup": {
                    "type": "string",
                    "default": "three_point",
                    "description": "Lighting setup (three_point, natural, dramatic, golden_hour).",
                },
                "color_grade": {"type": "string", "default": "cinematic", "description": "Color grade."},
                "composition": {
                    "type": "string",
                    "default": "rule_of_thirds",
                    "description": "Composition rule.",
                },
                "camera_move": {
                    "type": "string",
                    "default": "static",
                    "description": "Camera movement (static, pan, tilt, dolly, tracking, orbital).",
                },
                "notes": {"type": "string", "description": "Additional DoP notes."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "shot_id"],
        },
        "description": "DoP specifications for a shot — lens, aperture, lighting, grade, composition, camera move.",
    },
    "editor": {
        "handler": _editor,
        "schema": {
            "type": "object",
            "title": "Editor",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "clip_id": {"type": "string", "description": "Clip id."},
                "start_time": {"type": "number", "default": 0.0, "description": "Edit start time."},
                "end_time": {"type": "number", "default": 0.0, "description": "Edit end time."},
                "transition": {
                    "type": "string",
                    "default": "cut",
                    "description": "Transition type (cut, fade, wipe, dissolve).",
                },
                "transition_duration": {"type": "number", "default": 0.5, "description": "Transition duration."},
                "color_grade": {"type": "string", "default": "none", "description": "Color grade."},
                "volume": {"type": "number", "default": 1.0, "description": "Volume level."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "clip_id"],
        },
        "description": "Editor's cut decision for a clip — trim, transition, grade, volume for stitch/assembly.",
    },
    "fight_choreography": {
        "handler": _fight_choreography,
        "schema": {
            "type": "object",
            "title": "Fight Choreography",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "scene_id": {"type": "string", "description": "Scene id."},
                "fighters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Fighter name."},
                            "role": {"type": "string", "description": "Role: hero, opponent, master, student."},
                            "lead_hand": {"type": "string", "description": "Strong side forward: right or left."},
                            "style": {"type": "string", "description": "Fighting style: jkd, wing_chun, classical, street."},
                            "description": {"type": "string", "description": "Physical description for body geometry."},
                        },
                        "required": ["name", "role"],
                    },
                    "description": "Fighters in the scene.",
                },
                "pattern": {
                    "type": "string",
                    "description": "Beat pattern: P1 (intercept), P2 (kick-to-punch), P3 (trap-combo), P4 (straight blast).",
                },
                "duration": {"type": "integer", "default": 6, "description": "Shot duration in seconds."},
                "location": {"type": "string", "description": "Where the fight takes place."},
                "emotion": {"type": "string", "description": "Emotional tone of the exchange."},
                "winner": {"type": "string", "description": "Who wins the fight."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "scene_id", "fighters"],
        },
        "description": "Build a Seedance-proof fight-choreography prompt from beat patterns (JKD-derived).",
    },
}
# ---------------------------------------------------------------------------
