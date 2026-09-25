"""Video performance analysis and quality scoring."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from brandly_cli.io import proc_output

# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def analyze_hook_strength(script: str, first_seconds: int = 3) -> int:
    """Score hook strength (0-10).

    Analyzes the first few words/seconds of the script for engagement potential.
    """
    if not script:
        return 5  # Neutral

    script_lower = script.lower()[:100]  # First 100 chars

    # Hook indicators
    hooks = [
        "wait",
        "you",
        "stop",
        "secret",
        "hack",
        "tip",
        "best",
        "amazing",
        "incredible",
        "never",
        "must",
        "watch",
        "see",
        "discover",
        "reveal",
    ]

    score = 5  # Base score
    for hook in hooks:
        if hook in script_lower:
            score += 1

    return min(10, max(0, score))


def analyze_pacing(duration: float, word_count: int) -> int:
    """Score pacing based on duration and content density (0-10)."""
    if duration <= 0:
        return 5

    words_per_minute = (word_count / duration) * 60

    # Ideal: 100-150 words per minute for engagement
    if 100 <= words_per_minute <= 150:
        return 9
    elif 75 <= words_per_minute <= 175:
        return 7
    elif 50 <= words_per_minute <= 200:
        return 5
    else:
        return 3


def analyze_visual_quality(style: str, resolution: tuple[int, int]) -> int:
    """Score visual quality based on style and resolution (0-10)."""
    score = 5  # Base

    # Resolution bonus
    if resolution[0] >= 1920 and resolution[1] >= 1080:
        score += 3
    elif resolution[0] >= 1280 and resolution[1] >= 720:
        score += 2
    elif resolution[0] >= 640:
        score += 1

    # Style bonus
    professional_styles = ["cinematic", "commercial", "professional"]
    if style.lower() in professional_styles:
        score += 1

    return min(10, score)


def analyze_ctr_prediction(text_overlay: str | None) -> int:
    """Score CTR potential based on text overlay quality (0-10)."""
    if not text_overlay:
        return 5

    # Strong CTR indicators
    strong = ["link in bio", "subscribe", "follow", "shop now", "limited", "free", "deal"]
    weak = ["hello", "welcome", "today", "here"]

    overlay_lower = text_overlay.lower()
    score = 5

    for word in strong:
        if word in overlay_lower:
            score += 1
            break

    for word in weak:
        if word in overlay_lower:
            score -= 1
            break

    return min(10, max(0, score))


def analyze_platform_fit(video_duration: float, aspect_ratio: str) -> int:
    """Score platform fit (0-10)."""
    score = 5

    # TikTok/Reels: 9:16, max 60s
    if aspect_ratio == "9:16" and video_duration <= 60:
        score += 2
    elif aspect_ratio == "9:16":
        score += 1

    # YouTube: 16:9, any duration
    if aspect_ratio == "16:9":
        score += 1

    return min(10, max(0, score))


# ---------------------------------------------------------------------------
# G8: ingested-metrics blending (DEV-G8-002)
# ---------------------------------------------------------------------------


def _latest_ingest_for_root(
    root: Path | None,
) -> tuple[str, dict[str, Any]] | None:
    """Latest ingested snapshot across all platforms of the latest project.

    ``root`` is the working directory; the newest project under
    ``<root>/.brandly`` (by ``project.json`` mtime) supplies the snapshots.
    """
    if root is None:
        return None
    brandly = Path(root) / ".brandly"
    if not brandly.is_dir():
        return None
    projects = [p for p in brandly.iterdir() if p.is_dir()]
    if not projects:
        return None

    def _mtime(p: Path) -> float:
        pj = p / "project.json"
        return pj.stat().st_mtime if pj.is_file() else 0.0

    proj_dir = max(projects, key=_mtime)
    from brandly_cli.metrics import latest_ingest_any

    return latest_ingest_any(proj_dir)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


async def analyze_video(
    video_path: Path,
    script: str | None = None,
    *,
    style: str = "cinematic",
    root: Path | None = None,
) -> dict[str, Any]:
    """Predict video performance metrics.

    Args:
        video_path: Path to video file.
        script: Optional script text for hook analysis.
        style: Visual style preset.
        root: Optional project root.

    Returns:
        Dict with scores and recommendations.
    """
    video_path = Path(video_path)

    if not video_path.exists():
        return {"error": f"Video file not found: {video_path}"}

    # Get video properties
    duration = 0.0
    resolution = (0, 0)
    aspect_ratio = "unknown"

    try:
        import json as _json

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0:
            data = _json.loads(proc_output(result.stdout))
            fmt = data.get("format", {})
            duration = float(fmt.get("duration", 0.0))

            # Get resolution from video stream
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    resolution = (
                        int(stream.get("width", 0)),
                        int(stream.get("height", 0)),
                    )
                    w, h = resolution
                    if w > 0 and h > 0:
                        # Simplify to common ratios
                        ratio = w / h
                        if abs(ratio - 16 / 9) < 0.1:
                            aspect_ratio = "16:9"
                        elif abs(ratio - 9 / 16) < 0.1:
                            aspect_ratio = "9:16"
                        elif abs(ratio - 1) < 0.1:
                            aspect_ratio = "1:1"
                        elif abs(ratio - 4 / 5) < 0.1:
                            aspect_ratio = "4:5"
                    break
    except Exception:
        pass

    # Analyze components
    hook_strength = analyze_hook_strength(script or "")
    word_count = len((script or "").split())
    pacing_score = analyze_pacing(duration, word_count)
    visual_quality = analyze_visual_quality(style, resolution)
    ctr_prediction = analyze_ctr_prediction(None)  # No overlay info yet
    platform_fit = analyze_platform_fit(duration, aspect_ratio)

    # G8 (DEV-G8-002): prefer a recent ingest over heuristics; the output
    # always labels which source produced the CTR row.
    ingested = _latest_ingest_for_root(root)
    if ingested is not None:
        platform, snap = ingested
        last_row = (snap.get("rows") or [{}])[-1]
        ctr_pct = float(last_row.get("ctr_pct", 0.0))
        # Deterministic blend rule: percentage points, clamped to the 0-10
        # row scale (a 10 %+ CTR saturates the row at 10/10).
        ctr_prediction = int(max(0, min(10, round(ctr_pct))))
        source = "ingested"
    else:
        source = "heuristic"

    # Calculate overall score (weighted average)
    overall = (
        hook_strength * 0.25
        + pacing_score * 0.15
        + visual_quality * 0.25
        + ctr_prediction * 0.20
        + platform_fit * 0.15
    )

    # Generate recommendations
    recommendations: list[str] = []
    if hook_strength < 6:
        recommendations.append("Add a stronger hook in the first 3 seconds")
    if pacing_score < 6:
        recommendations.append("Consider adjusting video pace")
    if visual_quality < 6:
        recommendations.append("Use higher resolution or better style preset")
    if platform_fit < 7:
        recommendations.append("Check aspect ratio for target platform")
    if source == "ingested":
        recommendations.append(
            "CTR row reflects ingested platform data; heuristics only where no ingest exists"
        )

    metadata: dict[str, Any] = {
        "duration_seconds": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "style": style,
    }
    if ingested is not None:
        platform, snap = ingested
        last_row = (snap.get("rows") or [{}])[-1]
        metadata["metrics"] = {
            "platform": platform,
            "date": snap.get("date"),
            **last_row,
        }

    return {
        "video_path": str(video_path),
        "source": source,
        "overall_score": round(overall, 1),
        "hook_strength": hook_strength,
        "pacing_score": pacing_score,
        "visual_quality": visual_quality,
        "ctr_prediction": ctr_prediction,
        "platform_fit": platform_fit,
        "recommendations": recommendations,
        "metadata": metadata,
    }
