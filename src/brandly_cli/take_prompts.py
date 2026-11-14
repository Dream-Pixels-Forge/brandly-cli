"""Per-take prompt pack (v0.15.4).

A prompt pack is a file projection of the shot list — one Markdown file per
take, grouped by scene::

    .brandly/<project>/prompts/
        Scene 1/Scene 1.1.md   ← Take 1 of Scene 1
        Scene 1/Scene 1.2.md
        Scene 2/Scene 2.1.md
        ...

Terminology
-----------
* **Take** — one prompt slot = one shot position inside a scene
  (``docs/general/scenes.json`` → ``scenes[i].shots[t]``).
* **Redo** — regenerating the clip of an existing take
  (``produce --only``). It replaces the clip; it does **not** create
  ``Scene N.T+1.md``.
* **Prompt pack** — the ``prompts/`` tree plus ``prompt-manifest.json``.

Contract
--------
* The folder is **opt-in**. It is never created eagerly; only
  :func:`export` creates it. Its presence makes it the prompt source of
  truth, and ``brandly produce`` refuses to run while it is out of sync.
* The take file body is the prompt verbatim (no frontmatter, no added
  heading, no wrapping fence). One trailing newline is written and ignored
  on read.
* ``shots.json`` stays the structural source of truth (ids, refs,
  durations, beats, folders). :func:`apply` copies file bodies into
  ``shots.json``; :func:`export` copies shot prompts into files.
* Structured prompt **dicts** (``{"subject": …}``) cannot round-trip through
  Markdown without losing their keys, so they are ``unsupported``: never
  exported, never applied, and they do not block a run.
* For structured plans the take file holds the **shot's own prompt**; the
  act-level ``prefix``/``style`` stay structural and are applied at
  generation time (``flatten_shots``).
* A ``(scene, take)`` pair must be unique. Scene folders are numbered by
  project-unique ordinal (the ``S01``, ``S02`` … order in ``scenes.json``),
  so two acts that both declare ``"scene": 1`` get different folders.

State matrix (also used by ``brandly produce``)
-----------------------------------------------
====================  ==============================================  =====
state                 condition                                       exit
====================  ==============================================  =====
``in-sync``            file hash and shot prompt hash match manifest    0
``edited``             only the file changed                            1
``drifted``            only ``shots.json`` changed                      1
``conflict``           both changed                                     2
``missing``            shot has a prompt, take file absent              1
``unscripted``         shot has no prompt and no file                   0
``unsupported``        prompt is a dict (structured)                    0
``orphan``             file has no matching shot                        2
``invalid``            bad path/name/empty file/manifest                2
====================  ==============================================  =====
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brandly_cli import layout, scenes, shot_runner
from brandly_cli.io import now_iso, write_json

#: Manifest file name at the pack root (machine-written).
MANIFEST_FILENAME = "prompt-manifest.json"
MANIFEST_VERSION = 1

_SCENE_DIR_RE = re.compile(r"^Scene ([1-9]\d*)$")
_TAKE_FILE_RE = re.compile(r"^Scene ([1-9]\d*)\.([1-9]\d*)\.md$")

#: Every per-take state, in rollup precedence order.
TAKE_STATES: tuple[str, ...] = (
    "in-sync",
    "edited",
    "drifted",
    "conflict",
    "missing",
    "unscripted",
    "unsupported",
    "invalid",
    "orphan",
)

_FAIL_STATES = frozenset({"conflict", "invalid", "orphan"})
_WARN_STATES = frozenset({"edited", "drifted", "missing"})


class TakePromptError(ValueError):
    """A structural problem with the shot list or the pack."""


@dataclass(frozen=True)
class Take:
    """One prompt slot: a shot position inside a project-unique scene."""

    scene: int
    take: int
    scene_number: int
    act: str
    prompt: str | None
    shot: dict[str, Any]

    @property
    def key(self) -> str:
        """Stable ``"scene.take"`` key, e.g. ``"1.2"``."""
        return f"{self.scene}.{self.take}"

    @property
    def relpath(self) -> str:
        """Canonical pack-relative path, e.g. ``Scene 1/Scene 1.2.md``."""
        return format_take_relpath(self.scene, self.take)


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


def format_take_relpath(scene: int, take: int) -> str:
    """Canonical pack-relative path for a take (``Scene N/Scene N.T.md``)."""
    if scene < 1 or take < 1:
        raise TakePromptError(f"scene/take must be >= 1, got {scene}.{take}")
    return f"Scene {scene}/Scene {scene}.{take}.md"


def format_take_path(scene: int, take: int) -> str:
    """Spec name for :func:`format_take_relpath` (``Scene N/Scene N.T.md``)."""
    return format_take_relpath(scene, take)


def parse_take_relpath(rel: str | Path) -> tuple[int, int] | None:
    """Parse a canonical pack-relative path, or ``None`` when non-canonical.

    The scene folder and the take file must agree (``Scene 2/Scene 1.1.md``
    is not a take — it is a misplaced file the status scan reports).
    """
    parts = Path(rel).as_posix().split("/")
    if len(parts) != 2:
        return None
    scene_match = _SCENE_DIR_RE.match(parts[0])
    take_match = _TAKE_FILE_RE.match(parts[1])
    if not scene_match or not take_match:
        return None
    if scene_match.group(1) != take_match.group(1):
        return None
    return int(take_match.group(1)), int(take_match.group(2))


def parse_take_path(rel: str | Path) -> tuple[int, int] | None:
    """Spec name for :func:`parse_take_relpath`."""
    return parse_take_relpath(rel)


def take_sort_key(pair: tuple[int, int]) -> tuple[int, int]:
    """Numeric sort key — ``Scene 10`` after ``Scene 9``, never lexicographic."""
    return pair


# ---------------------------------------------------------------------------
# Prompt text
# ---------------------------------------------------------------------------


def normalize_prompt(text: str) -> str:
    """Canonical prompt text for hashing/compare: LF endings, no trailing LF."""
    return text.replace("\r\n", "\n").rstrip("\n")


def prompt_sha256(text: str) -> str:
    """SHA-256 of the normalized prompt text."""
    return hashlib.sha256(normalize_prompt(text).encode("utf-8")).hexdigest()


def _shot_prompt(shot: dict[str, Any]) -> str | None:
    """Return the shot's own prompt text, or ``None`` when it cannot round-trip.

    Missing/empty prompt → ``""`` (unscripted). A non-string prompt (the
    structured-prompt dict schema) → ``None`` (unsupported).
    """
    raw = shot.get("prompt", "")
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return None


# ---------------------------------------------------------------------------
# Take walk (mirrors scenes.build_scenes order)
# ---------------------------------------------------------------------------


def iter_takes(data: dict[str, Any] | list[dict[str, Any]]) -> list[Take]:
    """Yield the shot list's takes in production order.

    * flat list → ``scene`` = ``shot["scene"]`` (default 1),
      ``take`` = ``shot["shot"]`` (default array position) — exactly the pair
      ``clip_filename`` encodes;
    * structured plan → acts in JSON key order, scene assigned in
      first-appearance order (the ``S01``/``S02`` manifest order), take =
      the shot's position inside its act (``Shot.index_in_scene``).
    """
    rows: list[tuple[int, int, int, str, str | None, dict[str, Any]]] = []

    if isinstance(data, list):
        for position, shot in enumerate(data, start=1):
            if not isinstance(shot, dict):
                raise TakePromptError(f"shot #{position} is not an object")
            scene_number = shot_runner.as_int(shot.get("scene"), 1)
            take = shot_runner.as_int(shot.get("shot"), position)
            rows.append((scene_number, take, scene_number, "", _shot_prompt(shot), shot))
    elif isinstance(data, dict):
        acts = data.get("acts") or {}
        if not isinstance(acts, dict) or not acts:
            raise TakePromptError("structured shot list must define a non-empty 'acts' mapping")
        for act_position, (act_key, act) in enumerate(acts.items(), start=1):
            if not isinstance(act, dict):
                raise TakePromptError(f"act {act_key!r} is not an object")
            act_name = str(act.get("name", act_key))
            act_scene = shot_runner.as_int(act.get("scene"), act_position)
            for shot_position, shot in enumerate(act.get("shots", []), start=1):
                if not isinstance(shot, dict):
                    raise TakePromptError(f"shot #{shot_position} of act {act_key!r} is not an object")
                scene_number = shot_runner.as_int(shot.get("scene"), act_scene)
                rows.append(
                    (
                        scene_number,
                        shot_position,
                        scene_number,
                        act_name,
                        _shot_prompt(shot),
                        shot,
                    )
                )
    else:
        raise TakePromptError("shot list must be a JSON array or an object with 'acts'")

    # Scene folder = project-unique ordinal in first-appearance order. The
    # grouping key includes the act, so two acts declaring scene 1 get
    # distinct folders (mirrors scenes.build_scenes).
    group_ordinal: dict[tuple[str, int], int] = {}
    takes: list[Take] = []
    seen: set[tuple[int, int]] = set()
    for scene_number, take, _raw_scene, act, prompt, shot in rows:
        group = (act, scene_number)
        if group not in group_ordinal:
            group_ordinal[group] = len(group_ordinal) + 1
        scene = group_ordinal[group]
        if (scene, take) in seen:
            raise TakePromptError(
                f"duplicate take {scene}.{take} in the shot list — "
                "each (scene, take) pair must be unique"
            )
        seen.add((scene, take))
        takes.append(
            Take(
                scene=scene,
                take=take,
                scene_number=scene_number,
                act=act,
                prompt=prompt,
                shot=shot,
            )
        )
    return takes


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _manifest_path(pack: Path) -> Path:
    return pack / MANIFEST_FILENAME


def _load_manifest(pack: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load and validate the manifest. Returns ``(manifest, error)``."""
    path = _manifest_path(pack)
    if not path.is_file():
        return None, f"{MANIFEST_FILENAME} is missing"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{MANIFEST_FILENAME} is unreadable: {exc}"
    if not isinstance(raw, dict):
        return None, f"{MANIFEST_FILENAME} is not an object"
    if raw.get("version") != MANIFEST_VERSION:
        return None, (
            f"{MANIFEST_FILENAME} has unsupported version {raw.get('version')!r} "
            f"(expected {MANIFEST_VERSION})"
        )
    if not isinstance(raw.get("takes"), dict):
        return None, f"{MANIFEST_FILENAME} has no 'takes' mapping"
    return raw, None


def _write_manifest(pack: Path, project_id: str, entries: dict[str, dict[str, Any]]) -> None:
    write_json(
        _manifest_path(pack),
        {
            "version": MANIFEST_VERSION,
            "project_id": project_id,
            "generated_at": now_iso(),
            "takes": {key: entries[key] for key in sorted(entries, key=_manifest_sort_key)},
        },
    )


def _manifest_sort_key(key: str) -> tuple[int, int]:
    try:
        scene, take = key.split(".", 1)
        return int(scene), int(take)
    except ValueError:
        return (1 << 30, 0)


# ---------------------------------------------------------------------------
# Pack scanning
# ---------------------------------------------------------------------------


def pack_dir(root: Path | str | None, project_id: str) -> Path:
    """Resolve the pack directory for a project."""
    return layout.prompts_dir(Path(root) if root is not None else Path.cwd(), project_id)


def pack_exists(root: Path | str | None, project_id: str) -> bool:
    """True when the opt-in prompt pack folder exists."""
    return pack_dir(root, project_id).is_dir()


def load_scene_direction(pack: Path, scene: int) -> str | None:
    """Read the scene direction file ``Scene N/Scene N.md``, or ``None``.

    Scene direction is authored directly (never written by pack tools). The
    returned text has its trailing newline stripped so callers can join it to a
    take prompt cleanly (``direction + "\\n\\n" + take_prompt``).
    """
    if scene < 1:
        return None
    path = pack / f"Scene {scene}" / f"Scene {scene}.md"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8").rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return None


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"unreadable: {exc}"


def _scan_files(pack: Path) -> tuple[dict[tuple[int, int], Path], list[dict[str, str]]]:
    """Scan the pack.

    Returns ``(files, invalid)`` where ``files`` maps every canonically named
    take file to its path and ``invalid`` lists entries that are legal to
    ignore: stray root entries, wrong scene folders, nested dirs, wrong
    extension, misplaced takes.
    """
    files: dict[tuple[int, int], Path] = {}
    invalid: list[dict[str, str]] = []
    if not pack.is_dir():
        return files, invalid

    for entry in sorted(pack.iterdir(), key=lambda p: p.name):
        if entry.name == MANIFEST_FILENAME and entry.is_file():
            continue
        scene_match = _SCENE_DIR_RE.match(entry.name) if entry.is_dir() else None
        if not scene_match:
            invalid.append(
                {"file": entry.name, "error": "unexpected entry at pack root"}
            )
            continue
        scene = int(scene_match.group(1))
        for child in sorted(entry.iterdir(), key=lambda p: p.name):
            rel = f"{entry.name}/{child.name}"
            if not child.is_file():
                invalid.append({"file": rel, "error": "not a file"})
                continue
            # Scene direction file: ``Scene N/Scene N.md`` — scene metadata,
            # authored directly, never a take file. Not invalid, not an orphan.
            if child.name == f"Scene {scene}.md":
                continue
            parsed = parse_take_relpath(rel)
            if parsed is None:
                invalid.append(
                    {
                        "file": rel,
                        "error": "not a canonical take file (expected 'Scene N/Scene N.T.md')",
                    }
                )
                continue
            file_scene, take = parsed
            if file_scene != scene:
                invalid.append(
                    {"file": rel, "error": "take file is in the wrong scene folder"}
                )
                continue
            files[(file_scene, take)] = child
    return files, invalid


def _scene_meta(project_id: str, root: Path | str | None) -> dict[int, dict[str, Any]]:
    manifest = scenes.load_scenes(project_id, root=root)
    if not manifest:
        return {}
    out: dict[int, dict[str, Any]] = {}
    for entry in manifest.get("scenes", []):
        scene_id = str(entry.get("id", ""))
        if not scene_id.startswith("S"):
            continue
        try:
            ordinal = int(scene_id[1:])
        except ValueError:
            continue
        out[ordinal] = entry
    return out


def _clip_for(take: Take, meta: dict[int, dict[str, Any]]) -> str:
    entry = meta.get(take.scene)
    if entry:
        shots = entry.get("shots") or []
        if 0 <= take.take - 1 < len(shots):
            clip = shots[take.take - 1].get("clip")
            if clip:
                return str(clip)
    return shot_runner.clip_filename(take.scene_number, take.take)


def _scene_id_for(take: Take, meta: dict[int, dict[str, Any]]) -> str:
    entry = meta.get(take.scene)
    if entry and entry.get("id"):
        return str(entry["id"])
    return f"S{take.scene:02d}"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def _empty_counts() -> dict[str, int]:
    return dict.fromkeys(TAKE_STATES, 0)


def _verdict(states: list[str], invalid: list[dict[str, str]], orphans: list[dict[str, str]]) -> str:
    all_states = set(states)
    if invalid or orphans or (all_states & _FAIL_STATES):
        return "fail"
    if all_states & _WARN_STATES:
        return "warn"
    return "pass"


def status(
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    root: Path | str | None = None,
) -> dict[str, Any]:
    """Compute the prompt-pack state matrix for a shot list.

    Read-only. Never creates the pack, never writes ``shots.json``.
    """
    pack = pack_dir(root, project_id)
    meta = _scene_meta(project_id, root)
    counts = _empty_counts()
    invalid: list[dict[str, str]] = []
    orphans: list[dict[str, str]] = []

    try:
        takes = iter_takes(data)
    except TakePromptError as exc:
        return {
            "pack_exists": pack.is_dir(),
            "project_id": project_id,
            "verdict": "fail",
            "takes": [],
            "counts": counts,
            "orphans": [],
            "invalid": [{"file": "shots.json", "error": str(exc)}],
        }

    if not pack.is_dir():
        no_pack_entries: list[dict[str, Any]] = [
            {
                "scene": take.scene,
                "take": take.take,
                "key": take.key,
                "state": "unsupported" if take.prompt is None else "unscripted",
                "file": None,
                "clip": _clip_for(take, meta),
                "scene_id": _scene_id_for(take, meta),
                "error": None,
            }
            for take in takes
        ]
        for no_pack_entry in no_pack_entries:
            counts[no_pack_entry["state"]] += 1
        return {
            "pack_exists": False,
            "project_id": project_id,
            "verdict": "pass",
            "takes": no_pack_entries,
            "counts": counts,
            "orphans": [],
            "invalid": [],
        }

    files, invalid = _scan_files(pack)
    manifest, manifest_error = _load_manifest(pack)
    if manifest_error:
        invalid.append({"file": MANIFEST_FILENAME, "error": manifest_error})
        manifest = None
    manifest_takes = (manifest or {}).get("takes", {})

    entries: list[dict[str, Any]] = []
    known: set[tuple[int, int]] = set()
    for take in takes:
        key = (take.scene, take.take)
        known.add(key)
        path = files.get(key)
        entry: dict[str, Any] = {
            "scene": take.scene,
            "take": take.take,
            "key": take.key,
            "state": "in-sync",
            "file": take.relpath if path else None,
            "clip": _clip_for(take, meta),
            "scene_id": _scene_id_for(take, meta),
            "error": None,
        }

        if take.prompt is None:
            entry["state"] = "unsupported"
            if path is not None:
                invalid.append(
                    {
                        "file": take.relpath,
                        "error": "structured prompt cannot round-trip through a take file",
                    }
                )
        elif manifest_error:
            entry["state"] = "invalid"
            entry["error"] = manifest_error
        elif path is None:
            entry["state"] = "missing" if take.prompt.strip() else "unscripted"
        else:
            text, read_error = _read_text(path)
            if read_error:
                entry["state"] = "invalid"
                entry["error"] = read_error
            elif not (text or "").strip():
                entry["state"] = "invalid"
                entry["error"] = "take file is empty"
            else:
                synced = manifest_takes.get(take.key)
                file_hash = prompt_sha256(text or "")
                prompt_hash = prompt_sha256(take.prompt)
                if not isinstance(synced, dict):
                    entry["state"] = "edited"
                else:
                    file_changed = file_hash != synced.get("synced_file_sha256")
                    prompt_changed = prompt_hash != synced.get("synced_prompt_sha256")
                    if file_changed and prompt_changed:
                        entry["state"] = "conflict"
                        entry["error"] = "both the take file and shots.json changed"
                    elif file_changed:
                        entry["state"] = "edited"
                    elif prompt_changed:
                        entry["state"] = "drifted"
                    else:
                        entry["state"] = "in-sync"
        counts[entry["state"]] += 1
        entries.append(entry)

    for key, path in sorted(files.items(), key=lambda item: take_sort_key(item[0])):
        if key in known:
            continue
        rel = path.relative_to(pack).as_posix()
        orphans.append({"file": rel, "error": "no matching shot"})
        counts["orphan"] += 1

    entries.sort(key=lambda e: (e["scene"], e["take"]))
    verdict = _verdict([e["state"] for e in entries], invalid, orphans)
    return {
        "pack_exists": True,
        "project_id": project_id,
        "verdict": verdict,
        "takes": entries,
        "counts": counts,
        "orphans": orphans,
        "invalid": invalid,
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _entry_for(
    take: Take,
    text: str,
    *,
    meta: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scene": take.scene,
        "take": take.take,
        "scene_id": _scene_id_for(take, meta),
        "clip": _clip_for(take, meta),
        "file": take.relpath,
        "synced_file_sha256": prompt_sha256(text),
        "synced_prompt_sha256": prompt_sha256(take.prompt or ""),
    }


def export(
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    root: Path | str | None = None,
    force: bool = False,
    missing_only: bool = False,
    prune: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create/refresh take files from ``shots.json`` prompts.

    Never overwrites an ``edited``/``conflict`` file without ``force``.
    ``prune`` (with ``force``) deletes orphan files. ``dry_run`` writes
    nothing. Returns the report plus an ``actions`` list.
    """
    pack = pack_dir(root, project_id)
    report = status(project_id, data, root=root)
    actions: list[dict[str, Any]] = []
    report["actions"] = actions
    if report["verdict"] == "fail" and report["invalid"]:
        report["error"] = "invalid pack entries must be fixed before export"
        return report
    if report["orphans"]:
        if not (prune and force):
            report["error"] = "orphan take files: pass --prune --force to delete them"
            return report

    meta = _scene_meta(project_id, root)
    take_by_key = {take.key: take for take in iter_takes(data)}
    files, _ = _scan_files(pack)
    manifest, _ = _load_manifest(pack)
    manifest_entries: dict[str, dict[str, Any]] = dict(
        (manifest or {}).get("takes", {})
    )

    if prune and force:
        for key, path in sorted(files.items(), key=lambda item: take_sort_key(item[0])):
            if f"{key[0]}.{key[1]}" in take_by_key:
                continue
            actions.append({"action": "prune", "key": f"{key[0]}.{key[1]}", "path": str(path)})
            if not dry_run:
                path.unlink(missing_ok=True)
                try:
                    path.parent.rmdir()
                except OSError:
                    pass

    for take in take_by_key.values():
        if take.prompt is None:
            continue
        if not take.prompt.strip():
            continue
        path = pack / take.relpath
        state = next((e["state"] for e in report["takes"] if e["key"] == take.key), None)
        if state == "in-sync":
            continue
        if missing_only and path.exists():
            continue
        if state in {"edited", "conflict", "invalid"} and not force:
            continue
        action = "write" if state in {"missing", "unscripted", None} else "overwrite"
        actions.append({"action": action, "key": take.key, "path": str(path)})
        if dry_run:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(normalize_prompt(take.prompt) + "\n", encoding="utf-8")
        manifest_entries[take.key] = _entry_for(take, take.prompt, meta=meta)

    if not dry_run:
        for manifest_key in list(manifest_entries):
            remaining = take_by_key.get(manifest_key)
            if remaining is None or remaining.prompt is None:
                manifest_entries.pop(manifest_key, None)

    if not dry_run and actions:
        pack.mkdir(parents=True, exist_ok=True)
        _write_manifest(pack, project_id, manifest_entries)

    if dry_run:
        return report
    after = status(project_id, data, root=root)
    after["actions"] = actions
    if report.get("error") and after["verdict"] != "fail":
        after.pop("error", None)
    return after


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def _parse_key(key: str) -> tuple[int, int]:
    try:
        scene, take = key.split(".", 1)
        pair = int(scene), int(take)
    except (ValueError, AttributeError) as exc:
        raise TakePromptError(f"invalid take key {key!r} (expected 'scene.take', e.g. '1.2')") from exc
    if pair[0] < 1 or pair[1] < 1:
        raise TakePromptError(f"invalid take key {key!r} (expected 'scene.take', e.g. '1.2')")
    return pair


def _shots_path(root: Path | str | None, project_id: str) -> Path:
    return layout.resolve_project_dir(Path(root) if root is not None else Path.cwd(), project_id) / "shots.json"


def load_shots(
    project_id: str, *, root: Path | str | None = None
) -> dict[str, Any] | list[dict[str, Any]]:
    """Load the project's ``shots.json`` (raises :class:`TakePromptError`)."""
    path = _shots_path(root, project_id)
    if not path.is_file():
        raise TakePromptError(f"no shots.json for project {project_id!r} at {path}")
    try:
        return shot_runner.load_shots_file(path)
    except ValueError as exc:
        raise TakePromptError(f"invalid shots.json: {exc}") from exc


def apply(
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    root: Path | str | None = None,
    force: bool = False,
    clear: str | None = None,
    scene: int | None = None,
    take: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Write take-file bodies back into ``shots.json``.

    Refuses on ``invalid``/``orphan`` packs and on ``conflict``/``drifted``
    takes unless ``force``. ``clear`` empties one take's prompt and removes
    its file (the explicit way to remove direction). ``scene``/``take`` scope
    the apply to one folder / one take index so a single conflict can be
    resolved without touching the rest of the pack. ``dry_run`` writes
    nothing.
    """
    report = status(project_id, data, root=root)
    actions: list[dict[str, Any]] = []
    report["actions"] = actions
    pack = pack_dir(root, project_id)

    if not report["pack_exists"]:
        report["verdict"] = "fail"
        report["error"] = (
            f"no prompt pack for project {project_id!r} — "
            "run `brandly takes export` first"
        )
        return report

    if report["invalid"] or report["orphans"]:
        report["verdict"] = "fail"
        report["error"] = "invalid or orphan pack entries; run `brandly takes export --prune --force` or remove them"
        return report

    takes = iter_takes(data)
    take_by_key = {take.key: take for take in takes}
    manifest, _ = _load_manifest(pack)
    manifest_entries: dict[str, dict[str, Any]] = dict(
        (manifest or {}).get("takes", {})
    )

    if clear is not None:
        pair = _parse_key(clear)
        cleared = take_by_key.get(f"{pair[0]}.{pair[1]}")
        if cleared is None:
            report["verdict"] = "fail"
            report["error"] = f"no take {clear} in the shot list"
            return report
        path = pack / cleared.relpath
        cleared.shot["prompt"] = ""
        manifest_entries.pop(cleared.key, None)
        if path.exists():
            actions.append(
                {"action": "delete", "key": cleared.key, "path": str(path)}
            )
            if not dry_run:
                path.unlink()
                try:
                    path.parent.rmdir()
                except OSError:
                    pass
        if not dry_run:
            _persist(project_id, data, root=root)
            if actions:
                _write_manifest(pack, project_id, manifest_entries)
        after = report if dry_run else status(project_id, data, root=root)
        after["actions"] = actions
        return after

    # Validate every selected take before mutating anything (fail-closed, no
    # partial apply). drifted/conflict means shots.json or the file moved
    # since the last sync; applying would silently discard the other side.
    # Scoping (--scene/--take) narrows both the checks and the writes, so one
    # conflicting take can be resolved without blocking on the rest.
    selected = [
        entry
        for entry in report["takes"]
        if (scene is None or entry["scene"] == scene)
        and (take is None or entry["take"] == take)
    ]
    if not selected:
        report["verdict"] = "warn"
        report["error"] = (
            "no takes match the given --scene/--take filter"
            if (scene is not None or take is not None)
            else "the shot list has no takes"
        )
        return report

    blocking: list[str] = []
    for entry in selected:
        if entry["state"] in {"conflict", "drifted"} and not force:
            blocking.append(entry["key"])
        if entry["state"] == "invalid":
            blocking.append(entry["key"])
    if blocking:
        report["verdict"] = "fail"
        report["error"] = (
            "takes out of sync: " + ", ".join(sorted(blocking)) + " — "
            "re-export, resolve manually, or pass --force"
        )
        return report

    meta = _scene_meta(project_id, root)

    for entry in selected:
        target = take_by_key.get(entry["key"])
        if target is None or target.prompt is None:
            continue
        if entry["state"] in {"missing", "unscripted", "unsupported", "in-sync"}:
            continue
        path = pack / target.relpath
        text, read_error = _read_text(path)
        if read_error or text is None:
            report["verdict"] = "fail"
            report["error"] = f"take {entry['key']}: {read_error or 'unreadable'}"
            return report
        prompt = normalize_prompt(text)
        target.shot["prompt"] = prompt
        actions.append({"action": "apply", "key": target.key, "path": str(path)})
        manifest_entries[target.key] = {
            "scene": target.scene,
            "take": target.take,
            "scene_id": _scene_id_for(target, meta),
            "clip": _clip_for(target, meta),
            "file": target.relpath,
            "synced_file_sha256": prompt_sha256(text),
            "synced_prompt_sha256": prompt_sha256(prompt),
        }

    if dry_run:
        return report

    if actions:
        _persist(project_id, data, root=root)
        _write_manifest(pack, project_id, manifest_entries)
    after = status(project_id, data, root=root)
    after["actions"] = actions
    return after


def _persist(
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    root: Path | str | None,
) -> None:
    path = _shots_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
