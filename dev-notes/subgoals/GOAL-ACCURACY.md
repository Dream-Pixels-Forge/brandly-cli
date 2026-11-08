# GOAL — Measured truth: self-correcting, agent-drivable film

> **Project:** brandly-cli · **Created:** goal-audit session (goal-writer)
> **Base:** `main` @ `70623d0` (v0.10.2) · **Suite:** 1319 passed / 0 failed
> **Evidence:** architectural audit of `origin/main` (agent surface, quality
> gate, shot runner, provider seam, quota model)
> **Extends:** `GOAL-AGENTIC-PIPELINE.md` (G1–G6, shipped) with the accuracy
> half that the audit found missing.

## Program Objective

Make brandly-cli produce **self-correcting, verifiably-measured films** that an
agent can drive end-to-end **without ever being lied to about the result**.

**North star (unchanged):** agents drive it; cinema is the core bone; everything
reads like a film.

## Program Context — the one root cause

The audit scored the original goal at **~65%** and found that all four gaps are
the *same* bug at different layers:

> **brandly trusts requests, not reality.**

| Symptom | Evidence | Status |
|---|---|---|
| 8–12s shots return as 5–6s | `agnes_client.py:654` clamps the **request**; `shot_runner` writes the clip and records `OK` without measuring it | never measured |
| Video is never vision-judged | `production.py:1563,2799` pass `use_ai=False` | **capability already built** (`_extra_video_frames`, issue #171) |
| Gate fails open | no `AGNES_API_KEY` ⇒ status `skipped`, never a failure | by design, undocumented as a trust issue |
| No closed loop | nothing measures the finished film and re-plans | `--only` re-runs already mature (issue #49) |

**Key economic fact:** two of the four gaps are *switched-off or unmeasured
capability*, not missing features. The measuring primitives already exist three
times over (`stitch._clip_duration`, `quality_gate._probe_video`,
`beat_sync._get_duration`). This program is therefore mostly **wiring, policy
and honesty** — not a new engine.

## Honest current state

| Goal clause | Score | Verdict |
|---|---|---|
| Agents can drive it | **90%** | genuinely met (15-tool MCP surface; tools map to real CLI argv) |
| Cinema as core bone | **70%** | real cinematography layer; no dramatic-arc model |
| Long video | **55%** | architecturally unbounded, externally throttled |
| Accurate result | **55%** | strong on stills, **unverified on footage** |

## Goal order (dependencies)

| Goal | Depends on | Why this order |
|---|---|---|
| **G7 Duration truth** | — | Keystone. Nothing can be reconciled that is not measured |
| **G8 Continuation take** | G7 | Needs the measured shortfall to compute the retry |
| **G9 Video judging wired** | — | Shipped capability; independent of G7 |
| **G10 Closed rework loop** | G9 | Scorecard needs verdicts to score |
| **G11 Fail-honest** | — | Small, independent, high trust value |
| **G12 Narrative beats** | G7 | Durations derive from beat role (G7) |
| **G13 Quota-aware planning** | G7 | Ledger needs real durations to schedule |
| **G14 Provider seam** | — | Design-only this cycle |

G9 and G11 are the cheapest high-leverage wins: one is a flag, one is a status
literal. G7 is the keystone everything else leans on.

---

## G7: Duration truth — measure every returned clip

### Objective
Stop trusting the requested duration. Measure the delivered one, record both,
and never report a short clip as a success.

### Context
`agnes_client.py:654` sends `body["seconds"] = str(max(4, min(12, duration or 5)))`.
The response is never validated. `shot_runner` records `OK` and moves on, so a
5–6s take for a 12s request is indistinguishable from success. The gotcha is
already *documented as a comment* (`shot_runner.py:111-113`) but never *handled*.
Meanwhile `stitch.py:147` already ffprobes real clip lengths for the final cut —
so the film is real-length and silently shorter than the script.

### Deliverables
- [ ] One shared probe helper for clip duration (3 existing duplicates collapse
      to a single call site) — do not add a 4th
- [ ] After each clip lands, measure it; persist `requested_s`, `measured_s`,
      `delta_s` in the shot record
- [ ] Separate the **legal** max (12s, provider) from a **reliable** max (~6s);
      treat 7–12s as a measured-risk zone
- [ ] `get_timeline` returns `measured_duration` + `duration_status`
      (`ok` | `short` | `continuation`)
- [ ] A shot that came up short is **never** recorded `OK`

### Acceptance criteria
- [ ] A stub client returning 4.5s for a 6s request produces a `SHORT` record,
      not a silent `OK` (regression test)
- [ ] `--dry-run`/timeline output shows requested vs measured side by side
- [ ] No clip is `OK` with `measured_s` short beyond tolerance
      (tolerance = `max(1s, 10%)`)

---

## G8: Continuation take — reconcile a short clip instead of shipping it short

### Objective
When a clip comes up short, spend a bounded extra request to finish the action
rather than shipping a truncated shot.

### Context
The credit is already spent whether or not we retry, so a continuation costs
latency, not credits. `split_long_shots` (`shot_runner.py:699`) already splits
over-long shots into 6s parts and attaches a `[CONTINUITY]` directive — the
vocabulary for a continuation take already exists.

### Deliverables
- [ ] Tiered reconcile: within tolerance ⇒ accept; beyond tolerance ⇒
      continuation take for **the shortfall only**, then head+tail stitch
- [ ] Bounded: max N continuations per shot (default 2), then mark `SHORT` and
      record the real duration
- [ ] Continuation prompt carries the shot identity anchor (issue #38 mechanism)
      so the seam is not a visible jump cut
- [ ] Every continuation attempt is recorded in the shot record

### Acceptance criteria
- [ ] A 4.5s take for a 6s request triggers exactly one continuation, and the
      stitched result is ~6s (regression test)
- [ ] Continuations stop at the bound and leave an honest `SHORT` status
- [ ] The cost tracker attributes the extra request (no silent over-spend)

---

## G9: Wire the vision gate to video clips

### Objective
Judge the footage, not just the plates. The capability already exists — switch
it on with a cost-aware policy.

### Context
`quality_gate._extra_video_frames` (issue #171) samples N evenly-spaced frames
and judges them in **one** call; `judge_frames` accepts 1–8; the CLI already
exposes `--use-ai/--no-ai --judge-frames N` (`cmd/gate.py:252,314`). The only
reason video is unverified is that the produce path passes `use_ai=False`
(`production.py:1563,2799`).

### Deliverables
- [ ] Gate policy `off | scene-first | all` (default `scene-first`: the first
      clip of each scene — highest identity signal per credit)
- [ ] `judge_frames=3` for the scene-first clip (first + 2, one judge call)
- [ ] A FAIL on a judged clip blocks **that scene**, matching the existing
      keyframe discipline (`production.py:1569`)
- [ ] The verdict is persisted per scene and surfaced in the scorecard

### Acceptance criteria
- [ ] Default produce records a vision verdict for the first clip of every
      scene (regression test with a stub judge)
- [ ] A stub judge returning drift on scene 1 blocks scene 1 and not scenes 2+
- [ ] `--gate-ai off` restores today's behaviour exactly

---

## G10: Close the loop — scene scorecard and bounded rework

### Objective
Turn measurement into correction: a scene that scores badly is re-run, and only
that scene.

### Context
Today `validate` runs a per-scene deterministic gate and stops. Nothing looks at
the aggregate, so a bad scene is carried into the final cut unless a human
notices. `--only` targeted re-runs are already mature (issue #49), and the
director prompt is already an LLM loop that can act on instruction.

### Deliverables
- [ ] `validate` emits a **scene scorecard**: identity consistency, drift,
      duration fidelity, slop
- [ ] Below threshold ⇒ scene marked `NEEDS_REWORK`
- [ ] The director is told to re-run **only** that scene via `--only`
- [ ] Bounded: ≤2 rework attempts per scene, then stop and report (bounded-loop
      mandate — no unbounded agent loop)
- [ ] Data honesty: a missing dimension is `unverified`, never a passing score

### Acceptance criteria
- [ ] A scorecard below threshold triggers a targeted re-run of that scene
      only, capped at 2 attempts (regression test)
- [ ] Scenes at or above threshold are not re-run
- [ ] The attempt cap is enforced, not advisory

---

## G11: Fail-honest — `UNVERIFIED` is never `PASS`

### Objective
An unverified result must never be reported as a verified one. This is the
repo's own data-honesty rule, applied to the gate.

### Context
Without `AGNES_API_KEY` the gate marks AI analysis `skipped` — a warning, never
a hard failure. So a project can complete with `PASS` on every element while
nothing was actually verified. The reference path (`generation.py:503`) is
likewise advisory + human review rather than fail-closed.

### Deliverables
- [ ] New status literal `UNVERIFIED`, distinct from `PASS`/`WARN`/`FAIL`
- [ ] Absent a judge ⇒ `UNVERIFIED` (never `PASS`), recorded in the report
- [ ] `--strict` (and produce's default) exits non-zero on `UNVERIFIED`
- [ ] `UNVERIFIED` surfaces in the timeline so the agent knows it is blind

### Acceptance criteria
- [ ] A no-API-key run never yields `PASS` for an AI-judged element
      (regression test)
- [ ] `UNVERIFIED` is non-zero in strict mode, non-fatal in lenient mode
- [ ] The gate report and the timeline both distinguish `UNVERIFIED` from `PASS`

---

## G12: Narrative beats — give the film a shape

### Objective
Make "everything reads like a film" structural, not only cinematographic.

### Context
The 10-phase pipeline produces well-framed shots in a production order, but
nothing enforces a dramatic arc: no act structure, and shot durations are
hand-entered per shot rather than derived from narrative role. A reel of
beautiful shots is not a film.

### Deliverables
- [ ] Beat labels on shots: `setup | turn | consequence | resolve`
- [ ] The `script` phase **rejects** a shot list missing required beats (a
      completeness contract, in the spirit of the existing scene gate)
- [ ] Shot durations **derive** from beat role rather than hand-entry
- [ ] Derived durations land in the reliable 4–6s window (feeds G7's split
      policy for free)

### Acceptance criteria
- [ ] A shot list with no `resolve` beat is rejected at the `script` phase
      (regression test)
- [ ] Beat role determines duration; editing a duration alone does not
      override the beat-derived value
- [ ] Existing projects without beat labels still load (back-compat)

---

## G13: Quota-aware planning — design for growth, don't fight 500s/day

### Objective
Accept the current 500 video-seconds/day ceiling for now, but make the tool
*schedulable* across days so growth is configuration, not redesign.

### Context
`NOMINAL_VIDEO_SECONDS_PER_DAY = 500` (`cost_tracker.py:16`) ≈ 8 minutes of
finished footage per day. The pipeline is **already resumable** (`--until`,
`produce_progress.txt`, `--only`), so multi-day long-form is architecturally
within reach — it just isn't *scheduled*. The #214/#192 preflight warns about
budget/quota but does not plan against it.

### Deliverables
- [ ] Quota ledger as a first-class budget object (seconds used/remaining)
- [ ] `--target-duration` warns when a plan exceeds the remaining quota and
      proposes a **multi-day schedule** (shots/day split)
- [ ] A run resumes cleanly across day boundaries
- [ ] Duration fidelity from G7 feeds the schedule (no planning on fiction)

### Acceptance criteria
- [ ] A `--target-duration 900` run under 500s remaining proposes a 2-day
      schedule and says so *before* spending (regression test)
- [ ] Resuming on day 2 continues the same shot list without duplication
- [ ] The ledger survives a crash mid-run (no double-counted seconds)

---

## G14: Provider seam — make video backends pluggable

### Objective
Turn the Agnes-only video path into one implementation of a `VideoBackend`
protocol, so a second provider (or a local model) is additive.

### Context
Video generation is effectively single-provider:
`DEFAULT_AGNES_VIDEO_MODEL = "agnes-video-2.5-flash"` (`constants.py:226`) with
no failover. `providers.py` shows intent, but there is no seam — adding a
backend today means touching `shot_runner`/`agnes_client`. This is the main
architectural fragility behind both the 12s cap and the daily quota.

### Deliverables
- [ ] A `VideoBackend` protocol (submit → poll → fetch clip, plus a capability
      descriptor: max duration, reliable duration, rate limits)
- [ ] Agnes becomes one implementation; `shot_runner` depends on the protocol
- [ ] The capability descriptor drives G7's split policy and G13's quota estimate
- [ ] **Design + protocol only this cycle** — no second provider ships

### Acceptance criteria
- [ ] `shot_runner` no longer imports a provider client directly
- [ ] The capability descriptor drives split/quota decisions (unit-tested with
      a fake backend)
- [ ] A second backend is a new file, not a change to `shot_runner`
      (demonstrated by a test double)

---

## Non-goals (this cycle)

- **Exceeding 500 video-seconds/day.** Accepted as the operating ceiling.
- **Shipping a second video provider.** G14 is the seam only.
- **A full dramaturgy engine.** G12 is a shape contract, not a story generator.
- **Rewriting the director loop.** The LLM-loop-over-CLI shape is correct.

## Why this is the *accurate* goal

It targets the one thing that is actually broken — **trusting requests over
reality** — instead of adding features. G7–G11 close the accuracy gap, G12
closes the "like a film" gap, and G13–G14 make growth a configuration change
rather than a redesign.

**Projected confidence on the original goal: ~65% → ~85%**, with the residual
15% genuinely external (provider output quality, quota) rather than
architectural — which is the correct place for the remainder to live.



