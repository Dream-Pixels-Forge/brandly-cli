"""Credit-cost tracker for Brandly projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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

    ``base`` is the ``.brandly`` directory. Each project's cost state lives at
    ``.brandly/{project_id}/cost.json`` (new layout); the legacy
    ``.brandly/projects/{project_id}/cost.json`` location is used as a
    fallback for older installs.
    """

    def __init__(self, base: str | Path) -> None:
        self.base = Path(base)

    def _resolve_project_dir(self, project_id: str) -> Path:
        """New layout first; fall back to the legacy ``projects/`` tree."""
        new_dir = self.base / project_id
        if (new_dir / "project.json").exists() or (new_dir / "cost.json").exists():
            return new_dir
        legacy_dir = self.base / "projects" / project_id
        if (legacy_dir / "project.json").exists() or (legacy_dir / "cost.json").exists():
            return legacy_dir
        return new_dir

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

        from brandly_cli.utils import now_iso

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
