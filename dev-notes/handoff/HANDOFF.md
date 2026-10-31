# Handoff — brandly-cli web server security hardening

**Session:** 2026-10-31  
**Branch:** `main` (all changes committed)  
**Last commit:** `2dbc8b8` (security fixes) + rate-limiting spec added (uncommitted spec file only)

---

## Summary of work completed

Three high-priority security findings from the teammate analysis were fixed:

### 1. Token leaked in browser URL (`server.py`)
- `start_server()` now opens `http://127.0.0.1:8765/` instead of `/?token={token}`
- SPA index route (`/` and `/index.html`) sets a same-site `brandly_token` cookie (`httponly`, `samesite=lax`, `path=/`)
- `app.state.brandly_token` set in `create_app()` and read by the SPA route

### 2. Loopback API open without token (`security.py`)
- `LocalGuardMiddleware._token_from_scope()` now checks: query string → `x-brandly-token` header → `brandly_token` cookie
- Token required on all `/api` and `/ws` paths when app created with a token
- `create_app(root=..., token=None)` remains unauthenticated (test-only)

### 3. Errors masked as HTTP 200 (`routes/timeline.py`, `routes/clips.py`)
- `get_timeline`, `put_timeline`, `regenerate_clip` now raise `HTTPException` (404/400/500) instead of returning `{"error": ...}` with default 200

### Additional fixes in same session
- **Security headers** (`SecurityHeadersMiddleware` in `security.py`): CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` — applied to every response
- **Atomic state saves** (`state.py`): `timeline.json` and `shots.json` now written via temp file + `os.replace()`; no temp files left behind
- **CI vulnerability scanning** (`.github/workflows/ci.yml`): added `pip-audit` step
- **Rate-limiting spec** written at `dev-notes/SECURITY-RATE-LIMITING.md` (not yet implemented — see below)

### Verification
- `ruff check src/ tests/ web/` — 0 errors
- `pytest tests/` — **1692 passed, 1 skipped, 0 failed** (28 security tests + 5 state tests added, all green)

---

## Current state of repo

Working tree: **clean** — all security work committed as `2dbc8b8`.  
One uncommitted file: `dev-notes/SECURITY-RATE-LIMITING.md` (spec only, no code).

Last commit message:
```
fix: web server security — token leak, optional token, masked errors
```

---

## What remains (deferred findings from teammate analysis)

These are lower-priority and were intentionally NOT implemented (per AGENTS.md §0.4 / CONVENTIONS §4 — API contract changes need design specs first):

### A. Rate limiting on generation endpoints (SPEC READY)
- **Spec:** `dev-notes/SECURITY-RATE-LIMITING.md` (complete — token bucket, per-project, 10 req/60s for regenerate, 429 + Retry-After)
- **Status:** Not implemented. Code is in `security.py` where `LocalGuardMiddleware` and `SecurityHeadersMiddleware` live — add a `RateLimitMiddleware` there and register in `create_app()`
- **RED tests:** Not yet written — write them per CONVENTIONS §2 before implementing

### B. CSP/security headers — DONE (see above)
### C. Atomic saves — DONE (see above)
### D. Vulnerability scanning in CI — DONE (see above)

### E. Still out of scope (no spec exists)
- Data-schema migration for `project.json`/`timeline.json`
- JS test runner for SPA (issue #61 open)
- Rate limiting on read-only endpoints
- Persistent rate-limit state across server restarts

---

## Key files touched

| File | Change |
|------|--------|
| `src/brandly_cli/web/server.py` | start_server URL fix; cookie on SPA route; `SecurityHeadersMiddleware` registered; `app.state.brandly_token` |
| `src/brandly_cli/web/security.py` | cookie token source; `SecurityHeadersMiddleware` class |
| `src/brandly_cli/web/routes/timeline.py` | `HTTPException` instead of error-body-200 |
| `src/brandly_cli/web/routes/clips.py` | `HTTPException` instead of error-body-200 |
| `src/brandly_cli/web/state.py` | atomic `_write_atomic()` for timeline.json + shots.json |
| `.github/workflows/ci.yml` | added `pip-audit` step |
| `dev-notes/SECURITY.md` | added §1.5 Web Server Security threat model |
| `dev-notes/SPEC.md` | added §7.1 Web API error contract |
| `dev-notes/SECURITY-RATE-LIMITING.md` | NEW — rate limiting spec (unimplemented) |
| `tests/test_web_security.py` | +28 tests (token, cookie, headers, status codes) |
| `tests/test_web_state.py` | NEW — 5 atomic-save tests |
| `tests/test_web_sync.py` | updated failed-regenerate test to expect 500 |

---

## How to resume

1. `cd /home/dimona/Dream-Pixels-Forge/Dev/cli/brandly-cli`
2. Review `dev-notes/SECURITY-RATE-LIMITING.md` for the rate-limiting design
3. Write RED tests in `tests/test_web_security.py` (add a `TestRateLimiting` class)
4. Implement `RateLimitMiddleware` in `src/brandly_cli/web/security.py` and register in `create_app()`
5. Run gates: `ruff check src/ tests/` and `pytest tests/`
6. Commit on `main`

Relevant existing test patterns to copy: `TestSecurityHeaders`, `TestCookieToken`, `TestErrorStatusCodes` in `test_web_security.py`.
