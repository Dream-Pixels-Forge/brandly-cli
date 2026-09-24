"""Tests for the agent tool surface (Goal 1).

Behaviour under test: one dispatch layer that (a) exposes the brandly capability
set as a machine-readable manifest, (b) routes library tools to the existing
``agent_tools`` handlers, and (c) routes pipeline tools to real CLI commands.

Written test-first (RED) — see dev-notes/GOAL-AGENTIC-PIPELINE.md Goal 1.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from brandly_cli import agent_surface, agent_tools

# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


class TestToolManifest:
    def test_manifest_is_json_serializable(self) -> None:
        manifest = agent_surface.tool_manifest()
        payload = json.dumps(manifest)
        assert '"tools"' in payload

    def test_entries_carry_required_fields(self) -> None:
        manifest = agent_surface.tool_manifest()
        assert manifest["tools"], "manifest must not be empty"
        for entry in manifest["tools"]:
            for field in ("name", "description", "parameters", "read_only", "kind", "command"):
                assert field in entry, f"{entry.get('name')}: missing {field}"
            assert entry["parameters"]["type"] == "object"
            assert entry["kind"] in ("library", "cli")

    def test_read_only_core_tools_are_marked_read_only(self) -> None:
        entries = {e["name"]: e for e in agent_surface.tool_manifest()["tools"]}
        for name in ("list_projects", "get_project", "list_models", "get_timeline", "run_gate"):
            assert name in entries, f"{name} missing from manifest"
            assert entries[name]["read_only"] is True

    def test_pipeline_tools_are_cli_backed_and_not_read_only(self) -> None:
        entries = {e["name"]: e for e in agent_surface.tool_manifest()["tools"]}
        for name in ("produce", "stitch", "export_platforms", "job_poll"):
            assert name in entries, f"{name} missing from manifest"
            assert entries[name]["kind"] == "cli"
            assert entries[name]["read_only"] is False
            assert entries[name]["command"], f"{name} must map to a CLI command"

    def test_every_agent_tool_handler_is_exposed(self) -> None:
        """Single source of truth: no handler exists that agents cannot call."""
        manifest = {e["name"] for e in agent_surface.tool_manifest()["tools"]}
        missing = set(agent_tools.BUILTIN_TOOLS) - manifest
        assert not missing, f"handlers not exposed to agents: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Command building (pure — no subprocess)
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_produce_command_shape(self) -> None:
        argv = agent_surface.build_command("produce", {"project_id": "p1", "shots": "shots.json"})
        assert argv[:3] == [agent_surface.python_executable(), "-m", "brandly_cli"]
        assert argv[3:] == ["produce", "p1", "--shots", "shots.json"]

    def test_global_root_is_prefixed_before_the_subcommand(self) -> None:
        argv = agent_surface.build_command(
            "produce", {"project_id": "p1", "shots": "s.json"}, root="/tmp/home"
        )
        assert argv[3:] == ["--root", "/tmp/home", "produce", "p1", "--shots", "s.json"]

    def test_stitch_command_repeats_clips_and_sets_output(self) -> None:
        argv = agent_surface.build_command(
            "stitch", {"clips": ["a.mp4", "b.mp4"], "output": "final.mp4"}
        )
        assert argv[3:] == ["stitch", "a.mp4", "b.mp4", "--output", "final.mp4"]

    def test_job_poll_always_asks_for_machine_output(self) -> None:
        argv = agent_surface.build_command("job_poll", {"job_id": "job-1"})
        assert argv[3:] == ["job-poll", "job-1", "--json"]

    def test_job_poll_optional_flags(self) -> None:
        argv = agent_surface.build_command(
            "job_poll", {"job_id": "job-1", "max_age": 3600, "output": "out.png"}
        )
        assert argv[3:] == [
            "job-poll", "job-1", "--json", "--max-age", "3600", "--output", "out.png"
        ]

    def test_export_platforms_repeats_platform_flag(self) -> None:
        argv = agent_surface.build_command(
            "export_platforms", {"project_id": "p1", "platforms": ["tiktok", "youtube_standard"]}
        )
        assert argv[3:] == [
            "export-platforms", "p1", "--platforms", "tiktok", "--platforms", "youtube_standard"
        ]

    def test_missing_required_argument_raises(self) -> None:
        with pytest.raises(ValueError, match="shots"):
            agent_surface.build_command("produce", {"project_id": "p1"})

    def test_unknown_tool_raises(self) -> None:
        with pytest.raises(KeyError):
            agent_surface.build_command("not_a_tool", {})


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_library_tool_runs_real_handler(self) -> None:
        result = agent_surface.dispatch("list_models", {})
        assert result["ok"] is True
        assert result["tool"] == "list_models"
        assert result["data"], "list_models must return model data"

    def test_cli_tool_uses_injected_runner(self) -> None:
        seen: dict[str, Any] = {}

        def fake_runner(argv: list[str]) -> tuple[int, str, str]:
            seen["argv"] = argv
            return 0, '{"status": "success", "job_id": "job-9"}', ""

        result = agent_surface.dispatch("job_poll", {"job_id": "job-9"}, runner=fake_runner)
        assert result["ok"] is True
        assert result["exit_code"] == 0
        assert result["data"] == {"status": "success", "job_id": "job-9"}
        assert seen["argv"][3:] == ["job-poll", "job-9", "--json"]

    def test_cli_tool_failure_is_reported_not_raised(self) -> None:
        def failing_runner(argv: list[str]) -> tuple[int, str, str]:
            return 1, "", "provider exploded"

        result = agent_surface.dispatch("job_poll", {"job_id": "job-9"}, runner=failing_runner)
        assert result["ok"] is False
        assert result["exit_code"] == 1
        assert "provider exploded" in result["stderr"]
        assert result["error"]

    def test_non_json_output_is_returned_as_text(self) -> None:
        def fake_runner(argv: list[str]) -> tuple[int, str, str]:
            return 0, "stitched 3 clips", ""

        result = agent_surface.dispatch(
            "stitch", {"clips": ["a.mp4"], "output": "o.mp4"}, runner=fake_runner
        )
        assert result["ok"] is True
        assert result["data"] is None
        assert "stitched" in result["stdout"]

    def test_unknown_tool_returns_structured_error(self) -> None:
        result = agent_surface.dispatch("ghost_tool", {})
        assert result["ok"] is False
        assert "ghost_tool" in result["error"]
        assert result["tool"] == "ghost_tool"

    def test_dispatch_accepts_root(self) -> None:
        seen: dict[str, Any] = {}

        def fake_runner(argv: list[str]) -> tuple[int, str, str]:
            seen["argv"] = argv
            return 0, "", ""

        agent_surface.dispatch(
            "produce", {"project_id": "p", "shots": "s.json"}, root="/tmp/home", runner=fake_runner
        )
        assert seen["argv"][3:6] == ["--root", "/tmp/home", "produce"]


# ---------------------------------------------------------------------------
# CLI surface: brandly tools
# ---------------------------------------------------------------------------


class TestToolsCommand:
    def test_tools_json_is_machine_readable(self) -> None:
        from brandly_cli.cli import cli

        result = CliRunner().invoke(cli, ["tools", "--json"])
        assert result.exit_code == 0, result.output
        manifest = json.loads(result.output)
        assert any(t["name"] == "produce" for t in manifest["tools"])

    def test_tools_text_lists_names(self) -> None:
        from brandly_cli.cli import cli

        result = CliRunner().invoke(cli, ["tools"])
        assert result.exit_code == 0, result.output
        assert "produce" in result.output
        assert "run_gate" in result.output

