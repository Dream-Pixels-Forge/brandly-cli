"""Style preset helpers — apply cinematic/photorealistic boosts to prompts."""

from __future__ import annotations

from typing import Literal

from brandly_cli.constants import STYLE_CONFIG, STYLE_PRESET_OPTIONS, StylePreset

#: Media type selector for choosing the right cinematic variant.
MediaMode = Literal["video", "still"]


def apply_style_preset(
    prompt: str,
    preset: StylePreset | str,
    *,
    media: MediaMode = "video",
) -> str:
    """Append style suffix to a prompt.

    When ``media='still'`` and the preset has a ``prompt_suffix_still`` key
    (currently only ``cinematic``), that variant is used instead — it omits
    motion-specific language and emphasises sharp still-photography detail.
    """
    if preset is None or preset == "none":
        return prompt
    config = STYLE_CONFIG.get(preset)  # type: ignore[call-overload]
    if not config:
        return prompt
    # Still-image variant (cinematic photo vs cinematic live-action video)
    if media == "still" and "prompt_suffix_still" in config:
        suffix = config["prompt_suffix_still"]
    else:
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
