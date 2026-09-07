"""Director orchestrator — autonomous video production pipeline agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brandly_cli.agnes_client import create_video_task, generate_image, poll_video
from brandly_cli.ark_client import (
    create_video_task as ark_create_video_task,
)
from brandly_cli.ark_client import (
    generate_image as ark_generate_image,
)
from brandly_cli.ark_client import (
    poll_video as ark_poll_video,
)
from brandly_cli.audio_client import generate_music, generate_tts
from brandly_cli.constants import (
    PHASE_ORDER,
    SHOT_COSTS,
    STYLE_COSTS,
    VIDEO_STYLES,
    StylePreset,
)
from brandly_cli.cost_tracker import CostTracker
from brandly_cli.memory import UserPreferences
from brandly_cli.project_manager import ProjectManager
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.utils import _now_iso, generate_project_id
from brandly_cli.video_prompts import build_enhanced_video_prompt

DIRECTOR_PROMPT = """\
You are now in **Brandly Director Mode** — an autonomous video production pipeline.

## Your Role
You are the **Director**. Your job is to guide the creation of a
professional product video from concept to final render using the
Brandly toolset.

## Immediate Actions
1. Ask the user for their **product name** and **product idea**
   (what it is, key features, selling points)
2. Ask about **video style** preference: cinematic, ugc, montage,
   multi_shot, continuous, unboxing, lifestyle, collage_motion_graphic,
   brand_short_video, or explainer_video
3. Ask about **target platforms** (TikTok, Instagram, YouTube, or all)
4. Ask about **budget** (max credits to spend, default 500)
5. Ask if they have **reference images** for character/object consistency (optional but recommended)
6. Once you have this info, immediately call `brandly init` to create the project

## Video Prompt Engineering (Builtin Skill)
When generating videos, ALWAYS use the built-in prompt tools to craft professional prompts:

### Step 1: Generate Prompt
Use `brandly prompt` to create cinematic prompts before generating video:
```
brandly prompt --subject "product description" --action "what happens"
  --environment "where" --shots 4 --style cinematic
  --character "character details"
```

### Step 2: Generate Video
Use the generated prompt with `brandly video`:
```
brandly video <project_id> --prompt "your prompt" --style cinematic
  --character "description" --reference-images "url1,url2" --wait
```

### Key Consistency Techniques:
- **Character locking**: Always use `--character` with detailed description
  (face, hair, clothing, body type)
- **Reference images**: Use `--reference-images` with URLs to maintain
  visual consistency
- **Style presets**: Choose appropriate style
  (commercial for products, cinematic for storytelling)
- **Multi-shot**: Generate 3-4 shots with different camera angles
  for professional coverage

### Shot Types Available:
- establishing, medium, close_up, extreme_close_up, low_angle, high_angle
- tracking, orbital, dutch, static_product, pov

### Camera Moves Available:
- push_in, pull_out, pan_left, pan_right, tilt_up, tilt_down
- tracking, static, zoom_in, zoom_out, orbital, crane_up, crane_down
- whip_pan, dolly_in, dolly_out, handheld, locked_off

## Pipeline (provider → analyze → start → run → approve → validate → publish)
After project initialization, follow this phase pipeline:
1. **trends** — Research trending styles for this product category
2. **concept** — Create creative concept and mood board
3. **script** — Write shot-by-shot script with timing
4. **asset** — Generate/source visual assets (use `brandly prompt` + `brandly video`)
5. **audio** — Create music, SFX, voiceover
6. **re_edit** — Review and refine
7. **validate** — Quality checks and virality scoring
8. **publish** — Export final video with captions

## Dashboard
When the user asks to **see information**, **view progress**, **check status**,
**open dashboard**, or any similar request to visualize the project:
- Call `brandly status <project_id>` to check the project
- Or `brandly progress <project_id>` to see a detailed progress breakdown

## Rules
- Check `brandly status <id>` before each phase
- Use `brandly estimate --style <s> --shots <n>` to check budget before expensive operations
- Get user approval via `brandly approve <id> <phase>` before proceeding
- Record costs with `brandly record_cost <id> <phase> <action> <credits>` after paid operations
- Save artifacts with `brandly export <id>`
- Track decisions with `brandly memory view|like|dislike`
- When user wants to see project info, run `brandly status <id>`

## Communication Style
- Be concise and action-oriented
- Show progress after each phase
- Present options, let user decide on creative direction
- Explain what you're about to do before doing it
- Always generate prompts with `brandly prompt` before running `brandly video`

**Start by greeting the user and asking for their product information.**
"""


class DirectorConfig:
    """Configuration for the Director orchestrator."""

    def __init__(
        self,
        root: str | Path,
        default_style: str = "cinematic",
        default_budget: int = 500,
        default_shots: int = 5,
    ) -> None:
        self.root = Path(root)
        self.default_style = default_style
        self.default_budget = default_budget
        self.default_shots = default_shots
        self.pm = ProjectManager(self.root)
        self.ct = CostTracker(self.root / ".brandly" / "projects")
        self.mem = UserPreferences(self.root)


class Director:
    """Autonomous video production orchestrator."""

    def __init__(self, config: DirectorConfig) -> None:
        self.cfg = config

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    async def start_project(
        self,
        name: str,
        idea: str,
        *,
        style: str | None = None,
        budget: int | None = None,
        shots: int | None = None,
        platforms: list[str] | None = None,
    ) -> str:
        """Create a new project and return its ID."""
        s = style or self.cfg.default_style
        b = budget or self.cfg.default_budget
        sh = shots or self.cfg.default_shots
        pts = platforms or ["tiktok", "instagram"]

        if s not in VIDEO_STYLES:
            raise ValueError(f"Invalid style '{s}'. Choices: {', '.join(VIDEO_STYLES)}")
        if sh < 3 or sh > 10:
            raise ValueError("Shots must be between 3 and 10.")

        from brandly_cli.types import ProjectData

        proj = ProjectData(
            id=generate_project_id(),
            name=name,
            description=idea,
            style=s,
            shot_count=sh,
            budget=b,
            target_platforms=pts,
        )
        await self.cfg.pm.create(proj)
        return proj.id

    async def get_status(self, project_id: str) -> dict[str, Any]:
        """Return project status summary."""
        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")
        return {
            "id": proj.id,
            "name": proj.name,
            "status": proj.status,
            "current_phase": proj.current_phase,
            "style": proj.style,
            "shot_count": proj.shot_count,
            "budget": proj.budget,
            "spent": proj.spent,
            "remaining": proj.budget - proj.spent,
            "target_platforms": proj.target_platforms,
            "created_at": proj.created_at,
            "updated_at": proj.updated_at,
        }

    async def estimate(
        self,
        style: str,
        shots: int,
    ) -> dict[str, Any]:
        """Estimate cost for a given style and shot count."""
        if style not in STYLE_COSTS:
            raise ValueError(f"Invalid style '{style}'")
        if shots < 3 or shots > 10:
            raise ValueError("Shots must be between 3 and 10.")

        style_cost = STYLE_COSTS[style]
        shot_cost = SHOT_COSTS.get(shots, 0)
        total_base = style_cost + shot_cost
        overhead = 60

        return {
            "style": style,
            "shot_count": shots,
            "style_cost": style_cost,
            "shot_cost": shot_cost,
            "total_base": total_base,
            "overhead": overhead,
            "total_estimate": total_base + overhead,
        }

    # ------------------------------------------------------------------
    # Image generation
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        project_id: str,
        prompt: str,
        *,
        model: str = "agnes-image-2.1-flash",
        size: str = "2K",
        ratio: str = "16:9",
        style_preset: StylePreset | None = None,
        n: int = 1,
    ) -> dict[str, Any]:
        """Generate an image and store result in project."""
        enhanced = apply_style_preset(prompt, style_preset) if style_preset else prompt
        is_ark = model.startswith("seedream")

        if is_ark:
            result = await ark_generate_image(enhanced, model=model, size=size, n=n)
            urls = result.get("urls", [])
            url = urls[0] if urls else None
        else:
            result = await generate_image(enhanced, model=model, size=size, ratio=ratio)
            url = result.get("url")

        proj = await self.cfg.pm.read(project_id)
        if proj:
            analysis = proj.image_analysis or {}
            analysis.update(
                {
                    "generated_url": url,
                    "prompt": prompt,
                    "enhanced_prompt": enhanced,
                    "style_preset": style_preset,
                    "model": model,
                    "generated_at": _now_iso(),
                }
            )
            await self.cfg.pm.update(project_id, {"image_analysis": analysis})

        return result

    # ------------------------------------------------------------------
    # Video generation
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        project_id: str,
        prompt: str,
        *,
        model: str = "agnes-video-v2.0",
        mode: str = "text",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        style: str = "cinematic",
        character: str | None = None,
        reference_images: list[str] | None = None,
        wait: bool = False,
        max_wait: int = 300,
    ) -> dict[str, Any]:
        """Generate a video with enhanced prompt engineering and character consistency."""
        # Enhance prompt with style and consistency hints
        enhanced = build_enhanced_video_prompt(
            prompt, style, character=character, reference_images=reference_images
        )

        is_ark = model.startswith("seedance")
        if is_ark:
            task = await ark_create_video_task(
                enhanced,
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
            )
            video_id = task.get("task_id") or ""
        else:
            task = await create_video_task(
                enhanced,
                model=model,
                mode=mode,
                duration=duration,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
            )
            video_id = task["video_id"]

        if wait and video_id:
            if is_ark:
                result = await ark_poll_video(video_id, max_wait_seconds=max_wait)
            else:
                result = await poll_video(video_id, max_wait_seconds=max_wait)
            task["url"] = result.get("url")
            task["final_status"] = result.get("status")

        # Persist to project phase
        proj = await self.cfg.pm.read(project_id)
        if proj:
            phases = dict(getattr(proj, "phases", {}))
            current = proj.current_phase
            if current not in phases:
                phases[current] = {"status": "pending"}
            phase_out = json.loads(phases[current].get("output") or "{}")
            videos = phase_out.setdefault("video_generations", [])
            videos.append(
                {
                    "task_id": task.get("id"),
                    "video_id": video_id,
                    "model": model,
                    "mode": mode,
                    "prompt": prompt,
                    "url": task.get("url"),
                    "status": task.get("status"),
                    "created_at": _now_iso(),
                }
            )
            phases[current]["output"] = json.dumps(phase_out)
            await self.cfg.pm.update(project_id, {"phases": phases})

        return task

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    async def generate_music(
        self,
        prompt: str,
        *,
        model: str = "google-lyria",
        duration: int = 30,
        instrumental: bool = True,
    ) -> dict[str, Any]:
        """Generate background music."""
        return await generate_music(
            prompt, model=model, duration_seconds=duration, instrumental=instrumental
        )

    async def generate_tts(
        self,
        text: str,
        *,
        model: str = "eleven_v3",
        voice_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate voiceover."""
        return await generate_tts(
            text, model=model, voice_id=voice_id or "English_Insightful_Speaker"
        )

    # ------------------------------------------------------------------
    # Pipeline orchestration
    # ------------------------------------------------------------------

    async def run_phase(self, project_id: str, phase: str) -> dict[str, Any]:
        """Advance a single pipeline phase (mock — real agents would call MCP tools)."""
        if phase not in PHASE_ORDER:
            raise ValueError(f"Invalid phase '{phase}'")

        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")
        if proj.status == "cancelled":
            return {"error": "Project cancelled", "phase": phase}
        if proj.status == "paused":
            return {"error": "Project paused", "phase": phase}

        # Mark phase running
        phases = dict(getattr(proj, "phases", {}))
        phases[phase] = {"status": "running", "started_at": _now_iso()}
        await self.cfg.pm.update(project_id, {"phases": phases, "status": "running"})

        # Simulate phase work (in production, this would dispatch a subagent)
        result = await self._simulate_phase(phase, proj)

        # Mark phase completed
        phases = dict(getattr(proj, "phases", {}))
        phases[phase] = {
            "status": "completed",
            "started_at": phases.get(phase, {}).get("started_at"),
            "completed_at": _now_iso(),
            "output": json.dumps(result),
        }
        idx = PHASE_ORDER.index(phase)
        next_phase = PHASE_ORDER[idx + 1] if idx < len(PHASE_ORDER) - 1 else "done"
        await self.cfg.pm.update(
            project_id,
            {"phases": phases, "current_phase": next_phase},
        )

        return {"phase": phase, "next_phase": next_phase, "result": result}

    async def _simulate_phase(self, phase: str, proj: Any) -> dict[str, Any]:
        """Simulate phase execution (placeholder for real agent dispatch)."""
        from brandly_cli.constants import STYLE_COSTS as SC

        style_cost = SC.get(proj.style, 250)
        shot_cost = SHOT_COSTS.get(proj.shot_count, 30)
        base = style_cost + shot_cost

        phase_results = {
            "init": {"message": "Project initialized"},
            "trends": {
                "trending_formats": [
                    {"name": "Quick cut showcase", "virality_potential": 8.5},
                    {"name": "Before/after transformation", "virality_potential": 7.8},
                ],
                "recommended_style": proj.style,
            },
            "concept": {
                "concepts": [
                    {"id": 1, "name": "Hero reveal", "virality_score": 8.0},
                    {"id": 2, "name": "Lifestyle integration", "virality_score": 7.2},
                ],
                "recommended": 1,
            },
            "script": {
                "scenes": [
                    {"id": 1, "description": "Opening hook", "duration": 3},
                    {"id": 2, "description": "Product reveal", "duration": 4},
                    {"id": 3, "description": "Benefit showcase", "duration": 4},
                    {"id": 4, "description": "CTA", "duration": 2},
                ],
                "duration": 15,
            },
            "asset": {
                "estimated_credits": round(base * 0.25),
                "message": "Asset generation plan created",
            },
            "audio": {
                "estimated_credits": round(base * 0.15),
                "message": "Audio plan created",
            },
            "re_edit": {"message": "Review and refinement complete"},
            "validate": {
                "score": 75.0,
                "passed": True,
                "issues": [],
                "recommendations": ["Add subtitles for accessibility"],
            },
            "publish": {
                "message": "Video published successfully",
                "platforms": proj.target_platforms,
            },
            "done": {"message": "Pipeline complete!"},
        }
        return phase_results.get(phase, {"message": f"Phase {phase} completed"})

    async def run_pipeline(self, project_id: str) -> dict[str, Any]:
        """Run all remaining phases sequentially."""
        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")

        current_idx = PHASE_ORDER.index(str(proj.current_phase))  # type: ignore[arg-type]
        results = []
        for phase in PHASE_ORDER[current_idx:]:
            r = await self.run_phase(project_id, phase)
            results.append(r)
            if r.get("next_phase") == "done" or phase == "done":
                break

        return {
            "project_id": project_id,
            "phases_run": [r["phase"] for r in results],
            "final_phase": results[-1]["phase"] if results else "none",
            "results": results,
        }

    # ------------------------------------------------------------------
    # Dashboard / progress
    # ------------------------------------------------------------------

    async def get_progress(self, project_id: str) -> dict[str, Any]:
        """Return detailed progress information."""
        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")

        phases = getattr(proj, "phases", {})
        total = len(PHASE_ORDER)
        completed = sum(1 for p in PHASE_ORDER if phases.get(p, {}).get("status") == "completed")
        overall_pct = round((completed / total) * 100) if total else 0

        current = proj.current_phase
        current_data = phases.get(current, {})
        time_in_phase: str | None = None
        if current_data.get("started_at"):
            from datetime import datetime, timezone

            elapsed = int(
                (
                    datetime.now(timezone.utc).timestamp()
                    - datetime.fromisoformat(current_data["started_at"]).timestamp()
                )
                * 1000
            )
            mins, secs = divmod(elapsed // 1000, 60)
            time_in_phase = f"{mins}m {secs}s"

        return {
            "project_id": project_id,
            "project_status": proj.status,
            "current_phase": current,
            "overall_percent": overall_pct,
            "completed_phases": completed,
            "total_phases": total,
            "time_in_current_phase": time_in_phase,
            "phase_statuses": {p: phases.get(p, {}).get("status", "pending") for p in PHASE_ORDER},
        }


def get_director_prompt() -> str:
    """Return the Director system prompt for AI tools."""
    return DIRECTOR_PROMPT
