"""Tests for the Agnes AI agent / tool-calling layer (agent_tools + agnes_client)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brandly_cli import agent_tools
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
        assert agent_tools.to_json("hello") == "hello"

    def test_dict_serialised(self) -> None:
        assert agent_tools.to_json({"a": 1}) == '{"a": 1}'

    def test_unserialisable_falls_back(self) -> None:
        assert isinstance(agent_tools.to_json(object()), str)


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
