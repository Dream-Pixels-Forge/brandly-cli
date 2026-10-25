"""Contract tests: sound_design generates real audio via MiniMax.

The user requirement: sound_design must actually call the audio generation
API (TTS for voiceover, music for music/sfx/foley), download the result to
``production/<id>/audio/<category>/<track_id>.mp3``, and return the local
path. Verified with mocked ``generate_tts`` / ``generate_music`` so no
network is needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from brandly_cli.agent_tools import invoke_tool


def _fake_tts(**kwargs: Any) -> dict[str, Any]:
    return {
        "url": "https://cdn.minimaxi.com/audio/tts_001.mp3",
        "model": "speech-2.8-hd",
        "voice_id": "English_Insightful_Speaker",
    }


async def _fake_tts_async(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _fake_tts(**kwargs)


def _fake_music(**kwargs: Any) -> dict[str, Any]:
    return {
        "url": "https://cdn.minimaxi.com/audio/music_001.mp3",
        "duration_ms": 30000,
        "model": "music-3.0",
    }


async def _fake_music_async(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _fake_music(**kwargs)


class TestSoundDesign:
    def test_voiceover_generates_and_downloads(self, tmp_path) -> None:
        fake_audio = b"fake-tts-audio-bytes"

        with patch(
            "brandly_cli.audio_client.generate_tts", _fake_tts_async
        ), patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = fake_audio
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            result = invoke_tool(
                "sound_design",
                project_id="p1",
                sound_type="voiceover",
                description="Opening narration",
                prompt="Once upon a time, there was a hero.",
                root=str(tmp_path),
            )

        assert result.get("error") is None, result
        assert result["type"] == "voiceover"
        assert result["url"] == "https://cdn.minimaxi.com/audio/tts_001.mp3"
        assert result["downloaded"] is True
        assert result["output_path"].endswith("opening_narration.mp3")
        assert "production/p1/audio/general/opening_narration.json" in result["path"]
        # Local file was written
        import os

        assert os.path.exists(result["output_path"])
        assert open(result["output_path"], "rb").read() == fake_audio

    def test_music_generates_and_downloads(self, tmp_path) -> None:
        fake_audio = b"fake-music-audio-bytes"

        with patch(
            "brandly_cli.audio_client.generate_music", _fake_music_async
        ), patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = fake_audio
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            result = invoke_tool(
                "sound_design",
                project_id="p1",
                sound_type="music",
                description="Opening theme",
                prompt="Cinematic orchestral opening",
                duration=30,
                category="soundtrack",
                root=str(tmp_path),
            )

        assert result.get("error") is None, result
        assert result["type"] == "music"
        assert result["url"] == "https://cdn.minimaxi.com/audio/music_001.mp3"
        assert result["duration_ms"] == 30000
        assert result["downloaded"] is True
        assert result["output_path"].endswith("opening_theme.mp3")
        assert "production/p1/audio/soundtrack/opening_theme.json" in result["path"]

    def test_download_failure_is_non_fatal(self, tmp_path) -> None:
        """Download failure returns metadata with empty output_path (not an error)."""

        with patch(
            "brandly_cli.audio_client.generate_tts", _fake_tts_async
        ), patch("httpx.get") as mock_get:
            mock_get.side_effect = OSError("network down")

            result = invoke_tool(
                "sound_design",
                project_id="p1",
                sound_type="voiceover",
                description="Failing download",
                prompt="Test",
                root=str(tmp_path),
            )

        assert result.get("error") is None, result
        assert result["downloaded"] is False
        assert result["output_path"] == ""
        assert result["url"] == "https://cdn.minimaxi.com/audio/tts_001.mp3"

    def test_provider_error_is_reported(self, tmp_path) -> None:
        """Provider API error is surfaced as an error envelope."""

        async def _failing_tts(*args: Any, **kwargs: Any) -> dict[str, Any]:
            raise OSError("API key invalid")

        with patch("brandly_cli.audio_client.generate_tts", _failing_tts):
            result = invoke_tool(
                "sound_design",
                project_id="p1",
                sound_type="voiceover",
                description="Bad key",
                prompt="Test",
                root=str(tmp_path),
            )

        assert "error" in result, result
        assert "API key invalid" in result["error"]
