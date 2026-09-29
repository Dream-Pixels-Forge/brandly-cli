"""Issue #158: reference-mode prompts carry <Picture N>/<Audio N> tokens.

The Agnes Video 2.5 Flash API binds reference media through these tokens
referenced from the prompt (1-based, in array order) — doc examples:
"Use the character and art style in <Picture 1> as reference..." and
"Use <Audio 1> as the rhythm and ambience reference...".
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from brandly_cli.agnes_client import create_video_task

from .test_agnes_client import _make_mock_client


@pytest.fixture
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = "test-agnes-key-12345"
    monkeypatch.setenv("AGNES_API_KEY", key)
    monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
    return key


async def _prompt_for(**kwargs: object) -> str:
    mock_data = {"id": "task-1", "video_id": "vid-1", "status": "pending"}
    with patch("brandly_cli.agnes_client.httpx.AsyncClient") as mock_ctx:
        mock_ctx.return_value = _make_mock_client(mock_data)
        await create_video_task("a cinematic scene", **kwargs)  # type: ignore[arg-type]
        call_args = mock_ctx.return_value.__aenter__.return_value.post.call_args
        body = call_args.kwargs.get("json") or call_args[1]["json"]
    return body["prompt"]


async def test_images_only_prompt_has_picture_tokens(mock_api_key: str) -> None:
    prompt = await _prompt_for(
        reference_images=["https://x.invalid/1.png", "https://x.invalid/2.png"]
    )
    assert "<Picture 1>" in prompt
    assert "<Picture 2>" in prompt
    assert "<Audio" not in prompt


async def test_audios_only_prompt_has_audio_tokens(mock_api_key: str) -> None:
    prompt = await _prompt_for(
        reference_audios=["https://x.invalid/1.mp3", "https://x.invalid/2.mp3"]
    )
    assert "<Audio 1>" in prompt
    assert "<Audio 2>" in prompt
    assert "<Picture" not in prompt


async def test_mixed_prompt_has_both_token_sets(mock_api_key: str) -> None:
    prompt = await _prompt_for(
        reference_images=["https://x.invalid/1.png"],
        reference_audios=["https://x.invalid/1.mp3"],
    )
    assert "<Picture 1>" in prompt
    assert "<Audio 1>" in prompt


async def test_text_prompt_has_no_tokens(mock_api_key: str) -> None:
    prompt = await _prompt_for()
    assert "<Picture" not in prompt
    assert "<Audio" not in prompt


async def test_keyframe_prompt_has_no_tokens(mock_api_key: str) -> None:
    prompt = await _prompt_for(first_frame="https://x.invalid/f.png")
    assert "<Picture" not in prompt
    assert "<Audio" not in prompt
