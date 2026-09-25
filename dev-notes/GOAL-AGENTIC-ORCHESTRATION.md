# GOAL — G7: Agentic orchestration — orchestrator + subagent contract layer

> **Project:** brandly-cli · **Created:** session goal (goal-writer skill)
> **Base:** `main` @ a750d4e (v0.3.26) · **Rollback point:** tag `v0.3.26` (G1+G2+G3 shipped)
> **Sources:** G2 completion review — the pipeline is now real and fail-closed; the
> missing piece is letting an orchestrating agent safely dispatch phases to subagents.

## Program Objective

Turn brandly-cli into an **orchestrator-worker agentic system**: one orchestrating
agent (any MCP/manifest client) drives the 10-phase pipeline by dispatching
**phase-scoped subagents** with hard input/output/gate contracts, while
deterministic gates screen every worker result. Cognition runs in parallel,
execution is serialized (rate-limited provider), and no subagent can bypass the
fail-closed state machine.

## Program Context

G1–G3 (v0.3.26) delivered the substrate:

- **Tool surface** — `agent_surface.py` (manifest + `build_command` + `dispatch`
  with injectable runner and fail-safe envelopes), `brandly mcp serve`
  (stdio JSON-RPC 2.0), `brandly tools --json`, `READ_ONLY_TOOLS` classification.
- **Real orchestration** — `brandly run <id> --execute --until <phase>` over
  `Director.run_pipeline`: resumable from `project.phases`, fail-closed
  (error → phase `failed`, `current_phase` frozen, exit 1).
- **Authoritative scenes** — `scenes.json` manifest written pre-generation,
  `brandly scenes status` / `brandly gate --all-scenes` (exit 0/1/2),
  deterministic `verify_element` gate runner.
- **Agent plan source** — `director_plan()` (data-only) + the Director prompt
  (`director.py`).

What is missing: an **orchestrator-worker contract layer**. Today one agent
context must drive the whole pipeline; there is no machine-readable "what
inputs does this phase read, what must it produce, which gate verifies it"
spec, no subagent task contracts, and no structured retry envelope after a
gate failure. Subagents would have to improvise — the exact failure mode G1
eliminated at the tool level.

## Design rules (non-negotiable for this goal)

1. **Cognition in parallel, execution serialized.** Subagents may run
   read-only/local work concurrently (prompts, trends, gates, status, scene
   scripting). Provider generation stays single-writer — the 60s
   shot-by-shot queue in `produce` is the guardrail; no subagent may fan out
   generation calls.
2. **Screening, not trust.** A subagent's output is accepted only when the
   orchestrator runs its deterministic gate (`verify_element`,
   `use_ai=False`). Non-pass → re-dispatch with the failure report, max 3
   retries, then escalate to a human approval gate.
3. **Disk is the only shared state.** Subagents coordinate through the
   `.brandly/` store (project phases, `scenes.json`, jobs, gate verdicts) —
   never in-process memory, so concurrent subagents cannot race.
4. **Fail-closed everywhere.** A failed subagent must be able to corrupt
   nothing: `run --execute` freezes the phase, and resume is re-running the
   same command.
5. **Budget + human gates.** `brandly estimate` before dispatching paid
   subagents; `brandly approve <id> <phase>` before `publish`. Subagents
   never ship.

## PR breakdown (all TDD, RED → GREEN → REFACTOR)

### PR E — Phase handoff contracts (data-only)

- [x] `phase_handoffs(root, project_id) -> dict` in `cmd/production.py`
      (cmd layer, next to `director_plan`; shares `PHASE_ORDER`,
      `phase_costs()`, status/error derivation). Per phase:
      `{id, status, error, inputs, outputs, gate{command,exit_codes},
      next_command, est_cost}`; `current`/`next_command` mirror
      `director_plan` exactly. Delivered in `feature/g7-pr-e-phase-handoffs`.
- [x] `brandly plan <id> [--json]`: human table (Phase/Status/Gate/Est. cost)
      + `--json` one-document output (rich suppressed, #73 convention).
- [x] `agent_surface`: `plan` tool entry (`_build_plan`, CLI_TOOLS, manifest,
      `READ_ONLY_TOOLS` + read-only propagation through `tool_manifest()` /
      `dispatch()`); `brandly plan` is dispatchable via MCP and subprocess.
- [x] `estimate` now routes its per-phase math through `phase_costs()`
      (single formula, one home).
- TDD: 13 tests in `tests/test_phase_handoffs.py` written RED first —
      verified failing on `ImportError` (`phase_handoffs` missing) and on the
      missing `plan` command (exit 2 / click usage error) — then GREEN.

### PR F — Subagent dispatch contracts (prompt layer)

- [x] Director prompt gained a **"Subagent Dispatch"** section in
      `director.py` (pure prompt text): the 5-item per-subagent contract
      (scope, inputs, outputs, boundaries, verification), the
      parallel-cognition / serialized-execution rule (§Design rule 1),
      and the gate-screening loop pointing at
      `brandly plan <project_id> --json`. Delivered in
      `feature/g7-pr-f-subagent-dispatch`.
- [x] `brandly director` prints a compact dispatch table (Phase |
      Gives worker | Must produce | Verify with) after the orchestrator
      plan; `brandly init`'s `AGENTS.md` gets a short "subagent" note
      pointing at `brandly plan --json` as the dispatch source of truth.
- TDD: 8 tests in `tests/test_subagent_dispatch.py` — prompt section,
  dispatch table, AGENTS.md note (string assertions, no behaviour risk).

### PR G — Structured retry envelope + bounded re-dispatch

- [x] `run --execute --until <phase>` on gate failure prints a structured
      `retry_instruction` block: failing gate(s), verdict details, files to
      fix, exact re-run command — data-only, JSON-parseable (agent
      consumes it to re-dispatch a worker subagent with the reason for
      failure). Delivered in `feature/g7-pr-g-retry-envelope` (PR #93,
      squash @ `55139a0`): `run_phase` persists the counter and returns the
      envelope; `run_pipeline` carries it up; the `run` CLI prints
      `Retry attempt: N/3` + the JSON envelope block.
- [x] Bounded loop: retry counter persisted in `project.phases`
      (`attempts`), cap 3 (`MAX_PHASE_ATTEMPTS`); on cap → phase stays
      `failed`, `next_command` becomes the `brandly approve` escalation.
      No unbounded re-dispatch. The state-only `run` path preserves the
      counter too, so a mixed workflow cannot reset it and bypass the cap.
- TDD: 7 tests in `tests/test_retry_envelope.py` — envelope shape,
  cap-exceeded escalation, `plan --json` surfacing, CLI guidance,
  success-after-retry → resume (attempts preserved), state-only
  preservation (RED first, verified failing on `ImportError`).

## Acceptance (goal level)

- [ ] An orchestrator agent (MCP client or shell loop) can drive a
      finished video end-to-end by: read `brandly plan --json` → dispatch
      phase subagents → screen each result with its gate → advance with
      `run --execute --until <phase>` — without inventing tools or state.
- [x] A gate failure produces a `retry_instruction` that a re-dispatched
      subagent can act on directly.
- [ ] Full suite green; ruff/mypy/import-linter clean; README/G6 scope
      matrix updated with the subagent workflow (single-truth pass, G5 rule).
- [ ] Ships as **v0.4.0** (new major capability). If anything regresses:
      `git reset --hard v0.3.26` + `pip install brandly-cli==0.3.26` restores
      the working release.

## Out of scope (this goal)

- No in-process subagent runtime, scheduler, or message passing in
  brandly-cli — the host agent tool is the runtime; brandly exposes plan,
  contracts, and gates only.
- No G4 (ratio policy) / G5 (truth pass) / G6 (publish hardening) rework
  beyond touching their interfaces where PR E/G require.
