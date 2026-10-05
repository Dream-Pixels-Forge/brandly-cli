"""User preference memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: The self-describing default schema (issue #220). Merged into every load so
#: a fresh store renders a full, self-describing ``view`` instead of a bare
#: heading, and the defaults live in ONE place (not only inside ``reset``).
#: The dead ``budget`` key (write-never, read-never; the budget plumbing is
#: the preflight-cost work, issue #214) is dropped so ``view`` stops
#: advertising something unusable.
DEFAULTS: dict[str, Any] = {
    "preferred_style": None,
    "target_platforms": None,
    "liked_hooks": [],
    "disliked_hooks": [],
    "last_used_style": None,
}


class UserPreferences:
    """Stores user preferences (liked/disliked hooks, preferred style, etc.)."""

    def __init__(self, workspace_dir: str | Path) -> None:
        self.storage_path = Path(workspace_dir) / ".brandly" / "user-preferences.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        # Issue #220: merge the defaults into whatever is on disk so a fresh
        # store is self-describing; stored values win over the defaults.
        data: dict[str, Any] = {
            k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()
        }
        if self.storage_path.exists():
            try:
                stored = json.loads(self.storage_path.read_text())
                if isinstance(stored, dict):
                    data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass
        # Issue #220: drop the dead `budget` key (write-never, read-never) so
        # `view` stops advertising something unusable.
        data.pop("budget", None)
        return data

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self._data, indent=2))

    def get(self) -> dict[str, Any]:
        return dict(self._data)

    def exists(self) -> bool:
        """True when the storage file exists on disk (user-authored data)."""
        return self.storage_path.is_file()

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
            k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()
        }
        self._save()
