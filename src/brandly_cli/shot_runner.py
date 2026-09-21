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
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REF_CATEGORIES = ("character", "location", "prop")
_PLATE_SUFFIXES = (".opt.jpg", ".opt.png", ".jpg", ".jpeg", ".png")
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
DEFAULT_INTERVAL = 60.0  # Agnes: 1 request per minute
PROGRESS_FILENAME = "produce_progress.txt"  # under <project>/docs/tmp/


def utcnow() -> str:
    """UTC timestamp for progress-file lines."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clip_filename(scene: int, index_in_scene: int, ext: str = ".mp4") -> str:
    """Canonical generated-clip name for a scene/shot pair.

    ``Scene-{scene:02d}-Shot-{scene}-{index_in_scene}{ext}`` — the first
    shot of scene 1 is ``Scene-01-Shot-1-1.mp4``.
    """
    return f"Scene-{scene:02d}-Shot-{scene}-{index_in_scene}{ext}"


def as_int(value: Any, default: int) -> int:
    """Best-effort int for optional ``scene``/``shot`` overrides in a shot list.

    Returns ``default`` when the value is missing or not numeric, so a typo in
    a hand-written shot list degrades to automatic numbering instead of
    aborting a long production run.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Shot:
    """One flattened, reference-resolved shot ready for generation."""

    id: str
    act: str
    style: str
    folder: str
    prompt: str
    duration: int
    refs: list[str] = field(default_factory=list)
    character: str | None = None
    scene: int = 1
    index_in_scene: int = 1

    @property
    def clip_name(self) -> str:
        """Canonical file name for this shot's generated clip."""
        return clip_filename(self.scene, self.index_in_scene)

    def to_video_kwargs(self) -> dict[str, Any]:
        """Fields understood by the standard ``video`` pipeline."""
        return {
            "name": self.id,
            "prompt": self.prompt,
            "duration": self.duration,
            "style": self.style,
            "references": self.refs,
        }


def resolve_plate(stem: str, images_dir: Path) -> Path:
    """Resolve a bare plate stem to an on-disk image under ``images_dir``.

    Searches each known category folder, preferring the optimized
    ``.opt.jpg`` twin (keeps reference payloads small on the free tier).
    Falls back to the unqualified stem at the ``images_dir`` root.

    Categories are searched in ``REF_CATEGORIES`` order, so when a stem exists
    in several categories (or as both an optimized twin and the original), the
    first match wins: ``character`` > ``location`` > ``prop``.
    """
    for category in REF_CATEGORIES:
        folder = images_dir / category
        if not folder.is_dir():
            continue
        for suffix in _PLATE_SUFFIXES:
            candidate = folder / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    for suffix in _PLATE_SUFFIXES:
        candidate = images_dir / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"reference plate not found: {stem!r} under {images_dir} "
        f"(categories: {', '.join(REF_CATEGORIES)})"
    )


def _ref_entries(shot: dict[str, Any], act: dict[str, Any], data: dict[str, Any]) -> list[str]:
    """Reference entries: per-shot > per-act > top-level, paths or stems.

    An explicit empty ``refs``/``references`` list on a shot means "no
    references" and opts that shot out of the act/top-level lists (the
    fallback only applies when the key is absent).
    """
    raw = shot.get("refs", shot.get("references"))
    if raw is None:
        raw = act.get("refs", act.get("ref"))
    if raw is None:
        raw = data.get("refs", data.get("ref")) or []
    if isinstance(raw, str):
        return [r.strip() for r in raw.split(",") if r.strip()]
    if isinstance(raw, Sequence):
        return [str(r).strip() for r in raw if str(r).strip()]
    return []


def flatten_shots(
    data: dict[str, Any] | list[dict[str, Any]],
    images_dir: Path,
    character: str | None = None,
) -> list[Shot]:
    """Flatten a flat or structured shot list into production order.

    ``acts`` are iterated in their JSON key order; per-act ``prefix`` is
    prepended to each shot prompt, per-act ``style``/``folder`` default the
    shot, and a character identity string is attached as the anchor
    whenever the shot's resolved references include a character plate
    (shots with no character plate are left anchor-free). The anchor comes
    from the explicit ``character`` argument, else the shot list's
    top-level ``"character"``, else a per-shot ``"character"`` key.
    """
    if isinstance(data, list):
        acts: list[dict[str, Any]] = [{"name": "shots", "shots": data}]
        top_level: dict[str, Any] = {}
    else:
        acts = [
            {"name": act_key, **act}
            for act_key, act in (data.get("acts") or {}).items()
        ]
        top_level = data

    global_character = character or top_level.get("character")
    shots: list[Shot] = []
    for act_position, act in enumerate(acts, start=1):
        act_name = str(act.get("name", act.get("act", "")))
        # Scene number: explicit act key, else the act's position in the list.
        act_scene = as_int(act.get("scene"), act_position)
        prefix = str(act.get("prefix", ""))
        default_style = str(act.get("style", "cinematic"))
        default_folder = str(act.get("folder", "scenes"))
        for shot_position, shot in enumerate(act.get("shots", []), start=1):
            shot_id = str(shot.get("id") or shot.get("name") or f"shot-{len(shots) + 1}")
            entries = _ref_entries(shot, act, top_level)
            refs: list[str] = []
            has_character_plate = False
            for entry in entries:
                basename = entry.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                if (
                    "/" in entry
                    or "\\" in entry
                    or "://" in entry
                    or basename.lower().endswith(_IMAGE_EXTS)
                ):
                    refs.append(entry)  # explicit path or URL, use as-is
                else:
                    path = resolve_plate(entry, images_dir)
                    refs.append(str(path))
                    if path.parent.name == "character":
                        has_character_plate = True
            character_anchor: str | None = None
            if shot.get("character"):
                character_anchor = str(shot["character"])
            elif has_character_plate and global_character:
                character_anchor = str(global_character)
            shots.append(
                Shot(
                    id=shot_id,
                    act=act_name,
                    style=str(shot.get("style", default_style)),
                    folder=str(shot.get("folder", default_folder)),
                    prompt=prefix + str(shot.get("prompt", "")),
                    duration=int(shot.get("duration", 5)),
                    refs=refs,
                    character=character_anchor,
                    scene=as_int(shot.get("scene"), act_scene),
                    index_in_scene=shot_position,
                )
            )
    return shots


@dataclass
class ProgressLog:
    """Plain-text resumable progress file.

    One line per finished shot::

        2026-09-21T00:22:44Z shot16 OK exit=0
        2026-09-21T00:28:41Z shot17 OK exit=1 (clip downloaded; post-gen gate step failed)

    A shot id followed by ``OK`` is terminal (skipped on resume); ``FAIL``
    lines are history only.
    """

    path: Path

    def completed_ids(self, known: Iterable[str]) -> set[str]:
        """Shot ids already recorded as terminal (``OK``) in the progress file.

        Lines are ``<ts> <shot-id> <OK|FAIL> exit=<n> [note]``; only the
        shot-id field followed by the status field is trusted, so free-text
        notes can never accidentally mark a shot complete.
        """
        if not self.path.is_file():
            return set()
        known_set = set(known)
        done: set[str] = set()
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] in known_set and parts[2] == "OK":
                done.add(parts[1])
        return done

    def record(self, shot_id: str, status: str, exit_code: int | None, note: str = "") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(f"{utcnow()} {shot_id} {status} exit={exit_code}{note}\n")


@dataclass
class RunnerConfig:
    """Everything ``run_shots`` needs — assembled by the CLI layer."""

    shots: list[Shot]
    generate_one: Callable[[Shot], tuple[bool, int, str]]
    """Returns ``(succeeded, exit_code, note)`` for a single shot. A
    ``False`` with a non-empty note counts as recovered (the artifact
    exists even though a post-generation step failed)."""
    scenes_dir: Path
    progress: ProgressLog
    interval: float = DEFAULT_INTERVAL
    only: set[str] | None = None
    max_shots: int = 0
    say: Callable[[str], None] = lambda _msg: None

    def move_shot_clips(self, shot: Shot, new_clips: Sequence[Path]) -> list[Path]:
        """After generating ``shot``, relocate its clips when the shot is a
        transition (``folder: "transition"``)."""
        if shot.folder != "transition" or not new_clips:
            return []
        target_dir = self.scenes_dir.parent / "transition"
        target_dir.mkdir(parents=True, exist_ok=True)
        moved: list[Path] = []
        for clip in new_clips:
            target = target_dir / clip.name
            if target.exists():
                self.say(f"replacing previous transition take -> {target.name}")
            clip.replace(target)
            self.say(f"moved transition clip -> {target}")
            moved.append(target)
        return moved


def name_clips(
    shot: Shot,
    clips: Sequence[Path],
    say: Callable[[str], None] | None = None,
) -> list[Path]:
    """Rename freshly downloaded clips to the canonical Scene-XX-Shot-X-Y name.

    The first clip (sorted) takes the canonical name; extra clips from the
    same shot get a ``-2``/``-3``… suffix so nothing is silently dropped. An
    existing file under the canonical name is replaced — a redo is meant to
    supersede the previous take of that scene/shot.
    """
    renamed: list[Path] = []
    for position, clip in enumerate(sorted(clips), start=1):
        if position == 1:
            target = clip.with_name(shot.clip_name)
        else:
            stem = Path(shot.clip_name).stem
            target = clip.with_name(f"{stem}-{position}{clip.suffix}")
        if clip != target:
            target.parent.mkdir(parents=True, exist_ok=True)
            clip.replace(target)
            if say is not None:
                say(f"{clip.name} -> {target.name}")
        renamed.append(target)
    return renamed


def _clip_snapshot(scenes: Path) -> dict[str, int]:
    """Map clip file name -> modification time (ns) in ``scenes``.

    Comparing snapshots detects both a newly downloaded clip and a redo that
    overwrote the same canonical name in place.
    """
    if not scenes.is_dir():
        return {}
    return {
        p.name: p.stat().st_mtime_ns for p in scenes.glob("*.mp4") if p.is_file()
    }


def _new_clips(scenes: Path, before: Mapping[str, int]) -> list[Path]:
    """Clips that appeared or were rewritten since ``before``.

    Zero-byte files are ignored: a stranded/truncated download is not proof
    that a shot produced an artifact.
    """
    fresh = sorted(
        scenes / name
        for name, mtime in _clip_snapshot(scenes).items()
        if before.get(name) != mtime
    )
    return [p for p in fresh if p.stat().st_size > 0]


def run_shots(config: RunnerConfig) -> int:
    """Run every pending shot, stop on first unrecovered failure.

    Returns 0 when all pending shots finished, 1 when a shot failed and the
    run stopped (re-run the same command to resume — completed shots are
    recorded in the progress file).
    """
    shots = config.shots
    done = config.progress.completed_ids(s.id for s in shots)
    if config.only:
        # `--only` means "redo exactly these takes": drop them from the
        # progress-file skip list so a bad take can be regenerated.
        done -= config.only
    pending = [s for s in shots if s.id not in done]
    if config.only:
        pending = [s for s in pending if s.id in config.only]
    if config.max_shots:
        pending = pending[: config.max_shots]

    config.say(f"pending: {len(pending)} of {len(shots)} shots (done: {len(done)})")
    scenes = config.scenes_dir
    for i, shot in enumerate(pending):
        if i > 0:
            config.say(
                f"rate limit: waiting {config.interval:.0f}s before {shot.id}..."
            )
            time.sleep(config.interval)
        before = _clip_snapshot(scenes)
        succeeded, exit_code, note = config.generate_one(shot)
        new_clips = _new_clips(scenes, before)
        ok = succeeded or bool(new_clips)
        if ok and not succeeded:
            note = (note + " " if note else "") + "(clip downloaded; post-gen step failed)"
        config.progress.record(
            shot.id,
            "OK" if ok else "FAIL",
            exit_code,
            f" {note}" if note and ok else "",
        )
        config.say(f"{shot.id} {'OK' if ok else 'FAIL'} exit={exit_code}" + (f" {note}" if note and ok else ""))
        if ok:
            # Deterministic Scene-XX-Shot-X-Y name, then any transition move.
            config.move_shot_clips(shot, name_clips(shot, new_clips, config.say))
        else:
            config.say(
                f"STOP: {shot.id} failed. Fix and re-run to resume "
                f"(remaining shots stay pending)."
            )
            return 1
    config.say("all pending shots complete")
    return 0


def load_shots_file(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    """Load and minimally validate a shot list JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        if not raw or not all(isinstance(s, dict) for s in raw):
            raise ValueError("flat shot list must be a non-empty array of objects")
        return raw
    if isinstance(raw, dict):
        if not raw.get("acts"):
            raise ValueError("structured shot list must define a non-empty 'acts' mapping")
        return raw
    raise ValueError("shot list must be a JSON array or an object with 'acts'")
