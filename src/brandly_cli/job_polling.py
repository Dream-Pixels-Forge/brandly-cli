"""Shared job/tool-result plumbing for agent tool-calling.

Breaks the former ``agent_tools <-> agnes_client`` import cycle: both the
agent tool registry and the Agnes agent loop need the same result
serialization, so it lives here — one-directional arrows only:

    agent_tools  ->  job_polling  (tool-result serialization)
    agnes_client ->  job_polling  (tool-loop payload serialization)

``agent_tools`` may still call provider APIs (e.g. ``agnes_client.list_jobs``);
the reverse direction no longer exists.
"""

from __future__ import annotations

import json
from typing import Any


def to_json(value: Any) -> str:
    """Stringify a tool result for feeding back to the LLM."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
