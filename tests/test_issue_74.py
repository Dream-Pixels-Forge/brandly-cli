"""Issue #74: durable image-generation jobs and ``brandly job-poll``.

Acceptance criteria covered:
1. Every image-generation invocation gets a durable, provider-stable
   job identifier, created before the provider call so it survives a
   crash or disconnect.
2. After a timeout or disconnect, the user can poll the job, retrieve
   the completed result, and resume without submitting a duplicate
   generation request.
3. Polling is machine-readable: explicit exit codes (zero only for
   intermediate states), terminal states on failure/expiration.
4. Job records never persist provider URLs that contain live
   credentials/tokens.
5. Polling never triggers a duplicate provider submission.

Scope:
- Durable job ID + status + provider info + output location +
  recoverable result.
- ``brandly job-poll`` reports machine-readable state; a terminal
  state means re-invoke the command, not re-submit the provider.
- Simulated disconnect/recovery workflow with no provider calls.
- Documentation of timeout behavior and provider retry safety.
"""

from __future__ import annotations

import base64
import io as _io
import json
import os
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    env.pop("AGNES_API_KEY", None)
    return CliRunner(env=env)


@pytest.fixture(autouse=True)
def _reset_console_quiet():
    """A crashed --json run leaves the global rich console quiet (the
    process dies before the restore); reset it so later tests see output."""
    from brandly_cli.cli import console

    original = console.quiet
    yield
    console.quiet = original


def _png_bytes() -> bytes:
    buf = _io.BytesIO()
    Image.new("RGB", (64, 48), (1, 2, 3)).save(buf, "PNG")
    return buf.getvalue()


def _patch_client(content: bytes | None = None):
    """Patch httpx.AsyncClient so provider downloads return the given bytes."""
    data = content if content is not None else _png_bytes()

    resp = MagicMock()
    resp.content = data
    resp.raise_for_status = MagicMock()

    client = MagicMock()
    client.get = AsyncMock(return_value=resp)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)

    return patch("httpx.AsyncClient", return_value=cm)


def _b64_payload(b64_json: str | None = None) -> dict:
    return {
        "url": None,
        "b64_json": b64_json or base64.b64encode(_png_bytes()).decode(),
        "revised_prompt": None,
        "model": "agnes-image-2.5-flash",
        "generated_at": "2026-01-01T00:00:00Z",
    }


def _job_records(root: Path) -> list[Path]:
    jobs_dir = root / ".brandly" / "jobs"
    if not jobs_dir.exists():
        return []
    return sorted(jobs_dir.glob("*.json"))


def _first_job(root: Path) -> dict:
    records = _job_records(root)
    assert len(records) == 1, f"expected exactly one job record, got {records}"
    return json.loads(records[0].read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# AC1: durable job record is created BEFORE the provider call
# ---------------------------------------------------------------------------


def test_image_success_creates_durable_job_record(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "plates" / "img.png"
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.return_value = _b64_payload()
        result = runner.invoke(cli, ["image", "-p", "a plate", "--output", str(out), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "success"
    job_id = data["job_id"]
    assert isinstance(job_id, str) and len(job_id) >= 8

    record = _first_job(tmp_path)
    assert record["job_id"] == job_id
    assert record["status"] == "succeeded"
    assert record["kind"] == "image"


# ---------------------------------------------------------------------------
# Crash / disconnect: a dead process leaves a non-terminal record
# ---------------------------------------------------------------------------


def test_provider_crash_leaves_running_record(runner: CliRunner, tmp_path: Path) -> None:
    """Simulate a hard crash mid-generation: no terminal state is written."""
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.side_effect = SystemExit(137)
        result = runner.invoke(cli, ["image", "-p", "a plate", "--json"])

    assert result.exit_code == 137
    record = _first_job(tmp_path)
    assert record["status"] == "running"  # never reached a terminal write


def test_provider_failure_records_failed_state(runner: CliRunner, tmp_path: Path) -> None:
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.side_effect = RuntimeError("agnes down")
        result = runner.invoke(cli, ["image", "-p", "a plate", "--json"])

    assert result.exit_code == 1, result.output
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["job_id"]
    record = _first_job(tmp_path)
    assert record["status"] == "failed"
    assert "agnes down" in record["error"]


def test_no_payload_records_failed_state(runner: CliRunner, tmp_path: Path) -> None:
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.return_value = {
            "url": None,
            "b64_json": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(
            cli, ["image", "-p", "a plate", "--output", str(tmp_path / "o.png"), "--json"]
        )

    assert result.exit_code == 1, result.output
    record = _first_job(tmp_path)
    assert record["status"] == "failed"


# ---------------------------------------------------------------------------
# AC2: disconnect recovery — result retrieved without resubmission
# ---------------------------------------------------------------------------


def _simulate_remote_completion(root: Path, record: dict) -> Path:
    """Stand in for 'the provider finished while we were away'.

    The durable artifact is captured exactly the way a healthy run
    captures it: validated image bytes written into the job store.
    """
    from brandly_cli import jobs

    info = jobs.save_job_image(record, b64_json=base64.b64encode(_png_bytes()).decode())
    jobs.save_job({**record, "status": "succeeded"})
    return Path(info["path"])


def test_poll_retrieves_result_after_disconnect(runner: CliRunner, tmp_path: Path) -> None:
    # 1) Start a job, crash before completion.
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.side_effect = SystemExit(137)
        runner.invoke(cli, ["image", "-p", "a plate"])
    record = _first_job(tmp_path)
    job_id = record["job_id"]

    # 2) The generation completes remotely; the durable result is captured.
    artifact = _simulate_remote_completion(tmp_path, record)
    assert artifact.is_file()

    # 3) Poll (a fresh process) — recovers the result, zero provider calls.
    with patch("brandly_cli.cmd.generation.generate_image") as gen2:
        result = runner.invoke(cli, ["job-poll", job_id, "--json"])
        assert gen2.call_count == 0, "polling must never submit a generation"

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "succeeded"
    assert data["result_available"] is True
    assert data["path"] == str(artifact)
    assert data["job_id"] == job_id


def test_poll_output_flag_copies_recovered_result(runner: CliRunner, tmp_path: Path) -> None:
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.side_effect = SystemExit(137)
        runner.invoke(cli, ["image", "-p", "a plate"])
    record = _first_job(tmp_path)
    artifact = _simulate_remote_completion(tmp_path, record)

    dest = tmp_path / "recovered" / "copy.png"
    result = runner.invoke(cli, ["job-poll", record["job_id"], "--output", str(dest)])

    assert result.exit_code == 0, result.output
    assert dest.is_file()
    with Image.open(dest) as im:
        assert im.size == (64, 48)
    # The record's canonical artifact path is untouched by the copy.
    canonical = tmp_path / ".brandly" / "jobs" / f"{record['job_id']}.json"
    assert json.loads(canonical.read_text(encoding="utf-8"))["path"] == str(artifact)


def test_job_id_is_emitted_in_text_mode(runner: CliRunner, tmp_path: Path) -> None:
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.return_value = _b64_payload()
        result = runner.invoke(cli, ["image", "-p", "a plate", "--output", str(tmp_path / "t.png")])

    assert result.exit_code == 0, result.output
    record = _first_job(tmp_path)
    assert record["job_id"] in result.output


# ---------------------------------------------------------------------------
# AC3: machine-readable polling states and exit codes
# ---------------------------------------------------------------------------


def test_poll_running_is_intermediate_exit_zero(runner: CliRunner, tmp_path: Path) -> None:
    from brandly_cli import jobs

    rec = jobs.create_image_job(tmp_path, prompt="p", model="m", size="2K", ratio="16:9")
    result = runner.invoke(cli, ["job-poll", rec["job_id"], "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "running"
    assert data["result_available"] is False


def test_poll_unknown_id_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(cli, ["job-poll", "0" * 32, "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["error_code"] == "job_not_found"


def test_poll_stale_running_reports_expired(runner: CliRunner, tmp_path: Path) -> None:
    from brandly_cli import jobs

    rec = jobs.create_image_job(tmp_path, prompt="p", model="m", size="2K", ratio="16:9")
    jobs.save_job(rec)
    path = jobs.record_path(tmp_path, rec["job_id"])
    old = json.loads(path.read_text(encoding="utf-8"))
    stale = __import__("datetime").datetime.fromisoformat(
        old["created_at"].replace("Z", "+00:00")
    ) - timedelta(hours=48)
    old["created_at"] = stale.isoformat()
    path.write_text(json.dumps(old), encoding="utf-8")

    result = runner.invoke(cli, ["job-poll", rec["job_id"], "--json", "--max-age", "3600"])
    assert result.exit_code != 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "expired"


def test_poll_failed_job_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    from brandly_cli import jobs

    rec = jobs.create_image_job(tmp_path, prompt="p", model="m", size="2K", ratio="16:9")
    jobs.save_job({**rec, "status": "failed", "error": "provider 500"})

    result = runner.invoke(cli, ["job-poll", rec["job_id"], "--json"])
    assert result.exit_code != 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "failed"
    assert data["result_available"] is False


# ---------------------------------------------------------------------------
# AC4: credentials/tokens never persisted
# ---------------------------------------------------------------------------


def test_credential_urls_are_redacted_in_record(runner: CliRunner, tmp_path: Path) -> None:
    from brandly_cli import jobs

    url = (
        "https://cdn.example.com/img.png"
        "?AWSAccessKeyId=AKIA123&Signature=sig-val&token=tok&secret=sec"
    )
    record = jobs.create_image_job(tmp_path, prompt="p", model="m", size="2K", ratio="16:9")
    with _patch_client():  # no real network: provider download is faked
        info = jobs.save_job_image(record, url=url)
    jobs.save_job({**record, "status": "succeeded"})

    raw = jobs.record_path(tmp_path, record["job_id"]).read_text(encoding="utf-8")
    for secret in ("AKIA123", "sig-val", "tok", "sec"):
        assert secret not in raw, f"credential material leaked: {secret}"
    # The redacted URL still names the resource (host/path preserved).
    assert "cdn.example.com" in raw
    assert info["path"].is_file()  # artifact capture unaffected by redaction


def test_image_json_success_redacts_provider_url(runner: CliRunner, tmp_path: Path) -> None:
    cred_url = "https://cdn.example.com/img.png?key=SECRETKEY"
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.return_value = {
            "url": cred_url,
            "b64_json": base64.b64encode(_png_bytes()).decode(),
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(
            cli,
            [
                "image",
                "-p",
                "a plate",
                "--output",
                str(tmp_path / "o.png"),
                "--json",
            ],
        )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "SECRETKEY" not in json.dumps(data)
    record = _first_job(tmp_path)
    assert "SECRETKEY" not in json.dumps(record)


# ---------------------------------------------------------------------------
# jobs-module invariants (unit)
# ---------------------------------------------------------------------------


def test_jobs_module_rejects_malformed_ids(tmp_path: Path) -> None:
    from brandly_cli import jobs

    for bad in ("../evil", "a/b", "UPPER", "", "x" * 100):
        assert jobs.load_job(tmp_path, bad) is None, bad
    # Traversal never escapes the job store.
    rec = jobs.create_image_job(tmp_path, prompt="p", model="m", size="2K", ratio="16:9")
    assert jobs.record_path(tmp_path, rec["job_id"]).parent == tmp_path / ".brandly" / "jobs"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
