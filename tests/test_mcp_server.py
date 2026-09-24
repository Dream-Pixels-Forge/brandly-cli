"""Tests for the MCP stdio server (Goal 1, PR 2).

The server speaks JSON-RPC 2.0 over newline-delimited stdio and exposes exactly the
``agent_surface`` manifest, so an external AI tool can call brandly instead of
inventing its own tools (audit F1).

Written test-first (RED) — see dev-notes/GOAL-AGENTIC-PIPELINE.md Goal 1.
"""

from __future__ import annotations

import io
import json
from typing import Any

from click.testing import CliRunner

from brandly_cli import agent_surface, mcp_server


def _call(method: str, params: dict[str, Any] | None = None, msg_id: Any = 1) -> dict[str, Any]:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    response = mcp_server.handle_message(message)
    assert response is not None, f"{method} must produce a response"
    return response


# ---------------------------------------------------------------------------
# Handshake
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_initialize_returns_server_info_and_capabilities(self) -> None:
        response = _call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        result = response["result"]
        assert result["protocolVersion"]
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "brandly-cli"
        assert result["serverInfo"]["version"]

    def test_notification_gets_no_response(self) -> None:
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        assert response is None

    def test_ping_returns_empty_result(self) -> None:
        response = _call("ping")
        assert response["result"] == {}


# ---------------------------------------------------------------------------
# tools/list
# ---------------------------------------------------------------------------


class TestToolsList:
    def test_lists_every_manifest_tool_with_schema(self) -> None:
        result = _call("tools/list")["result"]
        names = [t["name"] for t in result["tools"]]
        assert names == agent_surface.tool_names()
        for tool in result["tools"]:
            assert tool["description"]
            assert tool["inputSchema"]["type"] == "object"

    def test_read_only_tools_are_annotated(self) -> None:
        tools = {t["name"]: t for t in _call("tools/list")["result"]["tools"]}
        assert tools["list_models"]["annotations"]["readOnlyHint"] is True
        assert tools["produce"]["annotations"]["readOnlyHint"] is False


# ---------------------------------------------------------------------------
# tools/call
# ---------------------------------------------------------------------------


class TestToolsCall:
    def test_library_read_only_tool_returns_text_content(self) -> None:
        response = _call("tools/call", {"name": "list_models", "arguments": {}})
        result = response["result"]
        assert result["isError"] is False
        assert result["content"][0]["type"] == "text"
        payload = json.loads(result["content"][0]["text"])
        assert "image" in payload

    def test_cli_tool_runs_through_injected_runner(self) -> None:
        seen: dict[str, Any] = {}

        def fake_runner(argv: list[str]) -> tuple[int, str, str]:
            seen["argv"] = argv
            return 0, '{"status": "success", "job_id": "job-7"}', ""

        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "job_poll", "arguments": {"job_id": "job-7"}}},
            runner=fake_runner,
        )
        assert response is not None
        result = response["result"]
        assert result["isError"] is False
        assert json.loads(result["content"][0]["text"])["job_id"] == "job-7"
        assert seen["argv"][3:] == ["job-poll", "job-7", "--json"]

    def test_failed_tool_reports_is_error_not_a_crash(self) -> None:
        def failing_runner(argv: list[str]) -> tuple[int, str, str]:
            return 1, "", "provider exploded"

        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "job_poll", "arguments": {"job_id": "job-7"}}},
            runner=failing_runner,
        )
        assert response is not None
        result = response["result"]
        assert result["isError"] is True
        assert "provider exploded" in result["content"][0]["text"]

    def test_unknown_tool_is_invalid_params(self) -> None:
        response = _call("tools/call", {"name": "ghost_tool", "arguments": {}})
        assert response["error"]["code"] == -32602
        assert "ghost_tool" in response["error"]["message"]

    def test_missing_tool_name_is_invalid_params(self) -> None:
        response = _call("tools/call", {"arguments": {}})
        assert response["error"]["code"] == -32602

    def test_bad_arguments_are_reported_as_tool_error(self) -> None:
        response = _call("tools/call", {"name": "produce", "arguments": {"project_id": "p"}})
        assert response["result"]["isError"] is True
        assert "shots" in response["result"]["content"][0]["text"]


# ---------------------------------------------------------------------------
# Protocol errors
# ---------------------------------------------------------------------------


class TestProtocolErrors:
    def test_unknown_method_returns_method_not_found(self) -> None:
        response = _call("resources/list")
        assert response["error"]["code"] == -32601

    def test_invalid_json_string_returns_parse_error(self) -> None:
        response = mcp_server.handle_raw("{not json")
        assert response["error"]["code"] == -32700

    def test_non_object_message_returns_invalid_request(self) -> None:
        response = mcp_server.handle_message({"nope": True})
        assert response["error"]["code"] == -32600


# ---------------------------------------------------------------------------
# stdio transport
# ---------------------------------------------------------------------------


class TestServeStdio:
    def _run(self, lines: list[str]) -> list[dict[str, Any]]:
        stdin = io.StringIO("\n".join(lines) + "\n")
        stdout = io.StringIO()
        mcp_server.serve_stdio(stdin, stdout)
        out = stdout.getvalue()
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    def test_handshake_then_tools_list_over_stdio(self) -> None:
        responses = self._run(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2024-11-05"}}),
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            ]
        )
        # the notification must not produce a line of its own
        assert [r["id"] for r in responses] == [1, 2]
        assert all(r["jsonrpc"] == "2.0" for r in responses)
        assert any(t["name"] == "produce" for t in responses[1]["result"]["tools"])

    def test_blank_and_malformed_lines_are_survivable(self) -> None:
        responses = self._run(
            [
                "",
                "{broken",
                json.dumps({"jsonrpc": "2.0", "id": 5, "method": "ping"}),
            ]
        )
        # blank line ignored (no response), malformed line reported, ping answered
        assert [r.get("id") for r in responses] == [None, 5]
        assert responses[0]["error"]["code"] == -32700
        assert responses[1]["result"] == {}


# ---------------------------------------------------------------------------
# CLI surface: brandly mcp serve
# ---------------------------------------------------------------------------


class TestMcpCommand:
    def test_mcp_serve_help_documents_the_transport(self) -> None:
        from brandly_cli.cli import cli

        result = CliRunner().invoke(cli, ["mcp", "serve", "--help"])
        assert result.exit_code == 0, result.output
        assert "stdio" in result.output.lower()
        assert "json-rpc" in result.output.lower()

    def test_mcp_group_lists_serve(self) -> None:
        from brandly_cli.cli import cli

        result = CliRunner().invoke(cli, ["mcp", "--help"])
        assert result.exit_code == 0, result.output
        assert "serve" in result.output

