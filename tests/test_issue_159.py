"""Issue #159: agnes-3.0-flash belongs in the Agnes text model catalog.

Specs per vault doc (raw/Agnes Docs/Agnes 3.0 Flash.md, clipped 2026-09-29):
512K context, 65,536 max output tokens, text + image-URL input, $0 pricing.
DEFAULT_TEXT_MODEL must stay on 2.5-flash until tool calling is verified.
"""

from __future__ import annotations

from click.testing import CliRunner

from brandly_cli.agnes_client import DEFAULT_TEXT_MODEL, list_text_models
from brandly_cli.cli import cli


class TestAgnes3Catalog:
    def test_list_text_models_includes_agnes_3(self) -> None:
        models = {m["id"]: m for m in list_text_models()}
        assert "agnes-3.0-flash" in models
        assert models["agnes-3.0-flash"]["context"] == "512K"
        assert models["agnes-3.0-flash"]["max_output"] == "65.5K"

    def test_default_stays_on_2_5(self) -> None:
        assert DEFAULT_TEXT_MODEL == "agnes-2.5-flash"

    def test_cli_list_models_shows_agnes_3(self) -> None:
        result = CliRunner().invoke(cli, ["agnes-chat", "irrelevant", "--list-models"])
        assert result.exit_code == 0
        assert "agnes-3.0-flash" in result.output
