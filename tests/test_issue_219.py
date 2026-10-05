r"""Issue #219: the reference-mode binding sentence assigns no role per image.

Agnes Video 2.5 Flash binds reference media through ``<Picture N>`` tokens
cited in the prompt text. brandly builds ONE flat sentence for all images
("Use <Picture 1>, <Picture 2>, <Picture 3> as reference: preserve exact
appearance, lighting, and composition from the provided reference image(s).")
— so mixed-category shots get contradictory instructions: a static
environment plate is told to preserve exact composition at the same time as
the character plates, which is precisely the drift ``mode: reference`` exists
to prevent.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brandly_cli.agnes_client import create_video_task


@pytest.fixture
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = "test-key-123"
    monkeypatch.setenv("AGNES_API_KEY", key)
    monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
    return key


def _mock_client(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.headers = {}
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.get = AsyncMock(return_value=resp)
    client.delete = AsyncMock(return_value=resp)
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=client)
    mock_context.__aexit__ = AsyncMock(return_value=False)
    return mock_context


def _captured_prompt(mock_ctx: MagicMock) -> str:
    call_args = mock_ctx.return_value.__aenter__.return_value.post.call_args
    body = call_args.kwargs.get("json") or call_args[1]["json"]
    return str(body.get("prompt") or "")


class TestReferenceBindingRoles:
    async def test_mixed_categories_emit_per_image_clauses(
        self, mock_api_key: str, tmp_path: Path
    ) -> None:
        # 2 character plates + 1 environment plate: the flat sentence told the
        # model to preserve exact composition from all three simultaneously.
        char1 = tmp_path / "pre-production" / "p" / "character" / "char_a.jpg"
        char2 = tmp_path / "pre-production" / "p" / "character" / "char_b.jpg"
        env = tmp_path / "pre-production" / "p" / "location" / "loc_c.jpg"
        for p in (char1, char2, env):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"jpg")
        mock_data = {"id": "t", "video_id": "v", "status": "pending"}
        with patch("brandly_cli.agnes_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _mock_client(mock_data)
            await create_video_task(
                "a6s01",
                mode="reference",
                reference_images=[str(char1), str(char2), str(env)],
            )
        prompt = _captured_prompt(mock_ctx)
        assert (
            "preserve exact appearance, lighting, and composition from the provided"
            not in prompt
        ), "the flat sentence must not be used when every plate has a known category"
        assert prompt.count("character reference") == 2, (
            "each character plate must get its own clause naming its role"
        )
        assert (
            "environment reference" in prompt
        ), "the environment plate must be named as the environment reference"
        assert "<Picture 1>" in prompt
        assert "<Picture 2>" in prompt
        assert "<Picture 3>" in prompt

    async def test_explicit_reference_roles_win(
        self, mock_api_key: str
    ) -> None:
        # The issue's option 2: the caller can pass roles verbatim.
        mock_data = {"id": "t", "video_id": "v", "status": "pending"}
        with patch("brandly_cli.agnes_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _mock_client(mock_data)
            await create_video_task(
                "a6s01",
                mode="reference",
                reference_images=[
                    "https://x.invalid/a.png",
                    "https://x.invalid/b.png",
                ],
                reference_roles=["character", "style"],
            )
        prompt = _captured_prompt(mock_ctx)
        assert "<Picture 1> is a character reference" in prompt
        assert "<Picture 2> is a style reference" in prompt
        assert (
            "preserve exact appearance, lighting, and composition from the provided"
            not in prompt
        )

    async def test_flat_sentence_preserved_for_unknown_categories(
        self, mock_api_key: str
    ) -> None:
        # Guard: URL references (no local category folder) keep the flat
        # sentence — unchanged behavior.
        mock_data = {"id": "t", "video_id": "v", "status": "pending"}
        with patch("brandly_cli.agnes_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _mock_client(mock_data)
            await create_video_task(
                "consistent character",
                mode="reference",
                reference_images=["https://x.invalid/ref.png"],
            )
        prompt = _captured_prompt(mock_ctx)
        assert (
            "Use <Picture 1> as reference: preserve exact appearance, "
            "lighting, and composition from the provided reference image(s)."
        ) in prompt
