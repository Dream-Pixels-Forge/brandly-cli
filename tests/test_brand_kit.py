"""G7 PR 1 (DEV-G7-001/002/003 confirmed): brand-kit model + `brandly brand`
command group + prompt-layer brand lock.

Anti-drift rules under test:
* ``brand.json`` lives only in the project dir (never user config — F2 rule);
* ``brand verify`` fails closed on malformed kits;
* a style conflicting with the kit's ``style_lock`` is rejected;
* the prompt suffix pins the palette + claim allowlist and bans third-party
  marks;
* capability row stays honest: ``brand_kit`` = partial (gate/export layers
  ship in G7 PR 2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import capabilities as caps_mod
from brandly_cli.brand_kit import (
    BrandKit,
    BrandLockConflict,
    apply_brand_lock,
    brand_constraints,
    load_brand_kit,
    parse_brand_kit,
    save_brand_kit,
)
from brandly_cli.cli import cli


def _kit(**overrides) -> BrandKit:
    raw = {
        "version": 1,
        "logo": "",
        "colors": ["#123456", "#ABCDEF"],
        "claims": ["Save 30% today"],
        "style_lock": "cinematic",
        "overlay": {"corner": "bottom-right", "safe_zone": 0.1, "opacity": 1.0},
    }
    raw.update(overrides)
    return parse_brand_kit(raw)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal project tree (same shape as test_publish)."""
    monkeypatch.setenv("BRANDLY_CONFIG_DIR", str(tmp_path / "config"))
    proj_dir = tmp_path / ".brandly" / "test-proj"
    proj_dir.mkdir(parents=True)
    (proj_dir / "project.json").write_text('{"id": "test-proj", "name": "t"}')
    return tmp_path


class TestKitModel:
    def test_roundtrip(self) -> None:
        kit = _kit()
        assert kit.colors == ("#123456", "#ABCDEF")
        assert kit.claims == ("Save 30% today",)
        assert kit.style_lock == "cinematic"
        assert kit.overlay.corner == "bottom-right"

    def test_invalid_hex_rejected(self) -> None:
        with pytest.raises(ValueError):
            _kit(colors=["not-a-color"])

    def test_unknown_style_rejected(self) -> None:
        with pytest.raises(ValueError):
            _kit(style_lock="watercolour")

    def test_empty_claims_rejected(self) -> None:
        with pytest.raises(ValueError):
            _kit(claims=[])

    def test_bad_overlay_bounds_rejected(self) -> None:
        with pytest.raises(ValueError):
            _kit(overlay={"corner": "middle", "safe_zone": 0.1, "opacity": 1.0})
        with pytest.raises(ValueError):
            _kit(overlay={"corner": "top-left", "safe_zone": 0.5, "opacity": 1.0})
        with pytest.raises(ValueError):
            _kit(overlay={"corner": "top-left", "safe_zone": 0.1, "opacity": 1.5})


class TestPersistence:
    def test_save_load(self, project: Path) -> None:
        proj_dir = project / ".brandly" / "test-proj"
        kit = _kit()
        path = save_brand_kit(proj_dir, kit)
        assert path == proj_dir / "brand.json"
        loaded = load_brand_kit(proj_dir)
        assert loaded is not None and loaded.claims == kit.claims

    def test_load_missing_is_none(self, project: Path) -> None:
        proj_dir = project / ".brandly" / "test-proj"
        assert load_brand_kit(proj_dir) is None

    def test_kit_stays_in_project_dir(self, project: Path) -> None:
        save_brand_kit(project / ".brandly" / "test-proj", _kit())
        assert not (project / "brand.json").exists()


class TestPromptLock:
    def test_suffix_pins_palette_and_bans_marks(self) -> None:
        suffix = brand_constraints(_kit())
        assert "#123456" in suffix.upper()
        assert "third-party" in suffix.lower()
        assert "Save 30% today" in suffix

    def test_conflicting_style_rejected(self) -> None:
        with pytest.raises(BrandLockConflict):
            apply_brand_lock("a hero shot", _kit(), style="documentary")

    def test_matching_style_appends_lock(self) -> None:
        kit = _kit()
        out = apply_brand_lock("a hero shot", kit, style="cinematic")
        assert out.startswith("a hero shot")
        assert brand_constraints(kit) in out

    def test_omitted_style_appends_lock(self) -> None:
        out = apply_brand_lock("a hero shot", _kit())
        assert brand_constraints(_kit()) in out


class TestBrandCli:
    def test_init_writes_brand_json(self, project: Path) -> None:
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(cli, [
            "brand", "init", "test-proj",
            "--color", "#123456", "--color", "#ABCDEF",
            "--claim", "Save 30% today",
            "--style", "cinematic",
        ])
        assert result.exit_code == 0, result.output
        kit = load_brand_kit(project / ".brandly" / "test-proj")
        assert kit is not None
        assert kit.claims == ("Save 30% today",)

    def test_verify_passes_on_valid_kit(self, project: Path) -> None:
        save_brand_kit(project / ".brandly" / "test-proj", _kit())
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(cli, ["brand", "verify", "test-proj"])
        assert result.exit_code == 0, result.output

    def test_verify_fails_closed_on_bad_hex(self, project: Path) -> None:
        (project / ".brandly" / "test-proj" / "brand.json").write_text(json.dumps({
            "version": 1, "logo": "", "colors": ["oops"],
            "claims": ["x"], "style_lock": "cinematic",
            "overlay": {"corner": "bottom-right", "safe_zone": 0.1, "opacity": 1.0},
        }))
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(cli, ["brand", "verify", "test-proj"])
        assert result.exit_code != 0

    def test_show_json(self, project: Path) -> None:
        save_brand_kit(project / ".brandly" / "test-proj", _kit())
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(cli, ["brand", "show", "test-proj", "--json"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["style_lock"] == "cinematic"

    def test_missing_project_fails(self, project: Path) -> None:
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(cli, ["brand", "verify", "no-such-proj"])
        assert result.exit_code != 0


class TestCapabilityRow:
    def test_brand_kit_partial_with_brand_command(self) -> None:
        row = next(c for c in caps_mod.CAPABILITIES if c["id"] == "brand_kit")
        assert row["status"] == "partial"
        assert row.get("command") == "brand"

