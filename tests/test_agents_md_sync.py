"""Tests for agent onboarding (Goal 1, PR 3).

* ``brandly init`` writes an ``AGENTS.md`` that points agents at the tool surface
  (manifest + MCP) instead of raw provider HTTP — audit F1's counterpart on disk.
* ``brandly sync`` no longer writes provider keys by default (audit F2): the raw-key
  behaviour must be explicitly requested via ``--legacy-provider-keys``.

Written test-first (RED) — see dev-notes/GOAL-AGENTIC-PIPELINE.md Goal 1.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from brandly_cli import agent_surface
from brandly_cli import sync as sync_mod
from brandly_cli.cli import cli


def _init(root: Path) -> object:
    return CliRunner().invoke(
        cli, ["--root", str(root), "init", "--name", "Acme", "--idea", "a widget"]
    )


# ---------------------------------------------------------------------------
# AGENTS.md on init
# ---------------------------------------------------------------------------


class TestInitWritesAgentsMd:
    def test_init_creates_agents_md_pointing_at_the_tool_surface(self, tmp_path: Path) -> None:
        result = _init(tmp_path)
        assert result.exit_code == 0, result.output
        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text(encoding="utf-8")
        assert "brandly tools --json" in content
        assert "brandly mcp serve" in content
        assert "produce" in content

    def test_init_never_overwrites_an_existing_agents_md(self, tmp_path: Path) -> None:
        existing = tmp_path / "AGENTS.md"
        existing.write_text("# MY OWN INSTRUCTIONS — do not touch\n", encoding="utf-8")
        result = _init(tmp_path)
        assert result.exit_code == 0, result.output
        assert existing.read_text(encoding="utf-8") == "# MY OWN INSTRUCTIONS — do not touch\n"

    def test_agents_md_contains_no_secrets_or_provider_endpoints(self, tmp_path: Path) -> None:
        result = _init(tmp_path)
        assert result.exit_code == 0, result.output
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "AGNES_API_KEY" not in content
        assert "MINIMAX_API_KEY" not in content
        assert "apihub" not in content

    def test_agents_md_lists_every_read_only_tool(self, tmp_path: Path) -> None:
        result = _init(tmp_path)
        assert result.exit_code == 0, result.output
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        for entry in agent_surface.tool_manifest()["tools"]:
            if entry["read_only"]:
                assert entry["name"] in content, f"{entry['name']} missing from AGENTS.md"


# ---------------------------------------------------------------------------
# brandly sync: no raw keys by default
# ---------------------------------------------------------------------------


class TestSyncDoesNotWriteKeysByDefault:
    def test_default_writes_no_tool_configs_and_no_dotenv(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fake_tools = {"opencode": tmp_path / "cfg" / "opencode.json"}
        monkeypatch.setattr(sync_mod, "TOOLS", fake_tools)
        monkeypatch.setattr(sync_mod, "HOME", tmp_path)
        monkeypatch.setattr(sync_mod, "_scan_for_dotenvs", lambda *a, **k: iter(()))
        monkeypatch.setenv("AGNES_API_KEY", "super-secret")
        monkeypatch.setenv("MINIMAX_API_KEY", "super-secret-2")

        messages = sync_mod.sync_keys()

        assert not fake_tools["opencode"].exists(), "default sync must not write provider keys"
        assert any("legacy-provider-keys" in m for m in messages), messages

    def test_legacy_flag_restores_the_key_writing_behaviour(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fake_tools = {"opencode": tmp_path / "cfg" / "opencode.json"}
        monkeypatch.setattr(sync_mod, "TOOLS", fake_tools)
        monkeypatch.setattr(sync_mod, "HOME", tmp_path)
        monkeypatch.setattr(sync_mod, "_scan_for_dotenvs", lambda *a, **k: iter(()))
        monkeypatch.setenv("AGNES_API_KEY", "super-secret")

        messages = sync_mod.sync_keys(["opencode"], legacy_provider_keys=True)

        assert fake_tools["opencode"].exists()
        assert "super-secret" in fake_tools["opencode"].read_text(encoding="utf-8")
        assert messages

    def test_cli_exposes_the_legacy_flag(self) -> None:
        result = CliRunner().invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0, result.output
        assert "--legacy-provider-keys" in result.output

    def test_cli_default_does_not_write(self, tmp_path: Path, monkeypatch) -> None:
        fake_tools = {"opencode": tmp_path / "cfg" / "opencode.json"}
        monkeypatch.setattr(sync_mod, "TOOLS", fake_tools)
        monkeypatch.setattr(sync_mod, "HOME", tmp_path)
        monkeypatch.setattr(sync_mod, "_scan_for_dotenvs", lambda *a, **k: iter(()))
        monkeypatch.setenv("AGNES_API_KEY", "super-secret")

        result = CliRunner().invoke(cli, ["sync"], env={"AGNES_API_KEY": "super-secret"})

        assert result.exit_code == 0, result.output
        assert not fake_tools["opencode"].exists()


# ---------------------------------------------------------------------------
# README claim (G5 alignment: docs must match shipped behaviour)
# ---------------------------------------------------------------------------


class TestReadmeAgentDocs:
    def test_readme_documents_the_agent_tool_surface(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        assert "Driving brandly from an AI tool" in readme
        assert "brandly mcp serve" in readme
        assert "brandly tools --json" in readme
