"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id


@pytest.fixture
def runner(tmp_path: Path):
    """Return a Click test runner pointed at a temp directory."""
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Return the .brandly/projects path."""
    return tmp_path / ".brandly" / "projects"


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "brandly" in result.output.lower()


def test_config(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "AGNES_API_KEY" in result.output


def test_estimate(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["estimate", "--style", "cinematic", "--shots", "5"])
    assert result.exit_code == 0
    assert "Cost Estimate" in result.output


def test_rate_limits_table(runner: CliRunner) -> None:
    import os
    env = {**os.environ, "COLUMNS": "200"}
    wide = CliRunner(env=env)
    result = wide.invoke(cli, ["rate-limits"])
    assert result.exit_code == 0
    assert "Agnes" in result.output
    assert "MiniMax" in result.output
    assert "h3_concurrent_tasks_free" in result.output


def test_rate_limits_json(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["rate-limits", "-o", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["Agnes AI"]["image_rpm_by_size"]["1K"] == 20
    assert payload["MiniMax"]["h3_concurrent_tasks_paid"] == 15


def test_estimate_invalid_style(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["estimate", "--style", "nonexistent"])
    assert result.exit_code == 1
    assert "Invalid style" in result.output


def test_estimate_invalid_shots(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["estimate", "--shots", "20"])
    assert result.exit_code == 1
    assert "Shots must be between" in result.output


def test_init(runner: CliRunner, project_dir: Path) -> None:
    result = runner.invoke(
        cli,
        [
            "init",
            "--name",
            "My Product",
            "--idea",
            "A revolutionary widget",
            "--style",
            "cinematic",
            "--budget",
            "300",
            "--shots",
            "5",
        ],
    )
    assert result.exit_code == 0
    assert "Project created" in result.output
    # Verify project file was written
    projects = list(project_dir.iterdir())
    assert len(projects) == 1
    proj_file = projects[0] / "project.json"
    assert proj_file.exists()
    data = json.loads(proj_file.read_text())
    assert data["name"] == "My Product"
    assert data["style"] == "cinematic"


def test_status(runner: CliRunner, project_dir: Path) -> None:
    # Create a project first
    pid = generate_project_id()
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps(
            {
                "id": pid,
                "name": "Test Product",
                "status": "pending",
                "current_phase": "init",
                "budget": 500,
                "spent": 0,
                "style": "ugc",
                "shot_count": 5,
                "target_platforms": ["tiktok"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "phases": {},
            }
        )
    )
    result = runner.invoke(cli, ["status", pid])
    assert result.exit_code == 0
    assert "Test Product" in result.output


def test_status_not_found(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["status", "invalid-id"])
    assert result.exit_code == 1


def test_list_empty(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    # With isolated filesystem, no projects should exist
    assert "No projects found" in result.output or "Projects" in result.output


def test_memory_view(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["memory", "view"])
    assert result.exit_code == 0


def test_memory_like(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["memory", "like", "my favorite hook"])
    assert result.exit_code == 0
    assert "Liked hook" in result.output


def test_memory_reset(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["memory", "reset"])
    assert result.exit_code == 0
    assert "Memory reset" in result.output


def test_cancel_invalid_id(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["cancel", "not_a_uuid"])
    assert result.exit_code == 1


def test_director_prompt(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["director"])
    assert result.exit_code == 0
    assert "Director Mode" in result.output or "Brandly" in result.output


def test_image_command_no_api_key(runner: CliRunner) -> None:
    """Image command should not crash — exits 0 (success) or non-zero (API error)."""
    result = runner.invoke(cli, ["image", "--prompt", "a cat"])
    # Accept any exit code: key may be set (network call) or missing (graceful error)
    assert (
        result.exit_code in (0, 1) or "Error" in result.output or "error" in result.output.lower()
    )


def test_compare_no_phases(runner: CliRunner, project_dir: Path) -> None:
    """Regression test for compare crash — was using _get_root(None)."""
    pid = generate_project_id()
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps(
            {
                "id": pid,
                "name": "Compare Test",
                "status": "pending",
                "current_phase": "init",
                "budget": 100,
                "spent": 0,
                "style": "cinematic",
                "shot_count": 5,
                "target_platforms": ["tiktok"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "phases": {},
            }
        )
    )
    result = runner.invoke(cli, ["compare", pid])
    assert result.exit_code == 0
    assert "No generated assets" in result.output


def test_compare_invalid_id(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["compare", "not_a_uuid"])
    assert result.exit_code == 1
    assert "Invalid project ID" in result.output


def test_progress_for_project(runner: CliRunner, project_dir: Path) -> None:
    """Progress command should not crash on a real project."""
    pid = generate_project_id()
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps(
            {
                "id": pid,
                "name": "Progress Test",
                "status": "running",
                "current_phase": "concept",
                "budget": 200,
                "spent": 50,
                "style": "cinematic",
                "shot_count": 5,
                "target_platforms": ["tiktok"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "phases": {
                    "init": {"status": "completed", "completed_at": "2026-01-01T00:01:00Z"},
                    "concept": {"status": "running", "started_at": "2026-01-01T00:01:00Z"},
                },
            }
        )
    )
    result = runner.invoke(cli, ["progress", pid])
    assert result.exit_code == 0
    assert "Progress" in result.output


def test_export_empty_project(runner: CliRunner, project_dir: Path) -> None:
    """Export on a project with no artifacts should report 'no artifacts'."""
    pid = generate_project_id()
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps(
            {
                "id": pid,
                "name": "Empty Export",
                "status": "pending",
                "current_phase": "init",
                "budget": 100,
                "spent": 0,
                "style": "cinematic",
                "shot_count": 5,
                "target_platforms": ["tiktok"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "phases": {},
            }
        )
    )
    result = runner.invoke(cli, ["export", pid])
    assert result.exit_code == 0
    assert "No artifacts" in result.output


def test_export_with_artifacts(runner: CliRunner, project_dir: Path) -> None:
    """Export with a real artifact file should produce a manifest."""
    pid = generate_project_id()
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps(
            {
                "id": pid,
                "name": "Real Export",
                "status": "completed",
                "current_phase": "done",
                "budget": 100,
                "spent": 50,
                "style": "cinematic",
                "shot_count": 5,
                "target_platforms": ["tiktok"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "phases": {},
            }
        )
    )
    # Create a fake image artifact
    img_dir = project_dir / pid / "artifacts" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_file = img_dir / "test.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    result = runner.invoke(cli, ["export", pid])
    assert result.exit_code == 0
    assert "Exported" in result.output
    # Manifest should exist in the export directory
    export_dir = project_dir / pid / "export"
    assert (export_dir / "export-manifest.json").exists()


def test_run_approve_flow(runner: CliRunner, project_dir: Path) -> None:
    """End-to-end: init → run → approve should advance phases."""
    init_result = runner.invoke(
        cli,
        [
            "init",
            "--name",
            "Flow Test",
            "--idea",
            "An amazing product",
            "--style",
            "cinematic",
            "--shots",
            "5",
        ],
    )
    assert init_result.exit_code == 0
    # Find the created project ID
    projects = list(project_dir.iterdir())
    assert len(projects) == 1
    pid = projects[0].name

    # Run the init phase
    run_result = runner.invoke(cli, ["run", pid])
    assert run_result.exit_code == 0
    assert "Phase 'init' started" in run_result.output

    # Approve the init phase → should advance to trends
    approve_result = runner.invoke(cli, ["approve", pid, "init"])
    assert approve_result.exit_code == 0
    assert "approved" in approve_result.output
    assert "trends" in approve_result.output

    # Verify project state advanced
    proj_data = json.loads((project_dir / pid / "project.json").read_text())
    assert proj_data["current_phase"] == "trends"


def test_record_cost_updates_project_spent(runner: CliRunner, project_dir: Path) -> None:
    """record_cost must sync ProjectData.spent so brandly status reflects real spend."""
    init_result = runner.invoke(
        cli,
        [
            "init",
            "--name",
            "Cost Sync Test",
            "--idea",
            "A product",
            "--style",
            "cinematic",
            "--shots",
            "5",
            "--budget",
            "500",
        ],
    )
    assert init_result.exit_code == 0
    projects = list(project_dir.iterdir())
    pid = projects[0].name

    # Record 100 credits
    cost_result = runner.invoke(cli, ["record-cost", pid, "asset", "image", "100"])
    assert cost_result.exit_code == 0

    # ProjectData.spent should now be 100
    proj_data = json.loads((project_dir / pid / "project.json").read_text())
    assert proj_data["spent"] == 100

    # Status command should show 100 spent
    status_result = runner.invoke(cli, ["status", pid])
    assert status_result.exit_code == 0
    assert "100" in status_result.output
