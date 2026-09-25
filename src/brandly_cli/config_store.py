"""G6: user-level credential store (decision record DEV-G6-001).

Credentials live in the user config directory (``~/.brandly/credentials.json``)
— never inside project trees (the F2 failure mode) and never in ``.env``
files (no secret sprawl). ``BRANDLY_CONFIG_DIR`` overrides the location
(tests).

Only credential *presence* is ever reported by the CLI; the secret value
itself is never printed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def config_dir() -> Path:
    """The user config directory (override with ``BRANDLY_CONFIG_DIR``)."""
    env = os.environ.get("BRANDLY_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".brandly"


def _store_path() -> Path:
    return config_dir() / "credentials.json"


def set_credential(platform: str, secret: str) -> None:
    """Store a credential for ``platform`` in the user config dir."""
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, str] = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    data[platform] = secret
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)  # best effort (Windows ignores the mode)
    except OSError:
        pass


def get_credential(platform: str) -> str | None:
    """Return the stored credential for ``platform`` (or None)."""
    path = _store_path()
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8") or "{}")
    return data.get(platform)


def has_credential(platform: str) -> bool:
    return get_credential(platform) is not None


def credential_names() -> list[str]:
    path = _store_path()
    if not path.is_file():
        return []
    return sorted(json.loads(path.read_text(encoding="utf-8") or "{}"))
