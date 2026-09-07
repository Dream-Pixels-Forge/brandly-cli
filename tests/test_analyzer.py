"""Tests for analyzer module — video performance prediction."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from brandly_cli import analyzer


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _make_test_clip(path: Path, duration: float = 2.0) -> Path:
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"testsrc2=size=320x240:duration={duration}:rate=10",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest", str(path),
    ]
    subprocess.run(cmd, capture_output=True, timeout=15)
    return path


class TestHookStrength:
    """Tests for hook strength analysis."""

    def test_empty_script_returns_neutral(self) -> None:
        """Empty script returns neutral score."""
        score = analyzer.analyze_hook_strength("")
        assert score == 5

    def test_script_with_hooks_scores_high(self) -> None:
        """Script with hook words scores high."""
        script = "Wait! You need to see this secret hack"
        score = analyzer.analyze_hook_strength(script)
        assert score > 5

    def test_script_without_hooks_score(self) -> None:
        """Script without hook words gets base score."""
        script = "This is a regular product description"
        score = analyzer.analyze_hook_strength(script)
        assert 4 <= score <= 6


class TestPacing:
    """Tests for pacing analysis."""

    def test_ideal_pacing(self) -> None:
        """Ideal WPM gets high score."""
        score = analyzer.analyze_pacing(60.0, 120)  # 120 WPM
        assert score >= 8

    def test_slow_pacing(self) -> None:
        """Very slow pacing gets lower score."""
        score = analyzer.analyze_pacing(60.0, 20)  # 20 WPM
        assert score < 6

    def test_zero_duration(self) -> None:
        """Zero duration returns neutral."""
        score = analyzer.analyze_pacing(0.0, 100)
        assert score == 5


class TestVisualQuality:
    """Tests for visual quality analysis."""

    def test_hd_resolution(self) -> None:
        """HD resolution gets bonus."""
        score = analyzer.analyze_visual_quality("cinematic", (1920, 1080))
        assert score >= 8

    def test_4k_resolution(self) -> None:
        """4K resolution gets high bonus."""
        score = analyzer.analyze_visual_quality("commercial", (3840, 2160))
        assert score >= 9

    def test_low_resolution(self) -> None:
        """Low resolution gets lower score."""
        score = analyzer.analyze_visual_quality("ugc", (320, 240))
        assert score < 7


class TestPlatformFit:
    """Tests for platform fit analysis."""

    def test_tiktok_format(self) -> None:
        """9:16 format under 60s fits TikTok."""
        score = analyzer.analyze_platform_fit(30.0, "9:16")
        assert score >= 7

    def test_youtube_format(self) -> None:
        """16:9 format fits YouTube."""
        score = analyzer.analyze_platform_fit(120.0, "16:9")
        assert score >= 6


class TestAnalyzeVideo:
    """Tests for analyze_video function."""

    def test_analyze_invalid_video(self, tmp_path: Path) -> None:
        """Invalid video returns error."""
        result = _run(analyzer.analyze_video(tmp_path / "missing.mp4"))
        assert "error" in result

    def test_analyze_valid_video(self, tmp_path: Path) -> None:
        """Valid video returns analysis."""
        video = _make_test_clip(tmp_path / "video.mp4", duration=2.0)
        result = _run(analyzer.analyze_video(video, script="Wait for it!"))
        assert "error" not in result
        assert "overall_score" in result
        assert "recommendations" in result

    def test_analyze_script_affects_score(self, tmp_path: Path) -> None:
        """Script with hooks improves score."""
        video = _make_test_clip(tmp_path / "video.mp4", duration=2.0)
        result_with = _run(analyzer.analyze_video(video, script="Wait! Secret hack!"))
        result_without = _run(analyzer.analyze_video(video, script=""))
        assert result_with["hook_strength"] >= result_without["hook_strength"]

    def test_analyze_recommendations(self, tmp_path: Path) -> None:
        """Recommendations list is populated."""
        video = _make_test_clip(tmp_path / "video.mp4", duration=2.0)
        result = _run(analyzer.analyze_video(video, script=""))
        assert isinstance(result["recommendations"], list)


class TestCTRPrediction:
    """Tests for CTR prediction."""

    def test_strong_cta(self) -> None:
        """Strong CTA text scores high."""
        score = analyzer.analyze_ctr_prediction("Link in bio!")
        assert score > 5

    def test_weak_cta(self) -> None:
        """Weak CTA text scores lower."""
        score = analyzer.analyze_ctr_prediction("Hello and welcome today")
        assert score < 6

    def test_no_text(self) -> None:
        """No text returns neutral."""
        score = analyzer.analyze_ctr_prediction(None)
        assert score == 5
