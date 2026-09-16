"""Tests for `brandly reference` command and reference-aware video generation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from brandly_cli.cli import (
    REFERENCE_PROMPT_TEMPLATES,
    REFERENCE_SUBJECTS,
    build_reference_prompt,
    cli,
)
from brandly_cli.utils import generate_project_id


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Return the .brandly root (new layout: projects at .brandly/{id}/)."""
    return tmp_path / ".brandly"


@pytest.fixture
def runner(project_dir: Path, tmp_path: Path) -> CliRunner:
    """Return a Click test runner pointed at the temp root (where ROOT env is set)."""
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, project_id: str, **overrides: object) -> Path:
    """Write a minimal project.json to disk.

    `project_dir` is the .brandly/projects root (as returned by the fixture),
    so the file lands at project_dir/<id>/project.json.
    """
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id": project_id,
        "name": overrides.get("name", "Test Project"),
        "description": overrides.get(
            "description", "A test product description for reference workflow"
        ),
        "status": "pending",
        "current_phase": "asset",
        "budget": 200,
        "spent": 0,
        "style": "cinematic",
        "shot_count": 3,
        "target_platforms": ["tiktok"],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "phases": {},
    }
    data.update(overrides)
    proj_file.write_text(json.dumps(data))
    return proj_file


# ---------------------------------------------------------------------------
# build_reference_prompt — pure function tests
# ---------------------------------------------------------------------------


def test_build_reference_prompt_object() -> None:
    result = build_reference_prompt("object", "Nike Air Max 1, white colorway")
    assert "Professional product reference sheet" in result
    assert "Nike Air Max 1, white colorway" in result
    assert "no people" in result.lower()
    assert "studio product lighting" in result.lower()
    assert "16:9" in result
    assert "multi-view grid" in result.lower()
    assert "3-column grid" in result.lower()


def test_build_reference_prompt_character() -> None:
    result = build_reference_prompt("character", "Maya, mid-20s, dark hair")
    assert "Character reference sheet" in result
    assert "Maya, mid-20s, dark hair" in result
    assert "16:9" in result
    assert "multi-view grid" in result.lower()
    assert "front view" in result.lower()
    assert "pure side profile" in result.lower()
    assert "three-quarter view" in result.lower()


def test_build_reference_prompt_location() -> None:
    result = build_reference_prompt("location", "Modern kitchen, white marble")
    assert "Location reference sheet" in result
    assert "Modern kitchen, white marble" in result
    assert "no people" in result.lower()
    assert "16:9" in result
    # Location is the EXCEPTION — full-frame, no grid
    assert "full-frame" in result.lower()
    assert "no grid" in result.lower()
    assert "multi-view grid" not in result.lower()


def test_build_reference_prompt_unknown_returns_empty() -> None:
    assert build_reference_prompt("not_a_sheet", "anything") == ""


def test_build_reference_prompt_vehicle() -> None:
    """Vehicle templates use the 16:9 multi-view grid layout."""
    result = build_reference_prompt("vehicle", "Vintage Porsche 911, silver")
    assert "Vehicle reference sheet" in result
    assert "Vintage Porsche 911, silver" in result
    assert "16:9" in result
    assert "multi-view grid" in result.lower()
    assert "front three-quarter" in result.lower()
    assert "pure side profile" in result.lower()
    assert "rear three-quarter" in result.lower()


def test_build_reference_prompt_animal() -> None:
    """Animal templates use the 16:9 multi-view grid layout."""
    result = build_reference_prompt("animal", "Adult golden retriever")
    assert "Animal reference sheet" in result
    assert "Adult golden retriever" in result
    assert "16:9" in result
    assert "multi-view grid" in result.lower()
    assert "head close-up" in result.lower()


def test_build_reference_prompt_plant() -> None:
    """Plant templates use the 16:9 multi-view grid layout."""
    result = build_reference_prompt("plant", "Monstera deliciosa")
    assert "Plant reference sheet" in result
    assert "Monstera deliciosa" in result
    assert "16:9" in result
    assert "multi-view grid" in result.lower()
    assert "leaf detail" in result.lower()


def test_build_reference_prompt_mecha() -> None:
    """Mecha templates use the 16:9 multi-view grid layout."""
    result = build_reference_prompt("mecha", "Bipedal combat mech")
    assert "Mecha reference sheet" in result
    assert "Bipedal combat mech" in result
    assert "16:9" in result
    assert "multi-view grid" in result.lower()
    assert "front three-quarter" in result.lower()
    assert "pure side profile" in result.lower()


def test_all_non_location_sheets_use_multi_view_grid() -> None:
    """Sanity check: every sheet except 'location' must use the multi-view grid."""
    multi_view_sheets = ["object", "character", "vehicle", "animal", "plant", "mecha"]
    for sheet in multi_view_sheets:
        result = build_reference_prompt(sheet, "test subject")
        assert "16:9" in result, f"{sheet} template missing 16:9"
        assert "multi-view grid" in result.lower(), (
            f"{sheet} template missing multi-view grid"
        )
        assert "full-frame" not in result.lower(), (
            f"{sheet} should NOT use full-frame (only location does)"
        )


def test_reference_subjects_covers_all_skills() -> None:
    """Every subject type has a template and a skill mapping."""
    assert set(REFERENCE_SUBJECTS.keys()) == set(REFERENCE_PROMPT_TEMPLATES.keys())
    for subject_type, skill in REFERENCE_SUBJECTS.items():
        assert skill.startswith("brandly-")
        assert subject_type in REFERENCE_PROMPT_TEMPLATES


# ---------------------------------------------------------------------------
# brandly reference CLI — validation paths
# ---------------------------------------------------------------------------


def test_reference_invalid_project_id(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "reference",
            "not_a_uuid",
            "--subject-type",
            "object",
            "--subject",
            "test description",
        ],
    )
    assert result.exit_code == 1
    assert "Invalid project ID" in result.output


def test_reference_unknown_subject_type_choice(
    runner: CliRunner, project_dir: Path
) -> None:
    pid = generate_project_id()
    _write_project(project_dir, pid)
    result = runner.invoke(
        cli,
        ["reference", pid, "--subject-type", "spaceship", "--subject", "test"],
    )
    assert result.exit_code == 2  # Click usage error


# ---------------------------------------------------------------------------
# brandly reference CLI — success path (with mocked Agnes API)
# ---------------------------------------------------------------------------


def test_reference_generates_image_and_saves_metadata(
    runner: CliRunner, project_dir: Path
) -> None:
    """Successful reference generation: writes image, updates project.primary_reference."""
    pid = generate_project_id()
    _write_project(project_dir, pid, name="Nike Reference Test")

    fake_result = {
        "url": "https://example.invalid/reference.png",
        "id": "reference-task-123",
    }

    # _save_artifact tries real network — mock it to return a deterministic path
    def fake_save(url, project_id, kind, root=None, prompt_hint=""):  # noqa: ANN001
        refs_dir = root / ".brandly" / project_id / "refs"
        refs_dir.mkdir(parents=True, exist_ok=True)
        target = (
            refs_dir
            / f"images_reference-{prompt_hint.replace(' ', '_')[:30]}.png"
        )
        target.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return target

    with (
        patch("brandly_cli.cli.generate_image", AsyncMock(return_value=fake_result)),
        patch("brandly_cli.cli._save_artifact", side_effect=fake_save),
    ):
        result = runner.invoke(
            cli,
            [
                "reference",
                pid,
                "--subject-type",
                "object",
                "--subject",
                "Nike Air Max 1 white colorway visible Air unit",
                "--style-preset",
                "commercial",
                "--size",
                "2K",
                "--ratio",
                "16:9",
            ],
        )

    assert result.exit_code == 0, f"reference failed: {result.output}"
    assert "Reference image saved" in result.output
    assert "primary_reference metadata updated" in result.output
    assert "auto-injected" in result.output

    # Project must have primary_reference metadata
    proj_data = json.loads((project_dir / pid / "project.json").read_text())
    assert "primary_reference" in proj_data
    assert proj_data["primary_reference"]["subject_type"] == "object"
    assert proj_data["primary_reference"]["skill"] == "brandly-object-sheet"
    assert proj_data["primary_reference"]["style_preset"] == "commercial"
    assert "Nike Air Max 1" in proj_data["primary_reference"]["subject"]

    # Reference image file must exist
    refs_dir = project_dir / pid / "refs"
    # object sheets are named with the `prop_` prefix (see layout.build_sheet_filename)
    ref_files = list(refs_dir.glob("prop_*.png"))
    assert len(ref_files) >= 1, f"expected a prop_*.png in {refs_dir}"
    assert all(f.stat().st_size > 0 for f in ref_files)


def test_reference_image_api_failure_writes_fail_doc(
    runner: CliRunner, project_dir: Path
) -> None:
    """When Agnes returns an error, a fail doc is written and exit code is 1."""
    pid = generate_project_id()
    _write_project(project_dir, pid)

    with patch(
        "brandly_cli.cli.generate_image",
        AsyncMock(side_effect=RuntimeError("Service Unavailable")),
    ):
        result = runner.invoke(
            cli,
            [
                "reference",
                pid,
                "--subject-type",
                "character",
                "--subject",
                "Test character",
            ],
        )

    assert result.exit_code == 1
    docs_dir = project_dir / pid / "docs" / "tmp"
    fail_docs = list(docs_dir.glob("reference_fail_*.md"))
    assert len(fail_docs) == 1
    assert "Service Unavailable" in fail_docs[0].read_text()


# ---------------------------------------------------------------------------
# brandly anchor (DEPRECATED alias) — must still work and forward
# ---------------------------------------------------------------------------


def test_anchor_alias_forwards_to_reference(
    runner: CliRunner, project_dir: Path
) -> None:
    """`brandly anchor --sheet X -d Y` should still work (deprecation alias)."""
    pid = generate_project_id()
    _write_project(project_dir, pid)

    fake_result = {
        "url": "https://example.invalid/alias-ref.png",
        "id": "alias-task-123",
    }

    def fake_save(url, project_id, kind, root=None, prompt_hint=""):  # noqa: ANN001
        refs_dir = root / ".brandly" / project_id / "refs"
        refs_dir.mkdir(parents=True, exist_ok=True)
        target = refs_dir / f"images_{prompt_hint.replace(' ', '_')[:30]}.png"
        target.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return target

    with (
        patch("brandly_cli.cli.generate_image", AsyncMock(return_value=fake_result)),
        patch("brandly_cli.cli._save_artifact", side_effect=fake_save),
    ):
        result = runner.invoke(
            cli,
            [
                "anchor",
                pid,
                "--sheet",
                "object",
                "-d",
                "Test subject",
            ],
        )

    assert result.exit_code == 0, f"anchor alias failed: {result.output}"
    assert "deprecated" in result.output
    assert "Reference image saved" in result.output
    # primary_reference should be written (proving the alias actually forwarded)
    proj_data = json.loads((project_dir / pid / "project.json").read_text())
    assert "primary_reference" in proj_data


# ---------------------------------------------------------------------------
# brandly video — reference detection
# ---------------------------------------------------------------------------


def test_video_warns_when_no_reference(runner: CliRunner, project_dir: Path) -> None:
    """When project has no primary reference, video shows a warning (default)."""
    pid = generate_project_id()
    _write_project(project_dir, pid)

    fake_result = {
        "video_id": "video-task-123",
        "url": "https://example.invalid/clip.mp4",
        "status": "queued",
        "progress": 0,
    }
    with patch(
        "brandly_cli.cli.create_video_task", AsyncMock(return_value=fake_result)
    ):
        result = runner.invoke(
            cli,
            [
                "video",
                pid,
                "-p",
                "Test prompt",
                "--style",
                "cinematic",
            ],
        )

    assert "No primary reference" in result.output
    assert "Continuing without reference" in result.output


def test_video_fails_when_require_reference_and_no_reference(
    runner: CliRunner, project_dir: Path
) -> None:
    """With --require-reference, video should exit 2 if no primary reference."""
    pid = generate_project_id()
    _write_project(project_dir, pid)

    result = runner.invoke(
        cli,
        [
            "video",
            pid,
            "-p",
            "Test prompt",
            "--style",
            "cinematic",
            "--require-reference",
        ],
    )

    assert result.exit_code == 2
    assert "No primary reference" in result.output
    assert "Aborting" in result.output


def test_video_picks_up_primary_reference(
    runner: CliRunner, project_dir: Path
) -> None:
    """When project has primary_reference metadata, video uses it as first ref."""
    pid = generate_project_id()
    # Write project WITH primary_reference metadata and a real reference image
    refs_dir = project_dir / pid / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    ref_file = refs_dir / "reference_object_2026-01-01_000000.png"
    ref_file.write_bytes(b"\x89PNG\r\n\x1a\nfake reference")
    _write_project(
        project_dir,
        pid,
        primary_reference={
            "subject_type": "object",
            "skill": "brandly-object-sheet",
            "subject": "Test product",
            "image_path": str(ref_file),
            "source_url": "https://example.invalid/reference.png",
            "model": "agnes-image-2.0",
            "style_preset": "commercial",
            "generated_at": "2026-01-01T00:00:00Z",
        },
    )

    fake_result = {
        "video_id": "video-task-456",
        "url": "https://example.invalid/clip.mp4",
        "status": "queued",
        "progress": 0,
    }
    with patch(
        "brandly_cli.cli.create_video_task", AsyncMock(return_value=fake_result)
    ):
        result = runner.invoke(
            cli,
            [
                "video",
                pid,
                "-p",
                "Test prompt",
                "--style",
                "cinematic",
                "--require-reference",
            ],
        )

    assert result.exit_code == 0, f"video failed: {result.output}"
    assert "Primary reference:" in result.output
    assert "Reference images:" in result.output


def test_video_stale_reference_metadata_falls_back_to_warning(
    runner: CliRunner, project_dir: Path
) -> None:
    """If primary_reference points to a deleted file, treat as no reference."""
    pid = generate_project_id()
    _write_project(
        project_dir,
        pid,
        primary_reference={
            "subject_type": "object",
            "skill": "brandly-object-sheet",
            "image_path": "C:/nonexistent/deleted.png",
            "source_url": "",
        },
    )

    result = runner.invoke(
        cli,
        [
            "video",
            pid,
            "-p",
            "Test prompt",
            "--style",
            "cinematic",
        ],
    )

    # The warn-but-proceed path should kick in (no --require-reference)
    assert "No primary reference" in result.output


def test_video_deprecated_anchor_flag_still_works(
    runner: CliRunner, project_dir: Path
) -> None:
    """--require-anchor / --allow-anchorless should still work as deprecated aliases."""
    pid = generate_project_id()
    _write_project(project_dir, pid)

    # --require-anchor should still fail with exit code 2
    result = runner.invoke(
        cli,
        [
            "video",
            pid,
            "-p",
            "Test prompt",
            "--style",
            "cinematic",
            "--require-anchor",
        ],
    )
    assert result.exit_code == 2
    assert "No primary reference" in result.output


# ---------------------------------------------------------------------------
# ProjectManager.update — extra fields (regression test)
# ---------------------------------------------------------------------------


def test_project_manager_update_with_extra_field(tmp_path: Path) -> None:
    """Regression: ProjectManager.update must accept extra fields like 'primary_reference'."""
    import asyncio

    from brandly_cli.project_manager import ProjectManager
    from brandly_cli.types import ProjectData

    root = tmp_path
    pm = ProjectManager(root)
    pid = "test-extras"

    proj = ProjectData(
        id=pid,
        name="Extras Test",
        status="pending",
        current_phase="init",
        budget=100,
        spent=0,
    )
    asyncio.run(pm.create(proj))

    # Now update with an extra field not on the model
    asyncio.run(
        pm.update(
            pid,
            {
                "primary_reference": {
                    "subject_type": "object",
                    "image_path": "/tmp/x.png",
                },
                "custom_metadata": {"foo": "bar"},
            },
        )
    )

    # Re-read and verify the extras survived
    reloaded = asyncio.run(pm.read(pid))
    assert reloaded is not None
    extras = reloaded.model_extra or {}
    assert extras.get("primary_reference") == {
        "subject_type": "object",
        "image_path": "/tmp/x.png",
    }
    assert extras.get("custom_metadata") == {"foo": "bar"}
