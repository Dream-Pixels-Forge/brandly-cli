"""Tests for the MCP ``take_prompts`` tool surface (v0.15.5, closes P2).

Behaviour under test: the four per-take prompt pack tools are registered in the
agent surface, backed by the real ``brandly takes`` CLI commands, and dispatch
through an injected runner (no subprocess in these tests).

Written RED first per the repo convention; GREEN once the surface is wired.
"""

from __future__ import annotations

from typing import Any

import pytest

from brandly_cli import agent_surface

# ---------------------------------------------------------------------------
# Manifest registration
# ---------------------------------------------------------------------------


class TestTakesManifest:
    def test_takes_tools_registered(self) -> None:
        entries = {e["name"]: e for e in agent_surface.tool_manifest()["tools"]}
        for name in (
            "take_prompts_status",
            "take_prompts_list",
            "take_prompts_export",
            "take_prompts_apply",
        ):
            assert name in entries, f"{name} missing from manifest"
            entry = entries[name]
            assert entry["kind"] == "cli", f"{name} must be CLI-backed"
            assert entry["command"], f"{name} must map to a CLI command"

    def test_takes_annotations_and_read_only(self) -> None:
        entries = {e["name"]: e for e in agent_surface.tool_manifest()["tools"]}
        assert entries["take_prompts_status"]["read_only"] is True
        assert entries["take_prompts_list"]["read_only"] is True
        assert entries["take_prompts_export"]["read_only"] is False
        assert entries["take_prompts_apply"]["read_only"] is False
        for name in ("take_prompts_status", "take_prompts_list", "take_prompts_export", "take_prompts_apply"):
            assert name in agent_surface.TOOL_ANNOTATIONS, f"{name} missing annotations"
            assert name in agent_surface.TOOL_DOMAINS["takes"], f"{name} missing from takes domain"


# ---------------------------------------------------------------------------
# Command building (pure — no subprocess)
# ---------------------------------------------------------------------------


class TestTakesBuildCommand:
    def test_takes_status_command_shape(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_status", {"project_id": "p1"}
        )
        assert argv[3:] == ["takes", "status", "p1"]

    def test_takes_status_json_flag(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_status", {"project_id": "p1", "json": True}
        )
        assert argv[3:] == ["takes", "status", "p1", "--json"]

    def test_takes_list_command_shape(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_list", {"project_id": "p1"}
        )
        assert argv[3:] == ["takes", "list", "p1"]

    def test_takes_list_scene_and_json(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_list", {"project_id": "p1", "scene": 2, "json": True}
        )
        assert argv[3:] == ["takes", "list", "p1", "--scene", "2", "--json"]

    def test_takes_export_command_shape(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_export", {"project_id": "p1"}
        )
        assert argv[3:] == ["takes", "export", "p1"]

    def test_takes_export_all_flags(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_export",
            {"project_id": "p1", "missing_only": True, "force": True, "prune": True, "dry_run": True},
        )
        assert argv[3:] == [
            "takes", "export", "p1", "--missing-only", "--force", "--prune", "--dry-run",
        ]

    def test_takes_apply_command_shape(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_apply", {"project_id": "p1"}
        )
        assert argv[3:] == ["takes", "apply", "p1"]

    def test_takes_apply_all_options(self) -> None:
        argv = agent_surface.build_command(
            "take_prompts_apply",
            {"project_id": "p1", "scene": 1, "take": 3, "clear": "2.1", "force": True, "dry_run": True},
        )
        assert argv[3:] == [
            "takes", "apply", "p1", "--scene", "1", "--take", "3", "--clear", "2.1",
            "--force", "--dry-run",
        ]

    def test_missing_required_argument_raises(self) -> None:
        with pytest.raises(ValueError, match="project_id"):
            agent_surface.build_command("take_prompts_status", {})


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestTakesDispatch:
    def test_takes_status_dispatch_uses_injected_runner(self) -> None:
        seen: dict[str, Any] = {}

        def fake_runner(argv: list[str]) -> tuple[int, str, str]:
            seen["argv"] = argv
            return 0, '{"verdict": "pass", "counts": {}}', ""

        result = agent_surface.dispatch(
            "take_prompts_status", {"project_id": "p1"}, runner=fake_runner
        )
        assert result["ok"] is True
        assert result["exit_code"] == 0
        assert result["kind"] == "cli"
        assert result["read_only"] is True
        assert result["data"] == {"verdict": "pass", "counts": {}}
        assert seen["argv"][3:] == ["takes", "status", "p1"]

    def test_takes_export_dispatch_writes_and_reports(self) -> None:
        seen: dict[str, Any] = {}

        def fake_runner(argv: list[str]) -> tuple[int, str, str]:
            seen["argv"] = argv
            return 0, "wrote Scene 1/Scene 1.1.md\n", ""

        result = agent_surface.dispatch(
            "take_prompts_export", {"project_id": "p1", "force": True}, runner=fake_runner
        )
        assert result["ok"] is True
        assert result["read_only"] is False
        assert seen["argv"][3:] == ["takes", "export", "p1", "--force"]

    def test_takes_apply_dispatch_failure_reported_not_raised(self) -> None:
        def failing_runner(argv: list[str]) -> tuple[int, str, str]:
            return 2, "", "takes out of sync: 1.2"

        result = agent_surface.dispatch(
            "take_prompts_apply", {"project_id": "p1", "clear": "1.2"}, runner=failing_runner
        )
        assert result["ok"] is False
        assert result["exit_code"] == 2
        assert "takes out of sync: 1.2" in result["error"]

    def test_unknown_tool_returns_structured_error(self) -> None:
        result = agent_surface.dispatch("take_prompts_ghost", {})
        assert result["ok"] is False
        assert "take_prompts_ghost" in result["error"]
