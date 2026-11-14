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

### 3.4 Download / SSRF Hardening
`brandly_cli.io.download_file` (used to fetch provider media such as Agnes video and MiniMax audio) is hardened against SSRF (CWE-918):

- Only `http`/`https` schemes are accepted (`file://`, `ftp://`, `gopher://` refused).
- The resolved host must be a public internet address; loopback (`127/8`, `::1`), link-local (`169.254/16` incl. the cloud metadata service `169.254.169.254`), RFC1918 (`10/8`, `172.16/12`, `192.168/16`), reserved, multicast, and unspecified addresses are refused.
- The body is capped at 1 GiB (`MAX_DOWNLOAD_BYTES`) so a malicious provider cannot fill the disk.

Residual risk: redirects are followed (`follow_redirects=True`) so provider flows keep working; the initial host is validated but each redirect hop is not re-checked. Provider media URLs are normally direct, so the redirect window is narrow.


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

## 6. LLM Agent & MCP Trust Boundary

brandly-cli exposes its pipeline to AI agents two ways:

- **`brandly_cli.agent_surface`** — the discoverable tool manifest + `dispatch()` layer, backed by the real CLI (no parallel implementation).
- **`brandly_cli.mcp_server`** — an MCP (Model Context Protocol) stdio server (`brandly mcp serve`) exposing the same tool set over JSON-RPC 2.0.

Because the server runs tools headless via subprocess, the trust boundary must be explicit:

| Control | Status | Notes |
|---------|--------|-------|
| Tool descriptions are static | ✅ | `brandly`'s own tool descriptions come from `agent_surface` (committed code), not user-supplied text — so brandly's server is not itself a tool-poisoning vector. |
| MCP server allow-list / sandbox | ❌ | `mcp_server` exposes **all** manifest tools, including destructive/write tools (`produce`, `approve`, `record_cost`, `takes export/apply`, `memory set`). There is no allow-list, no sandbox, and no tool-description scanner at connect time. |
| Human-in-the-loop | ⚠️ Partial | The CLI tools have interactive confirm semantics, but `_subprocess_runner` is non-interactive, so tools invoked over MCP run **headless without HITL**. |
| Excessive agency (LLM06) | ⚠️ | A compromised or rogue MCP client can command `produce` (spends credits/generates media) or `approve` (advances pipeline state) without approval. |

### Recommendations for MCP consumers
1. **Only connect trusted MCP clients** to `brandly mpc serve`; treat the stdio server as privileged.
2. **Do not expose the MCP server over a network** — it is stdio/local by design.
3. **Prefer read-only tools** (`take_prompts_status`, `take_prompts_list`, `status`, `plan`, `run_gate`, …) for untrusted clients; gate write/destructive tools behind a human who runs `brandly` directly.
4. **Audit tool descriptions** like source code if you extend `agent_surface.CLI_TOOLS` — descriptions flow into the model's context and are an injection channel (MCP tool-poisoning, Invariant Labs 2025).
5. **Rotate provider API keys** if an MCP client is ever suspected compromised — the server forwards `AGNES_API_KEY`/`MINIMAX_API_KEY` from the environment to providers.

---

*Web server findings (§1.5) are high-severity and must be fixed before any production use of `brandly timeline`.*
