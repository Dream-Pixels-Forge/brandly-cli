# HANDOFF — brandly-cli

> **Written:** 2026-10-10, after the enforcement program (PR #306, `6e9c004`)
> **State:** main green (1595 passed / 0 failed, ruff + mypy + import contracts
> clean) · **0 open issues · 0 open PRs · 0 stray branches** · release
> **v0.13.0** on code + GitHub + PyPI (attested, smoke-tested)

## What just happened (read this first)

Three back-to-back programs, all landed via PRs with CI green:

1. **13-issue fix program (#270–#283) → v0.13.0** — pipeline honesty (async
   surface, phase machine), reference truth (gate-before-promotion, wardrobe),
   layout contract (`--output` root, folder routing, storyboards), document
   chain (trends category, single beat map, `--target-duration`), agent driver
   (`--agent-runner agnes`), screenplay phase. Ledger: `PROGRESS.md` Rounds
   27–28, goal in `GOAL-OPEN-ISSUES-270-283.md` (goal-met audit MET).
2. **Live demo pipeline test** (`demo/coffee-mug-duo` — two people showing a
   coffee mug, 30s target, storyboards on): the document chain
   (trends → concept → screenplay → script) + the storyboard keyframe pass
   completed live with real credits; video generation blocked by provider
   capacity (Agnes `503 video_queue_full`, 2+ hours). Road findings filed:
   #291 (closed by maintainer as known), #292–#295. `demo/` is gitignored.
3. **Enforcement program (#297–#302, #304) → PR #306** — the pipeline now
   honors the layout contract + the skills' production flow. Everything below.

## The enforced state (what PR #306 changed)

**Phase chain (13 phases, the skills' production flow):**
`init → trends → concept → bible → casting → screenplay → script → asset →
audio → re_edit → validate → publish → done`

- **bible (#297)** — derives `docs/bible/production_bible.md` from brief +
  concept + trends via the agent runner; **Section 4: Characters is
  mandatory** (fail-honest without it — casting cannot run).
- **casting (#301)** — parses Section 4 → per character: cast set (hero 3:2 /
  portrait 3:4 / full-body 2:3) + the GOLD sheet, composition-gated, under
  `pre-production/<id>/character/` (`char_<name>_cast-*` / `char_<name>_sheet`).
- **screenplay (#298)** — writes `docs/screenplay/screenplay.md` (NOT plan/).
- **storyboard (#300)** — panels carry the grid-style-lock **graphite
  preamble**; approved panels are **tiled in code (PIL)** into ONE
  `storyboard_grid_4x4.png` (4 cols × ≥4 rows, edge-to-edge, no text).
- **taxonomy (#299)** — `docs/general/` (trends, concept, scenes.json);
  `docs/plan/` = pre-generation plans only; the shots.json root placement is
  the documented load-bearing exception (timeline editor path).
- **run logs (#304)** — `run --execute` writes `docs/tmp/run_<ts>.log`
  (structured: RUN START / PHASE START|DONE|FAIL). Agents never invent
  locations.
- **resumability (#292)** — the storyboard pass consults
  `docs/tmp/storyboard_progress.txt`; approved keyframes skip regeneration
  (no credit re-spend on retries); per-shot console lines.
- **retries (#293)** — the pipeline-path produce runner gets `retries=1`.
- **provider saturation (#294)** — create-failure details persist to
  `docs/tmp/video_create_fail_<ts>.md`; the asset phase classifies
  `[provider saturated] … wait several minutes and re-run`.
- **ref cap (#295)** — canonical names (Scene-XX / char_ / loc_ / prop_ /
  wardrobe_) outrank unknown files; junk can never displace real references.

**Prevention layer (E7):** the generated `AGENTS.md` teaches the layout
contract, the production flow, the run-log convention, and the
no-junk-in-media-tree rule. `tests/test_layout_contract_enforcement.py`
(21 tests) pins ALL of it — a source-contract sweep forbids hardcoded
`docs/plan` paths in production.py, and the taxonomy/AGENTS contracts are
asserted. **Do not weaken these tests — they are the anti-drift mechanism.**

## Known-open items (filed, not yet enforced)

- **#291** (closed by maintainer as known): empty error messages on transient
  failures — the fix pattern is documented in the issue
  (`{type(e).__name__}: {e}` everywhere; `_generate_shot` and the storyboard
  pass already do it). Sweep `grep -rn "failed: {e}" src/brandly_cli/` when
  reopening.
- **#294 (partial)** — the saturation *classification* shipped; the provider
  *fallback* (alternate backend when Agnes is saturated) did not. The G14
  `VideoBackend` seam is the extension point.
- **#300 (ruling recorded in code)** — the grid always builds 4 columns ×
  ≥4 rows; cells beyond the panel count render as clean white paper. If the
  maintainer wants strict 16-frame grids only, tighten `_tile_contact_sheet`.
- **#302 (partial)** — the drift fixes shipped; the *caster prompt quality*
  (bible Section 4 → per-character prompts) is a first pass; refine with real
  bibles.

## Demo project (gitignored, resumable)

`demo/coffee-mug-duo` — two people showing a coffee mug, 30s target, food
category, storyboards on. Document chain + 5 gate-approved keyframes on disk;
blocked at video by provider capacity.

```
brandly --root demo run coffee-mug-duo --execute --yes
```
(The attempt counter may need the documented project.json reset —
`phases.asset.attempts = 1`.)

## Conventions that must not break

- RED → GREEN per increment (`AGENTS.md` §0, `CONVENTIONS.md` §2)
- Land via branch → PR → CI green → `gh pr merge --squash --delete-branch`
- `PHASE_HANDOFF_SPECS` is the dispatch contract — deliver what it says or
  correct it; never leave the two divergent
- Writers route through `layout.docs_dir(...)` — never hardcode a docs folder
- PR bodies: one `Fixes #N` keyword per line (space-separated lists only
  auto-close the first issue)
- Release flow: bump `__about__.py` (single source) + CHANGELOG → PR → CI →
  tag `vX.Y.Z` + `gh release create` → the Release-to-PyPI workflow (OIDC +
  attestations) → verify all three surfaces + fresh-venv smoke test

## Environment notes

- Windows local: rich ≥14 required (import-linter 2.15's nested Live crashes
  on rich 13's flat `_live` singleton) — the env was upgraded to rich 15.0.0,
  suite re-verified green.
- The demo run's Agnes video endpoint saturated (`video_queue_full`) for 2+
  hours — provider capacity, not code. The classification + resume path (#294)
  now makes this a wait-and-resume, not a dead end.

## Suggested next session

1. Re-run the demo pipeline (command above) — the enforced chain (bible →
   casting → screenplay → script → asset) end-to-end with real credits; watch
   `docs/tmp/run_*.log`.
2. Reopen #291 and do the empty-error-message sweep (pattern in the issue).
3. #294 provider fallback: `--fallback-model` on the produce path when a
   second provider key is configured.
4. Cut v0.14.0 when the demo completes end-to-end (the enforcement program is
   feature-worthy: bible + casting + grid).
