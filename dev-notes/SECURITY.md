# SECURITY — brandly-cli

> **Project:** brandly-cli  
> **Date:** 2026-09-07  
> **Classification:** Low-risk CLI tool (web server adds loopback API surface)

---

## 1. Threat Summary

brandly-cli is a **local CLI tool** that reads API keys from environment variables and forwards them to third-party AI generation providers. It does **not** store credentials or handle user data. The `brandly timeline` command additionally runs a loopback FastAPI server (`127.0.0.1`) serving the Studio SPA and project data — this adds a local network service boundary.

| Threat | Risk | Mitigation |
|--------|------|------------|
| API key leakage via logs | Low | Keys are never printed; only error messages may echo partial URLs |
| API key leakage via `.env` in repo | Low | `.env` is gitignored; `.env.example` contains no real keys |
| Key sync overwrites tool configs | Medium | `brandly sync` reads keys from env and writes to JSON/toml — user-controlled |
| Path traversal via project IDs | Low | `is_valid_project_id()` rejects `../`, `/`, `\`, drive letters, reserved names |
| Malicious artifact URLs | Low | URLs are stored as strings; download uses `httpx` with default TLS |
| FFmpeg supply-chain | Low | `edit.py` calls system `ffmpeg`/`ffprobe`; user must have them installed |
| **Per-run token leaked in browser URL** | High | `start_server` opened `?token={token}` — token lands in browser history, server access logs, and Referer headers |
| **Loopback API open without token** | High | `LocalGuardMiddleware` only enforced auth `if self.token` — no token = any loopback caller reaches `/api`/`/ws` |
| **Errors masked as HTTP 200** | Medium | Routes catch exceptions and return `error`/`ok:false` with HTTP 200, hiding failures from clients |

| Threat | Risk | Mitigation |
|--------|------|------------|
| API key leakage via logs | Low | Keys are never printed; only error messages may echo partial URLs |
| API key leakage via `.env` in repo | Low | `.env` is gitignored; `.env.example` contains no real keys |
| Key sync overwrites tool configs | Medium | `brandly sync` reads keys from env and writes to JSON/toml — user-controlled |
| Path traversal via project IDs | Low | `is_valid_project_id()` rejects `../`, `/`, `\`, drive letters, reserved names |
| Malicious artifact URLs | Low | URLs are stored as strings; download uses `httpx` with default TLS |
| FFmpeg supply-chain | Low | `edit.py` calls system `ffmpeg`/`ffprobe`; user must have them installed |

---

## 1.5 Web Server Security

### 1.5.1 Token contract
- `brandly timeline` generates a fresh per-run token via `security.new_token()`.
- The token is **never** embedded in the browser URL (`?token=...` is prohibited — see §5, fix #1).
- The server sets a same-site `brandly_token` cookie on the initial SPA load; the `LocalGuardMiddleware` validates the token from the cookie, the `x-brandly-token` header, **or** the query string (query string retained for backwards compatibility with existing SPA builds).
- Token validation applies to all `/api` and `/ws` paths; `/`, `/static`, and `/health` remain reachable without a token.

### 1.5.2 Token requirement
- When the app is created with a token (the normal `brandly timeline` path), the token is **required** on all guarded paths — no opt-out per request.
- `create_app(root=..., token=None)` runs in an unauthenticated mode for testing only; production `start_server` always passes a token.

### 1.5.3 Loopback guard
- Non-loopback `Host`/`Origin` are rejected with 403 (DNS-rebinding / CSRF from a visited page).
- The server binds to `127.0.0.1` only.

---

## 2. Secrets Handling

### 2.1 Where Keys Live
| Key | Source | Storage |
|-----|--------|---------|
| `AGNES_API_KEY` | Env var | In-memory only; never written to disk |
| `MINIMAX_API_KEY` | Env var | In-memory only; never written to disk |
| `ARK_API_KEY` | Env var | In-memory only; never written to disk |

### 2.2 Key Sync (`brandly sync`)
The `sync` command writes API keys into configuration files for AI tools:
- `~/.qwen/settings.json`
- `~/.claude/settings.json`
- `~/.gemini/settings.json`
- `~/.codex/config.toml`
- `~/.pi/agent/auth.json`
- `~/.opencode.json`
- `.env` files found in project directories

**Security note:** These tool config files may already contain other secrets. The sync operation uses atomic writes (`write_atomic`) to avoid partial writes, but users should review the resulting files.

### 2.3 What Is NOT Stored
- No API keys are persisted in `.brandly/` project directories
- No keys are logged to stdout/stderr
- No keys are sent to any server other than the configured API endpoints

---

## 3. Input Validation

### 3.1 Project ID Sanitization
`is_valid_project_id()` rejects:
- Empty strings
- Path traversal sequences (`..`, `/`, `\`)
- Windows drive-relative paths (`C:foo`)
- NUL bytes and control characters
- Reserved Windows device names (`con`, `prn`, `aux`, `nul`, `com1-9`, `lpt1-9`)

### 3.2 Prompt Length Limits
- Image prompts: truncated to 1500 chars before API submission
- Video prompts: no hard limit (API handles validation)
- Lyrics: max 3500 chars enforced

### 3.3 FFmpeg Safety
The `edit.py` module validates that input files exist before passing them to FFmpeg. Output paths are user-provided and not sandboxed — users control where files are written.

---

## 4. Dependency Security

| Package | Version | Notes |
|---------|---------|-------|
| `httpx` | >=0.27 | TLS-enabled HTTP client; no known critical CVEs |
| `pydantic` | >=2.0 | Input validation; well-audited library |
| `rich` | >=13.0 | Terminal rendering; no network access |
| `click` | >=8.0 | CLI framework; no network access |
| `python-dotenv` | >=1.0 | Reads `.env` files; trusted source |

Run `pip audit` or `pnpm audit` (via CI) periodically to check for new vulnerabilities.

---

## 5. Recommendations

### Web server
1. **Never embed the per-run token in a browser URL** — it leaks to browser history, server access logs, and Referer headers. Use a same-site cookie or the `x-brandly-token` header instead.
2. **Require the token by default** on all guarded paths when the app is created with a token; `token=None` is a test-only unauthenticated mode.
3. **Return proper HTTP status codes** for errors — never mask failures as HTTP 200 with an `error` body. Use `HTTPException` (400/404/500) so clients can distinguish success from failure.

1. **Rotate API keys** if you suspect any have been exposed in logs or synced configs
2. **Review `~/.qwen/settings.json`** and similar files after running `brandly sync`
3. **Keep FFmpeg updated** — it has had security vulnerabilities in the past
4. **Do not commit `.env` files** — the `.gitignore` already covers this
5. **Consider adding a `--dry-run` flag** to `brandly sync` for future versions

---

*Web server findings (§1.5) are high-severity and must be fixed before any production use of `brandly timeline`.*
