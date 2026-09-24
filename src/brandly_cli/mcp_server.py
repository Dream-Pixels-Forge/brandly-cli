"""MCP (Model Context Protocol) stdio server for brandly-cli (Goal 1, PR 2).

Newline-delimited JSON-RPC 2.0 over stdio, exposing exactly the
:mod:`brandly_cli.agent_surface` manifest, so an external AI tool can discover and
call brandly's real pipeline instead of inventing its own ffmpeg/HTTP tools
(audit F1).

Supported methods: ``initialize``, ``ping``, ``tools/list``, ``tools/call``.
Notifications (no ``id``) never produce a response. Tool *execution* failures are
returned as ``result.isError = true`` (per MCP), while protocol misuse (unknown
tool/method, bad params) is a JSON-RPC error object.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TextIO

from brandly_cli import __version__, agent_surface

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "brandly-cli"

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602

Runner = Callable[[list[str]], tuple[int, str, str]] | None


def server_info() -> dict[str, str]:
    return {"name": SERVER_NAME, "version": __version__}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _mcp_tools() -> list[dict[str, Any]]:
    """The manifest, shaped for MCP (``inputSchema`` + ``annotations``)."""
    tools = []
    for entry in agent_surface.tool_manifest()["tools"]:
        tools.append(
            {
                "name": entry["name"],
                "description": entry["description"],
                "inputSchema": entry["parameters"],
                "annotations": {"readOnlyHint": entry["read_only"]},
            }
        )
    return tools


def _tool_call(
    params: dict[str, Any], *, msg_id: Any, root: str | None, runner: Runner
) -> dict[str, Any]:
    name = params.get("name")
    if not name or not isinstance(name, str):
        return _error(msg_id, INVALID_PARAMS, "tools/call requires params.name")
    known = agent_surface.get_tool(name)
    if known is None:
        return _error(msg_id, INVALID_PARAMS, f"unknown tool: {name}")

    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return _error(msg_id, INVALID_PARAMS, "params.arguments must be an object")

    envelope = agent_surface.dispatch(name, arguments, root=root, runner=runner)
    if not envelope["ok"]:
        text = json.dumps(
            {
                "tool": envelope["tool"],
                "error": envelope["error"],
                "exit_code": envelope["exit_code"],
                "stderr": envelope["stderr"] or None,
                "stdout": envelope["stdout"] or None,
            },
            ensure_ascii=False,
        )
    elif envelope["data"] is not None:
        # Success with machine-readable data: return the payload itself.
        text = json.dumps(envelope["data"], ensure_ascii=False)
    else:
        # Success with plain CLI output (command has no --json): return its stdout.
        text = envelope["stdout"]
    return _result(
        msg_id,
        {"content": [{"type": "text", "text": text}], "isError": not envelope["ok"]},
    )


def handle_message(
    message: Any,
    *,
    root: str | None = None,
    runner: Runner = None,
) -> dict[str, Any] | None:
    """Handle one decoded JSON-RPC message.

    Returns ``None`` for notifications (never respond to a notification).
    """
    if not isinstance(message, dict) or "method" not in message:
        msg_id = message.get("id") if isinstance(message, dict) else None
        return _error(msg_id, INVALID_REQUEST, "Invalid Request")

    method = message.get("method")
    msg_id = message.get("id")

    # Notifications carry no id — never answer them.
    if "id" not in message:
        return None

    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(msg_id, INVALID_PARAMS, "params must be an object")

    if method == "initialize":
        return _result(
            msg_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": server_info(),
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": _mcp_tools()})
    if method == "tools/call":
        return _tool_call(params, msg_id=msg_id, root=root, runner=runner)

    return _error(msg_id, METHOD_NOT_FOUND, f"method not found: {method}")


def handle_raw(
    text: str,
    *,
    root: str | None = None,
    runner: Runner = None,
) -> dict[str, Any] | None:
    """Decode one raw stdio line and handle it (parse errors become -32700)."""
    try:
        message = json.loads(text)
    except json.JSONDecodeError:
        return _error(None, PARSE_ERROR, "Parse error")
    return handle_message(message, root=root, runner=runner)


def serve_stdio(
    stdin: TextIO,
    stdout: TextIO,
    *,
    root: str | None = None,
    runner: Runner = None,
) -> None:
    """Serve newline-delimited JSON-RPC 2.0 until stdin closes.

    Blank lines are ignored; malformed lines are answered with -32700 so a client
    never blocks waiting for a response.
    """
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        response = handle_raw(line, root=root, runner=runner)
        if response is None:
            continue
        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()

