"""P5 (#256): the agent tool manifest exposes the pipeline-control tools.

RED-first contract tests:
- ``brandly tools --json`` lists the 7 pipeline-control tools (init, status,
  progress, approve, estimate, record_cost, memory) mapped to EXISTING CLI
  commands (the tool surface IS the CLI surface — no new implementation)
- ``status``/``progress``/``estimate`` classified read-only; ``approve`` NOT
  read-only (the human gate); ``init``/``record_cost``/``memory`` write state
- each tool maps to the real CLI argv via ``build_command`` (pure function)
- the MCP ``tools/list`` serves them (the manifest is the single source)
"""

from __future__ import annotations

import json

from brandly_cli.agent_surface import (
    build_command,
    get_tool,
    tool_manifest,
    tool_names,
)

CONTROL_TOOLS = (
    "init",
    "status",
    "progress",
    "approve",
    "estimate",
    "record_cost",
    "memory",
)

#: tool name -> the real CLI command behind it
EXPECTED_COMMANDS = {
    "init": "init",
    "status": "status",
    "progress": "progress",
    "approve": "approve",
    "estimate": "estimate",
    "record_cost": "record-cost",
    "memory": "memory",
}


class TestControlToolManifest:
    """The manifest exposes the 7 control tools (#256)."""

    def test_tools_list_control_tools(self) -> None:
        names = set(tool_names())
        for tool in CONTROL_TOOLS:
            assert tool in names, f"{tool} missing from the agent tool manifest"

    def test_manifest_has_22_tools(self) -> None:
        # 15 (9 library + 6 cli) + 7 control tools
        assert len(tool_names()) == 22

    def test_read_only_classification(self) -> None:
        # status/progress/estimate are read-only (safe without asking)
        assert get_tool("status")["read_only"] is True
        assert get_tool("progress")["read_only"] is True
        assert get_tool("estimate")["read_only"] is True
        # The human gate is NOT read-only
        assert get_tool("approve")["read_only"] is False
        # init/record_cost/memory write state
        assert get_tool("init")["read_only"] is False
        assert get_tool("record_cost")["read_only"] is False
        assert get_tool("memory")["read_only"] is False

    def test_control_tools_map_to_existing_commands(self) -> None:
        for tool, command in EXPECTED_COMMANDS.items():
            spec = get_tool(tool)
            assert spec is not None, tool
            assert spec["command"] == command, tool
            assert spec["kind"] == "cli", tool

    def test_manifest_json_serializable(self) -> None:
        data = tool_manifest()
        assert json.loads(json.dumps(data)) == data


class TestControlToolCommands:
    """Each control tool maps to the real CLI argv (pure function)."""

    def test_build_command_maps_to_real_argv(self) -> None:
        argv = build_command("status", {"project_id": "p-20260101-000000"})
        assert argv[-2:] == ["status", "p-20260101-000000"]

    def test_build_approve(self) -> None:
        argv = build_command("approve", {"project_id": "p-20260101-000000", "phase": "script"})
        assert argv[-3:] == ["approve", "p-20260101-000000", "script"]

    def test_build_estimate(self) -> None:
        argv = build_command("estimate", {"style": "cinematic", "shots": 5})
        assert argv[-5:] == ["estimate", "--style", "cinematic", "--shots", "5"]

    def test_build_record_cost(self) -> None:
        argv = build_command(
            "record_cost",
            {"project_id": "p-20260101-000000", "phase": "audio", "action": "music", "credits": 40},
        )
        assert argv[-5:] == ["record-cost", "p-20260101-000000", "audio", "music", "40"]

    def test_build_memory(self) -> None:
        argv = build_command("memory", {"action": "list"})
        assert argv[-2:] == ["memory", "list"]

    def test_build_init(self) -> None:
        argv = build_command("init", {"name": "Widget", "idea": "A test"})
        assert "--name" in argv and "Widget" in argv
        assert "--idea" in argv and "A test" in argv

    def test_build_command_missing_required_raises(self) -> None:

        try:
            build_command("status", {})
            raise AssertionError("Should have raised")
        except ValueError:
            pass


class TestMcpServesControlTools:
    """MCP tools/list serves the control tools (the manifest is the single source)."""

    def test_mcp_tools_list_includes_control_tools(self) -> None:
        from brandly_cli import mcp_server

        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        names = [t["name"] for t in response["result"]["tools"]]
        for tool in CONTROL_TOOLS:
            assert tool in names, f"MCP tools/list missing {tool}"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
