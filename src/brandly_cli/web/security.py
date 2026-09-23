"""Local-server guards for the timeline API.

``brandly timeline`` serves the editor on loopback only. Two guards keep that
boundary honest:

``safe_join``
    Resolves every filesystem path and refuses anything that escapes the
    directory it was requested from, so a crafted ``clip_path`` or project id
    cannot read or write outside the project.

``LocalGuardMiddleware``
    Rejects non-loopback ``Host``/``Origin`` headers (DNS-rebinding / CSRF from
    a visited web page) and, when a token is configured, requires it on
    ``/api`` and ``/ws`` requests so another local process cannot drive paid
    generation.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

#: Hosts allowed to reach the API (the server binds to 127.0.0.1).
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

#: URL prefixes that expose project data or trigger work.
_GUARDED_PREFIXES = ("/api", "/ws")

_TOKEN_HEADER = b"x-brandly-token"


def new_token() -> str:
    """Return a fresh per-run token for the local server."""
    return secrets.token_urlsafe(24)


def safe_join(base: Path, *parts: str) -> Path | None:
    """Join ``parts`` onto ``base``, or return ``None`` if the result escapes it.

    ``resolve()`` collapses ``..`` and symlinks before the containment check, so
    ``safe_join(root, "..", "secret")`` is refused rather than served.
    """
    try:
        resolved_base = base.resolve()
        candidate = resolved_base.joinpath(*parts).resolve()
    except (OSError, ValueError):
        return None
    if candidate == resolved_base or not candidate.is_relative_to(resolved_base):
        return None
    return candidate


def _host_name(value: str) -> str:
    """Return the host part of a Host/Origin authority (port stripped)."""
    if value.startswith("["):  # IPv6 literal: [::1]:8765
        return value.split("]")[0].lstrip("[")
    return value.rsplit(":", 1)[0] if ":" in value else value


def _is_loopback_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.scheme in ("http", "https") and _host_name(parsed.netloc) in _LOOPBACK_HOSTS


def _token_from_scope(scope: Scope, headers: dict[str, str]) -> str | None:
    query = parse_qs(scope.get("query_string", b"").decode())
    if "token" in query:
        return query["token"][0]
    return headers.get(_TOKEN_HEADER.decode())


class LocalGuardMiddleware:
    """Reject foreign hosts/origins and (optionally) require a token."""

    def __init__(self, app: ASGIApp, *, token: str | None = None) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket") or not self._guarded(scope):
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        host = _host_name(headers.get("host", ""))
        if host not in _LOOPBACK_HOSTS:
            await self._reject(scope, receive, send, 403, "Requests must come from localhost")
            return
        origin = headers.get("origin")
        if origin and not _is_loopback_origin(origin):
            await self._reject(scope, receive, send, 403, "Cross-origin requests are not allowed")
            return
        if self.token and _token_from_scope(scope, headers) != self.token:
            await self._reject(scope, receive, send, 401, "Missing or invalid token")
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _guarded(scope: Scope) -> bool:
        path = scope.get("path", "")
        return path.startswith(_GUARDED_PREFIXES)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, status: int, detail: str) -> None:
        if scope["type"] == "websocket":
            await receive()
            await send({"type": "websocket.close", "code": 1008})
            return
        await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)
