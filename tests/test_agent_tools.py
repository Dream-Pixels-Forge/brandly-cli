"""Tests for the Agnes AI agent / tool-calling layer (agent_tools + agnes_client)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brandly_cli import agent_tools, job_polling
from brandly_cli.agnes_client import (
    _build_tools_payload,
    agent_tool_loop,
    chat_completion,
    list_text_models,
)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# list_text_models
# ---------------------------------------------------------------------------


class TestListTextModels:
    def test_returns_known_models(self) -> None:
        models = list_text_models()
        ids = [m["id"] for m in models]
        assert "agnes-2.5-flash" in ids
        assert "agnes-2.0-flash" in ids
        assert "agnes-1.5-flash" in ids

    def test_default_model_is_recommended(self) -> None:
        models = {m["id"]: m for m in list_text_models()}
        assert "tool calling" in models["agnes-2.5-flash"]["use"].lower()


# ---------------------------------------------------------------------------
# _build_tools_payload
# ---------------------------------------------------------------------------


class TestBuildToolsPayload:
    def test_tuple_shaped(self) -> None:
        tools = agent_tools.get_builtin_tools()
        payload = _build_tools_payload(tools)
        assert all(t["type"] == "function" for t in payload)
        names = [t["function"]["name"] for t in payload]
        assert "list_projects" in names
        assert "generate_image" in names
        # handler must NOT leak into the wire payload
        assert all("handler" not in t for t in payload)

    def test_dict_shaped_passthrough(self) -> None:
        shaped = {
            "type": "function",
            "function": {"name": "x", "description": "d", "parameters": {}},
        }
        out = _build_tools_payload([shaped])
        assert out[0]["function"]["name"] == "x"


# ---------------------------------------------------------------------------
# agent_tool_loop
# ---------------------------------------------------------------------------


class TestAgentToolLoop:
    def test_direct_answer_no_tools(self) -> None:
        fake = AsyncMock(
            return_value={
                "choices": [
                    {"message": {"role": "assistant", "content": "hi there"}}
                ]
            }
        )
        # Patch at the site of use: agent_tool_loop calls chat_completion.
        with patch("brandly_cli.agnes_client.chat_completion", fake):
            result = _run(
                agent_tool_loop(
                    [{"role": "user", "content": "hello"}],
                    agent_tools.get_builtin_tools(),
                )
            )
        assert result["content"] == "hi there"
        assert result["iterations"] == 1
        assert fake.call_count == 1

    def test_tool_call_then_answer(self) -> None:
        tool_call_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "list_models",
                        "arguments": '{"category": "video"}',
                    },
                }
            ],
        }
        final_msg = {"role": "assistant", "content": "There are video models."}

        async def _fake_chat(messages: list[dict[str, Any]], **_: Any) -> dict[str, Any]:
            if any(m.get("role") == "tool" for m in messages):
                return {"choices": [{"message": final_msg}]}
            return {"choices": [{"message": tool_call_msg}]}

        with patch("brandly_cli.agnes_client.chat_completion", _fake_chat):
            result = _run(
                agent_tool_loop(
                    [{"role": "user", "content": "list video models"}],
                    agent_tools.get_builtin_tools(),
                )
            )

        assert result["content"] == "There are video models."
        assert result["iterations"] == 2
        tool_msgs = [m for m in result["messages"] if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert "video" in tool_msgs[0]["content"]

    def test_respects_max_iterations(self) -> None:
        tool_call_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c",
                    "type": "function",
                    "function": {"name": "list_models", "arguments": "{}"},
                }
            ],
        }
        calls = 0

        async def _fake_chat(messages: list[dict[str, Any]], **_: Any) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return {"choices": [{"message": tool_call_msg}]}

        with patch("brandly_cli.agnes_client.chat_completion", _fake_chat):
            result = _run(
                agent_tool_loop(
                    [{"role": "user", "content": "loop"}],
                    agent_tools.get_builtin_tools(),
                    max_iterations=3,
                )
            )
        assert result["iterations"] == 3
        assert "max tool iterations" in result["content"]
        assert calls == 3


# ---------------------------------------------------------------------------
# to_json helper
# ---------------------------------------------------------------------------


class TestToJson:
    def test_passthrough_string(self) -> None:
        assert job_polling.to_json("hello") == "hello"

    def test_dict_serialised(self) -> None:
        assert job_polling.to_json({"a": 1}) == '{"a": 1}'

    def test_unserialisable_falls_back(self) -> None:
        assert isinstance(job_polling.to_json(object()), str)


# ---------------------------------------------------------------------------
# invoke_tool
# ---------------------------------------------------------------------------


class TestInvokeTool:
    def test_unknown_tool_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown tool"):
            agent_tools.invoke_tool("nope")

    def test_invoke_list_models(self) -> None:
        out = agent_tools.invoke_tool("list_models", category="audio")
        assert out["category"] == "audio"
        assert isinstance(out["models"], list)
        assert len(out["models"]) > 0


# ---------------------------------------------------------------------------
# Studio tools (issue #60): agent-callable coverage for every studio action
# ---------------------------------------------------------------------------


class TestStudioTools:
    def test_registry_covers_studio_actions(self) -> None:
        names = {name for name, _, _, _ in agent_tools.get_builtin_tools()}
        for expected in (
            "get_timeline",
            "update_clip",
            "reorder_timeline",
            "run_gate",
        ):
            assert expected in names, f"missing studio tool: {expected}"

    def test_describe_tools_includes_studio(self) -> None:
        described = agent_tools.describe_tools()
        assert "get_timeline" in described
        assert "update_clip" in described

    def test_get_timeline_returns_contract_shape(self, tmp_path) -> None:
        out = agent_tools.invoke_tool(
            "get_timeline", project_id="nope", root=str(tmp_path)
        )
        # TimelineState.load() synthesizes an empty timeline for unknown
        # projects (editor source-of-truth semantics) — the tool must at
        # least return the contract shape, never raise.
        assert out["project_id"] == "nope"
        assert "clips" in out

    def test_reorder_timeline_unknown_ids_return_error(self, tmp_path) -> None:
        out = agent_tools.invoke_tool(
            "reorder_timeline",
            project_id="nope",
            order=["ghost"],
            root=str(tmp_path),
        )
        assert "error" in out

    def test_update_clip_missing_clip_returns_error(self, tmp_path) -> None:
        out = agent_tools.invoke_tool(
            "update_clip",
            project_id="nope",
            clip_id="ghost",
            updates={"volume": 0.5},
            root=str(tmp_path),
        )
        assert "error" in out


# ---------------------------------------------------------------------------
# chat_completion payload assembly (real function, mocked transport)
# ---------------------------------------------------------------------------


class TestChatCompletionPayload:
    def test_sends_tools_and_caps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "test-key")
        monkeypatch.setenv("AGNES_BASE_URL", "https://test.example.com/v1")
        captured: dict[str, Any] = {}

        async def fake_post(url: str, headers: Any = None, json: Any = None) -> Any:
            captured["url"] = url
            captured["json"] = json
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
            return resp

        mock_client = MagicMock()
        mock_client.post = fake_post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        tools = _build_tools_payload(agent_tools.get_builtin_tools())[:1]
        with patch("brandly_cli.agnes_client.httpx.AsyncClient", return_value=ctx):
            result = _run(
                chat_completion(
                    [{"role": "user", "content": "x"}],
                    tools=tools,
                    temperature=0.2,
                    max_tokens=128,
                )
            )

        body = captured["json"]
        assert body["temperature"] == 0.2
        assert body["max_tokens"] == 128
        assert body["tools"] == tools
        assert "/chat/completions" in captured["url"]
        assert result["choices"][0]["message"]["content"] == "ok"

# ---------------------------------------------------------------------------
# agnes-chat CLI key guard
# ---------------------------------------------------------------------------


class TestAgnesChatKeyGuard:
    def test_missing_key_exits_cleanly(self, monkeypatch) -> None:
        """Without AGNES_API_KEY, agnes-chat errors out (not a raw traceback)."""
        from click.testing import CliRunner

        from brandly_cli.cli import cli

        monkeypatch.delenv("AGNES_API_KEY", raising=False)
        runner = CliRunner()
        result = runner.invoke(cli, ["agnes-chat", "hello"])
        # Should not raise; should mention the missing key and exit non-zero.
        assert result.exit_code != 0
        assert "AGNES_API_KEY" in result.output

    def test_list_models_needs_no_key(self, monkeypatch) -> None:
        from click.testing import CliRunner

        from brandly_cli.cli import cli

        monkeypatch.delenv("AGNES_API_KEY", raising=False)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["agnes-chat", "x", "--list-models"]
        )
        assert result.exit_code == 0
        assert "agnes-2.5-flash" in result.output

# ---------------------------------------------------------------------------
# download_and_verify_video (G7)
# ---------------------------------------------------------------------------


class TestDownloadAndVerifyVideo:
    def test_download_and_verify_ok(self, tmp_path, monkeypatch):
        """Downloaded clip with duration within tolerance is marked OK."""
        from brandly_cli.agnes_client import download_and_verify_video

        fake_audio = b"fake-video-bytes"

        async def fake_download(url, dest_path):
            Path(dest_path).write_bytes(fake_audio)
            return Path(dest_path)

        def fake_probe(path):
            return 5.0  # exactly matches requested_duration=5

        monkeypatch.setattr(
            "brandly_cli.agnes_client.download_file", fake_download
        )
        monkeypatch.setattr(
            "brandly_cli.agnes_client._probe_video_duration", fake_probe
        )

        result = __import__("asyncio").run(
            download_and_verify_video(
                "vid-001",
                "https://cdn.example.com/vid-001.mp4",
                "p1",
                5,
                root=str(tmp_path),
            )
        )

        assert result["downloaded"] is True
        assert result["requested_s"] == 5
        assert result["measured_s"] == 5.0
        assert result["delta_s"] == 0.0
        assert result["duration_status"] == "ok"
        assert result["checksum"] != ""
        assert result["local_path"].endswith("vid-001.mp4")
        assert Path(result["local_path"]).is_file()
        assert Path(result["local_path"]).read_bytes() == fake_audio

    def test_download_and_verify_short(self, tmp_path, monkeypatch):
        """Clip shorter than tolerance is marked short."""
        from brandly_cli.agnes_client import download_and_verify_video

        fake_audio = b"fake-video-bytes"

        async def fake_download(url, dest_path):
            Path(dest_path).write_bytes(fake_audio)
            return Path(dest_path)

        def fake_probe(path):
            return 3.0  # requested 5s, got 3s -> short

        monkeypatch.setattr(
            "brandly_cli.agnes_client.download_file", fake_download
        )
        monkeypatch.setattr(
            "brandly_cli.agnes_client._probe_video_duration", fake_probe
        )

        result = __import__("asyncio").run(
            download_and_verify_video(
                "vid-002",
                "https://cdn.example.com/vid-002.mp4",
                "p1",
                5,
                root=str(tmp_path),
            )
        )

        assert result["downloaded"] is True
        assert result["requested_s"] == 5
        assert result["measured_s"] == 3.0
        assert result["delta_s"] == -2.0
        assert result["duration_status"] == "short"

    def test_download_failure_non_fatal(self, tmp_path, monkeypatch):
        """Download failure returns error status, not an exception."""
        from brandly_cli.agnes_client import download_and_verify_video

        async def fake_download(url, dest_path):
            raise OSError("network down")

        monkeypatch.setattr(
            "brandly_cli.agnes_client.download_file", fake_download
        )

        result = __import__("asyncio").run(
            download_and_verify_video(
                "vid-003",
                "https://cdn.example.com/vid-003.mp4",
                "p1",
                5,
                root=str(tmp_path),
            )
        )

        assert result["downloaded"] is False
        assert result["output_path"] == ""
        assert result["duration_status"] == "download_failed"
        assert "network down" in result["download_error"]

    def test_unknown_duration_when_ffprobe_missing(self, tmp_path, monkeypatch):
        """When ffprobe is unavailable, duration_status is unknown."""
        from brandly_cli.agnes_client import download_and_verify_video

        fake_audio = b"fake-video-bytes"

        async def fake_download(url, dest_path):
            Path(dest_path).write_bytes(fake_audio)
            return Path(dest_path)

        monkeypatch.setattr(
            "brandly_cli.agnes_client.download_file", fake_download
        )
        monkeypatch.setattr("shutil.which", lambda cmd: None)

        result = __import__("asyncio").run(
            download_and_verify_video(
                "vid-004",
                "https://cdn.example.com/vid-004.mp4",
                "p1",
                5,
                root=str(tmp_path),
            )
        )

        assert result["downloaded"] is True
        assert result["duration_status"] == "unknown"
        assert result["measured_s"] is None
        assert result["delta_s"] is None
