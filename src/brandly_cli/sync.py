"""Auto-sync Brandly API keys into AI-tool configuration files."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path

from brandly_cli.utils import write_atomic

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = Path.home()

TOOLS = {
    "qwen": HOME / ".qwen" / "settings.json",
    "claude": HOME / ".claude" / "settings.json",
    "gemini": HOME / ".gemini" / "settings.json",
    "codex": HOME / ".codex" / "config.toml",
    "pi": HOME / ".pi" / "agent" / "auth.json",
    "opencode": HOME / ".opencode.json",
}

# Env var names used by each tool
AGNES_ENV_KEY = "AGNES_API_KEY"
MINIMAX_ENV_KEY = "MINIMAX_API_KEY"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False))


def _append_to_dotenv(dotenv_path: Path, keys: dict[str, str]) -> None:
    """Append KEY=VALUE lines to a .env file without overwriting existing lines."""
    dotenv_path.parent.mkdir(parents=True, exist_ok=True)
    existing = dotenv_path.read_text(encoding="utf-8") if dotenv_path.exists() else ""
    lines = existing.splitlines()
    existing_keys = {
        line.split("=", 1)[0].strip() for line in lines if "=" in line and not line.startswith("#")
    }
    for k, v in keys.items():
        if k not in existing_keys:
            lines.append(f"{k}={v}")
    dotenv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scan_for_dotenvs(root: Path | None = None) -> Generator[Path, None, None]:
    """Find .env files in common project and home locations."""
    bases = [Path.cwd()]
    if root:
        bases.append(Path(root))
    bases.append(HOME)
    for base in bases:
        p = base / ".env"
        if p.exists():
            yield p
        for sub in (base / ".brandly", base / "projects"):
            if sub.exists():
                yield from sub.rglob(".env")


# ---------------------------------------------------------------------------
# Per-tool sync
# ---------------------------------------------------------------------------


def _sync_qwen(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Update ~/.qwen/settings.json with Agnes key (OpenAI-compatible)."""
    if not agnes_key:
        return []
    path = TOOLS["qwen"]
    data = _read_json(path)
    # Add AGNES_API_KEY to env section
    if "env" not in data:
        data["env"] = {}
    # Use a stable env key name for Agnes (OpenAI-compatible endpoint)
    env_key_name = "AGNES_API_KEY"
    data["env"][env_key_name] = agnes_key
    # Ensure modelProviders has an openai entry for agnes
    providers = data.setdefault("modelProviders", {})
    openai_providers = providers.setdefault("openai", [])
    # Check if agnes provider already exists
    agnes_exists = any(
        p.get("baseUrl") == os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
        for p in openai_providers
    )
    if not agnes_exists:
        openai_providers.append(
            {
                "id": "agnes-image-2.1-flash",
                "name": "Agnes AI",
                "baseUrl": os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1"),
                "envKey": env_key_name,
            }
        )
    data.setdefault("security", {}).setdefault("auth", {})["selectedType"] = "openai"
    _write_json(path, data)
    return [f"qwen → {path}"]


def _sync_claude(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Create ~/.claude/settings.json with brandly API keys in env section."""
    if not agnes_key and not minimax_key:
        return []
    path = TOOLS["claude"]
    data = _read_json(path)
    if "env" not in data:
        data["env"] = {}
    if agnes_key and "AGNES_API_KEY" not in data["env"]:
        data["env"]["AGNES_API_KEY"] = agnes_key
    if minimax_key and "MINIMAX_API_KEY" not in data["env"]:
        data["env"]["MINIMAX_API_KEY"] = minimax_key
    _write_json(path, data)
    added = []
    if agnes_key:
        added.append("AGNES_API_KEY")
    if minimax_key:
        added.append("MINIMAX_API_KEY")
    return [f"claude → {path} ({', '.join(added)})"]


def _sync_gemini(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Update ~/.gemini/settings.json — store keys in env section."""
    keys_added = []
    path = TOOLS["gemini"]
    data = _read_json(path)
    if "env" not in data:
        data["env"] = {}
    if agnes_key and "AGNES_API_KEY" not in data["env"]:
        data["env"]["AGNES_API_KEY"] = agnes_key
        keys_added.append("AGNES_API_KEY")
    if minimax_key and "MINIMAX_API_KEY" not in data["env"]:
        data["env"]["MINIMAX_API_KEY"] = minimax_key
        keys_added.append("MINIMAX_API_KEY")
    if keys_added:
        _write_json(path, data)
    return [f"gemini → {path} ({', '.join(keys_added)})"] if keys_added else []


def _sync_codex(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Update ~/.codex/config.toml with AGNES as an OpenAI-compatible provider."""
    if not agnes_key:
        return []
    path = TOOLS["codex"]
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    # Check if AGNES entry already exists
    already_has = any("AGNES_API_KEY" in line for line in lines)
    if already_has:
        return []
    # Append [env] section if not present, then add the key
    new_lines = list(lines)
    if not any(line.startswith("[env]") for line in new_lines):
        new_lines.append("")
        new_lines.append("[env]")
    new_lines.append('OPENAI_API_KEY = "{AGNES_API_KEY}"')
    new_lines.append(
        f'OPENAI_BASE_URL = "{os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")}"'
    )
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return [f"codex → {path}"]


def _sync_pi(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Update ~/.pi/agent/auth.json with agnes and minimax providers."""
    added = []
    path = TOOLS["pi"]
    if not path.exists():
        return []
    data = _read_json(path)
    if agnes_key:
        data["agnes"] = {"type": "api_key", "key": agnes_key}
        added.append("agnes")
    if minimax_key:
        data["minimax"] = {"type": "api_key", "key": minimax_key}
        added.append("minimax")
    if added:
        _write_json(path, data)
    return [f"pi → {path} ({', '.join(added)})"] if added else []


def _sync_opencode(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Write ~/.opencode.json with agnes and minimax providers."""
    if not agnes_key and not minimax_key:
        return []
    path = TOOLS["opencode"]
    data = _read_json(path)
    providers = data.setdefault("providers", {})
    if agnes_key:
        providers["openai"] = {
            "apiKey": agnes_key,
            "baseUrl": os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1"),
            "disabled": False,
        }
    if minimax_key:
        providers["minimax"] = {
            "apiKey": minimax_key,
            "baseUrl": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1"),
            "disabled": False,
        }
    _write_json(path, data)
    targets = []
    if agnes_key:
        targets.append("openai(agnes)")
    if minimax_key:
        targets.append("minimax")
    return [f"opencode → {path}"] if targets else []


def _sync_dotenvs(agnes_key: str | None, minimax_key: str | None) -> list[str]:
    """Write keys to any .env files found in project/home directories."""
    added = []
    keys = {}
    if agnes_key:
        keys["AGNES_API_KEY"] = agnes_key
    if minimax_key:
        keys["MINIMAX_API_KEY"] = minimax_key
    if not keys:
        return []
    for env_path in _scan_for_dotenvs():
        _append_to_dotenv(env_path, keys)
        added.append(str(env_path))
    return [f".env → {p}" for p in added] if added else []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SYNC_HANDLERS = {
    "qwen": _sync_qwen,
    "claude": _sync_claude,
    "gemini": _sync_gemini,
    "codex": _sync_codex,
    "pi": _sync_pi,
    "opencode": _sync_opencode,
}


def detect_tools() -> dict[str, bool]:
    """Return {tool_name: exists} for all known tool config paths."""
    return {name: path.exists() for name, path in TOOLS.items()}


def sync_keys(
    tools: list[str] | None = None,
    include_dotenv: bool = True,
    *,
    legacy_provider_keys: bool = False,
) -> list[str]:
    """Sync AGNES_API_KEY and MINIMAX_API_KEY into detected tool configs.

    Since the agent-native surface landed (Goal 1), writing raw provider keys into
    AI-tool configs is **opt-in** (audit F2: handing agents direct provider access
    made them bypass the pipeline). By default nothing secret is written; callers
    are pointed at ``brandly mcp serve`` / ``brandly tools --json`` instead.

    Returns a list of human-readable messages describing what was updated.
    """
    if not legacy_provider_keys:
        return [
            "Provider keys NOT written (safe default). Drive AI tools through "
            "`brandly mcp serve` or `brandly tools --json` instead. To restore the "
            "old behaviour run: brandly sync --legacy-provider-keys"
        ]

    agnes_key = os.getenv(AGNES_ENV_KEY)
    minimax_key = os.getenv(MINIMAX_ENV_KEY)

    if not agnes_key and not minimax_key:
        return ["No API keys found in environment (AGNES_API_KEY, MINIMAX_API_KEY)."]

    selected = tools if tools else list(SYNC_HANDLERS.keys())
    results: list[str] = []
    for tool in selected:
        handler = SYNC_HANDLERS.get(tool)
        if not handler:
            continue
        msgs = handler(agnes_key, minimax_key)
        results.extend(msgs)

    if include_dotenv:
        results.extend(_sync_dotenvs(agnes_key, minimax_key))

    return results if results else ["No tool configs found to update."]
