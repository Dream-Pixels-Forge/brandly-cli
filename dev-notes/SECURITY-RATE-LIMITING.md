# Rate Limiting — brandly timeline web server

## Problem
The `/api/projects/{project_id}/clips/{clip_id}/regenerate` endpoint triggers paid AI video generation. A malicious local process (or a compromised SPA) could spam this endpoint and burn credits rapidly. No rate limiting exists today.

## Scope
In scope:
- Rate limit the clip regenerate endpoint (`POST /api/projects/{project_id}/clips/{clip_id}/regenerate`)
- Return HTTP 429 when the limit is exceeded, with a `Retry-After` header
- Per-project tracking (different projects have independent counters)

Out of scope:
- Rate limiting read-only endpoints (GET /timeline, GET /health, etc.) — these don't spend credits
- Distributed rate limiting (single local server instance)
- Persistent rate-limit state across server restarts (in-memory is fine for a local tool)

## Design

### Rate limit algorithm
Token bucket per `(project_id, endpoint)` pair, in-memory.

### Default limits
| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /api/projects/{id}/clips/{clip_id}/regenerate` | 10 requests | 60 seconds |
| All other `POST/PUT/PATCH` /api endpoints | 60 requests | 60 seconds |
| `GET` /api endpoints | 120 requests | 60 seconds |

### Response on limit exceeded
HTTP 429 with body `{"detail": "Rate limit exceeded. Retry after N seconds."}` and header `Retry-After: N`.

### Implementation
A `RateLimitMiddleware` in `src/brandly_cli/web/security.py` that:
1. Extracts `project_id` from the request path
2. Looks up the token bucket for `(project_id, endpoint_category)`
3. Allows or rejects with 429 + `Retry-After`
4. Does not apply to `/health`, `/static`, `/` (SPA), or `/ws` (WebSocket — connection-based, not request-based)

### Configuration
Limits are hardcoded constants (not user-configurable) for v1. The middleware is added to the FastAPI app in `create_app()` after `LocalGuardMiddleware`.

## Verification
- Test that 10 regenerate requests within 60s are allowed, the 11th returns 429
- Test that `Retry-After` header is present on 429
- Test that different projects have independent counters
- Test that GET endpoints have a higher limit
- Test that `/health` is not rate limited
