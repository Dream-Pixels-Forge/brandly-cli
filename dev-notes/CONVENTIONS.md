# Conventions — brandly-cli

> **Status:** STRICT MANDATORY. Established 2026-10-01 while implementing the
> Studio shell from the Paper design (PR #185, merged as `ed54983`).
> Referenced by `AGENTS.md` §0 and workspace `~/.agents/AGENTS.md` §10.

## 1. The design→code pipeline

```
Phase 0  Recon        read dev-notes/PROGRESS.md + the code you will change
Phase 2  Govern       freeze the design spec + goal with gates
Phase 3  Engineer     TDD per increment: RED → GREEN → gates
         Deliver      commit → push → PR → review → merge
```

Every phase produces an artifact; a phase is not done until its artifact
exists and its gates are green.

## 2. TDD per increment (RED → GREEN)

1. Write the contract test **first**.
2. **Run it and observe the failure** — that is the RED evidence.
3. Implement the minimum to make it pass.
4. Re-run every gate.

Never write code first and backfill a test. Never comment out, `.skip()` or
`xfail()` a test to get green.

## 3. Frontend verification convention

**Rule:** verify frontend work with Python source-contract tests + the
`web-quality` CI job. **Do not add a JS test runner** (vitest/Jest) without a
ratified decision — `tests/test_web_panels_wired.py` and
`test_web_shell_boot.py` both state *"no JS test runner in CI yet — see #61"*
and issue #61 remains open.

Why: it is the repo's ratified, CI-enforced convention. Inventing a new test
architecture mid-task is exactly the drift this rule prevents.

## 4. Anti-drift scope rule

If a design artifact does not exist, the feature is **out of scope**:

- An empty Paper artboard ⇒ that screen is not designed ⇒ do not build it.
- A missing store/API field ⇒ that datum does not exist ⇒ do not render it.

Record every deferral in `dev-notes/PROGRESS.md` under `DEFERRED` /
`out of scope`. Never silently skip.

## 5. Data honesty in the UI

| Situation | Required behaviour |
|---|---|
| Store/API has no value for a field | Omit it, or render `—` — never invent a number |
| Action has no backend | Render `disabled` + explanatory `title` — never a no-op handler |
| State cannot be derived | Say so (e.g. *"no gate score on the clip record"*) — never fake a "current" marker |

Worked examples from PR #185: the Status Bar omits gate score / credit budget
/ worker RSS; `ClipInspectorPanel` disables **Approve** and discloses the
missing gate score; `PhaseStepper` does **not** mark a fabricated PRIDES
"current" step; `PipelineStepper` derives only from `exportDone`.

## 6. Tokens and styling

- **Reuse** the existing CSS variables (`--md-*`). Never fork a second token
  namespace.
- You may **define** a variable that is referenced but missing (that is a bug
  fix — see §8).
- Match the frozen shell metrics: Header 52 · Toolbar 40 · Body · Status Bar
  28; sidebar 248; Main `padding:14` `gap:12`.
- No `display:grid`, no margins for layout; flex + gap + padding.

## 7. Git safety

Before switching branches:

1. `git rev-list --count main..HEAD` and `HEAD..main` — is it diverged?
2. `git diff --name-only HEAD main -- <paths you touched>` — any overlap?
3. If there is overlap, **stop** and reconcile first.

Never clobber unrelated work. Never merge without review. Never merge a
branch with failing or skipped tests.

**Non-negotiable merge condition:** every CI check green, zero lint warnings,
no unresolved review threads.

## 8. Fixing latent defects found mid-task

If you discover a defect (e.g. a CSS variable referenced ~20 times but never
defined), fixing it is in scope **if the design requires it**. Otherwise
record it in `dev-notes/PROGRESS.md` and leave it.

Defects found by a gate (build, lint, test) are always fixed before done.

## 9. Deferrals ledger (live)

| ID | Item | Why deferred | Status |
|---|---|---|---|
| B2 | V2 overlay track on the timeline | No overlay-track data model in the store/API | Out of scope — not fabricated |
| 05 | Review Queue screen redesign | Paper artboard `1T8-0` is empty | Blocked on design |
| 06 | Agnes AI Synthesizer screen | Paper artboard `1T9-0` is empty | Blocked on design |
