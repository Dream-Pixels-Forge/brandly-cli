"""Issue #148: 503 misclassified in both directions.

Live probes (2026-09-29, apihub.agnes-ai.com):

- POST /v1/videos with a bogus model -> 503::

      {"error": {"code": "model_not_found",
       "message": "No available channel for model X under group default
       (distributor) (request id: ...)", "type": "AgnesAI_error"}}

  ``model_not_found`` is gateway ROUTING state, not proof of a bad model
  name — a channel outage for a *correct* model produces the same body.
- The real 400 body is top-level ``{"code": "invalid_request", ...}``
  (``error.code`` is never present there) and ``error.code`` can be an
  ``int`` (404 probe).

Fix: normalize error bodies (``_parse_error_body``), classify them, and
disambiguate routing-class 503s against ``GET /v1/models`` — in catalog =>
transient, not in catalog => permanent with the catalog in the message.
Catalog fetch failure fails open to transient.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from brandly_cli import agnes_client
from brandly_cli.agnes_client import _retry_with_backoff

ROUTING_503_BODY = json.dumps(
    {
        "error": {
            "code": "model_not_found",
            "message": (
                "No available channel for model bogus-model-xyz under group "
                "default (distributor) "
                "(request id: 202609291259349933444972C6mSbpM)"
            ),
            "type": "AgnesAI_error",
        }
    }
)

TOP_LEVEL_400_BODY = json.dumps(
    {
        "code": "invalid_request",
        "message": "size must be one of [480P, 720P, 1080P]",
        "data": {"field": "size"},
    }
)

CATALOG = ["agnes-video-2.5-flash", "agnes-image-2.1-flash"]


def _status_error(status: int, text: str) -> httpx.HTTPStatusError:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.headers = {}
    return httpx.HTTPStatusError(
        f"HTTP {status}", request=MagicMock(), response=resp
    )


def _flaky(status: int, text: str, failures: int) -> tuple:
    """Request func failing `failures` times with (status, text), then OK."""
    calls = {"n": 0}

    async def _req() -> dict:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise _status_error(status, text)
        return {"ok": True}

    return _req, calls


def _console_out(console: MagicMock) -> str:
    return " ".join(str(c) for c in console.print.call_args_list)


# ---------------------------------------------------------------------------
# _parse_error_body — every observed shape, no silent AttributeError
# ---------------------------------------------------------------------------


class TestParseErrorBody:
    def test_nested_error_shape(self) -> None:
        parsed = agnes_client._parse_error_body(ROUTING_503_BODY)
        assert parsed["code"] == "model_not_found"
        assert "No available channel" in parsed["message"]
        assert parsed["request_id"] == "202609291259349933444972C6mSbpM"

    def test_top_level_code_shape(self) -> None:
        # The REAL 400 body shape — today's parser only reads error.*.
        parsed = agnes_client._parse_error_body(TOP_LEVEL_400_BODY)
        assert parsed["code"] == "invalid_request"
        assert parsed["message"].startswith("size must be one of")

    def test_int_error_code_is_normalized(self) -> None:
        body = json.dumps({"error": {"code": 404, "message": "task not found"}})
        parsed = agnes_client._parse_error_body(body)
        assert parsed["code"] == "404"

    def test_detail_shape(self) -> None:
        parsed = agnes_client._parse_error_body(json.dumps({"detail": "boom"}))
        assert parsed["code"] is None
        assert parsed["message"] == "boom"

    def test_non_json_body(self) -> None:
        parsed = agnes_client._parse_error_body("<html>503 Service Unavailable</html>")
        assert parsed["code"] is None


# ---------------------------------------------------------------------------
# Routing-class 503 -> consult GET /v1/models
# ---------------------------------------------------------------------------


class Test503CatalogDisambiguation:
    async def test_retried_when_model_in_catalog(self) -> None:
        """A channel outage for a *valid* model must retry, not fail fast."""
        req, calls = _flaky(503, ROUTING_503_BODY, failures=1)
        with patch.object(
            agnes_client, "_model_catalog", new=AsyncMock(return_value=CATALOG)
        ):
            result = await _retry_with_backoff(
                req, max_retries=3, base_delay=0.01, model="agnes-video-2.5-flash"
            )
        assert result == {"ok": True}
        assert calls["n"] == 2

    async def test_permanent_when_model_not_in_catalog(self) -> None:
        """Bogus model: raise on attempt 1, message carries catalog + request id."""
        req, calls = _flaky(503, ROUTING_503_BODY, failures=99)
        console = MagicMock()
        catalog = AsyncMock(return_value=CATALOG)
        with (
            patch.object(agnes_client, "_model_catalog", new=catalog),
            patch.object(agnes_client, "console", console),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await _retry_with_backoff(
                    req, max_retries=3, base_delay=0.01, model="bogus-model-xyz"
                )
        assert calls["n"] == 1  # no retries burned
        out = _console_out(console)
        assert "bogus-model-xyz" in out
        assert "agnes-video-2.5-flash" in out  # available-models hint
        assert "202609291259349933444972C6mSbpM" in out  # request id

    async def test_detail_503_consults_catalog_and_retries_when_known(self) -> None:
        """{'detail': ...} bodies carry no routing verdict -> check the catalog."""
        req, calls = _flaky(503, json.dumps({"detail": "Service Unavailable"}), 1)
        with patch.object(
            agnes_client, "_model_catalog", new=AsyncMock(return_value=CATALOG)
        ) as catalog:
            result = await _retry_with_backoff(
                req, max_retries=3, base_delay=0.01, model="agnes-video-2.5-flash"
            )
        assert result == {"ok": True}
        assert calls["n"] == 2
        assert catalog.await_count == 1

    async def test_detail_503_without_model_fails_open_without_catalog(self) -> None:
        """No model context -> can't disambiguate -> transient, no fetch."""
        req, calls = _flaky(503, json.dumps({"detail": "Service Unavailable"}), 1)
        with patch.object(
            agnes_client, "_model_catalog", new=AsyncMock(return_value=CATALOG)
        ) as catalog:
            result = await _retry_with_backoff(req, max_retries=3, base_delay=0.01)
        assert result == {"ok": True}
        assert calls["n"] == 2
        assert catalog.await_count == 0

    async def test_catalog_fetch_failure_fails_open_to_transient(self) -> None:
        """Can't fetch the model list (docs cause of 503) -> retry, don't fail."""
        req, calls = _flaky(503, ROUTING_503_BODY, failures=1)
        with patch.object(agnes_client, "_model_catalog", new=AsyncMock(return_value=None)):
            result = await _retry_with_backoff(
                req, max_retries=3, base_delay=0.01, model="agnes-video-2.5-flash"
            )
        assert result == {"ok": True}
        assert calls["n"] == 2

    async def test_no_model_arg_fails_open_to_transient(self) -> None:
        """Callers without a model (status poll w/o model_name) still retry."""
        req, calls = _flaky(503, ROUTING_503_BODY, failures=1)
        result = await _retry_with_backoff(req, max_retries=3, base_delay=0.01)
        assert result == {"ok": True}
        assert calls["n"] == 2

    async def test_permanent_503_code_skips_catalog(self) -> None:
        """invalid_request inside a 503 stays permanent without a catalog call."""
        body = json.dumps(
            {"error": {"code": "invalid_request", "message": "bad size"}}
        )
        req, calls = _flaky(503, body, failures=99)
        console = MagicMock()
        catalog = AsyncMock(return_value=CATALOG)
        with (
            patch.object(agnes_client, "_model_catalog", new=catalog),
            patch.object(agnes_client, "console", console),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await _retry_with_backoff(
                    req, max_retries=3, base_delay=0.01, model="m"
                )
        assert calls["n"] == 1
        assert catalog.await_count == 0
        assert "invalid_request" in _console_out(console)
