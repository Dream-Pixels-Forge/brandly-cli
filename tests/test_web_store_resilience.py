"""Contract tests for store.ts fetch resilience.

RED test: ``store.ts`` parses every fetch Response with ``res.json()``
directly. When the Vite dev proxy runs without the Python backend
(``brandly timeline`` not started), the proxy answers with an empty body
and ``res.json()`` throws the cryptic ``SyntaxError: Failed to execute
'json' on 'Response': Unexpected end of JSON input`` — surfaced to the
user as ``Failed to load projects: SyntaxError: ...``.

These tests pin the resilience contract at source level (no JS test
runner in CI — see #61):

1. ``store.ts`` must not call ``res.json()`` directly on fetch Responses.
2. ``store.ts`` must guard non-OK responses (``res.ok`` check) and
   surface the server's ``detail`` message when present.
3. ``store.ts`` must guard empty bodies with a readable error that tells
   the user how to start the backend.
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestFetchResilienceContract:
    def test_store_does_not_call_res_json_directly(self) -> None:
        store = _read("store.ts")
        assert "await res.json()" not in store, (
            "store.ts parses Responses with res.json() directly — an empty "
            "body (dev proxy without backend) throws a cryptic SyntaxError"
        )

    def test_store_checks_res_ok_before_parsing(self) -> None:
        store = _read("store.ts")
        assert "res.ok" in store, (
            "store.ts never checks res.ok — non-OK responses are parsed as JSON"
        )

    def test_store_surfaces_readable_empty_body_error(self) -> None:
        store = _read("store.ts")
        assert "Empty response" in store, (
            "store.ts has no readable error for empty response bodies"
        )
        assert "brandly timeline" in store, (
            "the empty-body error must tell the user how to start the backend"
        )

    def test_store_surfaces_server_detail_on_non_ok(self) -> None:
        store = _read("store.ts")
        assert "detail" in store, (
            "store.ts drops the server's detail message on non-OK responses"
        )
