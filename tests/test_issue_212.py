r"""Issue #212: ``brandly image`` has no auto-ref opt-out and silently rewrites
the prompt via ``--style-preset``.

Two compounding causes:
1. ``--style-preset`` appends photoreal/fashion language to the user's prompt
   (recorded in ``image_analysis.enhanced_prompt``) that directly contradicts
   the requested medium — and nothing distinguishes what the preset added.
2. Every ``brandly image`` call in a project silently attaches ALL other
   project plates as references ("Found N artifact(s) for reference") with no
   opt-out — for a style-locked grid, nine photoreal plates are injected as
   visual guides into a request for uniform pencil sketches.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

import base64
import io as _io
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id


def _tiny_png_b64() -> str:
    """A small valid PNG as base64 so the download path needs no network."""
    buf = _io.BytesIO()
    Image.new("RGB", (16, 16), (10, 10, 10)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path / ".brandly"


@pytest.fixture
def runner(project_dir: Path, tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, project_id: str) -> None:
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(json.dumps({"id": project_id, "name": "Test"}))


def _add_plate(project_dir: Path, pid: str, category: str, name: str) -> None:
    p = project_dir.parent / "pre-production" / pid / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (10, 10, 10)).save(p, "PNG")


def _fake_generate() -> Any:
    async def _gen(prompt, model=None, size=None, ratio=None, **kw):
        return {"url": None, "b64_json": _tiny_png_b64(), "task_id": None}

    return _gen


class TestImageAutoRefOptOut:
    def test_no_auto_refs_disables_injection(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.jpg")
        _add_plate(project_dir, pid, "prop", "prop_b.jpg")
        with patch(
            "brandly_cli.cmd.generation.generate_image", new=_fake_generate()
        ):
            result = runner.invoke(
                cli,
                [
                    "image", "--project-id", pid,
                    "--prompt", "a graphite pencil storyboard",
                    "--no-auto-refs",
                    "--output", str(tmp_path / "out.png"),
                ],
            )
        assert result.exit_code == 0, result.output
        assert (
            "artifact(s) for reference" not in result.output
        ), "--no-auto-refs must disable the auto-ref injection"

    def test_auto_ref_category_scopes_injection(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.jpg")
        _add_plate(project_dir, pid, "prop", "prop_b.jpg")
        with patch(
            "brandly_cli.cmd.generation.generate_image", new=_fake_generate()
        ):
            result = runner.invoke(
                cli,
                [
                    "image", "--project-id", pid,
                    "--prompt", "a graphite pencil storyboard",
                    "--auto-ref-category", "prop",
                    "--output", str(tmp_path / "out.png"),
                ],
            )
        assert result.exit_code == 0, result.output
        assert (
            "Found 1 artifact(s) for reference" in result.output
        ), "--auto-ref-category prop must scope the injection to the prop plates only"

    def test_auto_refs_on_by_default_unchanged(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        # Guard: without the new flags the legacy behavior is unchanged.
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.jpg")
        _add_plate(project_dir, pid, "prop", "prop_b.jpg")
        with patch(
            "brandly_cli.cmd.generation.generate_image", new=_fake_generate()
        ):
            result = runner.invoke(
                cli,
                [
                    "image", "--project-id", pid,
                    "--prompt", "a graphite pencil storyboard",
                    "--output", str(tmp_path / "out.png"),
                ],
            )
        assert result.exit_code == 0, result.output
        assert "Found 2 artifact(s) for reference" in result.output

    def test_preset_appending_is_recorded(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        with patch(
            "brandly_cli.cmd.generation.generate_image", new=_fake_generate()
        ):
            result = runner.invoke(
                cli,
                [
                    "image", "--project-id", pid,
                    "--prompt", "rough graphite pencil sketch",
                    "--style-preset", "editorial",
                    "--output", str(tmp_path / "out.png"),
                ],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(
            (project_dir / pid / "project.json").read_text(encoding="utf-8")
        )
        analysis = data.get("image_analysis") or {}
        assert (
            analysis.get("preset_applied") is True
        ), "image_analysis must record preset_applied so the rewrite is visible"
        appended = (analysis.get("preset_text") or "").strip()
        assert appended, "image_analysis must record the appended preset string"

    def test_dry_run_spends_no_credits(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.jpg")
        with patch(
            "brandly_cli.cmd.generation.generate_image",
            side_effect=_fake_generate(),
        ) as gen_mock:
            result = runner.invoke(
                cli,
                [
                    "image", "--project-id", pid,
                    "--prompt", "a graphite pencil storyboard",
                    "--dry-run",
                ],
            )
        assert result.exit_code == 0, result.output
        gen_mock.assert_not_called()
        assert "Dry run" in result.output
        assert (
            "a graphite pencil storyboard" in result.output
        ), "--dry-run must print the exact final prompt"
        assert (
            "char_a" in result.output
        ), "--dry-run must print the resolved reference list"
