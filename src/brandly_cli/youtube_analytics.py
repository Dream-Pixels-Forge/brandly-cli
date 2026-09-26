"""G8 PR 2 (issue #99): YouTube Analytics API adapter — credential-gated,
dry-run-first (G6 pattern, DEV-G6-001 / DEV-G8-003).

Pulls channel-level real metrics from the YouTube Analytics
``reports:query`` endpoint (read-only) and writes them through the SAME
project-local snapshot store as G8 PR 1 (`brandly metrics import`). No
credential → fail-closed with the exact `brandly config set
youtube:analytics <token>` command; the dry-run path renders the exact
request and never touches the network. TikTok/IG analytics adapters are
planned follow-ups, not in scope (DEV-G8-003).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

#: YouTube Analytics property-report endpoint base.
API_BASE = "https://www.googleapis.com/youtubeAnalytics/v1"

#: Metrics requested for the `reports:query` call (deterministic, versioned).
ANALYTICS_METRICS = "views,likes,estimatedWatchTime,clickThroughRate"

#: The credential key in the user-level store (G6 pattern).
CREDENTIAL_KEY = "youtube:analytics"


class YouTubeAnalyticsAdapter:
    """Pure request builder + live executor (mirrors the G6 `Adapter` shape)."""

    platform = "youtube"

    def build_request(self, property_id: str, *, days: int = 28) -> dict[str, Any]:
        """Build the exact GET request (pure — no I/O)."""
        return {
            "platform": self.platform,
            "method": "GET",
            "endpoint": f"{API_BASE}/properties/{property_id}/reports:query",
            "query_params": {
                "metrics": ANALYTICS_METRICS,
                "dimensions": "day",
                "dateRange": f"-{days}d",
            },
        }

    def execute(self, payload: dict[str, Any], token: str) -> dict[str, Any]:
        """GET the request live. Only called when a credential is present."""
        from urllib.parse import urlencode

        url = payload["endpoint"] + "?" + urlencode(payload["query_params"])
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))


def rows_from_report(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Map a `reports:query` response to the G8 PR 1 row schema (pure).

    Each report row is ``[day, views, likes, estimatedWatchTime,
    clickThroughRate]`` (order follows the requested metrics); the CTR
    arrives as a fraction and is stored as a percentage, matching the
    import schema. Rows are then validated by the same fail-closed
    parser `metrics.import_metrics` uses.
    """
    rows: list[dict[str, Any]] = []
    for report in payload.get("reports", []):
        for row in report.get("rows", []):
            day, views, likes, watch_time, ctr_fraction = (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
            )
            rows.append(
                {
                    "date": str(day),
                    "views": int(views),
                    "likes": int(likes),
                    "watch_time_seconds": int(watch_time),
                    "ctr_pct": round(float(ctr_fraction) * 100.0, 4),
                }
            )
    return rows
