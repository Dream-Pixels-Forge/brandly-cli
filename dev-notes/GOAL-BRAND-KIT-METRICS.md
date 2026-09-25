# GOAL: close the F9 gaps — brand-kit enforcement (G7) + metrics ingest (G8)

> **Companion to** `GOAL-AGENTIC-PIPELINE.md` (G1–G6 shipped in v0.5.0, 2026-09-25).
> **Issues:** [#98](https://github.com/Dream-Pixels-Forge/brandly-cli/issues/98) brand-kit,
> [#99](https://github.com/Dream-Pixels-Forge/brandly-cli/issues/99) metrics ingest
> (audit F9 gap register in `AUDIT-AGENTIC-PIPELINE.md`).
> **Grounding:** `src/brandly_cli/capabilities.py` (G5 source of truth):
> `brand_kit` = **absent** (no `brand` command; style presets only),
> `metrics_ingest` = **partial** (`analyze` is a heuristic predictor —
> `analyzer.py`: hook strength, pacing, visual quality, CTR; no real platform data).

## G7 — Brand-kit enforcement (logo/colour/claim lock) · 2 PRs

### PR 1/2 — brand-kit model + `brandly brand` command group + prompt-layer lock

- New module `src/brandly_cli/brand_kit.py`: `BrandKit` dataclass —
  `logo` (path spec), `colors` (hex list), `claims` (allowed-copy allowlist),
  `style_lock` (style preset the kit pins), `overlay` (logo placement:
  corner, safe-zone fraction, opacity).
- Project-level store: `.brandly/<project>/brand.json` (project files stay
  git-ignorable; kit never leaks into user-level config — same rule as F2).
- New command group `brandly brand`:
  - `brand init` — flags-driven scaffold (non-interactive, CI-safe)
  - `brand verify` — deterministic validation: hex format, non-empty claims,
    style_lock exists in `STYLE_PRESET_OPTIONS`, logo path resolvable;
    fail-closed exit code
  - `brand show` — print the kit (JSON or human)
- **Prompt-layer lock:** `brand_constraints(kit) -> str` suffix appended
  *after* `apply_style_preset()` (the "style applied by the caller" rule):
  pins the colour palette, bans third-party logos/trademarks/watermarks,
  restricts on-screen copy to the kit's claim allowlist.
- TDD: schema validation tests, prompt-suffix injection tests (a conflicting
  style lock is rejected), `brand verify` fail-closed tests (RED first).
- Capability row `brand_kit`: absent → **partial** (prompt-layer + verify
  shipped); CI guard syncs README + `capabilities.py`.

### PR 2/2 — gate-layer claim lock + export-layer logo overlay

- **Gate:** `brandly gate` gains a brand check — text overlays / captions must
  stay inside the claim allowlist; unknown claim = **hard fail** (fail-closed),
  mirroring the G3 scene-gate pattern.
- **Export:** `export --brand` composites the logo via ffmpeg (`overlay`
  filter; placement + safe-zone from the platform preset in
  `export_platforms.py`); production masters stay untouched (G4 ratio policy).
- E2E dry-run test: kit → prompt → gate → export overlay, no provider calls.
- Capability row `brand_kit`: partial → **supported** only when the e2e
  dry-run test passes (G4 rule), README sync via G5 guard.

### Decision gates (answer before implementing)

- **DEV-G7-001:** Store the kit project-level only (`brand.json` inside
  `.brandly/<project>/`), no user-level default kit? *(default: y)*
- **DEV-G7-002:** Gate-layer claim lock is a **hard fail** on any
  overlay/caption copy outside the allowlist (fail-closed)? *(default: y)*
- **DEV-G7-003:** Ship the logo overlay in the same PR 2 as the gate check
  (ffmpeg `overlay`), not a follow-up? *(default: y)*

## G8 — Real performance-metrics ingest · 2 PRs

### PR 1/2 — platform metrics import (no network, no credentials)

- New module `src/brandly_cli/metrics.py` + command group `brandly metrics`:
  - `metrics import <file> --platform youtube [--project <id>]` — accepts CSV
    or JSON with schema `{date, views, likes, watch_time_seconds,
    ctr_pct}` (schema versioned); validation deterministic, fail-closed on
    unknown platforms / malformed rows
  - Stored **project-local**: `.brandly/<project>/metrics/<platform>-<date>.json`
  - `metrics show` — latest ingested snapshot per platform
- **`analyze` integration:** when a latest ingest exists for the project, the
  scorecard blends real metrics (rows labelled `source: ingested`); otherwise
  it falls back to today's heuristics (`source: heuristic`) — output always
  states which source was used (G5 scope-truth rule).
- Capability row `metrics_ingest`: partial → **supported** (import + analyze
  blend shipped); the planned column keeps "YouTube Analytics API (G8 PR 2)"
  — CI guard syncs README.

### PR 2/2 — YouTube Analytics API adapter (credential-gated, G6 pattern)

- Reuse G6's `Adapter` Protocol + `brandly config` credential store:
  `metrics ingest --platform youtube` pulls real stats for a channel's recent
  videos (`youtube/analytics` read-only scopes) and writes the same
  project-local snapshot files as PR 1.
- **No credential → fail-closed** with the exact `brandly config set
  youtube:analytics <key>` command (DEV-G6-001 pattern); the dry-run path
  renders the exact request and never posts.
- Unit tests with mocked HTTP (payload assertions only, no network); the
  capability row gains a next-step note for TikTok/IG analytics.

### Decision gates (answer before implementing)

- **DEV-G8-001:** Ingested metrics live project-local
  (`.brandly/<project>/metrics/`), never in the user-level config store?
  *(default: y)*
- **DEV-G8-002:** `analyze` prefers the latest ingest over heuristics when
  one exists, and labels the source in output? *(default: y)*
- **DEV-G8-003:** G8 PR 2 is YouTube Analytics only this round — TikTok/IG
  analytics adapters land later, alongside the G6 live-upload follow-ups?
  *(default: y)*

## Order, release, and success

- **Sequence:** G7 PR 1 → G8 PR 1 (independent modules — may parallelize) →
  G7 PR 2 → G8 PR 2. All four behind one release: **v0.6.0 closes F9**
  (remaining open items: live TikTok/IG uploads + campaign-AB variant
  matrix, both already `planned` rows).
- **Conventions per PR:** TDD red-green (failing test committed first),
  `capabilities.py` + README + CHANGELOG updated in the same PR (G5 guard),
  CI gate stack green, squash-merge, delete branch.
- **Done looks like:** `brandly brand verify` + gate claim-lock + export
  logo overlay proven by e2e dry-run; `brandly metrics import` → `analyze`
  shows a real-metrics scorecard; capability matrix `brand_kit` = supported,
  `metrics_ingest` = supported; issues #98 / #99 closed with the
  capability-matrix link.

