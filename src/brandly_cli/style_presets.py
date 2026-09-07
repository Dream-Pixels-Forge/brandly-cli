"""Style preset helpers — apply cinematic/photorealistic boosts to prompts."""

from __future__ import annotations

from brandly_cli.constants import STYLE_CONFIG, STYLE_PRESET_OPTIONS, StylePreset


def apply_style_preset(prompt: str, preset: StylePreset | str) -> str:
    """Append style suffix to a prompt."""
    if preset is None or preset == "none":
        return prompt
    config = STYLE_CONFIG.get(preset)  # type: ignore[call-overload]
    if not config:
        return prompt
    suffix = config.get("prompt_suffix", "")
    if not suffix:
        return prompt
    return f"{prompt}{suffix}"


def get_negative_prompt(preset: StylePreset | str) -> str:
    """Return the negative prompt for a style preset."""
    if preset is None or preset == "none":
        return ""
    config = STYLE_CONFIG.get(preset)  # type: ignore[call-overload]
    if not config:
        return ""
    return config.get("negative_prompt", "")


def list_style_presets() -> list[str]:
    """Return available style preset names."""
    return list(STYLE_PRESET_OPTIONS)
