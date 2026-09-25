"""G5: scope truth pass — capability matrix + README claim guard.

The capability list in :mod:`brandly_cli.capabilities` is the single source
of truth: ``brandly capabilities`` renders it, and this test file checks
that the README makes no claim the list does not back. Roadmap lines
carrying a planning marker ("planned", "gap", …) stay allowed; aspirational
claims do not.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from brandly_cli import capabilities as caps_mod
from brandly_cli.cli import cli

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# `brandly capabilities` command
# ---------------------------------------------------------------------------


class TestCapabilitiesCommand:
    def test_json_exits_0_and_lists_every_persona(self) -> None:
        result = CliRunner().invoke(cli, ["capabilities", "--json"])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.output)
        assert "capabilities" in doc and doc["capabilities"]
        for persona in caps_mod.PERSONAS:
            assert any(c["persona"] == persona for c in doc["capabilities"])

    def test_text_rendering_exits_0(self) -> None:
        result = CliRunner().invoke(cli, ["capabilities"])
        assert result.exit_code == 0, result.output
        assert "supported" in result.output.lower()

    def test_statuses_are_valid(self) -> None:
        for cap in caps_mod.CAPABILITIES:
            assert cap["status"] in caps_mod.STATUSES, cap["id"]

    def test_supported_rows_name_real_commands(self) -> None:
        # Force the lazy CLI registration, then check the command surface.
        CliRunner().invoke(cli, ["capabilities", "--json"])
        known = set(cli.commands)
        for cap in caps_mod.CAPABILITIES:
            if cap["status"] == "supported" and cap.get("command"):
                assert cap["command"] in known, f"{cap['id']} -> {cap['command']!r}"


# ---------------------------------------------------------------------------
# README claim guard (checked against the capability list)
# ---------------------------------------------------------------------------


class TestReadmeClaimGuard:
    def _banned_pairs(self) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for cap in caps_mod.CAPABILITIES:
            if cap["status"] in ("absent", "partial"):
                for phrase in cap.get("banned_claims", ()):
                    pairs.append((cap["id"], phrase))
        return pairs

    def test_readme_makes_no_unbacked_claims(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        offenders: list[tuple[str, str, str]] = []
        for cap_id, phrase in self._banned_pairs():
            for line in readme.splitlines():
                if phrase.lower() not in line.lower():
                    continue
                if not any(m in line.lower() for m in caps_mod.PLANNING_MARKERS):
                    offenders.append((cap_id, phrase, line.strip()))
        assert not offenders, f"unbacked README claims: {offenders}"

    def test_readme_links_the_gap_register(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        # The audit file is the single source of truth for open gaps.
        assert "AUDIT-AGENTIC-PIPELINE" in readme
        assert "brandly capabilities" in readme.lower() or "capabilities" in readme.lower()
