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

    `project_dir` is the .brandly root (as returned by the fixture),
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
    assert "Subject and Character" in result
    assert "Composition and Layout" in result
    assert "Lighting and Technical" in result
    assert "Constraints" in result
    assert "Nike Air Max 1, white colorway" in result
    assert "seamless matte neutral mid-grey" in result
    assert "16:9" in result


def test_build_reference_prompt_character() -> None:
    result = build_reference_prompt("character", "Maya, mid-20s, dark hair")
    # Four-section structure, each exactly once, in order.
    assert result.count("Subject and Character") == 1
    assert result.count("Composition and Layout") == 1
    assert result.count("Lighting and Technical") == 1
    assert result.count("Constraints") == 1
    assert "Maya, mid-20s, dark hair" in result
    # The goal's exact structural markers:
    assert "2 by 2 grid" in result
    assert "seamless matte neutral mid-grey" in result
    assert "extreme close-up of the face from eyes to chin" in result
    assert "full-body front-facing standing view" in result
    assert "full-body back standing view" in result
    assert "85mm lens" in result
    # Constraints section:
    assert "No text, no labels, no watermarks, no logos" in result
    assert "no distorted facial features" in result


def test_build_reference_prompt_location() -> None:
    result = build_reference_prompt("location", "Modern kitchen, white marble")
    assert "Subject and Character" in result
    assert "Composition and Layout" in result
    assert "Lighting and Technical" in result
    assert "Constraints" in result
    assert "Modern kitchen, white marble" in result
    assert "No people" in result
    assert "16:9" in result


def test_build_reference_prompt_unknown_returns_empty() -> None:
    assert build_reference_prompt("not_a_sheet", "anything") == ""


def test_build_reference_prompt_vehicle() -> None:
    """Vehicle templates use the 4-section matte-grey board layout."""
    result = build_reference_prompt("vehicle", "Vintage Porsche 911, silver")
    assert "Subject and Character" in result
    assert "Vintage Porsche 911, silver" in result
    assert "16:9" in result
    assert "seamless matte neutral mid-grey" in result
    assert "front three-quarter" in result.lower()
    assert "rear three-quarter" in result.lower()


def test_build_reference_prompt_animal() -> None:
    """Animal templates use the 4-section matte-grey board layout."""
    result = build_reference_prompt("animal", "Adult golden retriever")
    assert "Subject and Character" in result
    assert "Adult golden retriever" in result
    assert "16:9" in result
    assert "seamless matte neutral mid-grey" in result
    assert "head close-up" in result.lower()


def test_build_reference_prompt_plant() -> None:
    """Plant templates use the 4-section matte-grey board layout."""
    result = build_reference_prompt("plant", "Monstera deliciosa")
    assert "Subject and Character" in result
    assert "Monstera deliciosa" in result
    assert "16:9" in result
    assert "seamless matte neutral mid-grey" in result
    assert "leaf detail" in result.lower()


def test_build_reference_prompt_mecha() -> None:
    """Mecha templates use the 4-section matte-grey board layout."""
    result = build_reference_prompt("mecha", "Bipedal combat mech")
    assert "Subject and Character" in result
    assert "Bipedal combat mech" in result
    assert "16:9" in result
    assert "seamless matte neutral mid-grey" in result
    assert "front three-quarter" in result.lower()


def test_all_sheets_use_matt_grey_backdrop() -> None:
    """Every sheet template must specify the seamless matte mid-grey backdrop."""
    for sheet in ["object", "character", "vehicle", "animal", "plant", "mecha", "location"]:
        result = build_reference_prompt(sheet, "test subject")
        for header in (
            "Subject and Character",
            "Composition and Layout",
            "Lighting and Technical",
            "Constraints",
        ):
            assert header in result, f"{sheet} template missing '{header}'"
        # Sheets (non-location) require the matte grey board backdrop; location
        # is a full-frame environment and does not use a studio board.
        if sheet != "location":
            assert "seamless matte neutral mid-grey" in result, (
                f"{sheet} template missing matte-grey backdrop"
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
    def fake_save(url, project_id, kind, root=None, prompt_hint="", category=None):  # noqa: ANN001
        target_dir = root / ".brandly" / project_id / "images" / (category or "general")
        target_dir.mkdir(parents=True, exist_ok=True)
        target = (
            target_dir
            / f"images_reference-{prompt_hint.replace(' ', '_')[:30]}.png"
        )
        target.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return target

    with (
        patch("brandly_cli.cmd.generation.generate_image", AsyncMock(return_value=fake_result)),
        patch("brandly_cli.cmd.generation._save_artifact", side_effect=fake_save),
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

    # Reference image file must exist — objects live in images/prop/
    prop_dir = project_dir / pid / "images" / "prop"
    ref_files = list(prop_dir.glob("prop_*.png"))
    assert len(ref_files) >= 1, f"expected a prop_*.png in {prop_dir}"
    assert all(f.stat().st_size > 0 for f in ref_files)


def test_reference_image_api_failure_writes_fail_doc(
    runner: CliRunner, project_dir: Path
) -> None:
    """When Agnes returns an error, a fail doc is written and exit code is 1."""
    pid = generate_project_id()
    _write_project(project_dir, pid)

    with patch(
        "brandly_cli.cmd.generation.generate_image",
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
        "brandly_cli.cmd.generation.create_video_task", AsyncMock(return_value=fake_result)
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
                "--no-wait",
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
    # (primary references live in images/<category>/ — objects in images/prop/)
    prop_dir = project_dir / pid / "images" / "prop"
    prop_dir.mkdir(parents=True, exist_ok=True)
    ref_file = prop_dir / "prop_reference_2026-01-01_000000.png"
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
        "brandly_cli.cmd.generation.create_video_task", AsyncMock(return_value=fake_result)
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
                "--no-wait",
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

    # Mock the API so the test never touches the network (or spends credits).
    with patch(
        "brandly_cli.cmd.generation.create_video_task",
        AsyncMock(
            return_value={
                "video_id": "video-task-stale",
                "url": "",
                "status": "queued",
                "progress": 0,
            }
        ),
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
                "--no-wait",
            ],
        )

    # The warn-but-proceed path should kick in (no --require-reference)
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
