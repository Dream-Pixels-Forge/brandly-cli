"""G8 PR 1 (issue #99): project-local platform-metrics ingest.

`brandly metrics import` accepts CSV/JSON files with the versioned row
schema ``{date, views, likes, watch_time_seconds, ctr_pct}`` and writes
one snapshot file per (platform, date) into
``.brandly/<project>/metrics/<platform>-<date>.json`` — **project-local
only, never the user config store** (DEV-G8-001). No network, no
credentials in this PR; the YouTube Analytics API adapter is G8 PR 2.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

#: Version of the on-disk snapshot schema.
METRICS_SCHEMA_VERSION = 1

#: Directory inside a project dir that holds metric snapshots.
METRICS_DIR = "metrics"

#: Platforms accepted by `metrics import` (G8 PR 2 adds the analytics adapter).
SUPPORTED_PLATFORMS: tuple[str, ...] = ("youtube",)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: Row schema (versioned): one row per (platform, date) observation.
ROW_FIELDS: tuple[str, ...] = (
    "date",
    "views",
    "likes",
    "watch_time_seconds",
    "ctr_pct",
)


def metrics_dir(proj_dir: Path) -> Path:
    """Return the project's snapshot directory (not created on read)."""
    return Path(proj_dir) / METRICS_DIR


def _parse_row(raw: dict[str, Any], line_no: int) -> dict[str, Any]:
    """Deterministically parse + validate one row (fail-closed)."""
    date = str(raw.get("date", "")).strip()
    if not _DATE_RE.match(date):
        raise ValueError(f"row {line_no}: date must be ISO YYYY-MM-DD, got {date!r}")
    values: dict[str, Any] = {"date": date}
    try:
        for field in ("views", "likes", "watch_time_seconds"):
            values[field] = int(float(str(raw.get(field, "")).strip()))
        values["ctr_pct"] = float(str(raw.get("ctr_pct", "")).strip())
    except (TypeError, ValueError):
        raise ValueError(f"row {line_no}: non-numeric metric value") from None
    for field in ("views", "likes", "watch_time_seconds"):
        if values[field] < 0:
            raise ValueError(f"row {line_no}: {field} must be >= 0")
    if not 0.0 <= values["ctr_pct"] <= 100.0:
        raise ValueError(f"row {line_no}: ctr_pct must be in [0, 100]")
    return values


def _rows_from_file(source: Path) -> list[dict[str, Any]]:
    suffix = source.suffix.lower()
    if suffix == ".csv":
        with source.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or [f.strip() for f in reader.fieldnames] != list(
                ROW_FIELDS
            ):
                raise ValueError(f"CSV header must be {','.join(ROW_FIELDS)}")
            return [dict(row) for row in reader]
    if suffix == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON metrics file must be a list of row objects")
        return data
    raise ValueError(f"unsupported metrics file type: {source.suffix}")


def import_metrics(source: Path | str, platform: str, proj_dir: Path) -> list[Path]:
    """Import a CSV/JSON metrics file into the project's snapshot store.

    Returns the list of snapshot files written (one per date). Raises
    ``ValueError`` on unknown platform, unreadable file, or any malformed
    row (fail-closed — a bad file never produces a partial ingest).
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unknown platform {platform!r}; supported: {SUPPORTED_PLATFORMS}")
    source = Path(source)
    if not source.is_file():
        raise ValueError(f"metrics file not found: {source}")

    raw_rows = _rows_from_file(source)
    if not raw_rows:
        raise ValueError("metrics file has no rows")

    by_date: dict[str, list[dict[str, Any]]] = {}
    for line_no, raw in enumerate(raw_rows, start=2):
        if not isinstance(raw, dict):
            raise ValueError(f"row {line_no}: expected an object")
        parsed = _parse_row(raw, line_no)
        by_date.setdefault(parsed["date"], []).append(parsed)

    out_dir = metrics_dir(Path(proj_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for date, rows in sorted(by_date.items()):
        snapshot = {
            "platform": platform,
            "schema": METRICS_SCHEMA_VERSION,
            "date": date,
            "rows": rows,
        }
        path = out_dir / f"{platform}-{date}.json"
        path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def latest_ingest(proj_dir: Path, platform: str) -> Path | None:
    """Latest snapshot file for a platform (max ISO date); None when absent."""
    d = metrics_dir(Path(proj_dir))
    files = sorted(d.glob(f"{platform}-*.json")) if d.is_dir() else []
    return files[-1] if files else None


def latest_snapshot(proj_dir: Path, platform: str) -> dict[str, Any] | None:
    """Parsed latest snapshot for a platform; None when no ingest exists."""
    path = latest_ingest(proj_dir, platform)
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_ingest_any(proj_dir: Path) -> tuple[str, dict[str, Any]] | None:
    """Latest snapshot across all platforms (used by `analyze` blending)."""
    d = metrics_dir(Path(proj_dir))
    if not d.is_dir():
        return None
    best: tuple[str, dict[str, Any], str] | None = None
    for path in d.glob("*.json"):
        snap = json.loads(path.read_text(encoding="utf-8"))
        date_key = str(snap.get("date", ""))
        if best is None or (date_key, path.name) > (best[2], best[1].get("date", "")):
            best = (str(snap.get("platform", "")), snap, date_key)
    if best is None:
        return None
    return best[0], best[1]


def summarize(proj_dir: Path) -> dict[str, dict[str, Any]]:
    """Latest ingested snapshot per platform: {platform: {date, row_count, ...}}."""
    out: dict[str, dict[str, Any]] = {}
    d = metrics_dir(Path(proj_dir))
    if not d.is_dir():
        return out
    by_platform: dict[str, Path] = {}
    for path in d.glob("*.json"):
        platform = path.name.split("-", 1)[0]
        current = by_platform.get(platform)
        if current is None or path.name > current.name:
            by_platform[platform] = path
    for platform, path in sorted(by_platform.items()):
        snap = json.loads(path.read_text(encoding="utf-8"))
        out[platform] = {
            "date": snap.get("date"),
            "row_count": len(snap.get("rows", [])),
            "latest_row": (snap.get("rows") or [None])[-1],
            "file": str(path),
        }
    return out
