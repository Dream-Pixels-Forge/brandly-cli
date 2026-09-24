"""Durable generation-job records (issue #74).

One JSON record per generation job, written to
``<root>/.brandly/jobs/<job_id>.json`` **before** the provider call is
made, so a crashed or disconnected client keeps a stable handle it can
poll later to retrieve the result without re-submitting the generation
(``brandly job-poll`` reports the machine-readable state).

Lifecycle::

    running ──> succeeded        (result captured + redacted URL stored)
        ├──> failed              (provider error / no payload)
        └──> expired             (still running after ``--max-age``)

Records never persist credential-bearing material: provider URLs are
stripped of credential-bearing query parameters before they are written
to disk (issue #74 acceptance criterion 4), and job IDs are
``uuid4`` hex strings, so record paths cannot escape the job store.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from brandly_cli.io import fetch_image_atomic, now_iso

#: Job lifecycle statuses.
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_EXPIRED = "expired"

#: Non-terminal statuses (polling exits zero while in these).
NON_TERMINAL_STATUSES = frozenset({STATUS_RUNNING})

#: Query-parameter names that carry live credentials/tokens and are
#: never persisted into job records (issue #74 AC4).
CREDENTIAL_PARAM_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "access_key",
        "awsaccesskeyid",
        "secret_key",
        "secret",
        "token",
        "auth",
        "authorization",
        "bearer",
        "credential",
        "credentials",
        "password",
        "passwd",
        "signature",
        "sig",
        "session",
        "key",
    }
)

#: Job IDs are uuid4 hex — strict match keeps record paths inside the
#: job store (no traversal, no case- or length-fuzzing).
_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def new_job_id() -> str:
    """A fresh, durable, provider-stable job identifier."""
    return uuid.uuid4().hex


def _is_valid_job_id(job_id: str | None) -> bool:
    return bool(job_id and _JOB_ID_RE.match(job_id))


def jobs_dir(root: Path | str) -> Path:
    """The durable job store for a Brandly home: ``<root>/.brandly/jobs``."""
    return Path(root) / ".brandly" / "jobs"


def record_path(root: Path | str, job_id: str) -> Path:
    """On-disk path of a job record (validates the id, raises ValueError)."""
    if not _is_valid_job_id(job_id):
        raise ValueError(f"invalid job id: {job_id!r}")
    return jobs_dir(root) / f"{job_id}.json"


def _atomic_write(path: Path, record: dict[str, Any]) -> None:
    """Write ``record`` atomically: sibling ``.part`` file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def create_image_job(
    root: Path | str,
    *,
    prompt: str,
    model: str,
    size: str,
    ratio: str,
    style_preset: str | None = None,
    project_id: str | None = None,
    provider_task_id: str | None = None,
) -> dict[str, Any]:
    """Create + persist a durable image-job record *before* the provider call.

    Returns the record (with ``job_id`` and ``record_path``). Status is
    ``running``; callers transition it to a terminal state when the
    provider outcome is known (or leave it running when the process
    dies — that is exactly the recoverable case).
    """
    root = Path(root)
    job_id = new_job_id()
    ts = now_iso()
    record: dict[str, Any] = {
        "job_id": job_id,
        "kind": "image",
        "status": STATUS_RUNNING,
        "prompt": prompt,
        "model": model,
        "size": size,
        "ratio": ratio,
        "style_preset": style_preset,
        "project_id": project_id,
        "provider_task_id": provider_task_id,
        "provider_url": None,
        "path": None,
        "format": None,
        "width": None,
        "height": None,
        "error": None,
        "created_at": ts,
        "updated_at": ts,
        "record_path": str(jobs_dir(root) / f"{job_id}.json"),
    }
    _atomic_write(Path(record["record_path"]), record)
    return record


def save_job(record: dict[str, Any]) -> dict[str, Any]:
    """Persist a record transition (``updated_at`` stamped, atomic write)."""
    record = dict(record)
    record["updated_at"] = now_iso()
    _atomic_write(Path(record["record_path"]), record)
    return record


def load_job(root: Path | str, job_id: str) -> dict[str, Any] | None:
    """Read a job record; None when the id is malformed or unknown."""
    if not _is_valid_job_id(job_id):
        return None
    path = jobs_dir(Path(root)) / f"{job_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_job_image(
    record: dict[str, Any],
    *,
    url: str | None = None,
    b64_json: str | None = None,
) -> dict[str, Any]:
    """Capture the finished image into the job store (durable result).

    Writes ``<jobs_dir>/<job_id><ext>`` with the same atomic,
    fully-decoded validation used for ``--output`` files, records the
    (redacted) provider URL + artifact path on the record, and returns
    the ``fetch_image_atomic`` info dict.
    """
    job_id = record["job_id"]
    ext = ""
    if url:
        ext = Path(url.split("?")[0]).suffix or ""
    if not ext:
        ext = ".png"
    dest = Path(record["record_path"]).parent / f"{job_id}{ext}"
    info = fetch_image_atomic(url, dest, b64_json=b64_json)
    # Mutate the caller's record so follow-up saves carry the artifact fields.
    if url:
        record["provider_url"] = redact_credentials(url)
    record["path"] = str(info["path"])
    record["format"] = info["format"]
    record["width"] = info["width"]
    record["height"] = info["height"]
    save_job(record)
    return info


def redact_credentials(value: str | None) -> str | None:
    """Strip credential-bearing query params from a URL (issue #74 AC4).

    Non-URL values and URLs without a query are returned unchanged;
    host/path are preserved so the resource remains identifiable.
    """
    if not value:
        return value
    split = urlsplit(value)
    if not split.scheme or not split.query:
        return value
    parsed = parse_qsl(split.query, keep_blank_values=True)
    kept = [(k, v) for k, v in parsed if k.lower() not in CREDENTIAL_PARAM_NAMES]
    if len(kept) == len(parsed):
        return value  # nothing sensitive found
    query = "&".join(f"{k}={v}" for k, v in kept)
    return urlunsplit(split._replace(query=query))


def is_stale(record: dict[str, Any], max_age_seconds: float) -> bool:
    """True when a non-terminal record is older than ``max_age_seconds``."""
    if record.get("status") not in NON_TERMINAL_STATUSES:
        return False
    created = record.get("created_at")
    if not created:
        return False
    try:
        created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    except ValueError:
        return False
    if created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - created_dt).total_seconds()
    return age > max_age_seconds


def resolve_status(record: dict[str, Any], max_age_seconds: float) -> str:
    """Effective status: stale non-terminal records become ``expired``."""
    status = record.get("status") or STATUS_FAILED
    if status in NON_TERMINAL_STATUSES and is_stale(record, max_age_seconds):
        return STATUS_EXPIRED
    return status
