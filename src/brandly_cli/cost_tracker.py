"""Credit-cost tracker for Brandly projects."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


#: Nominal free-tier daily video quota (Agnes Token Plan docs, 2026-06).
NOMINAL_VIDEO_SECONDS_PER_DAY = 500


def video_seconds_today(root: str | Path) -> dict[str, int]:
    """Sum video-seconds generated today (UTC) across ALL projects (issue #118).

    The Agnes free tier allows ~500 video-seconds/day, but nothing reported
    actual usage - during provider 503/429 waves there was no way to tell
    quota exhaustion from service degradation. The per-video generation
    records (``.brandly/<id>/docs/tmp/video_*.json``) already carry
    ``generated_at`` + ``metadata.duration``, so this is a pure local read.

    Counts a record when: asset_type == "video", the UTC date of
    ``generated_at`` is today, and ``metadata.duration`` parses as a
    positive number. Malformed files are skipped silently.
    """
    from datetime import datetime
    from datetime import timezone as _tz

    root_path = Path(root)
    today = datetime.now(_tz.utc).date()
    seconds = 0
    records = 0
    for record_path in root_path.glob(".brandly/*/docs/tmp/video_*.json"):
        try:
            data = json.loads(record_path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict) or data.get("asset_type") != "video":
            continue
        try:
            stamp = datetime.fromisoformat(str(data.get("generated_at", "")))
        except ValueError:
            continue
        if stamp.tzinfo is None:
            from datetime import timezone as _tz2

            stamp = stamp.replace(tzinfo=_tz2.utc)
        if stamp.astimezone(_tz.utc).date() != today:
            continue
        try:
            duration = int(data.get("metadata", {}).get("duration", 0))
        except (AttributeError, TypeError, ValueError):
            continue
        if duration > 0:
            seconds += duration
            records += 1
    return {"seconds": seconds, "records": records}


#: Issue #192: the Agnes free tier allows ~500 video-seconds/day
#: (``PROVIDER_RATE_LIMITS["Agnes AI"]["video"]``). Warn as the day fills up so
#: quota exhaustion is distinguishable from service degradation (#148).
DAILY_VIDEO_SECONDS_FREE_TIER = 500
#: Fraction of the daily cap at which the quota warning fires.
DAILY_VIDEO_SECONDS_WARN_RATIO = 0.8


def daily_video_quota_status(root: str | Path) -> dict[str, Any]:
    """Issue #192: today's video-seconds against the free-tier daily cap."""
    usage = video_seconds_today(root)
    cap = DAILY_VIDEO_SECONDS_FREE_TIER
    seconds = usage["seconds"]
    return {
        **usage,
        "cap": cap,
        "remaining": max(0, cap - seconds),
        "percent_used": round((seconds / cap) * 100) if cap else 0,
        "at_risk": seconds >= cap * DAILY_VIDEO_SECONDS_WARN_RATIO,
    }


def compute_multi_day_schedule(
    target_seconds: int,
    daily_quota: int = NOMINAL_VIDEO_SECONDS_PER_DAY,
    avg_shot_duration: float = 5.0,
) -> dict[str, Any]:
    """Compute a multi-day schedule for a target duration given daily quota.

    Args:
        target_seconds: Total video seconds needed.
        daily_quota: Daily video seconds quota (default 500).
        avg_shot_duration: Average shot duration in seconds (default 5.0 from G7 reliable window).

    Returns:
        Dict with days, seconds_per_day, and shots_per_day.
    """
    if target_seconds <= daily_quota:
        return {
            "days": 1,
            "seconds_per_day": [target_seconds],
            "shots_per_day": [max(1, round(target_seconds / avg_shot_duration))],
        }

    days = (target_seconds + daily_quota - 1) // daily_quota  # Ceiling division
    seconds_per_day = []
    remaining = target_seconds
    for _ in range(days):
        day_seconds = min(daily_quota, remaining)
        seconds_per_day.append(day_seconds)
        remaining -= day_seconds

    shots_per_day = [max(1, round(s / avg_shot_duration)) for s in seconds_per_day]

    return {
        "days": days,
        "seconds_per_day": seconds_per_day,
        "shots_per_day": shots_per_day,
    }


def estimate_video_credits(shot_count: int, model: str) -> tuple[int, int]:
    """Issue #214: ``(cost_per_shot, total)`` from the same model/cost table
    the ``models`` command displays, so a dry-run can price a shot list."""
    from brandly_cli.constants import get_model_info

    info = get_model_info(model)
    per_shot = int(info.get("cost_credits", 0)) if info else 0
    return per_shot, per_shot * shot_count


class CostEntry:
    def __init__(self, phase: str, action: str, credits: int, timestamp: str) -> None:
        self.phase = phase
        self.action = action
        self.credits = credits
        self.timestamp = timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "action": self.action,
            "credits": self.credits,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CostEntry:
        return cls(d["phase"], d["action"], d["credits"], d["timestamp"])


class ProjectCostState:
    def __init__(
        self, id_: str, budget_credits: int, credits_spent: int, cost_log: list[CostEntry]
    ) -> None:
        self.id = id_
        self.budget_credits = budget_credits
        self.credits_spent = credits_spent
        self.cost_log = cost_log

    @property
    def remaining(self) -> int:
        return self.budget_credits - self.credits_spent

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "budget_credits": self.budget_credits,
            "credits_spent": self.credits_spent,
            "cost_log": [e.to_dict() for e in self.cost_log],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectCostState:
        return cls(
            d["id"],
            d["budget_credits"],
            d["credits_spent"],
            [CostEntry.from_dict(e) for e in d.get("cost_log", [])],
        )


class CostTracker:
    """Tracks credit spend per project and enforces budget gates.

    ``base`` is the ``.brandly`` directory. Each project's cost state lives
    at ``.brandly/{project_id}/cost.json``.
    """

    def __init__(self, base: str | Path) -> None:
        self.base = Path(base)

    def _resolve_project_dir(self, project_id: str) -> Path:
        """Return the canonical project dir: ``.brandly/{project_id}/``."""
        return self.base / project_id

    def _cost_path(self, project_id: str) -> Path:
        return self._resolve_project_dir(project_id) / "cost.json"

    def _load(self, project_id: str) -> ProjectCostState:
        path = self._cost_path(project_id)
        if not path.exists():
            raise FileNotFoundError(f"Cost state not found for project {project_id}")
        return ProjectCostState.from_dict(json.loads(path.read_text()))

    def _ensure(self, project_id: str, budget_credits: int) -> ProjectCostState:
        """Load cost state, creating it from project.json budget if missing."""
        try:
            return self._load(project_id)
        except FileNotFoundError:
            state = ProjectCostState(project_id, budget_credits, 0, [])
            self._save(state)
            return state

    def _save(self, state: ProjectCostState) -> None:
        path = self._cost_path(state.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict(), indent=2))

    async def can_afford(self, project_id: str, credits: int) -> dict[str, Any]:
        """Check if a project can afford a cost. Returns {allowed, remaining, over_budget}."""
        try:
            state = self._load(project_id)
        except FileNotFoundError:
            return {"allowed": False, "remaining": 0, "over_budget": credits}
        remaining = state.remaining
        over_budget = max(0, credits - remaining)
        return {
            "allowed": credits <= remaining,
            "remaining": remaining,
            "over_budget": over_budget,
        }

    async def record_spend(
        self,
        project_id: str,
        phase: str,
        action: str,
        credits: int,
        budget_credits: int | None = None,
    ) -> dict[str, Any]:
        """Record a credit spend. Raises ValueError if budget exceeded.

        If cost.json doesn't exist yet and ``budget_credits`` is provided,
        the cost state is initialized from the project budget (auto-create).
        """
        try:
            state = self._load(project_id)
        except FileNotFoundError:
            if budget_credits is None:
                raise ValueError(f"Project {project_id} not found") from None
            state = ProjectCostState(project_id, budget_credits, 0, [])
            self._save(state)

        if state.credits_spent + credits > state.budget_credits:
            raise ValueError(
                f"Budget exceeded! Attempted: {state.credits_spent + credits}, "
                f"Budget: {state.budget_credits}"
            )

        from brandly_cli.io import now_iso

        state.credits_spent += credits
        state.cost_log.append(CostEntry(phase, action, credits, now_iso()))
        self._save(state)

        return {
            "project_id": project_id,
            "phase": phase,
            "action": action,
            "credits": credits,
            "total_spent": state.credits_spent,
            "budget": state.budget_credits,
            "remaining": state.remaining,
        }

    async def get_summary(self, project_id: str) -> dict[str, Any]:
        """Return spending summary grouped by phase."""
        state = self._load(project_id)
        by_phase: dict[str, int] = {}
        for entry in state.cost_log:
            by_phase[entry.phase] = by_phase.get(entry.phase, 0) + entry.credits

        return {
            "total": state.credits_spent,
            "budget": state.budget_credits,
            "remaining": state.remaining,
            "percent_used": round((state.credits_spent / state.budget_credits) * 100)
            if state.budget_credits
            else 0,
            "by_phase": by_phase,
            "entries": [e.to_dict() for e in state.cost_log],
        }

    async def record_continuation(
        self,
        project_id: str,
        shot_id: str,
        shortfall_s: float,
        attempt_number: int,
        credits: int,
        budget_credits: int | None = None,
    ) -> dict[str, Any]:
        """Record a continuation take spend.

        Continuations are extra requests to finish a short clip. They cost
        credits but don't count as new shots - they're attributed to the
        original shot's continuation history.

        Args:
            project_id: Project identifier
            shot_id: The original shot ID this continuation is for
            shortfall_s: Duration shortfall this continuation addresses
            attempt_number: Which continuation attempt (1, 2, etc.)
            credits: Credit cost of the continuation generation
            budget_credits: Optional budget for auto-initialization

        Returns:
            Dict with spend result including total_spent and remaining budget
        """
        # Reuse record_spend but tag the action as a continuation
        action = f"continuation-{shot_id}-attempt-{attempt_number}"
        return await self.record_spend(
            project_id=project_id,
            phase="continuation",
            action=action,
            credits=credits,
            budget_credits=budget_credits,
        )



# ---------------------------------------------------------------------------
# Media spend auto-recording (moved out of cli.py — P2-8)
# ---------------------------------------------------------------------------


def record_media_spend(root: Path, project_id: str, kind: str, model_id: str) -> None:
    """Auto-record credit spend after a successful media generation.

    Looks up the model's ``cost_credits`` from constants and calls
    CostTracker.record_spend, then syncs the result back into the
    project's ``spent`` field so ``brandly status`` stays accurate.
    """
    from brandly_cli.constants import IMAGE_MODEL_INFO, VIDEO_MODEL_INFO

    cost = (
        VIDEO_MODEL_INFO.get(model_id, {}).get("cost_credits")  # type: ignore[call-overload]
        or IMAGE_MODEL_INFO.get(model_id, {}).get("cost_credits")  # type: ignore[call-overload]
        or 0
    )
    if cost <= 0:
        return
    ct = CostTracker(root / ".brandly")
    from brandly_cli.project_manager import ProjectManager

    pm = ProjectManager(root)
    try:
        proj = asyncio.run(pm.read(project_id))
        budget = proj.budget if proj else None
    except Exception:
        budget = None
    try:
        result = asyncio.run(ct.record_spend(project_id, kind, kind, cost, budget_credits=budget))
        asyncio.run(pm.update(project_id, {"spent": result["total_spent"]}))
        console.print(
            f"[dim]  Spent: {result['credits']} credits for {kind} ({model_id})  "
            f"Total: {result['total_spent']}/{result['budget']}[/dim]"
        )
    except ValueError as e:
        console.print(f"[yellow]⚠ Budget exceeded — {e}[/yellow]")
    except Exception as e:
        console.print(f"[dim]  Cost record failed (non-fatal): {e}[/dim]")
