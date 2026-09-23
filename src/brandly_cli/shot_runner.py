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
A shot's ``prompt`` may be a plain string OR a dict using the 8-layer film
direction framework (``subject, emotion, optics, motion, lighting, style,
audio, continuity``). Dict prompts are expanded via
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
import math
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REF_CATEGORIES = ("character", "location", "prop")
_PLATE_SUFFIXES = (".opt.jpg", ".opt.png", ".jpg", ".jpeg", ".png")
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
DEFAULT_INTERVAL = 60.0  # Agnes: 1 request per minute
PROGRESS_FILENAME = "produce_progress.txt"  # under <project>/docs/tmp/

#: Agnes video models silently clamp shots longer than this (issue #35):
#: the model max is 12s; plans requesting 8-12s come back as ~5-6s takes.
AGNES_MAX_SHOT_DURATION = 12
#: Default segment length when splitting over-long shots.
SPLIT_SEGMENT_DURATION = 6


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
            # Issue #38: presence-declared characters win — only those that
            # are actually in the shot go into the identity anchor.
            present = shot.get("characters")
            if isinstance(present, str):
                present = [p for p in (c.strip() for c in present.split(",")) if p]
            if isinstance(present, (list, tuple)) and present:
                character_anchor = ", ".join(str(c) for c in present)
            elif shot.get("character"):
                character_anchor = str(shot["character"])
            elif has_character_plate and global_character:
                character_anchor = str(global_character)

            # Issue #31: structured 8-layer prompt dicts expand to text here.
            raw_prompt = shot.get("prompt", "")
            if isinstance(raw_prompt, Mapping):
                from brandly_cli.video_prompts import expand_structured_prompt

                try:
                    raw_prompt = expand_structured_prompt(
                        raw_prompt,
                        character=character_anchor,
                        duration=int(shot.get("duration", 5)),
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"shot {shot_id!r}: {exc}"
                    ) from exc

            shots.append(
                Shot(
                    id=shot_id,
                    act=act_name,
                    style=str(shot.get("style", default_style)),
                    folder=str(shot.get("folder", default_folder)),
                    prompt=prefix + str(raw_prompt),
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

        Lines are ``<ts> <shot-id> <OK|RETRY|FAIL> exit=<n> [retry=N] [note]``;
        only the shot-id field followed by the status field is trusted, so
        free-text notes can never accidentally mark a shot complete.
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

    def record(
        self,
        shot_id: str,
        status: str,
        exit_code: int | None,
        note: str = "",
        retry: int = 0,
        backoff: float = 0.0,
    ) -> None:
        """Append one line: ``<ts> <id> <status> exit=<n> [retry=N backoff=Xs] [note]``.

        ``RETRY`` marks an intermediate failure that will be retried; ``FAIL``
        marks a terminal failure (after all retries). Both carry the retry
        count, backoff delay, and failure reason so a reader of the log can
        reconstruct exactly what happened between two lines (issue #39).
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        extras = ""
        if retry > 0:
            extras = f" retry={retry}"
            if backoff > 0:
                extras += f" backoff={backoff:.0f}s"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(f"{utcnow()} {shot_id} {status} exit={exit_code}{extras}{note}\n")


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
    retries: int = 0
    """On-the-spot retries per shot (issue #39). ``0`` = fail fast (legacy).
    Each retry is preceded by a ``retry_backoff``-second wait and logged as a
    ``RETRY`` line carrying the attempt count, backoff and failure reason."""
    retry_backoff: float = 0.0
    """Seconds to wait between retries of the same shot. Defaults to the
    shot ``interval`` (Agnes 1 request/minute) when left at ``0``."""
    on_shot_done: Callable[[Shot, bool], None] | None = None
    """Called after each shot's terminal result as ``(shot, ok)`` — used to
    update production-plan rows and project.json (issues #36/#37). A hook
    exception is reported but never aborts the run."""
    aspect_ratio: str | None = None
    """Target aspect ratio (e.g. ``"2.39:1"``). When set, every freshly
    generated clip is cropped to it after naming (issue #40)."""

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


def split_long_shots(
    shots: list[Shot],
    max_duration: int = AGNES_MAX_SHOT_DURATION,
    segment: int = SPLIT_SEGMENT_DURATION,
) -> list[Shot]:
    """Split shots longer than one segment into uniform parts (issue #35).

    In production, Agnes clamps every shot down to ~5-6s no matter what the
    plan requested (8-12s takes came back at 5-6s while burning full
    credits). Shots longer than a single ``segment`` are therefore sliced
    into ``n = ceil(duration / segment)`` uniform parts (a 12s shot → two
    6s parts, a 7s shot → 4+3), each carrying a ``[CONTINUITY]`` note so the
    model knows which slice of the action it owns. Scene/act/style/folder/
    references are preserved; only parts longer than ``max_duration`` are
    additionally rejected upstream by the plan-time warning.
    """
    out: list[Shot] = []
    for shot in shots:
        if shot.duration <= segment:
            out.append(shot)
            continue
        n = max(1, math.ceil(shot.duration / segment))
        base = math.ceil(shot.duration / n)
        for k in range(1, n + 1):
            part_len = base if k < n else shot.duration - base * (n - 1)
            part = replace(
                shot,
                id=f"{shot.id}-p{k}",
                duration=max(1, part_len),
            )
            part = replace(
                part,
                prompt=(
                    f"{shot.prompt}\n"
                    f"[CONTINUITY] This take is part {k} of {n} of a longer shot "
                    f"({shot.duration}s total). Cover only this slice of the action."
                ),
            )
            out.append(part)
    return out


def expand_only_ids(
    only: set[str],
    split_shots: list[Shot],
) -> set[str]:
    """Expand a ``--only`` set of pre-split shot IDs into their split parts.

    Issue #49: when ``split_long_shots`` renames ``shot04_silas`` into
    ``shot04_silas-p1`` / ``shot04_silas-p2``, a CLI invocation that passed
    the *original* ID to ``--only`` matched zero pending shots and exited
    with "all pending shots complete" without generating anything.

    This helper maps each requested ID to the split IDs it produced:

    * a pre-split parent ID (``shot04_silas``) expands to all of its parts;
    * an explicit part ID (``shot04_silas-p1``) passes through unchanged;
    * a mixed set with both a parent and one of its parts is de-duplicated;
    * an unknown ID (neither a parent nor a part of any split shot) is
      preserved as-is so the caller can still report "pending 0" rather than
      silently dropping the user's input.

    The result is a *superset* of the input: every ID the user asked for is
    still representable in the expanded set, and split parents are replaced
    by their parts so they actually match the post-split shot list.

    Parameters
    ----------
    only:
        The raw ``--only`` set the user passed on the command line. May be
        empty (returns an empty set).
    split_shots:
        The shot list *after* ``split_long_shots`` has run — this is the
        list the runner will actually iterate over. Used to know which part
        IDs exist.

    Returns
    -------
    A set of shot IDs that matches the post-split shot list.
    """
    if not only:
        return set()

    parent_to_parts: dict[str, set[str]] = {}
    for s in split_shots:
        m = _SPLIT_PART_RE.match(s.id)
        if m:
            parent = m.group(1)
            parent_to_parts.setdefault(parent, set()).add(s.id)

    expanded: set[str] = set()
    for req in only:
        if req in parent_to_parts:
            expanded |= parent_to_parts[req]
        else:
            expanded.add(req)
    return expanded


# Matches a split-part ID like "shot04_silas-p1" / "shot04_silas-p2"
# and captures the parent ("shot04_silas") in group 1.
_SPLIT_PART_RE = __import__("re").compile(r"^(.+)-p(\d+)$")


def apply_aspect_ratio(
    clip: Path, target: str, say: Callable[[str], None] | None = None
) -> bool:
    """Crop a generated clip to the target aspect ratio (issue #40).

    ``target`` accepts ``"2.39:1"``, ``"16:9"`` or a bare ratio like
    ``"2.39"``. Source clips wider than the target are center-cropped
    vertically; narrower ones are center-cropped horizontally. Without
    ffmpeg the clip is left untouched and a warning is reported.
    """
    if not clip.is_file():
        return False
    try:
        if ":" in target:
            w_s, h_s = target.split(":", 1)
            ratio = float(w_s) / float(h_s)
        else:
            ratio = float(target)
        if ratio <= 0:
            raise ValueError
    except ValueError:
        if say:
            say(f"ignoring --aspect-ratio: cannot parse {target!r}")
        return False

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        if say:
            say(f"--aspect-ratio skipped for {clip.name}: ffmpeg not available")
        return False

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(clip),
        ],
        capture_output=True, text=True, timeout=30,
    )
    parts = (probe.stdout or "").split(",")
    if len(parts) < 2:
        if say:
            say(f"--aspect-ratio skipped for {clip.name}: could not probe dimensions")
        return False
    w, h = int(parts[0]), int(parts[1])
    if w <= 0 or h <= 0:
        return False
    source_ratio = w / h
    if abs(source_ratio - ratio) / ratio < 0.02:
        return True  # already at target — nothing to do
    if source_ratio > ratio:
        vfilter = f"crop=iw:2*trunc(iw/{ratio}/2)"
    else:
        vfilter = f"crop=2*trunc(ih*{ratio}/2):ih"
    fd, tmp_name = tempfile.mkstemp(suffix=".mp4", dir=str(clip.parent))
    os.close(fd)
    cmd = [
        "ffmpeg", "-y", "-i", str(clip), "-vf", vfilter,
        "-c:v", "libx264", "-crf", "16", "-c:a", "copy", tmp_name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        Path(tmp_name).unlink(missing_ok=True)
        if say:
            say(f"--aspect-ratio crop failed for {clip.name}: {result.stderr.strip()[:200]}")
        return False
    Path(tmp_name).replace(clip)
    if say:
        say(f"cropped {clip.name} to {target}")
    return True


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
    backoff = config.retry_backoff or config.interval
    max_attempts = 1 + max(config.retries, 0)
    for i, shot in enumerate(pending):
        if i > 0:
            config.say(
                f"rate limit: waiting {config.interval:.0f}s before {shot.id}..."
            )
            time.sleep(config.interval)
        for attempt in range(1, max_attempts + 1):
            before = _clip_snapshot(scenes)
            succeeded, exit_code, note = config.generate_one(shot)
            new_clips = _new_clips(scenes, before)
            ok = succeeded or bool(new_clips)
            if ok and not succeeded:
                note = (note + " " if note else "") + "(clip downloaded; post-gen step failed)"
            if ok:
                retries_used = attempt - 1
                # Final OK line: retry count only when a retry actually happened.
                config.progress.record(
                    shot.id, "OK", exit_code, f" {note}" if note and retries_used == 0 else "", retry=retries_used,
                )
                config.say(
                    f"{shot.id} OK exit={exit_code}" + (f" (retry {retries_used})" if retries_used else "")
                )
                # Deterministic Scene-XX-Shot-X-Y name, then any transition move.
                moved = config.move_shot_clips(shot, name_clips(shot, new_clips, config.say))
                if config.aspect_ratio:
                    targets = moved or _shot_clips(config.scenes_dir, shot)
                    for clip in targets:
                        apply_aspect_ratio(clip, config.aspect_ratio, config.say)
                _fire_hook(config, shot, True)
                break
            if attempt < max_attempts:
                reason = f" {note}" if note else ""
                config.progress.record(
                    shot.id, "RETRY", exit_code, reason, retry=attempt, backoff=backoff,
                )
                config.say(
                    f"{shot.id} RETRY {attempt}/{config.retries} exit={exit_code}{reason} — "
                    f"backoff {backoff:.0f}s"
                )
                time.sleep(backoff)
                continue
            # Terminal failure after all attempts.
            reason = f" {note}" if note else ""
            config.progress.record(
                shot.id, "FAIL", exit_code, reason, retry=attempt - 1,
            )
            config.say(f"{shot.id} FAIL exit={exit_code}{reason}")
            _fire_hook(config, shot, False)
            config.say(
                f"STOP: {shot.id} failed after {max_attempts} attempt(s). Fix and "
                f"re-run to resume (remaining shots stay pending)."
            )
            return 1
    config.say("all pending shots complete")
    return 0


def _shot_clips(scenes: Path, shot: Shot) -> list[Path]:
    """Canonical clip files for a shot (primary take + -2/-3 extras)."""
    stem = Path(shot.clip_name).stem
    found = list(scenes.glob(f"{stem}*.mp4")) if scenes.is_dir() else []
    return sorted(found)


def _fire_hook(config: RunnerConfig, shot: Shot, ok: bool) -> None:
    """Run the optional on_shot_done hook without letting it crash the run."""
    if config.on_shot_done is None:
        return
    try:
        config.on_shot_done(shot, ok)
    except Exception as e:  # state syncs must never abort a production run
        config.say(f"on_shot_done hook error (non-fatal): {e}")


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
