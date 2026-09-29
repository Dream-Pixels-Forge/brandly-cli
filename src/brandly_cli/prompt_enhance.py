"""Opt-in LLM prompt enhancement (issue #170).

Renders the already-assembled deterministic prompt through ONE Agnes text
model polish pass with a preservation contract:

- subject / product / character and every concrete instruction must survive,
- every ``<Picture N>`` / ``<Audio N>`` reference-binding token must survive,
- aspect-ratio, duration and style statements must survive.

All failures (API error, malformed/empty response, lost binding token) are
fail-open: ``None`` is returned and the caller keeps the deterministic
prompt. The feature is opt-in via ``brandly image --llm-enhance`` /
``brandly video --llm-enhance`` and never changes default behavior.
"""

from __future__ import annotations

import re

from brandly_cli.agnes_client import DEFAULT_TEXT_MODEL, chat_completion

#: Reference-binding tokens injected by the reference pipeline (issue #158).
BINDING_TOKEN_RE = re.compile(r"<(?:Picture|Audio) \d+>")

SYSTEM_PROMPT = (
    "You are a prompt editor for an AI image/video generation model.\n"
    "Rewrite the user's prompt to enrich cinematography, lighting, texture, "
    "material and motion prose.\n"
    "Hard rules (never violate):\n"
    "- Keep the subject, product, character and every concrete instruction intact.\n"
    "- Keep every <Picture N> and <Audio N> token exactly as written, unchanged.\n"
    "- Keep aspect-ratio, duration and style statements intact.\n"
    "- Output ONLY the rewritten prompt text: no preamble, no quotes, no explanations."
)


async def llm_enhance_prompt(
    prompt: str,
    *,
    model: str | None = None,
    context: str = "",
) -> str | None:
    """Return the enhanced prompt, or ``None`` to signal fallback.

    Fail-open: every error path returns ``None``; never raises.
    """
    user = prompt if not context else f"{prompt}\n\nContext:\n{context}"
    try:
        data = await chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            model=model or DEFAULT_TEXT_MODEL,
        )
    except Exception:
        return None
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(text, str) or not text.strip():
        return None
    text = text.strip()
    original_tokens = set(BINDING_TOKEN_RE.findall(prompt))
    if original_tokens and not original_tokens <= set(BINDING_TOKEN_RE.findall(text)):
        return None
    return text
