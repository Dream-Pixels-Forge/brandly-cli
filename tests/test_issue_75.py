"""Issue #75: image workflow must isolate generated metadata to the selected
project context.

Acceptance criteria covered:
  2. A run without an intentional project context reports that context
     clearly and does not create misleading undefined/untitled records.
  4. An external run (isolated ROOT home + explicit --output destination)
     leaves the surrounding tree unchanged.
"""

from __future__ import annotations

import base64
import io as _io
import os
import time
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
    """A crashed --json run leaves the global rich console quiet; reset it so
    later tests see output."""
    from brandly_cli.cli import console

    original = console.quiet
    yield
    console.quiet = original


def _png_bytes() -> bytes:
    buf = _io.BytesIO()
    Image.new("RGB", (64, 48), (1, 2, 3)).save(buf, "PNG")
    return buf.getvalue()


def _patch_client():
    """Patch httpx.AsyncClient so no real network happens (downloads faked)."""
    resp = MagicMock()
    resp.content = _png_bytes()
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch("httpx.AsyncClient", return_value=cm)


def _tree(root: Path) -> set[str]:
    """All relative file+dir entries under root — the 'repository tree',
    normalised to ``/`` separators (platform-independent assertions)."""
    entries: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            entries.add(str(Path(dirpath).relative_to(root) / name).replace(os.sep, "/"))
    return entries


def _tree_minus_job_store(tree: set[str]) -> set[str]:
    """Drop the root-level durable job store (``.brandly/jobs``, #74).

    The job store is deliberately home-level and exists regardless of any
    project context, so #75's "no metadata" assertions must not treat it
    as a project-metadata leak."""
    kept = {e for e in tree if e != ".brandly/jobs" and not e.startswith(".brandly/jobs/")}
    # The container itself is not metadata: drop it when its only content
    # was the job store.
    if ".brandly" in kept and not any(e.startswith(".brandly/") and e != ".brandly" for e in kept):
        kept.discard(".brandly")
    return kept


def _fake_save_factory() -> tuple[patch, list[str]]:
    """Simulate save_artifact's filesystem effect: write a marker file under
    the exact media root the real function would use, so any implicit
    project context becomes visible in the tree."""
    from brandly_cli import layout

    calls: list[str] = []

    def fake_save(
        url: str,
        project_id: str,
        type_label: str,
        *,
        root: Path,
        prompt_hint: str = "",
        category: str | None = None,
        filename: str | None = None,
    ) -> Path | None:
        calls.append(project_id)
        if not url:
            return None
        media_category = category or "general"
        artifacts_dir = layout.resolve_media_root(root, project_id, type_label) / media_category
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = artifacts_dir / f"{type_label}_{int(time.time())}_{prompt_hint[:24]}.png"
        path.write_bytes(_png_bytes())
        return path

    return patch("brandly_cli.cmd.generation._save_artifact", side_effect=fake_save), calls


# ---------------------------------------------------------------------------
# AC2: no project context -> explicit report, no untitled/undefined records
# ---------------------------------------------------------------------------


def test_no_project_run_creates_no_project_records(runner: CliRunner, tmp_path: Path) -> None:
    save_patch, save_calls = _fake_save_factory()
    before = _tree(tmp_path)

    with (
        _patch_client(),
        patch("brandly_cli.cmd.generation.generate_image") as gen,
        save_patch,
    ):
        gen.return_value = {
            "url": "https://cdn.example.com/a.png",
            "b64_json": None,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "a plate"])

    assert result.exit_code == 0, result.output
    # No implicit autosave under an inferred project context.
    assert save_calls == [], f"implicit save with context: {save_calls}"
    # No project metadata: the only writes allowed are the root-level durable
    # job store (#74) — everything else in the home must be untouched.
    added = _tree_minus_job_store(_tree(tmp_path)) - before
    assert not added, f"unexpected project-metadata changes: {sorted(added)[:10]}"


def test_no_project_run_reports_context_explicitly(runner: CliRunner, tmp_path: Path) -> None:
    save_patch, _save_calls = _fake_save_factory()
    with (
        _patch_client(),
        patch("brandly_cli.cmd.generation.generate_image") as gen,
        save_patch,
    ):
        gen.return_value = {
            "url": "https://cdn.example.com/a.png",
            "b64_json": None,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "a plate"])

    assert result.exit_code == 0, result.output
    assert "Image generated" in result.output  # text mode still works
    # The absence of a project context is reported, with the two ways out.
    assert "--project-id" in result.output
    assert "--output" in result.output


# ---------------------------------------------------------------------------
# Explicit project context: behavior preserved, metadata stays inside it
# ---------------------------------------------------------------------------


def test_explicit_project_still_saves_and_records(runner: CliRunner, tmp_path: Path) -> None:
    """With an intentional project, autosave + docs keep working — under that
    project only (no 'untitled' anywhere)."""
    with (
        _patch_client(),
        patch("brandly_cli.cmd.generation.generate_image") as gen,
    ):
        gen.return_value = {
            "url": "https://cdn.example.com/a.png",
            "b64_json": None,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "a plate", "--project-id", "myproj"])

    assert result.exit_code == 0, result.output
    # Autosaved media lands in the selected project's media root (v2 layout).
    media_root = tmp_path / "pre-production" / "myproj" / "general"
    assert any(media_root.iterdir()), "expected autosaved media under pre-production/myproj"
    # Generation doc written under the project's docs dir.
    assert (tmp_path / ".brandly" / "myproj" / "docs").exists()
    tree = _tree(tmp_path)
    assert not any("untitled" in entry for entry in tree)


# ---------------------------------------------------------------------------
# AC4: external runs leave the surrounding tree unchanged
# ---------------------------------------------------------------------------


def test_external_run_without_project_touches_nothing(runner: CliRunner, tmp_path: Path) -> None:
    """An external b64 run (isolated ROOT home, no --project-id, --output to
    an external destination) must not create any project records at all."""
    dest = tmp_path / "external" / "plate.png"
    b64 = base64.b64encode(_png_bytes()).decode()
    before = _tree(tmp_path)
    with (
        _patch_client(),
        patch("brandly_cli.cmd.generation.generate_image") as gen,
    ):
        gen.return_value = {
            "url": None,
            "b64_json": b64,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "a plate", "--output", str(dest), "--json"])

    assert result.exit_code == 0, result.output
    assert dest.is_file()
    added = _tree_minus_job_store(_tree(tmp_path)) - before
    assert added == {"external", "external/plate.png"}, f"unexpected tree changes: {sorted(added)}"


def test_external_run_with_project_keeps_metadata_inside_project(
    runner: CliRunner, tmp_path: Path
) -> None:
    """With an explicit project, an external --output run writes metadata only
    under that project — nothing under pre-production/ or untitled."""
    dest = tmp_path / "external" / "plate.png"
    b64 = base64.b64encode(_png_bytes()).decode()
    before = _tree(tmp_path)
    with (
        _patch_client(),
        patch("brandly_cli.cmd.generation.generate_image") as gen,
    ):
        gen.return_value = {
            "url": None,
            "b64_json": b64,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(
            cli, ["image", "-p", "a plate", "--output", str(dest), "--project-id", "myproj"]
        )

    assert result.exit_code == 0, result.output
    assert dest.is_file()
    added = _tree(tmp_path) - before
    for entry in sorted(added):
        parts = entry.split("/")
        if parts == ["external"] or parts == [".brandly"] or parts == ["pre-production"]:
            continue  # top-level container directories
        if parts[:2] == [".brandly", "jobs"]:
            continue  # root-level durable job store (#74), not project metadata
        if parts[0] == "external":
            assert entry == "external/plate.png", f"unexpected external write: {entry}"
        elif parts[0] in (".brandly", "pre-production"):
            assert len(parts) > 1 and parts[1] == "myproj", (
                f"metadata leaked outside the project: {entry}"
            )
        else:
            raise AssertionError(f"unexpected top-level entry: {entry}")
    assert not any("untitled" in entry for entry in added)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
