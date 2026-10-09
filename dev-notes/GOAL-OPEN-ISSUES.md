# GOAL — Fix all 9 open issues: async correctness, reference injection, gate automation, prompt variation, web data honesty

> **Project:** brandly-cli · **Created:** goal-writer session (2026-10-07)
> **Base:** `origin/main` @ `6188253` (v0.11.0) — **after PR #254 merges** (see Sequencing)
> **Evidence:** `gh issue list` (9 open issues) + per-issue bodies fetched 2026-10-07
> **Convention:** every increment is RED → GREEN (contract/pytest test first),
> subagent-executable, subagent-verified (goal-met audit, independent of executor).

## Program Objective

Resolve all 9 open GitHub issues (#245–#253) so the automated pipeline
(`brandly run --execute`) completes end-to-end without async crashes, without
false "No primary reference" warnings, without manual Y/n gates when the AI
verdict is pass, with per-beat shot prompts, consistent `--root` support, and
a web UI that never wires no-ops or fabricates data.

**North star (unchanged):** agents drive it; cinema is the core bone.

## Program Context

| # | Type | Symptom (verified from issue body) | Suspected layer |
|---|------|------------------------------------|-----------------|
| 246 | bug, high | `RuntimeError: asyncio.run() cannot be called from a running event loop`; `create_video_task` never awaited — blocks **all** video generation | `cmd/generation.py:~2221` |
| 249 | bug | `RuntimeWarning: coroutine 'ProjectManager.read' was never awaited` (×2 sites) | `cli.py:127`, `project_manager.py:244` |
| 252 | bug, high | asset phase warns "No primary reference" despite approved reference in `pre-production/` + `primary_reference` in `project.json` | reference discovery in asset phase |
| 245 | bug, high | same warning, same repro — **same root as #252** (fix together, close both) | reference discovery in asset phase |
| 250 | enhancement | reference gate prompts Y/n twice even when AI verdict is `pass` (score 92/100) — blocks fully automated MCP pipelines | reference gate |
| 251 | bug | `brandly status <id> --root <path>` → `No such option '--root'`; `list`/`run` have it | `status` command |
| 248 | bug | 10 shots → near-identical prompts (same subject/action/setting/lighting/grade/negatives); only camera/duration/beat-label differ | shot prompt builder |
| 247 | enhancement | `Phase 'concept' failed: concept phase is not implemented yet` — blocks trends→script; workaround is manual `brandly approve <id> concept` | concept phase |
| 253 | audit | web UI: CFG slider **corrupts clip volume** (real data bug), no-op M/S buttons, fabricated seed/checkbox values, no-op "Update Shot Props" button, dead help button | `PropsInspectorPanel.tsx`, `TimelineTrackHeader.tsx` |

**Cross-cutting facts (verified this session):**
- The repo already has `src/brandly_cli/async_compat.py` — check it before inventing new async shims.
- `#245` and `#252` are the same bug at the same layer: one fix, two closes.
- CI on `main` is currently red from 4 README docs-contract failures — PR #254 fixes those; it must merge first.

## Sequencing (hard order)

1. **PR #254 merges first** (`fix/web-empty-state-fetch-resilience` — CI green).
   Rationale: this goal's web fixes rebuild the same static bundle; branching
   off a red main that still carries the README failures would chain-fail CI.
2. Branch `fix/open-issues-245-253` from the post-merge `main`.
3. Phases F1→F7 in order; each phase is its own PR (RED → GREEN → CI green → squash-merge).

## Phases

### F1 — Async/event-loop correctness (#246, #249)

**Objective:** Video generation and CLI runs produce no `asyncio.run()` /
never-awaited-coroutine warnings; async calls chain properly from every context.

**Deliverables**
- [ ] RED tests first: pytest that asserts `create_video_task` is awaited (not `asyncio.run()`-wrapped) when called from a running loop, and that no sync context calls `ProjectManager.read` without `await` (source-level contract on `cli.py` / `project_manager.py` / `cmd/generation.py`).
- [ ] Fix `cmd/generation.py:~2221` — replace `asyncio.run(create_video_task(...))` with a context-aware await (reuse `async_compat.py` helper if it provides one).
- [ ] Fix `cli.py:127` and `project_manager.py:244` un-awaited `ProjectManager.read` paths.
- [ ] `python -W error::RuntimeWarning` clean on the affected test modules.

**Definition of Done**
- [ ] New tests pass; full suite has **zero new** failures vs the pre-phase baseline.
- [ ] Repro from #246 (`brandly reference … && brandly run <id> --execute --until asset --yes`) runs without `RuntimeError`/`RuntimeWarning` output.
- [ ] `ruff check src/ tests/` clean.

**Verification**
1. `python3 -m pytest tests/ -q -W error::RuntimeWarning --ignore=tests/test_architecture_contracts.py` — no runtime-warning escalations on touched modules.
2. Manual repro of #246 — no `RuntimeError: asyncio.run()` in output.
3. `grep -n "asyncio.run(" src/brandly_cli/cmd/generation.py` — no call site inside a running-loop context.

**Anti-drift:** fix only the async mismatch; no behavior change beyond awaiting correctly; do not touch the video prompt builder (that is F5).

---

### F2 — Reference auto-discovery + injection (#252, #245 — same root)

**Objective:** The asset phase auto-discovers the human-approved reference
(from `pre-production/<project>/**` + `primary_reference` in `project.json`)
and injects it into the video generation plan; the false warning is gone.

**Deliverables**
- [x] RED test first: pytest reproducing #252 — project with approved reference in `pre-production/` + `primary_reference` in `project.json` → asset phase reference resolution finds it (no "No primary reference" warning; reference present in the generation plan).
- [x] Fix reference discovery: locate via the timeline/pre-production layout (never a raw path — mirrors the `deps.require_clip_media_file` pattern).
- [x] Inject the approved reference into the video generation request.
- [x] Update the `analyze`/asset-phase summary so the warning reflects reality.

**Definition of Done**
- [x] New test passes; #252 repro produces no "No primary reference" warning.
- [x] The injected reference id appears in the generation plan output.
- [x] Full suite: zero new failures; `ruff` clean.

**Verification**
1. Repro steps from #245 — warning gone, reference injected.
2. `python3 -m pytest tests/test_web_*.py tests/test_shot_runner.py -q` — green.
3. `git diff` review — no unrelated layout changes.

**Anti-drift:** one fix closes BOTH #252 and #245; close both issues in the PR description; do not touch the gate prompts (that is F3).

---

### F3 — Reference gate auto-approve on AI pass (#250)

**Objective:** When the reference gate's AI verdict is `pass` (and score ≥ the
configured threshold), the gate proceeds without Y/n prompts; human prompting
remains for anything below threshold. Blocks-automation complaint resolved.

**Deliverables**
- [x] RED test first: pytest — gate with AI verdict `pass` + score ≥ threshold + non-interactive stdin completes with no Y/n prompt; verdict below threshold still prompts (or fails non-interactively, preserving current fail-honest semantics).
- [x] Implement auto-approve path in the reference gate.
- [x] `--yes`/non-interactive path documented in `brandly reference --help`.

**Definition of Done**
- [x] New tests pass; existing gate tests still pass (fail-honest G11 semantics unchanged).
- [x] Manual: reference generation with a passing AI verdict completes without Y/n.
- [x] Full suite zero new failures; `ruff` clean.

**Verification**
1. Run the #250 scenario — no `[reference gate] … [Y/n]:` prompts on pass.
2. `python3 -m pytest tests/ -q` (gate modules) — green.
3. `brandly reference --help` documents the behavior.

**Anti-drift:** do NOT weaken fail-honest gates (G11); auto-approve applies only to the reference gate on explicit AI pass; extension to other gates is a new goal.

---

### F4 — `brandly status` accepts `--root` (#251)

**Objective:** `brandly status <id> --root <path>` works, consistent with
`list` and `run`.

**Deliverables**
- [x] RED test first: pytest (CliRunner) — `brandly status <id> --root <tmp>` resolves the project from the given root; exit code 0.
- [x] Add the `--root` option to the `status` command.
- [x] Help text mentions `--root` consistently with sibling commands.

**Definition of Done**
- [x] `brandly status <id> --root /path` succeeds from a different cwd.
- [x] New test passes; full suite zero new failures; `ruff` clean.

**Verification**
1. `python3 -m pytest tests/ -q -k status` — green.
2. Manual: run `brandly status` with `--root` from another directory.
3. `brandly status --help` shows `--root`.

**Anti-drift:** option parity only; no other command flags touched.

---

### F5 — Per-beat shot prompt variation (#248)

**Objective:** Shot prompts vary by beat role (`setup→turn→consequence→resolve`)
with distinct action/framing per shot — not one identical template stamped on
all shots; camera/duration/beat-label remain beat-derived as today.

**Deliverables**
- [x] RED test first: pytest — N shots (≥4, spanning ≥3 beat roles) produce prompts whose subject-action-setting lines differ per beat role; shared global style (color grade, negatives) stays consistent (brandly-consistency convention).
- [x] Fix the shot prompt builder so beat role drives the action/setting segment.
- [x] Keep global style block shared (no drift — per `brandly-consistency` skill).

**Definition of Done**
- [x] New test passes: distinct per-beat prompts, consistent global style.
- [x] Full suite zero new failures; `ruff` clean.
- [x] Generated sample (manual, if API key available) shows varied prompts.

**Verification**
1. [x] `python3 -m pytest tests/ -q -k prompt` — green.
2. [x] Inspect generated `scenes.json`/shot prompts for a 10-shot project — per-beat variation present.
3. [x] Diff review — global style block unchanged across shots.

**Anti-drift:** variation lives in the action/setting segment only; never fork the global style namespace; do not change beat-duration derivation (already ratified).

---

### F6 — Concept phase implemented (#247)

**Objective:** `brandly run --execute` progresses past `trends` → `concept` →
`script` without a manual `brandly approve <id> concept`.

**Deliverables**
- [x] RED test first: pytest — `run --execute --until script` on a fresh project passes the concept phase automatically (no "not implemented yet" failure).
- [x] Implement the concept phase: derive the concept from the project brief with the agent (same shape as the Director does for script). If no agent/API key is configured, the phase fails honestly (G11 semantics — never fake-pass).
- [x] Wire the phase into the phase-handoff table (`test_phase_handoffs.py` contract fields).

**Definition of Done**
- [x] New test passes with an agent runner injected (mocked); fails honestly without one.
- [x] `brandly run <id> --execute --until script --yes` progresses past concept.
- [x] Phase-handoffs contract tests still green; full suite zero new failures; `ruff` clean.

**Verification**
1. [x] `python3 -m pytest tests/test_phase_handoffs.py tests/test_pipeline_orchestration.py -q` — green.
2. [x] Manual repro of #247 — no "concept phase is not implemented yet".
3. [x] `brandly director` output reflects the new phase contract.

**Anti-drift:** implement per issue option 1 (derive with agent); the auto-approve alternative (option 2) is rejected — it would violate fail-honest G11; do not touch reference gate prompts (F3).

---

### F7 — Web UI data honesty (#253)

**Objective:** The Studio Shell wires no no-op actions and fabricates no data;
the CFG slider no longer corrupts clip volume.

**Deliverables**
- [x] RED contract tests first (`tests/test_web_*.py`, source-level):
  - CFG slider does NOT write `volume` (must write a real cfg/guidance field or be disabled with an explanatory title).
  - No empty handlers `() => {}` in `TimelineTrackHeader.tsx` (M/S buttons disabled with explanatory titles per convention, or wired to real mute/solo state).
  - No hardcoded fabricated values (`value={42}` seed, "Cam: 120 deg CCW…", "BPM: 120 · Bar: 4/4") in `PropsInspectorPanel.tsx`.
  - "Update Shot Props" footer button either removed or performs a real write.
- [x] Fix `PropsInspectorPanel.tsx:185-191` (CFG→volume corruption — the real data bug).
- [x] Fix `TimelineTrackHeader.tsx:112-114` (no-op M/S buttons).
- [x] Fix `PropsInspectorPanel.tsx:157-183, 246-267, 140-155, 193-205` (seed, footer button, fabricated checkbox values).
- [x] Rebuild bundle; bundle fresh (`git diff --exit-code -- src/brandly_cli/web/static/`).

**Definition of Done**
- [ ] All new contract tests RED first, then GREEN.
- [ ] `python3 -m pytest tests/test_web_*.py -v` — green.
- [ ] `npm --prefix web run lint` — 0 warnings/errors; `npm --prefix web run build` green.
- [ ] Full suite zero new failures.

**Verification**
1. `python3 -m pytest tests/test_web_props*.py tests/test_web_audio_honesty.py -q` — green.
2. `grep -n "() => {}" web/src/components/timeline/TimelineTrackHeader.tsx` — none.
3. `grep -n "volume: v" web/src/components/panels/PropsInspectorPanel.tsx` — none in the CFG slider.
4. `git diff --exit-code -- src/brandly_cli/web/static/` — bundle fresh.

**Anti-drift:** convention fixes only (disable + explanatory title, or real wiring); never invent new panels or a seed backend field without a design artifact; the dead help button in the title is verified and fixed under the same convention.

## Program Definition of Done

- [x] F1–F7 all MERGED (each with CI green, zero lint warnings)
- [x] Issues #245, #246, #247, #248, #249, #250, #251, #252, #253 all CLOSED with fix references
- [x] Full suite on post-program `main`: zero NEW failures vs the `6188253` baseline (pre-existing failures tracked separately, never papered over)
- [x] `python -m pytest tests/ -q` + `ruff check src/ tests/` + web gates green on `main`
- [x] goal-met audit returns **MET** (independent auditor, re-runs every verification step)

## Verification Steps (program level)

1. [x] `gh issue list --state open` — none of #245–#253 remain.
2. [x] `python3 -m pytest tests/ -q --ignore=tests/test_architecture_contracts.py` — compare failures against the baseline list; zero new.
3. [x] `cd web && npm run lint && npm run build` — green.
4. [x] Manual pipeline: `brandly init → reference (auto-approved) → run --execute --until asset → script` — no RuntimeError, no false reference warning, no Y/n on AI pass.
5. [x] `gh pr list --state open` — no unmerged fix branches remain.

## Anti-Drift Rules (program level)

- Stay within the 9 issues. New findings get NEW issues, not silent scope growth.
- RED → GREEN for every increment; no code without a failing test first.
- Never fabricate telemetry, gate verdicts, or UI data (fail-honest G11 stands).
- One fix closes #252 + #245 together; do not duplicate work.
- Do not touch the ratified beat-duration derivation or the frozen design spec (`dev-notes/DESIGN-STUDIO-SHELL.md`).
- If blocked (e.g., API key unavailable for a manual repro), report the blocker — do not work around silently.
- Subagent discipline: executor ≠ auditor; the goal-met audit re-runs evidence.

## Estimated Effort

| Phase | Complexity | Estimate |
|-------|-----------|----------|
| F1 async correctness | medium (cross-file await chains) | 0.5–1 day |
| F2 reference injection | medium (layout + plan wiring) | 0.5–1 day |
| F3 gate auto-approve | small | 2–4 h |
| F4 status --root | small | 1–2 h |
| F5 prompt variation | medium (prompt builder + consistency) | 0.5–1 day |
| F6 concept phase | medium–large (agent wiring + handoffs) | 1 day |
| F7 web data honesty | medium (5 findings + contract tests) | 0.5–1 day |
| **Total** | | **~4–6 days** |
