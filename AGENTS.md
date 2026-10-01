# AGENTS.md — brandly-cli

> **Authority:** repo-level operating instructions for every agent working in
> this repository. Extends the workspace rules (`~/.agents/AGENTS.md`) — where
> they conflict, the stricter rule wins.

---

## 0. Process discipline (STRICT MANDATORY — never break)

Every task follows the design→code pipeline recorded in
**[`dev-notes/CONVENTIONS.md`](dev-notes/CONVENTIONS.md)**. The short form:

1. Frozen design spec → code. No spec, no code; never improvise layout.
2. Use this repo's ratified verification convention. Do **not** invent new
   architecture (e.g. no JS test runner — issue #61 is still open).
3. **RED → GREEN** for every increment; observe the test fail first.
4. If a design artifact doesn't exist, the feature is **out of scope** — don't
   invent it; record the deferral in `dev-notes/PROGRESS.md`.
5. **Data honesty** — never fabricate telemetry or wire no-op actions.
6. Reuse existing tokens; never fork a token namespace.
7. All gates green or it is not done.
8. Git safety: check divergence + overlap before switching; never merge
   without review.

**Non-negotiable merge condition:** every CI check green, zero lint warnings,
no unresolved review threads.

---

## 1. Project layout

| Path | What it is |
|---|---|
| `src/brandly_cli/` | Python CLI, agent surface, MCP server, web server |
| `web/` | React 19 + TypeScript + Vite SPA (built into `src/brandly_cli/web/static`) |
| `tests/` | pytest — Python source-contract tests for the SPA + CLI tests |
| `dev-notes/` | Pipeline governance; **`PROGRESS.md` is the state ledger** |
| `skills/` | Bundled Agent Skills (shipped in the wheel) |

## 2. Frontend verification convention (do not invent new architecture)

- The SPA is verified with **Python source-contract tests** (they read the
  `.tsx` sources) plus the **`web-quality` CI job**.
- Contract tests live in `tests/test_web_*.py`. New frontend work adds a
  contract test **RED first**.
- There is **no JS test runner** in CI (see `tests/test_web_panels_wired.py`,
  issue #61). Adding vitest/Jest is a separate, unratified decision.

## 3. Web gates (all green or the increment is not done)

| # | Gate | Command |
|---|---|---|
| 1 | Contract tests | `python -m pytest tests/test_web_*.py -v` |
| 2 | Frontend lint | `npm --prefix web run lint` — **0 warnings / 0 errors** |
| 3 | Typecheck + build | `npm --prefix web run build` |
| 4 | Bundle freshness | `git diff --exit-code -- src/brandly_cli/web/static/` |
| 5 | Full suite | `python -m pytest tests/ -q` |
| 6 | Python lint | `ruff check src/ tests/` |

## 4. Design source of truth

- `dev-notes/DESIGN-STUDIO-SHELL.md` — **frozen** spec (Paper file
  `01M3VWT0PHVWKPN9JSECCES8T4`, page `p-3-0`, artboards `01`–`04`).
- Artboards **05/06 are empty** in Paper — those screens are out of scope
  until a design exists.

## 5. Non-negotiables

- ❌ No code without a failing test first
- ❌ No merge without review + all CI green
- ❌ Never clobber unrelated work — check branch divergence **and** file
  overlap before switching
- ❌ Never fabricate data in the UI
- ❌ Never improvise layout away from the frozen spec
