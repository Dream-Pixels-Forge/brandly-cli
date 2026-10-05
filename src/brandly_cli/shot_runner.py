"""Resumable multi-shot film runner for ``brandly produce``.

Generates a full shot list (a flat array or a structured
``{"acts": {...}, "character": ...}`` production plan) one shot at a time,
honouring the Agnes 1 request/minute rate limit. The run is resumable:
every completed shot is recorded in a plain-text progress file, and a new
invocation of the same command skips those shots.

Schema
------
Flat (existing)::

    [{"name": "shot-1", "prompt": "...", "duration": 5,
      "style": "cinematic", "references": "a.png,b.png"}, ...]

Structured (acts with per-act prefix/style/folder and stem references)::

    {"character": "natural afro, ...",
     "acts": {"act1": {"name": "ACT I", "prefix": "Ink world: ...",
                        "style": "cinematic", "folder": "scenes",
                        "shots": [{"id": "shot01", "prompt": "...",
                                    "duration": 6,
                                    "refs": ["char_rebel", "loc_ink"]}]}}}

References may be explicit file paths/URLs or bare plate stems. Stems are
resolved under ``.brandly/<project>/images/<category>/<stem>`` (categories:
``character``, ``location``, ``prop``), preferring the optimized
``<stem>.opt.jpg`` twin over the full-size original.

Structured prompts (issue #31)
-------------------------------
A shot's ``prompt`` may be a plain string OR a dict using the film
direction framework (``subject, emotion, optics, motion, lighting, style,
audio, continuity`` plus the clip-chain sections ``performance``,
``physics``, ``locks``). Dict prompts are expanded via
``video_prompts.expand_structured_prompt``; unknown keys fail loudly at
flatten time.

Character presence (issue #38)
-------------------------------
Per-shot ``character`` (string or comma-separated) or ``characters`` (list)
declare which characters are PRESENT in the shot; only those appear in the
identity anchor. Shots without an explicit presence declaration fall back to
the top-level character string when they reference a character plate.

Retry/backoff logging (issue #39)
---------------------------------
When ``RunnerConfig.retries`` > 0, a failing shot is retried on the spot:
intermediate failures log ``RETRY retry=N backoff=Xs <reason>``, the
terminal failure logs ``FAIL retry=N <reason>``, and a successful retry logs
``OK retry=N``. ``completed_ids`` only trusts ``OK`` lines, so resume
behavior is unchanged.

Transition shots (``folder: "transition"``) have their generated clips
moved from ``videos/scenes/`` to ``videos/transition/`` so assembly
tooling can address them separately.

Clip naming
-----------
Every generated clip is renamed to a deterministic, assembly-friendly name::

    Scene-{scene:02d}-Shot-{scene}-{shot-in-scene}.mp4

e.g. the third shot of scene 1 becomes ``Scene-01-Shot-1-3.mp4`` and the
first shot of scene 2 becomes ``Scene-02-Shot-2-1.mp4``. The scene number
comes from an explicit ``"scene"`` key on the act (or on a single shot),
else the act's position in the shot list; the trailing number is the shot's
position inside its scene. A redo replaces the previous take of the same
scene/shot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brandly_cli import layout

#: Reference categories a shot may resolve bare plate stems against, searched
#: in priority order. Mirrors the generation-side ``layout.IMAGE_CATEGORIES``
#: for the categories that carry live consistency references:
#: ``character`` > ``location`` > ``prop`` > ``wardrobe``. The ``hq/`` master
#: sub-folder under each category is never searched - only the optimized
#: working twin sitting directly in the category root is eligible (see
#: ``resolve_plate`` / ``layout.HQ_DIRNAME``).
REF_CATEGORIES = ("character", "location", "prop", "wardrobe")
_PLATE_SUFFIXES = (".opt.jpg", ".opt.png", ".jpg", ".jpeg", ".png")
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

#: The strictest reference-image cap across the video models: Agnes Video 2.5
#: Flash server-validates at most 5 reference images
#: (``agnes_client.MAX_REFERENCE_IMAGES``) and hard-fails the create call
#: beyond it. The generator caps every shot's selection to this number so it
#: respects the model limit instead of erroring, keeping the
#: highest-priority references first.
MAX_SHOT_REFERENCE_IMAGES = 5
DEFAULT_INTERVAL = 60.0  # Agnes: 1 request per minute
PROGRESS_FILENAME = "produce_progress.txt"  # under <project>/docs/tmp/

#: Agnes video models silently clamp shots longer than this (issue #35):
#: the model max is 12s; plans requesting 8-12s come back as ~5-6s takes.
AGNES_MAX_SHOT_DURATION = 12
#: Default segment length when splitting over-long shots.
SPLIT_SEGMENT_DURATION = 6

# --- Duration truth (G7) ---
#: Legal provider max (12s) vs reliable max (~6s). 7-12s is a measured-risk zone.
RELIABLE_MAX_SHOT_DURATION = 6
#: Acceptable deviation: max(1s, 10% of requested).
DURATION_TOLERANCE_FACTOR = 0.10
DURATION_TOLERANCE_MIN = 1.0
#: Maximum number of continuation attempts per shot.
MAX_CONTINUATION_ATTEMPTS = 2

# --- Duration truth (G7) ---
#: Legal provider max (12s) vs reliable max (~6s). 7-12s is a measured-risk zone.
RELIABLE_MAX_SHOT_DURATION = 6
#: Acceptable deviation: max(1s, 10% of requested).
DURATION_TOLERANCE_FACTOR = 0.10
DURATION_TOLERANCE_MIN = 1.0
#: Status enum for a shot's duration fidelity.
DURATION_STATUSES: tuple[str, ...] = ("ok", "short", "continuation")


# --- Duration truth helpers (G7) ---

def duration_tolerance(requested_s: int | float) -> float:
    """Acceptable deviation: max(1s, 10% of requested)."""
    return max(DURATION_TOLERANCE_MIN, abs(requested_s) * DURATION_TOLERANCE_FACTOR)


def is_within_tolerance(requested: int | float, measured: float) -> bool:
    """True if measured duration is within tolerance of requested."""
    tol = duration_tolerance(requested)
    return abs(measured - requested) <= tol


def duration_status(requested_s: int | float, measured_s: float | None) -> str:
    """Classify a clip's duration fidelity.

    Returns "ok" if within tolerance (or unmeasured), "short" if measurably
    short beyond tolerance, "continuation" if a continuation take was added.
    """
    if measured_s is None:
        return "ok"  # unmeasured defaults to ok (legacy behaviour)
    if is_within_tolerance(requested_s, measured_s):
        return "ok"
    return "short"


# --- Probe helpers ---

def clip_filename(scene: int, index_in_scene: int, ext: str = ".mp4") -> str:
    """Canonical generated-clip name for a scene/shot pair.

    ``Scene-{scene:02d}-Shot-{scene}-{index_in_scene}{ext}`` — the first
    shot of scene 1 is ``Scene-01-Shot-1-1.mp4``.

    Note: this is the *base* name. ``Shot.clip_name`` may append an
    act-based disambiguator (issue #50) when two shots share the same
    ``(scene, index_in_scene)`` pair.
    """
    return f"Scene-{scene:02d}-Shot-{scene}-{index_in_scene}{ext}"


def _probe_video_duration(path: Path) -> float | None:
    """Return the duration of a video clip in seconds using ffprobe.

    Returns None if the file doesn't exist, isn't a valid video, or ffprobe fails.
    """
    import subprocess

    if not path.is_file():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None
        dur = streams[0].get("duration")
        return float(dur) if dur is not None else None
    except Exception:
        return None


def get_timeline(project_id: str, root: Path | str = ".") -> list[dict[str, Any]]:
    """Return a timeline view with measured vs requested durations.

    This reads the production plan and progress log to build a timeline view
    that includes measured vs requested durations and duration status.
    """
    from brandly_cli.planning import production_plan_path

    root_path = Path(root) if isinstance(root, str) else root
    plan_path = production_plan_path(project_id, root=root_path)
    if not plan_path.exists():
        return []

    import json

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    shots = plan.get("shots", [])

    # Read progress log for completed shots
    from brandly_cli.shot_runner import ProgressLog

    progress_log = ProgressLog(layout.docs_dir(layout.resolve_project_dir(Path("."), project_id), "tmp") / PROGRESS_FILENAME)
    completed = progress_log.completed_ids([])

    timeline = []
    for shot in shots:
        shot_id = shot.get("id") or shot.get("name")
        requested = shot.get("duration", 0)
        entry = {
            "shot_id": shot_id,
            "requested_s": requested,
            "measured_s": None,
            "delta_s": None,
            "duration_status": "pending",
        }
        if shot_id in completed:
            # Try to find the clip and measure it
            videos_root = layout.resolve_media_root(Path("."), project_id, "videos") / "scenes"
            clip_path = videos_root / clip_filename(shot.get("scene", 1), shot.get("index_in_scene", 1))
            if clip_path.exists():
                measured = _probe_video_duration(clip_path)
                entry["measured_s"] = measured
                if measured is not None:
                    entry["delta_s"] = round(measured - requested, 2)
                    entry["duration_status"] = duration_status(requested, measured)
        timeline.append(entry)

    return timeline


# --- Duration truth helpers (G7) ---

