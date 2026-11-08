# GOAL — Fix the issues found by a real idea→production pipeline test (demo run)

> **Project:** brandly-cli · **Base:** `main` @ `6188253` (v0.11.1) ·
> **Created:** session goal (goal-writer skill) ·
> **Evidence:** live end-to-end run in `demo/` (init → … → publish) with a real
> `AGNES_API_KEY`, 2026-10-06. Logs: `demo/run_asset.log`, `demo/produce_23.log`.
> **Workflow:** git-driven-development (branch → TDD RED→GREEN → rebase → PR →
> review → merge) dispatched through pipeline-orchestrator (parallel where safe).

## Goal: Close every defect surfaced by the demo pipeline run and make `brandly run --execute` reach `done` unattended

### Objective
Fix the 11 issues caught while driving a fresh project from idea to finished
production in the `demo/` folder, so that a single `brandly run <id> --execute --yes`
takes a new project to `done` with real clips, no manual JSON edits, no
manual artifact downloads, and zero event-loop warnings.

### Context

A real pipeline test was run in `demo/` (init → trends → concept → script →
asset → audio → re_edit → validate → publish). The generation half worked
(Agnes produced a real 4.48 s clip for a 4 s request — G7 tolerance held),
but the orchestration half broke in multiple places. The most expensive bug:
**the Director path generated a video on Agnes, then failed to download it
(`asyncio.run() cannot be called from a running event loop`) and failed the
phase — every retry re-generates and re-burns credits.** The URL had to be
recovered by hand with `curl`.

Root cause class: sync code calling `asyncio.run()` while the Director's event
loop is running. A **local uncommitted diff already adds a `_run_async` helper**
to `cmd/generation.py` and `cmd/production.py` (several call sites) but misses
`io.py`, `cli.py`, `project_manager.py` and the produce-runner artifact path —
observed RuntimeWarnings prove the gaps:

- `io.py:414` — `coroutine 'download_file' was never awaited` (artifact not saved; **credits burned**)
- `cli.py:127` — `coroutine 'ProjectManager.read' was never awaited` (`_load_project_reference` silently returns `None` → primary-reference detection disabled inside pipeline runs)
- `project_manager.py:244` — `coroutine 'ProjectManager.read' was never awaited` (`sync_production_state` swallows the failure)
- `production.py:2646` — `coroutine 'ProjectManager.update' was never awaited`

### Issue register (evidence-anchored)

| # | Sev | Step | Issue | Evidence |
|---|-----|------|-------|----------|
| I1 | **Critical** | asset | Director path cannot save generated artifacts: sync-in-async `asyncio.run` → `RuntimeError: asyncio.run() cannot be called from a running event loop`; artifact skipped (URL-only), phase fails, retry re-generates → repeated credit burn. `io.py:410` `asyncio.run(download_file(...))` is the observed crash site; sibling misses: `cli.py:125`, `project_manager.py:196`, plus any remaining `asyncio.run(` reachable from `_run_phase_real` | `demo/run_asset.log`: "⚠ Could not save artifact", "✗ Phase 'asset' failed: RuntimeError"; task `task_i5Qt8JPcrdruysyJCEny6klzvs4dQoLJ` recovered manually |
| I2 | High | concept | `concept` phase unimplemented → every fresh `run --execute` hard-fails at concept; workaround is a manual `approve`, which then records the phase as `completed` while keeping its `error` (state lies) | reproduced twice; `project.json` concept.status=completed + error retained |
| I3 | High | asset→resume | Download failure is not recoverable: the successful task URL is only printed to the console; the progress file never records the shot; a re-run creates a NEW task (new credits) instead of downloading the existing result | `run_asset.log` vs missing `docs/tmp/produce_progress.txt` entry |
| I4 | High | audio | `audio` hard-requires `MINIMAX_API_KEY`: missing key → 3 retries → project `failed`; no graceful explicit skip (audio is optional for the pipeline) and no way to reach `done` without the key | retry envelope ×3, `status: failed` |
| I5 | Medium | asset | No primary reference → pipeline silently continues in text mode ("Mode: text", high-drift warning only in console); nothing in `plan`/gate records the missing reference | `run_asset.log`: "No primary reference … Continuing without reference" |
| I6 | Medium | run | `run --until <X>` with `current_phase` already past `X` prints `✓ Pipeline executed: ` (empty phases list) — a misleading success for a no-op (`production.py:377` joins an empty `phases_run`) | observed output: `✓ Pipeline executed: ` |
| I7 | Medium | validate | Gate verdict divergence: pipeline `validate` (vision, scene-first) reported `S01=fail` while manual `brandly gate --all-scenes` reported `PASS`; neither states which mode produced the verdict | both outputs in session log |
| I8 | Medium | trends | `trends` fake-completes: `{"trending_formats": [], "recommended_style": …}` — claims research, does none (data honesty) | `project.json` trends.output |
| I9 | Low | state | State hygiene: `created_at` stays `""` until the first later update; `approve` keeps stale `error`/null `output` on completed phases | `project.json` dumps |
| I10 | Low | repo | Repo health: `tests/test_web_studio_preview.py::test_readme_demos_links_producer_videos_and_preview` fails (README has no `## Demos`); `test_architecture_contracts.py` cannot import `importlinter` in this env | pytest output (2026-10-06) |
| I11 | Note | env | `demo/` (git-ignored) was wiped mid-test by an external checkpoint operation; tests must be re-creatable from commands, artifacts not precious | folder emptied between steps |

### Decision gates (answer before implementing — do not decide silently)

- **DEV-D1:** I2 concept — (a) implement `concept` via one Agnes text-model call deriving a concept from the brief (fail-closed on API error), or (b) honest auto-skip: complete with `output.source="agent-pending"` + a loud notice. *(default: a, since the text model + `--llm-enhance` machinery already exists)*
- **DEV-D2:** I4 audio — skip-with-warning when `MINIMAX_API_KEY` is missing (pipeline continues, final video has no music), vs fail-closed as today. *(default: skip-with-warning + persisted `audio_skipped: missing-key` marker; data honesty preserved)*
- **DEV-D3:** I5 reference — elevate to a gate failure without a primary reference vs keep warning but record `reference: missing` in `brandly plan --json` + scene gate report. *(default: record in plan + gate report; warn-only in run)*
- **DEV-D4:** I8 trends — mark the phase `skipped (no data source)` honestly vs wire a real source. *(default: honest skip; wiring a source is a separate goal)*

### Deliverables

- [ ] **D1 (I1)** Move/extend the sync-in-async helper (the uncommitted `_run_async`) into one shared module (e.g. `src/brandly_cli/async_compat.py`); route **every** `asyncio.run(` call site reachable from the Director through it — at minimum `io.py:410`, `cli.py:125` (`_load_project_reference`), `project_manager.py:196` (`sync_production_state`), `production.py:2646` path — and add a repo-wide audited inventory (call-site list in the PR description; each remaining bare `asyncio.run` justified).
- [ ] **D2 (I1, I3)** Artifact-download failure recovery: on save failure persist the task id/URL (progress file or plan row); on resume, **download-first** before re-generating; never create a new task while an unsaved successful URL exists.
- [ ] **D3 (I2)** Concept phase per DEV-D1, with the `approve` state-hygiene fix (I9: completed phase must not retain `error`; `approve` must not fabricate `output: null` completion without a note).
- [ ] **D4 (I4)** Audio graceful skip per DEV-D2: explicit `SKIPPED (missing MINIMAX_API_KEY)` in phase output + console warning; pipeline reaches `re_edit` without the key.
- [ ] **D5 (I6)** Fix the no-op success print: `phases_run` empty → print `already past '<until>' (current: <phase>)` and keep exit 0; never render an empty arrow line.
- [ ] **D6 (I7)** Gate-mode transparency: `brandly gate` prints the mode (`deterministic` / `ai:N-frames`), `validate` stores `{mode, verdict}` in its phase output; a mode mismatch notice when the CLI verdict differs from the pipeline verdict.
- [ ] **D7 (I8)** Trends honesty per DEV-D4.
- [ ] **D8 (I9)** State hygiene: `created_at` set at init; phase `error` cleared on successful completion/approve.
- [ ] **D9 (I5)** Reference visibility per DEV-D3.
- [ ] **D10 (I10)** Repo health: README regains a `## Demos` section (or the contract test is corrected to the current README structure — no `.skip`); document `importlinter` as the dev dependency that `test_architecture_contracts.py` requires (install/verify in CI docs).
- [ ] **D11 (acceptance)** Fresh end-to-end re-run: scripted demo reproduction (documented commands in this file's appendix) running `init → run --execute --yes` with real keys, asserting: scene clips saved on disk without manual curl, no `Could not save artifact` / `never awaited` / `running event loop` strings in logs, phases advance past concept/audio per the decision gates, final `videos/final.mp4` + `export/` outputs exist, `status: completed`.
- [ ] Tests: a regression test per deliverable (RED confirmed before GREEN), per repo TDD mandate.

### Definition of Done

- [ ] `PYTHONPATH=src python3 -m pytest tests/ -q` — 0 failures, count ≥ current baseline (1319+), no tests deleted/skipped to reach green
- [ ] `ruff check src/ tests/` — 0 warnings
- [ ] `grep -rn "asyncio.run(" src/brandly_cli/` — every hit either routed through the shared helper or listed with a one-line justification in the PR
- [ ] Regression test proves the I1 fix: Director asset path downloads the artifact (mocked generator) with `pytest -W error::RuntimeWarning` for the affected module — no un-awaited-coroutine warnings
- [ ] I3 test: download failure → resume downloads the same task URL and does NOT create a second task (assert generator call count == 1)
- [ ] Fresh demo run logs contain none of: `Could not save artifact`, `never awaited`, `cannot be called from a running event loop` (grep on `demo/*.log`)
- [ ] Fresh demo run reaches `status: completed` with `videos/final.mp4` and at least one file in `production/<id>/export/` — without hand-editing `project.json`
- [ ] Decision gates DEV-D1..D4 answered in this document (recorded, not assumed)
- [ ] `dev-notes/PROGRESS.md` updated with the round entry; PR opened on a `fix/` branch with CI green

### Verification Steps

1. `PYTHONPATH=src python3 -m pytest tests/ -q` — full suite green
2. `ruff check src/ tests/` — clean
3. `grep -rn "asyncio.run(" src/brandly_cli/` — inventory matches the PR justification list
4. Repro I1: `cd demo && rm -rf .brandly production pre-production AGENTS.md && PYTHONPATH=../src python3 -m brandly_cli init -n 'Demo Product' -i 'A demo product for testing brandly-cli end-to-end' -s cinematic -b 500 --shots 3 -p all && PYTHONPATH=../src python3 -m brandly_cli run demo-product --execute --yes` — clips appear under `production/demo-product/videos/scenes/` with no manual download
5. `grep -E "Could not save artifact|never awaited|running event loop" demo/*.log` — empty output
6. Repro I4: run audio without `MINIMAX_API_KEY` — phase records an explicit skip, pipeline continues
7. `ffprobe -v error -show_entries format=duration production/demo-product/videos/final.mp4` — stitched master exists and is > 0 s
8. `PYTHONPATH=../src python3 -m brandly_cli status demo-product` — all phases `completed`, `status: completed`

### Anti-Drift Rules

- Stay within the Objective (I1–I11). New findings from the re-run become a **new** goal, not scope creep here.
- Reconcile with the **uncommitted local diff** (`_run_async` in `generation.py`/`production.py`, `__about__.py` bump to 0.11.1) — build on it, do not clobber it; if it must change shape, commit it as the first RED→GREEN increment.
- Answer DEV-D1..D4 before coding the corresponding deliverable; if a gate's default is rejected, record the decision in this file.
- TDD: failing test first for every deliverable; bug fixes start with a regression test that reproduces the bug (I1/I3 repros above).
- Do not weaken, `.skip()` or delete existing tests; do not add new providers, UI surface or abstractions beyond the shared async helper.
- Data honesty: no phase may report `completed` while its work is undone; no fabricated outputs.
- One concern per commit; PR per logical group (D1+D2 first — they unblock the flagship path).

### Estimated Effort

High — ~2–3 focused sessions (same class as `GOAL-ISSUES-31-43.md`).
Suggested pipeline-orchestrator dispatch:

1. **Wave 1 (serialized, unblocks everything):** D1 → D2 (same seam, one PR).
2. **Wave 2 (parallel, independent):** D3 | D4 | D5 | D6 | D7 | D8 | D9 (one subagent each, contract = deliverable + its regression test).
3. **Wave 3:** D10 (repo health) ∥ D11 acceptance run (depends on Waves 1–2).
4. **Gate:** full suite + ruff + fresh demo run → goal-met audit.

### Appendix — demo reproduction commands (as executed)

```bash
mkdir -p demo && cd demo
PYTHONPATH=../src python3 -m brandly_cli init -n 'Demo Product' \
  -i 'A demo product for testing brandly-cli end-to-end' \
  -s cinematic -b 500 --shots 3 -p all
PYTHONPATH=../src python3 -m brandly_cli run demo-product --execute --yes --until concept
# ↑ fails at concept (I2) → approve → continue
PYTHONPATH=../src python3 -m brandly_cli approve demo-product concept
PYTHONPATH=../src python3 -m brandly_cli run demo-product --execute --yes --until script
PYTHONPATH=../src python3 -m brandly_cli run demo-product --execute --yes --until asset
# ↑ I1: video generated (task_i5Qt8JPcrdruysyJCEny6klzvs4dQoLJ) but download
#   failed with "asyncio.run() cannot be called from a running event loop";
#   recovered manually:
curl -sL -o production/demo-product/videos/scenes/Scene-01-Shot-1-1.mp4 \
  'https://platform-outputs.agnes-ai.space/videos/agnes-video-2.5/task_i5Qt8JPcrdruysyJCEny6klzvs4dQoLJ.mp4'
# shots 2-3 via the standalone (working) produce path:
PYTHONPATH=../src python3 -m brandly_cli produce demo-product \
  --shots .brandly/demo-product/shots.json --only shot-2 --only shot-3 --interval 10
```



