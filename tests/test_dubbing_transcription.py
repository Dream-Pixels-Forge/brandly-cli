"""Tests for automatic transcription/translation in the dubbing module.

Covers the faster-whisper STT path: the model is loaded lazily, the correct
Whisper task is selected (transcribe vs translate), segments are joined, and
``dub_video`` fails honestly when no transcript and no STT backend exist.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import patch

from click.testing import CliRunner

from brandly_cli import dubbing
from brandly_cli.cli import cli


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


class _FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModel:
    """Minimal stand-in for faster_whisper.WhisperModel."""

    def __init__(self, segments: list[str] | None = None) -> None:
        self._segments = segments if segments is not None else ["hello", "world"]
        self.calls: list[dict[str, Any]] = []

    def transcribe(self, path: str, **kwargs: Any) -> tuple[list[_FakeSegment], Any]:
        self.calls.append({"path": path, **kwargs})
        return [_FakeSegment(text) for text in self._segments], None


class TestLoadWhisperModel:
    """Tests for _load_whisper_model."""

    def test_returns_none_when_backend_unavailable(self) -> None:
        """No faster-whisper installed -> no model, no crash."""
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", False):
            assert dubbing._load_whisper_model() is None

    def test_uses_int8_cpu_model(self) -> None:
        """Model is constructed for CPU int8 inference."""
        model = _FakeModel()
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "WhisperModel", return_value=model) as ctor:
            assert dubbing._load_whisper_model("small") is model
        ctor.assert_called_once_with("small", device="cpu", compute_type="int8")

    def test_returns_none_when_construction_fails(self) -> None:
        """A broken backend degrades to None instead of raising."""
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "WhisperModel", side_effect=RuntimeError("boom")):
            assert dubbing._load_whisper_model() is None


class TestTranscribeAudio:
    """Tests for _transcribe_audio."""

    def test_returns_none_when_backend_unavailable(self, tmp_path: Path) -> None:
        """No faster-whisper -> None (caller reports the honest error)."""
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"")
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", False):
            assert _run(dubbing._transcribe_audio(audio, "en", "es")) is None

    def test_joins_segments(self, tmp_path: Path) -> None:
        """All transcript segments are joined into one string."""
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"")
        model = _FakeModel(["hola ", "mundo"])
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "_load_whisper_model", return_value=model):
            text = _run(dubbing._transcribe_audio(audio, "es", "es"))
        assert text == "hola  mundo"

    def test_same_language_uses_transcribe_task(self, tmp_path: Path) -> None:
        """Same source/target language -> Whisper 'transcribe' task."""
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"")
        model = _FakeModel(["hello"])
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "_load_whisper_model", return_value=model):
            _run(dubbing._transcribe_audio(audio, "en", "en"))
        assert model.calls[0]["task"] == "transcribe"
        assert model.calls[0]["language"] == "en"

    def test_different_language_uses_translate_task(self, tmp_path: Path) -> None:
        """A different target language -> Whisper 'translate' task."""
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"")
        model = _FakeModel(["hello"])
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "_load_whisper_model", return_value=model):
            _run(dubbing._transcribe_audio(audio, "en", "es"))
        assert model.calls[0]["task"] == "translate"
        assert model.calls[0]["language"] is None

    def test_empty_transcript_returns_none(self, tmp_path: Path) -> None:
        """Silent/blank audio yields None rather than an empty string."""
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"")
        model = _FakeModel(["   "])
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "_load_whisper_model", return_value=model):
            assert _run(dubbing._transcribe_audio(audio, "en", "es")) is None

    def test_backend_failure_returns_none(self, tmp_path: Path) -> None:
        """A raising backend degrades to None instead of propagating."""
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"")
        model = _FakeModel()
        model.transcribe = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[method-assign]
        with patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", True), \
                patch.object(dubbing, "_load_whisper_model", return_value=model):
            assert _run(dubbing._transcribe_audio(audio, "en", "es")) is None


class TestDubVideoTranscriptionWiring:
    """Tests for how dub_video sources its transcript."""

    def test_explicit_transcript_skips_stt(self, tmp_path: Path) -> None:
        """A supplied transcript must not trigger automatic transcription."""
        src = tmp_path / "in.mp4"
        src.write_bytes(b"not a real video")
        with patch.object(dubbing, "async_run_ffmpeg", return_value=(0, "")), \
                patch.object(dubbing, "_transcribe_audio") as stt, \
                patch.object(dubbing, "_generate_tts_audio") as tts:
            tts.return_value = {"audio_path": "x", "duration_seconds": 1.0}
            _run(dubbing.dub_video(src, "en", "es", transcript="hola"))
        stt.assert_not_called()

    def test_missing_transcript_and_stt_reports_honest_error(self, tmp_path: Path) -> None:
        """Without a transcript and without an STT backend, fail loudly."""
        src = tmp_path / "in.mp4"
        src.write_bytes(b"not a real video")
        with patch.object(dubbing, "async_run_ffmpeg", return_value=(0, "")), \
                patch.object(dubbing, "FASTER_WHISPER_AVAILABLE", False):
            result = _run(dubbing.dub_video(src, "en", "es"))
        assert "error" in result
        assert "faster-whisper" in result["error"]
        assert "transcript" in result["error"]

    def test_automatic_transcript_is_used_for_tts(self, tmp_path: Path) -> None:
        """The auto-transcribed text is what gets sent to the TTS stage."""
        src = tmp_path / "in.mp4"
        src.write_bytes(b"not a real video")
        with patch.object(dubbing, "async_run_ffmpeg", return_value=(0, "")), \
                patch.object(dubbing, "_transcribe_audio", return_value="hola mundo"), \
                patch.object(dubbing, "_generate_tts_audio", return_value={"duration_seconds": 1.0}) as tts:
            _run(dubbing.dub_video(src, "en", "es"))
        assert tts.call_args.args[0] == "hola mundo"


class TestVoiceMatchCli:
    """The CLI must expose the transcript escape hatch the error message names."""

    def test_transcript_option_is_accepted_and_forwarded(self, tmp_path: Path) -> None:
        """`brandly voice-match --transcript` forwards the text to dub_video."""
        src = tmp_path / "in.mp4"
        src.write_bytes(b"not a real video")
        with patch.object(dubbing, "async_run_ffmpeg", return_value=(0, "")), \
                patch.object(dubbing, "_generate_tts_audio", return_value={"duration_seconds": 1.0}):
            with patch("brandly_cli.dubbing.dub_video", return_value={
                "target_lang": "es", "output_path": "out.mp4", "duration_seconds": 1.0,
            }) as dub:
                result = CliRunner().invoke(
                    cli,
                    ["voice-match", str(src), "--source", "en", "--target", "es",
                     "--transcript", "hola mundo"],
                )
        assert result.exit_code == 0, result.output
        assert dub.call_args.kwargs["transcript"] == "hola mundo"
