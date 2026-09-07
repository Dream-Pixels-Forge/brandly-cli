"""User preference memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class UserPreferences:
    """Stores user preferences (liked/disliked hooks, preferred style, etc.)."""

    def __init__(self, workspace_dir: str | Path) -> None:
        self.storage_path = Path(workspace_dir) / ".brandly" / "user-preferences.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.storage_path.exists():
            try:
                return json.loads(self.storage_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self._data, indent=2))

    def get(self) -> dict[str, Any]:
        return dict(self._data)

    def exists(self) -> bool:
        return bool(self._data)

    def update(self, prefs: dict[str, Any]) -> None:
        self._data.update(prefs)
        self._save()

    def like_hook(self, hook: str) -> None:
        liked = self._data.get("liked_hooks", [])
        disliked: list[str] = self._data.get("disliked_hooks", [])
        if hook not in liked:
            liked.append(hook)
        if hook in disliked:
            disliked.remove(hook)
        self._data["liked_hooks"] = liked
        self._data["disliked_hooks"] = disliked
        self._save()

    def dislike_hook(self, hook: str) -> None:
        disliked = self._data.get("disliked_hooks", [])
        liked: list[str] = self._data.get("liked_hooks", [])
        if hook not in disliked:
            disliked.append(hook)
        if hook in liked:
            liked.remove(hook)
        self._data["liked_hooks"] = liked
        self._data["disliked_hooks"] = disliked
        self._save()

    def reset(self) -> None:
        self._data = {
            "preferred_style": None,
            "target_platforms": None,
            "liked_hooks": [],
            "disliked_hooks": [],
            "budget": None,
            "last_used_style": None,
        }
        self._save()
