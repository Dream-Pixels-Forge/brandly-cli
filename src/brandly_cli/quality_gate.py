"""Quality gate — pre-step verification that prevents slop, drift and bad output.

The gate is the "intelligent check before the next step" layer of the
pipeline. Instead of hand-rolled pixel heuristics, the **assessment**
(quality / slop / drift / matte backdrop / description match) is delegated
to the Agnes multimodal text model's image analysis capability: one vision
call receives the candidate (and optionally a locked reference) and returns
a structured JSON verdict.

Only cheap offline pre-checks remain in code:
* file presence + non-empty size,
* Pillow decodability (images) / ffprobe video-stream presence (video),
* first-frame extraction for video (ffmpeg) so the vision model can see it.

If no ``AGNES_API_KEY`` is set, or the vision call fails, the gate degrades
gracefully: it reports the deterministic pre-checks, marks the AI analysis
as ``skipped`` (warning, never a hard failure), and still writes an
auditable report to ``.brandly/{project}/docs/tmp/``.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brandly_cli import layout
from brandly_cli.constants import DEFAULT_AGNES_TEXT_MODEL

PASS = "pass"
WARN = "warn"
FAIL = "fail"

# ---------------------------------------------------------------------------
# Gate policy (issue #34 — documented threshold + override logic)
# ---------------------------------------------------------------------------
#
# The gate fails an element when ANY of the following holds:
#
#   1. A deterministic pre-check fails (missing/empty element, undecodable
#      media, blank-frame guard).
#   2. An AI artifact cutoff is crossed (``GATE_ARTIFACT_CUTOFFS``):
#      distortion ≥ 6/10, slop ≥ 7/10, drift ≥ 6/10.
#   3. A configured score floor is crossed: when ``threshold`` is set and the
#      AI ``quality_score`` < ``threshold`` the gate FAILs, regardless of the
#      model's own verdict (``--threshold`` on ``brandly gate``; the default
#      is None = no score floor, pre-checks + artifact cutoffs only).
#
# ``strict`` mode promotes warnings to failures (already available).
# ``lenient`` mode raises every artifact fail cutoff by +2 (max 10) and
# demotes the model's own "fail" verdict to a warning — use it to approve
# borderline takes without overriding the deterministic pre-checks.

GATE_ARTIFACT_CUTOFFS: dict[str, int] = {"distortion": 6, "slop": 7, "drift": 6}
GATE_WARN_CUTOFFS: dict[str, int] = {"distortion": 4, "slop": 4, "drift": 4}
LENIENT_CUTOFF_BUMP = 2

_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv"}

_VISION_SYSTEM = (
    "You are a strict QA reviewer for AI-generated video-production assets "
    "(character/object/location sheets, keyframe videos, storyboards). "
    "You are shown one CANDIDATE image; optionally a REFERENCE image that "
    "locks the locked identity/style. Analyze the visual content yourself. "
    "Reply with ONLY a JSON object, no prose, matching this schema:\n"
    '{'
    '"quality_score": 0-100, '
    '"slop": 0-10, '
    '"distortion": 0-10, '
    '"drift": 0-10 or null (null if no reference image is provided), '
    '"matte_background": true/false/null (null if not a reference sheet), '
    '"identity_bleed": true/false (true if a multi-character shot rendered any figure with a different character\'s face/identity than its own reference plate), '
    '"identity_bleed_detail": "one-line explanation when identity_bleed is true, else empty string", '
    '"issues": ["short concrete problems"], '
    '"verdict": "pass"|"warn"|"fail", '
    '"notes": "one-line summary" '
    '}\n'
    "Scoring guidance: 'slop' 0 = crisp professional output, 10 = generic "
    "AI slop; 'distortion' 0 = anatomically/structurally clean, 10 = "
    "severe artifacts; 'drift' 0 = identical to reference identity, 10 = "
    "completely different. 'matte_background' true only if the sheet is "
    "rendered against a seamless neutral mid-grey studio backdrop (not "
    "white, not a scene, not a busy environment). 'identity_bleed' true "
    "only when a figure's face/identity matches a DIFFERENT character's "
    "reference plate than the one it is supposed to be (cross-character "
    "bleed in a multi-character shot). Verdict: pass when "
    "quality_score>=80 and no hard issues; warn when 50-79 or minor "
    "issues; fail when <50, when distortion>=6, when drift>=6, when "
    "identity_bleed is true, or when the asset is unusable."
)


def _vision_user_prompt(
    description: str,
    expect_matt_background: bool,
    has_reference: bool,
    kind: str,
    expected_characters: list[str] | None = None,
) -> str:
    parts = [f"Asset type: {kind}."]
    if description:
        parts.append(f"Expected subject/description: {description}")
    if expect_matt_background:
        parts.append(
            "This is a reference sheet: set matte_background accordingly "
            "(the intended backdrop is a seamless neutral mid-grey studio "
            "backdrop)."
        )
    if has_reference:
        parts.append(
            "A reference image is attached: compare the candidate to it and "
            "score drift."
        )
    # Issue #51: multi-character identity bleed. When the caller names the
    # characters that are supposed to co-appear in the frame, ask the model
    # to verify each one is rendered distinctly (their own face, not the
    # dominant/first-listed character's face), and to set identity_bleed.
    if expected_characters:
        names = ", ".join(expected_characters)
        parts.append(
            f"This shot is supposed to contain these distinct characters: "
            f"{names}. For EACH character, check that the corresponding "
            f"figure in the frame actually looks like THAT character's "
            f"reference (face, skin tone, wardrobe) and NOT like another "
            f"character in the same list. If any figure's face/identity has "
            f"bled into a different character's identity (e.g. the "
            f"secondary character rendered with the primary character's "
            f"face), set identity_bleed=true and describe it in "
            f"identity_bleed_detail. Otherwise set identity_bleed=false."
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    """Structured outcome of a quality-gate run."""

    status: str = PASS
    score: int = 100
    element: str = ""
    kind: str = "image"
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    ai: dict[str, Any] = field(default_factory=dict)
    threshold: int | None = None
    """Score floor used for this run (issue #34). None = no floor."""
    lenient: bool = False
    """Whether this run used lenient artifact cutoffs."""

    def add_issue(self, msg: str, *, check: str | None = None, detail: Any = None) -> None:
        self.status = FAIL
        self.issues.append(msg)
        if check:
            self.checks[check] = {"status": FAIL, "detail": detail}

    def add_warning(self, msg: str, *, check: str | None = None, detail: Any = None) -> None:
        if self.status != FAIL:
            self.status = WARN
        self.warnings.append(msg)
        if check:
            self.checks[check] = {"status": WARN, "detail": detail}

    def record_check(self, name: str, ok: bool, detail: Any = None) -> None:
        self.checks[name] = {"status": PASS if ok else WARN, "detail": detail}

    def finalize(self, *, strict: bool = False) -> None:
        """Recompute status from issues/warnings and apply strict mode."""
        if self.issues:
            self.status = FAIL
        elif self.warnings:
            self.status = WARN
        if strict and self.status == WARN:
            self.status = FAIL

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score": self.score,
            "element": self.element,
            "kind": self.kind,
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "checks": self.checks,
            "ai": self.ai,
            "threshold": self.threshold,
            "lenient": self.lenient,
        }

    def policy_line(self) -> str:
        """One-line gate-policy summary for reports (issue #34)."""
        parts = []
        if self.threshold is not None:
            verdict = "below" if self.score < self.threshold else "at/above"
            parts.append(f"score floor {self.threshold} ({self.score} {verdict})")
        else:
            parts.append("no score floor")
        cutoffs = GATE_ARTIFACT_CUTOFFS if not self.lenient else {
            k: min(v + LENIENT_CUTOFF_BUMP, 10) for k, v in GATE_ARTIFACT_CUTOFFS.items()
        }
        parts.append(
            "artifact fail cutoffs "
            + ", ".join(f"{k}≥{v}" for k, v in cutoffs.items())
            + (" (lenient)" if self.lenient else "")
        )
        return "Gate policy: " + "; ".join(parts)

    def markdown(self) -> str:
        lines = [
            f"# Quality Gate Report — {self.element or self.kind}",
            "",
            f"**Status:** {'✓' if self.status == PASS else '✗'} {self.status.upper()} "
            f"({self.score}/100)",
            "",
        ]
        lines.append(self.policy_line())
        lines.append("")
        if self.issues:
            lines.append("## Failures")
            lines += [f"- {i}" for i in self.issues]
            lines.append("")
        if self.warnings:
            lines.append("## Warnings")
            lines += [f"- {w}" for w in self.warnings]
            lines.append("")
        if self.ai:
            lines.append(f"## AI Analysis\n```json\n{json.dumps(self.ai, indent=2)}\n```")
            lines.append("")
        lines.append("_Written to .brandly/{project}/docs/tmp/_")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cheap offline pre-checks
# ---------------------------------------------------------------------------


def is_video(path: Path) -> bool:
    """Return True when *path* looks like a video file by extension."""
    return path.suffix.lower() in _VIDEO_EXTS


def detect_identity_bleed_heuristic(
    frame: Path,
    expected_character_count: int,
) -> bool:
    """Deterministic backstop for multi-character identity bleed (issue #51).

    The authoritative check is the AI verdict's ``identity_bleed`` field.
    This helper is a cheap offline guard for when the AI check is
    unavailable (no API key / use_ai off): it counts distinct skin-toned
    face-like clusters in the frame and flags a mismatch with the expected
    character count.

    Heuristic only — a real face detector is out of scope for a quality
    gate, so this is intentionally conservative: it returns ``True``
    (suspected bleed) only when the observed cluster count differs from the
    expected character count by more than 1. A single miscount is tolerated
    because faces in shadow or partial framing are hard to count. Returns
    ``False`` when the count matches, when the frame cannot be read, or
    when the expected count is 0/1 (single-character or object shots — no
    bleed possible).
    """
    if expected_character_count <= 1:
        return False
    try:
        from PIL import Image  # type: ignore

        with Image.open(frame) as opened:
            im = opened.convert("RGB")
            im.thumbnail((512, 512))
    except Exception:
        return False  # unreadable -> no signal, don't raise a false flag
    # Count connected skin clusters on a 16x16 grid (no scipy).
    # NOTE: im.getdata() is deprecated in Pillow 14; use get_flattened_data()
    # when the minimum Pillow version allows. Kept as getdata() for the
    # current pinned range (>=8.0).
    pixels = list(im.getdata())
    w, h = im.size
    # Build a coarse skin-tone mask.
    skin_mask: list[int] = []
    for r, g, b in pixels:
        # Loose skin-tone band (light + dark complexions): R > G > B,
        # R above B, not near-black, not near-white.
        if r > b + 12 and r > g and g > b and r > 50 and r < 245:
            skin_mask.append(1)
        else:
            skin_mask.append(0)
    # Count connected skin clusters on a 16x16 grid (no scipy).
    grid = 16
    cell_w = max(1, w // grid)
    cell_h = max(1, h // grid)
    clusters = 0
    seen: set[tuple[int, int]] = set()
    for cy in range(grid):
        for cx in range(grid):
            if (cx, cy) in seen:
                continue
            idx = (cy * cell_h) * w + cx * cell_w
            if idx >= len(skin_mask) or skin_mask[idx] == 0:
                continue
            stack = [(cx, cy)]
            size = 0
            while stack:
                x, y = stack.pop()
                if (x, y) in seen or x < 0 or y < 0 or x >= grid or y >= grid:
                    continue
                i2 = (y * cell_h) * w + x * cell_w
                if i2 >= len(skin_mask) or skin_mask[i2] == 0:
                    continue
                seen.add((x, y))
                size += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    stack.append((x + dx, y + dy))
            if size >= 2:  # a real face spans >= 2 grid cells
                clusters += 1
    # Suspected bleed when the observed count differs from expected by > 1.
    return abs(clusters - expected_character_count) > 1


def _probe_video(path: Path) -> dict[str, Any] | None:
    """ffprobe the first video stream; None when ffprobe is unavailable."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(path),
            ],
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout.decode())
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                return {
                    "width": int(stream.get("width", 0)),
                    "height": int(stream.get("height", 0)),
                    "duration": float(data.get("format", {}).get("duration", 0)),
                }
        return {"width": 0, "height": 0, "duration": 0}
    except Exception:
        return None


def _precheck(
    result: GateResult,
    path: Path,
) -> Path | None:
    """Presence + decodability. Returns an analyzable image path or None.

    For videos, extracts the first frame so the vision model can analyze it.
    """
    if not path.exists() or path.stat().st_size == 0:
        result.add_issue(f"Element not found or empty: {path}", check="presence")
        result.finalize()
        return None
    result.record_check("presence", True, f"{path.stat().st_size} bytes")

    if is_video(path):
        info = _probe_video(path)
        if info is None:
            result.add_warning(
                "ffprobe unavailable — video not pre-checked, AI analysis "
                "will still run on the first frame",
                check="probe",
            )
            frame = _first_frame(path)
            if frame is None:
                result.add_issue(
                    "Could not read or extract a frame from the video "
                    "(ffmpeg unavailable or corrupt file)",
                    check="video_frame",
                )
                result.finalize()
                return None
            result.record_check("video_frame", True, "first frame extracted")
            return frame

        if info.get("width", 0) == 0 or info.get("duration", 0) <= 0:
            result.add_issue(
                f"Video has no readable stream/duration "
                f"({info.get('width')}x{info.get('height')}, "
                f"{info.get('duration')}s)",
                check="video_stream",
            )
            result.finalize()
            return None
        result.record_check(
            "video_stream", True, f"{info['width']}x{info['height']}, {info['duration']:.1f}s"
        )
        frame = _first_frame(path)
        if frame is None:
            result.add_warning(
                "Could not extract the first frame for visual analysis "
                "(ffmpeg unavailable) — falling back to metadata checks only",
                check="video_frame",
            )
            return None
        result.record_check("video_frame", True, "first frame extracted")
        return frame

    # Image: verify Pillow can decode it.
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.load()
        result.record_check("decodable", True, f"{im.size[0]}x{im.size[1]}")
    except Exception:
        result.add_issue(f"Image not decodable / corrupt: {path}", check="decodable")
        result.finalize()
        return None

    # Offline blank guard: a fully-blank / solid render is a bad generation.
    # (Slop, drift and matte-backdrop are judged by the model, not heuristics.)
    center_std = _center_entropy(path)
    if center_std >= 0 and center_std < 6:
        result.add_issue(
            f"Center region is near-blank/blank (std={center_std:.1f}) — "
            f"probable failed generation",
            check="blank",
        )
        result.finalize()
        return None
    return path


def _center_entropy(path: Path) -> float:
    """Standard deviation of the central region of an image file.

    Used only for an offline blank-guard: a fully-solid render has near-zero
    center std. Slop / drift / matte judgement is left to the model.
    Returns -1.0 when the image cannot be opened.
    """
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.load()
            w, h = im.size
            x0 = int(w * 0.25)
            y0 = int(h * 0.25)
            crop = im.convert("L").crop((x0, y0, w - x0, h - y0)).resize((32, 32))
            px = crop.tobytes()  # flattened bytes, one channel per pixel
            n = len(px)
            mean = sum(px) / n
            var = sum((v - mean) ** 2 for v in px) / n
            return var ** 0.5
    except Exception:
        return -1.0


def _first_frame(video: Path) -> Path | None:
    """Extract frame 0 to a temp PNG; None on failure."""
    try:
        out = Path(tempfile.mkstemp(suffix=".png")[1])
        proc = subprocess.run(
            ["ffmpeg", "-y", "-v", "quiet", "-i", str(video), "-frames:v", "1", str(out)],
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
            out.unlink(missing_ok=True)
            return None
        return out
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Model-based visual analysis
# ---------------------------------------------------------------------------


def _parse_verdict(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from the model output."""
    text = text.strip()
    candidates = [text]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return {}


def _apply_ai_verdict(
    result: GateResult,
    verdict: dict[str, Any],
    *,
    expect_matt_background: bool,
    has_reference: bool,
    threshold: int | None = None,
    lenient: bool = False,
) -> None:
    """Map the model's JSON verdict onto issues/warnings/score.

    Policy (issue #34): ``threshold`` floors the quality score; ``lenient``
    raises artifact fail cutoffs and demotes the model's "fail" verdict to a
    warning. Both are recorded on the result so the report can show exactly
    which policy produced the outcome.
    """
    if not verdict:
        result.add_warning(
            "AI analysis returned an unparseable response — treat as inconclusive",
            check="ai",
        )
        return

    result.ai = verdict
    fail_cutoffs = GATE_ARTIFACT_CUTOFFS
    if lenient:
        fail_cutoffs = {
            k: min(v + LENIENT_CUTOFF_BUMP, 10) for k, v in GATE_ARTIFACT_CUTOFFS.items()
        }
    result.threshold = threshold
    result.lenient = lenient
    quality = int(verdict.get("quality_score", 100) or 100)
    slop = int(verdict.get("slop", 0) or 0)
    distortion = int(verdict.get("distortion", 0) or 0)
    drift = verdict.get("drift")
    matte = verdict.get("matte_background")
    result.score = max(0, min(100, quality))

    for issue in verdict.get("issues", []):
        if str(issue).strip():
            result.issues.append(str(issue).strip())

    # Hard distortion
    if distortion >= fail_cutoffs["distortion"]:
        result.add_issue(
            f"Severe distortion detected by AI review (score {distortion}/10)",
            check="distortion",
            detail=distortion,
        )
    elif distortion >= GATE_WARN_CUTOFFS["distortion"]:
        result.add_warning(
            f"Distortion artifacts detected by AI review (score {distortion}/10)",
            check="distortion",
            detail=distortion,
        )

    # Slop
    if slop >= fail_cutoffs["slop"]:
        result.add_issue(
            f"Output looks like generic AI slop (slop {slop}/10)",
            check="slop",
            detail=slop,
        )
    elif slop >= GATE_WARN_CUTOFFS["slop"]:
        result.add_warning(
            f"Output shows signs of AI slop (slop {slop}/10)",
            check="slop",
            detail=slop,
        )

    # Drift (only when a reference was supplied)
    if has_reference and drift is not None:
        drift = int(drift)
        if drift >= fail_cutoffs["drift"]:
            result.add_issue(
                f"High identity drift from the reference (drift {drift}/10)",
                check="drift",
                detail=drift,
            )
        elif drift >= GATE_WARN_CUTOFFS["drift"]:
            result.add_warning(
                f"Possible drift from the reference (drift {drift}/10)",
                check="drift",
                detail=drift,
            )

    # Identity bleed (issue #51): a multi-character shot rendered a figure
    # with a different character's face/identity than its own reference.
    identity_bleed = verdict.get("identity_bleed")
    if identity_bleed is True:
        detail = str(verdict.get("identity_bleed_detail") or "").strip()
        msg = "Identity bleed: a figure was rendered with a different character's face/identity"
        if detail:
            msg += f" — {detail}"
        result.add_issue(msg, check="identity_bleed", detail=detail or True)

    # Identity bleed (issue #51): a multi-character shot rendered a figure
    # with a different character's face/identity than its own reference.
    identity_bleed = verdict.get("identity_bleed")
    if identity_bleed is True:
        detail = str(verdict.get("identity_bleed_detail") or "").strip()
        msg = "Identity bleed: a figure was rendered with a different character's face/identity"
        if detail:
            msg += f" — {detail}"
        result.add_issue(msg, check="identity_bleed", detail=detail or True)

    # Matte backdrop requirement
    if expect_matt_background and matte is not None and not matte:
        result.add_warning(
            "Backdrop is not a seamless matte mid-grey studio background "
            "— regenerate with the matte-grey backdrop instruction",
            check="matte_background",
            detail=False,
        )

    # The model's own verdict floors/caps the status.
    model_verdict = str(verdict.get("verdict", "")).lower()
    if model_verdict == "fail":
        if result.status == PASS:
            result.status = WARN
            result.add_warning(
                "AI reviewer verdict: fail"
                + (" (kept at warn by lenient mode)" if lenient else "")
            )
        elif lenient:
            result.add_warning("AI reviewer verdict: fail (kept at warn by lenient mode)")
    elif model_verdict == "warn" and result.status == PASS:
        result.status = WARN
        result.add_warning("AI reviewer verdict: warn")

    # Configured score floor (issue #34).
    if threshold is not None and result.score < threshold:
        result.add_issue(
            f"Quality score {result.score} is below the required threshold "
            f"{threshold} (AI verdict: {model_verdict or 'n/a'})",
            check="threshold",
            detail={"score": result.score, "threshold": threshold},
        )


async def _run_vision_check(
    frame: Path,
    *,
    reference: Path | None,
    description: str,
    expect_matt_background: bool,
    kind: str,
    model: str,
    expected_characters: list[str] | None = None,
) -> dict[str, Any]:
    """Single multimodal chat completion; returns the parsed verdict JSON."""
    import base64

    from brandly_cli.agnes_client import chat_completion

    def data_uri(p: Path) -> str:
        b64 = base64.b64encode(p.read_bytes()).decode()
        suffix = p.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"

    ref_path = Path(reference) if reference else None
    has_reference = ref_path is not None and ref_path.exists()
    content: list[dict[str, Any]] = []
    if has_reference and ref_path is not None:
        content.append(
            {"type": "image_url", "image_url": {"url": data_uri(ref_path)}}
        )
    content.append({"type": "image_url", "image_url": {"url": data_uri(frame)}})

    labels: list[str] = []
    if has_reference:
        labels.append("IMAGE 1 = REFERENCE (locked identity)")
    labels.append("IMAGE " + ("2" if has_reference else "1") + " = CANDIDATE")
    user_text = "\n".join(
        [
            _vision_user_prompt(
                description, expect_matt_background, has_reference, kind,
                expected_characters=expected_characters,
            ),
            *labels,
        ]
    )

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": user_text},
        *content,
    ]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _VISION_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    raw = await chat_completion(
        messages,
        model=model,
        response_format={"type": "json_object"},
    )
    text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
    return _parse_verdict(text or "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _unlink_quietly(path: Path) -> None:
    """Best-effort delete of a temp frame.

    On Windows a freshly written file can still be locked by antivirus or
    the search indexer (WinError 32); cleanup must never hard-fail the
    command after the generated artifact is already on disk.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


async def verify_element(
    element: str | Path,
    *,
    reference: str | Path | None = None,
    description: str = "",
    expect_matt_background: bool = False,
    use_ai: bool = True,
    model: str = DEFAULT_AGNES_TEXT_MODEL,
    root: Path | None = None,
    project_id: str | None = None,
    strict: bool = False,
    threshold: int | None = None,
    lenient: bool = False,
    write_report: bool = True,
    expected_characters: list[str] | None = None,
) -> GateResult:
    """Run the quality gate on one element (image or video).

    Pre-checks are deterministic and offline; the visual judgment (slop,
    distortion, drift, matte backdrop, description match) is made by the
    Agnes multimodal model. When ``use_ai`` is off or no key is available,
    the AI verdict is skipped and the gate reports the pre-checks only.

    ``expected_characters`` (issue #51): a list of character names that are
    supposed to co-appear distinctly in the frame. When given and the AI
    check runs, the vision prompt asks the model to verify each character is
    rendered with their own identity (not another character's face) and to
    set ``identity_bleed`` in the verdict; a ``true`` bleed becomes a gate
    issue. Pass ``None`` (the default) for single-character or object shots
    to keep the prompt unchanged.

    Gate policy (issue #34): ``threshold`` sets a quality-score floor
    (None = no floor — default; pre-checks + artifact cutoffs only) and
    ``lenient`` raises the artifact fail cutoffs by +2 and demotes the
    model's own "fail" verdict to a warning. ``strict`` (existing) promotes
    warnings to failures. The active policy is recorded in the gate report.
    """
    element = Path(element)
    kind = "video" if is_video(element) else "image"
    result = GateResult(element=str(element), kind=kind)
    result.threshold = threshold
    result.lenient = lenient

    frame = _precheck(result, element)
    if frame is None:
        result.finalize(strict=strict)
        if write_report and root is not None and project_id:
            _write_report(result, root, project_id)
        return result

    if use_ai:
        try:
            import os

            if os.getenv("AGNES_API_KEY"):
                verdict = await _run_vision_check(
                    frame,
                    reference=Path(reference) if reference else None,
                    description=description,
                    expect_matt_background=expect_matt_background,
                    kind=kind,
                    model=model,
                    expected_characters=expected_characters,
                )
                _apply_ai_verdict(
                    result,
                    verdict,
                    expect_matt_background=expect_matt_background,
                    has_reference=bool(reference and Path(reference).exists()),
                    threshold=threshold,
                    lenient=lenient,
                )
            else:
                result.add_warning(
                    "AI visual analysis skipped (AGNES_API_KEY not set) — "
                    "only offline pre-checks were run",
                    check="ai",
                )
        except Exception as e:  # graceful: AI checks must never hard-fail the gate
            result.add_warning(
                f"AI visual analysis skipped ({e.__class__.__name__}) — "
                f"offline pre-checks passed",
                check="ai",
            )
        finally:
            # Clean up a temp extracted frame (only ours).
            if frame != element and frame.exists() and str(frame).startswith(tempfile.gettempdir()):
                _unlink_quietly(frame)
    elif frame != element and frame.exists():
        _unlink_quietly(frame)

    result.finalize(strict=strict)
    if write_report and root is not None and project_id:
        _write_report(result, root, project_id)
    return result


def _write_report(result: GateResult, root: Path, project_id: str) -> Path:
    """Write the gate report to docs/tmp, returning the path."""
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    docs_tmp = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
    docs_tmp.mkdir(parents=True, exist_ok=True)
    out = docs_tmp / f"gate_{result.kind}_{ts}.md"
    out.write_text(result.markdown(), encoding="utf-8")
    result.checks["report"] = {"status": PASS, "detail": str(out)}
    return out


__all__ = [
    "GateResult",
    "verify_element",
    "PASS",
    "WARN",
    "FAIL",
    "GATE_ARTIFACT_CUTOFFS",
    "GATE_WARN_CUTOFFS",
    "drift_prevention",
    "PromptConsistencyChecker",
    "detect_identity_bleed_heuristic",
]


# ---------------------------------------------------------------------------
# Drift prevention — pre-generation prompt validation
# ---------------------------------------------------------------------------

class PromptConsistencyChecker:
    """Validates prompts for consistency before generation.

    Checks for:
    - Character description drift between shots
    - Missing anchor references
    - Inconsistent style/lighting instructions
    - Potential spatial confusion
    """

    def __init__(self, reference_description: str | None = None) -> None:
        self.reference_description = reference_description
        self._issues: list[str] = []
        self._warnings: list[str] = []

    def check_shot_prompt(
        self,
        prompt: str,
        shot_index: int,
        character_anchor: str | None = None,
        expected_style: str | None = None,
    ) -> list[str]:
        """Check a single shot prompt for consistency issues."""
        issues: list[str] = []
        warnings: list[str] = []

        # Check for character anchor presence
        if character_anchor and shot_index > 0:
            # Condensed anchor should still be present
            anchor_key_phrases = ["ANCHOR", "same character", "continuity", "preserve"]
            if not any(phrase.lower() in prompt.lower() for phrase in anchor_key_phrases):
                warnings.append(
                    f"Shot {shot_index + 1}: Missing character anchor — "
                    f"may cause identity drift"
                )

        # Check for reference image mention in first shot
        if shot_index == 0:
            ref_phrases = ["reference image", "provided image", "visual reference"]
            if not any(phrase.lower() in prompt.lower() for phrase in ref_phrases):
                warnings.append(
                    "Shot 1: No reference image mention — "
                    "character identity may not be locked"
                )

        # Check for style consistency
        if expected_style:
            style_keywords = {
                "cinematic": ["cinematic", "film", "widescreen"],
                "commercial": ["commercial", "product", "advertisement"],
                "documentary": ["documentary", "natural", "handheld"],
                "ugc": ["smartphone", "casual", "authentic"],
                "luxury": ["luxury", "elegant", "premium"],
                "action": ["dynamic", "fast", "energetic"],
                "lifestyle": ["lifestyle", "aspirational", "warm"],
            }
            expected_keywords = style_keywords.get(expected_style, [])
            if expected_keywords:
                prompt_lower = prompt.lower()
                matches = [kw for kw in expected_keywords if kw in prompt_lower]
                if not matches:
                    warnings.append(
                        f"Shot {shot_index + 1}: Style '{expected_style}' keywords "
                        f"not detected in prompt"
                    )

        # Check for conflicting instructions
        conflicting_pairs = [
            ("static", "tracking"),
            ("locked off", "handheld"),
            ("wide shot", "close-up"),
            ("high angle", "low angle"),
        ]
        prompt_lower = prompt.lower()
        for term1, term2 in conflicting_pairs:
            if term1 in prompt_lower and term2 in prompt_lower:
                warnings.append(
                    f"Shot {shot_index + 1}: Conflicting camera instructions "
                    f"'{term1}' and '{term2}'"
                )

        self._issues.extend(issues)
        self._warnings.extend(warnings)
        return issues + warnings

    def check_sequence(
        self,
        prompts: list[str],
        character_anchor: str | None = None,
        expected_style: str | None = None,
    ) -> dict[str, Any]:
        """Check a sequence of shot prompts for cross-shot consistency."""
        all_issues: list[str] = []
        all_warnings: list[str] = []

        for i, prompt in enumerate(prompts):
            issues = self.check_shot_prompt(
                prompt, i, character_anchor, expected_style
            )
            all_issues.extend(issues)

        # Cross-shot checks
        if len(prompts) > 1:
            # Check for repetitive content
            action_phrases: list[str] = []
            for prompt in prompts:
                # Extract action phrases (simplified)
                lines = prompt.split("\n")
                for line in lines:
                    if line.lower().startswith("the scene") or line.lower().startswith("setting:"):
                        action_phrases.append(line.lower())

            if len(set(action_phrases)) < len(action_phrases) * 0.5:
                all_warnings.append(
                    "Sequence has repetitive scene descriptions — "
                    "may lack visual variety"
                )

        self._issues.extend(all_issues)
        self._warnings.extend(all_warnings)

        return {
            "issues": all_issues,
            "warnings": all_warnings,
            "pass": len(all_issues) == 0,
        }

    @property
    def has_issues(self) -> bool:
        """Return True if any issues were found."""
        return bool(self._issues)

    @property
    def has_warnings(self) -> bool:
        """Return True if any warnings were found."""
        return bool(self._warnings)

    def get_report(self) -> str:
        """Return a human-readable consistency report."""
        lines = ["Prompt Consistency Report", "=" * 40]
        if self._issues:
            lines.append("\nIssues (must fix):")
            for issue in self._issues:
                lines.append(f"  - {issue}")
        if self._warnings:
            lines.append("\nWarnings (recommended):")
            for warning in self._warnings:
                lines.append(f"  - {warning}")
        if not self._issues and not self._warnings:
            lines.append("\nAll checks passed.")
        return "\n".join(lines)


async def drift_prevention(
    prompts: list[str],
    reference_description: str | None = None,
    expected_style: str | None = None,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Validate prompts for drift risk before generation.

    This is a pre-generation check that analyzes prompt text for consistency
    issues that could lead to visual drift, identity loss, or style
    inconsistency across shots.

    Args:
        prompts: List of shot prompts to validate.
        reference_description: Expected character/subject description.
        expected_style: Expected visual style.
        strict: If True, warnings become errors.

    Returns:
        Dict with validation results and recommendations.
    """
    checker = PromptConsistencyChecker(reference_description)
    result = checker.check_sequence(prompts, reference_description, expected_style)

    # Add recommendations
    recommendations: list[str] = []
    if result["warnings"]:
        recommendations.append(
            "Consider adding explicit character anchors to each shot prompt"
        )
    if len(prompts) > 3:
        recommendations.append(
            "For sequences >3 shots, consider using the ShotChain class "
            "for automatic continuity hooks"
        )

    return {
        "valid": result["pass"] if not strict else not result["warnings"],
        "issues": result["issues"],
        "warnings": result["warnings"],
        "recommendations": recommendations,
        "report": checker.get_report(),
    }
