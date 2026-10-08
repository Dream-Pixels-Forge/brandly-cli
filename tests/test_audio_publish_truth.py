"""P4 (#260 #255): audio truth + publish platform truth.

RED-first contract tests:
- #260: the audio phase downloads the generated music into
  ``production/<id>/audio/`` (mocked ``generate_music`` + ``download_file``);
  the music duration derives from the scene manifest's scene durations
  (never a hardcoded 30s); ``re_edit`` mixes the audio track into
  ``final.mp4`` (mocked ffmpeg — the mix command includes the audio input)
- #255: publish derives the platform list from the project's stored
  target-platform selection (``all`` -> the full set; a family name like
  ``instagram`` maps to its export variants); per-platform fail-closed
  behavior preserved
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import patch

from brandly_cli import async_compat, export_platforms, layout, scenes, stitch
from brandly_cli.cmd.production import (
    PHASE_HANDOFF_SPECS,
    Director,
    DirectorConfig,
)
from brandly_cli.project_manager import ProjectManager
from brandly_cli.shot_runner import clip_filename
from brandly_cli.types import ProjectData

PID = "p4proj"
BRIEF = "A precision espresso machine for small cafes"

#: Four-beat shot list — the manifest durations are beat-derived
#: (setup 5 + turn 6 + consequence 6 + resolve 5 = 22s).
_FOUR_BEATS = [
    {"id": "s1", "prompt": "p", "scene": 1, "shot": 1, "beat": "setup"},
    {"id": "s2", "prompt": "p", "scene": 1, "shot": 2, "beat": "turn"},
    {"id": "s3", "prompt": "p", "scene": 2, "shot": 1, "beat": "consequence"},
    {"id": "s4", "prompt": "p", "scene": 2, "shot": 2, "beat": "resolve"},
]


def _make_project(root: Path) -> None:
    asyncio.run(
        ProjectManager(root).create(
            ProjectData(id=PID, name="P4 Project", description=BRIEF)
        )
    )


def _write_manifest(root: Path) -> None:
    scenes.write_scenes(PID, _FOUR_BEATS, root=root)


def _write_scene_clips(root: Path) -> None:
    scenes_dir = layout.resolve_media_root(root, PID, "videos") / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    for shot in _FOUR_BEATS:
        (scenes_dir / clip_filename(shot["scene"], shot["shot"])).write_bytes(b"clip")


def _write_music(root: Path) -> Path:
    audio_dir = layout.resolve_media_root(root, PID, "audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    music = audio_dir / "music.mp3"
    music.write_bytes(b"music bytes")
    return music


def _write_final(root: Path) -> Path:
    videos_root = layout.resolve_media_root(root, PID, "videos")
    videos_root.mkdir(parents=True, exist_ok=True)
    final = videos_root / "final.mp4"
    final.write_bytes(b"stitched final")
    return final


class TestAudioPhase260:
    """#260: the audio phase produces a real downloaded asset."""

    def test_audio_downloads_music_into_audio_dir(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _write_manifest(tmp_path)
        director = Director(DirectorConfig(tmp_path))

        async def fake_music(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {
                "url": "https://example.invalid/music.mp3",
                "duration_ms": 25000,
                "model": "google-lyria",
            }

        async def fake_download(url: str, dest_path: Path) -> Path:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(b"fake mp3")
            return dest_path

        with patch.object(Director, "generate_music", fake_music), patch(
            "brandly_cli.io.download_file", side_effect=fake_download
        ):
            result = asyncio.run(director.run_phase(PID, "audio"))

        assert "error" not in result, result
        audio_dir = layout.resolve_media_root(tmp_path, PID, "audio")
        expected = audio_dir / "music.mp3"
        assert expected.is_file(), "the music was not downloaded into audio/"
        assert result["result"]["music_path"] == str(expected)

    def test_audio_duration_derives_from_scenes(self, tmp_path: Path) -> None:
        """The music duration derives from the scene durations — not 30s."""
        _make_project(tmp_path)
        _write_manifest(tmp_path)  # 5 + 6 + 6 + 5 = 22s (beat-derived)
        director = Director(DirectorConfig(tmp_path))
        captured: dict[str, Any] = {}

        async def fake_music(*args: Any, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {"url": None}

        with patch.object(Director, "generate_music", fake_music):
            result = asyncio.run(director.run_phase(PID, "audio"))

        assert "error" not in result, result
        assert captured.get("duration") == 22, captured
        assert result["result"]["duration_seconds"] == 22


class TestReEditMix260:
    """#260: re_edit mixes the audio track into final.mp4."""

    def test_re_edit_mixes_audio_into_final(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        _make_project(tmp_path)
        _write_manifest(tmp_path)
        _write_scene_clips(tmp_path)
        music = _write_music(tmp_path)
        final = _write_final(tmp_path)

        async def fake_stitch(clips: list[Path], output: Path, **kwargs: Any) -> dict[str, Any]:
            output.write_bytes(b"stitched")
            return {"output_path": str(output), "duration_seconds": 22.0}

        monkeypatch.setattr(stitch, "stitch_videos", fake_stitch)

        mix_calls: list[list[str]] = []

        def fake_ffmpeg(cmd: list[str]) -> tuple[int, str, str]:
            mix_calls.append(list(cmd))
            Path(cmd[-1]).write_bytes(b"mixed")
            return 0, "", ""

        monkeypatch.setattr(async_compat, "async_run_ffmpeg", fake_ffmpeg)

        director = Director(DirectorConfig(tmp_path))
        result = asyncio.run(director.run_phase(PID, "re_edit"))

        assert "error" not in result, result
        assert len(mix_calls) == 1, mix_calls
        # The mix command includes the audio input
        assert str(music) in mix_calls[0], mix_calls[0]
        # The mixed file shipped as final.mp4
        assert final.read_bytes() == b"mixed"
        assert result["result"]["music_mixed"] is True

    def test_re_edit_without_music_ships_silent_final(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """No music under audio/ -> the silent stitch ships (audio optional)."""
        _make_project(tmp_path)
        _write_manifest(tmp_path)
        _write_scene_clips(tmp_path)
        _write_final(tmp_path)

        async def fake_stitch(clips: list[Path], output: Path, **kwargs: Any) -> dict[str, Any]:
            output.write_bytes(b"stitched")
            return {"output_path": str(output), "duration_seconds": 22.0}

        monkeypatch.setattr(stitch, "stitch_videos", fake_stitch)

        mix_calls: list[list[str]] = []

        def fake_ffmpeg(cmd: list[str]) -> tuple[int, str, str]:
            mix_calls.append(list(cmd))
            return 0, "", ""

        monkeypatch.setattr(async_compat, "async_run_ffmpeg", fake_ffmpeg)

        director = Director(DirectorConfig(tmp_path))
        result = asyncio.run(director.run_phase(PID, "re_edit"))

        assert "error" not in result, result
        assert mix_calls == []  # no mix attempted
        assert result["result"]["music_mixed"] is False


class TestPublishPlatforms255:
    """#255: publish derives platforms from the stored target-platform selection."""

    def test_publish_derives_platforms_from_target_platforms(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        _make_project(tmp_path)
        _write_final(tmp_path)
        asyncio.run(ProjectManager(tmp_path).update(PID, {"target_platforms": ["instagram"]}))

        calls: list[tuple[str, str, str]] = []

        async def fake_export(source: Path, platform: str, out_dir: Path, **kwargs: Any) -> dict[str, Any]:
            calls.append((str(source), platform, str(out_dir)))
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"final_{platform}.mp4"
            out.write_bytes(b"export")
            return {"platform": platform, "output_path": str(out)}

        monkeypatch.setattr(export_platforms, "export_for_platform", fake_export)

        director = Director(DirectorConfig(tmp_path))
        result = asyncio.run(director.run_phase(PID, "publish"))

        assert "error" not in result, result
        # "instagram" maps to its export variants
        assert result["result"]["platforms"] == ["instagram_reel", "instagram_post"]
        assert len(calls) == 2

    def test_publish_all_maps_to_full_set(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        _make_project(tmp_path)
        _write_final(tmp_path)
        asyncio.run(ProjectManager(tmp_path).update(PID, {"target_platforms": ["all"]}))

        calls: list[str] = []

        async def fake_export(source: Path, platform: str, out_dir: Path, **kwargs: Any) -> dict[str, Any]:
            calls.append(platform)
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"final_{platform}.mp4"
            out.write_bytes(b"export")
            return {"platform": platform, "output_path": str(out)}

        monkeypatch.setattr(export_platforms, "export_for_platform", fake_export)

        director = Director(DirectorConfig(tmp_path))
        result = asyncio.run(director.run_phase(PID, "publish"))

        assert "error" not in result, result
        assert result["result"]["platforms"] == list(PLATFORM_PRESET_KEYS)

    def test_publish_empty_target_platforms_fails_closed(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """An empty target-platform selection must not fake an empty publish."""
        _make_project(tmp_path)
        _write_final(tmp_path)
        asyncio.run(ProjectManager(tmp_path).update(PID, {"target_platforms": []}))

        async def fake_export(source: Path, platform: str, out_dir: Path, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("export must not run with no target platforms")

        monkeypatch.setattr(export_platforms, "export_for_platform", fake_export)

        director = Director(DirectorConfig(tmp_path))
        result = asyncio.run(director.run_phase(PID, "publish"))

        assert "error" in result, result
        assert "target platform" in result["error"].lower()


PLATFORM_PRESET_KEYS = list(export_platforms.PLATFORM_PRESETS.keys())


class TestHandoffSpecsAudioPublish:
    """PHASE_HANDOFF_SPECS audio/publish text matches what is delivered."""

    def test_audio_spec_honest_outputs(self) -> None:
        outputs = " ".join(PHASE_HANDOFF_SPECS["audio"]["outputs"]).lower()
        assert "music" in outputs
        # SFX/voiceover stay unimplemented — honestly removed from the spec
        assert "sfx" not in outputs
        assert "voiceover" not in outputs

    def test_publish_spec_real_platform_contract(self) -> None:
        outputs = " ".join(PHASE_HANDOFF_SPECS["publish"]["outputs"]).lower()
        assert "target platform" in outputs


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
