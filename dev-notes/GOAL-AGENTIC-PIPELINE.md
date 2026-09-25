# GOAL — Agent-native pipeline: real director orchestration, scene gates, ratio policy

> **Project:** brandly-cli · **Created:** session goal (goal-writer skill)
> **Base:** `main` @ 9fedee4 (v0.3.25) · **Evidence:** `dev-notes/AUDIT-AGENTIC-PIPELINE.md`
> **Sources:** external report (agents invent their own tools; director does not
> orchestrate; scenes broken + ungated; ratio crop must be post-only; scope alignment).

## Program Objective

Make brandly-cli the **single agent-native go-to tool** for filmmakers, content
creators and marketers: an external LLM drives it through a documented tool/manifest
surface, one command takes an idea to a finished, scene-gated, correctly-ratioed
product, and no claim in the README exceeds what the code does.

## Program Context

The audit (`dev-notes/AUDIT-AGENTIC-PIPELINE.md`) confirms all four reported
symptoms with 9 evidenced findings: the tool surface is only wired to the Agnes
model loop (F1), `brandly sync` hands agents raw provider keys (F2), `brandly run`
dispatches nothing while the real orchestrator is dead code (F3/F4), README
overclaims (F5), scenes are positional (F6) with no completeness gate (F7), and
aspect-ratio cropping runs inside production (F8). Per the audit verdict, the
generation half of the product is strong; the pipeline half is claimed but missing.

## Goal order (dependencies)

| Goal | Depends on | Why this order |
|---|---|---|
| G1 Agent-native tool surface | — | Nothing else can be driven by an agent until tools exist |
| G2 Real director orchestration | G1 (optional), G3 (scene ids) | Orchestration must call the *produce* path, not a stub |
| G3 Explicit scenes + scene gate | — | G2's `asset`/`validate` phases need authoritative scenes |
| G4 Ratio policy → assembly only | G3 (assembly reads scenes) | Touches the same produce/stitch seam as G2 |
| G5 Scope truth pass | G1–G4 | README must describe the finished system |
| G6 Publish path for creators/marketers | G5 | Largest new scope; needs an explicit go/no-go |

## Goal 1: Expose brandly-cli's capabilities as agent-callable tools

### Objective
Ship a machine-consumable tool surface — an MCP (stdio) server plus a JSON tool
manifest — so an external agent calls brandly instead of hand-rolling provider HTTP
and ffmpeg, and stop `brandly sync` from writing raw provider keys by default.

### Context
`agent_tools.py:1-13` wires tool schemas only to the Agnes model; repo-wide `mcp`
sweep has zero hits; `python -m brandly_cli --help` exposes no tool surface. Meanwhile
`sync.py:18-25`, `:200-225`, `:228-241` push `AGNES_API_KEY`/`MINIMAX_API_KEY` into
`~/.opencode.json`, `~/.claude/settings.json`, `~/.codex/config.toml`, `.env` files —
so bypassing the pipeline is the documented integration path (F1, F2).

### Deliverables
- [ ] `brandly mcp serve` — stdio JSON-RPC MCP server exposing the real commands:
      `list_projects`, `get_project`, `project_status`, `produce_shots`,
      `job_status`, `job_poll`, `run_gate`, `scenes_status` (G3), `stitch`,
      `export_platforms`
- [ ] `brandly tools --json` — manifest of every exposed tool: name, description,
      JSON-Schema parameters, read/write class, and the CLI command it maps to
- [ ] Tool dispatch module (`brandly_cli/agent_surface.py`) shared by the MCP server
      and the existing Agnes tool loop (no duplicated handlers)
- [ ] `brandly init` writes an `AGENTS.md` into the project root instructing agents to
      use the manifest/tools, never raw provider URLs
- [ ] `brandly sync` requires `--legacy-provider-keys` for the raw-key behaviour;
      default path writes only the brandly tool/CLI guidance, and warns about
      secrets already written
- [ ] README section "Driving brandly from an AI tool" with one worked opencode/Claude
      example

### Definition of Done
- [ ] `brandly tools --json` exits 0 and every entry's schema validates against the
      handler's signature (asserted in a test)
- [ ] An MCP client harness in `tests/test_agent_surface.py` completes
      `initialize` → `tools/list` → `tools/call` for each read-only tool
- [ ] No tool writes outside the selected project context (asserted by a test reusing
      the #75 isolation harness)
- [ ] `brandly sync` without the new flag writes **zero** provider keys into any tool
      config or `.env` (asserted by a test)
- [ ] `pytest tests/test_agent_surface.py -q` passes; full suite green
- [ ] README claim matches the shipped surface (no aspirational tools listed)

### Verification Steps
1. `python -m brandly_cli tools --json | python -c "import json,sys; d=json.load(sys.stdin); assert d['tools']"`
2. `python -m pytest tests/test_agent_surface.py -q`
3. `python -m pytest -q` (full suite)
4. Manual: run an external agent against `brandly mcp serve` and confirm it calls
   `project_status`/`produce_shots` without invoking ffmpeg directly

### Anti-Drift Rules
- Do not build a new REST API or the old read-only Agnes tool set "for symmetry";
  one dispatch layer, MCP + manifest only.
- Do not change existing command semantics to suit the transport.
- Do not remove the raw-key sync path — deprecate it behind the explicit flag.

### Estimated Effort
2–3 focused PRs (medium): surface + manifest + tests, then MCP transport, then sync
deprecation and docs.

## Goal 2: Make the director a real orchestrator (idea → finished product)

### Objective
Give brandly one command that actually executes the pipeline end to end — using the
existing `produce` shot pipeline — with per-phase gates, and delete the stubs that
pretend to do it.

### Context
`cmd/production.py:208-242` (`run`) only flips state and prints "Next: approve";
`approve` (244-310) is presence-checked; the real dispatcher `run_phase`/
`_run_phase_real`/`run_pipeline` (1457-1624) is unreachable — `run_pipeline` has zero
callers and no tests. `_run_phase_real` is itself fake in places (`concept` returns
hard-coded names at 1516-1523; `asset` regenerates one identical prompt at 1540-1561;
`re_edit` says "stitch/captions not yet wired" at 1570-1571), and
`autodirector.auto_direct` (47-95) is a stub reachable only from tests (F3, F4).

### Deliverables
- [ ] `brandly run <id> --execute [--until <phase>] [--yes]` drives
      `Director.run_pipeline`, resumable from `project.phases`
- [ ] `script` phase writes a real `shots.json` (scene ids per G3) from
      `video_prompts`/storyboard skills — no hard-coded concept list
- [ ] `asset` phase invokes the `produce` runner (shot_runner): scene naming,
      identity anchors, retries, production-plan rows, cost recording — never a
      private generation loop
- [ ] `re_edit` phase stitches scenes + attaches captions/audio; `validate` phase
      runs the scene gate (G3) before allowing advance; `publish` phase calls
      `export-platforms`
- [ ] Phase advance fails closed when the phase gate fails (no state-only approval)
- [ ] `autodirector.auto_direct` either delegates to the real pipeline or is deleted;
      `tests/test_autodirector.py` updated accordingly (no test locking a stub)
- [ ] `brandly director` prints the orchestrator plan (phases, current step, next
      command) in addition to the prompt text

### Definition of Done
- [ ] E2E test with mocked providers: `init` → `run --execute` produces
      `videos/scenes/Scene-01-Shot-1-1.mp4…`, a stitched output, and an export bundle
- [ ] Killing the run mid-way and re-running resumes without regenerating completed
      shots (asserted via production-plan/`completed_ids` state)
- [ ] A gate failure blocks `current_phase` advance (asserted by test)
- [ ] No `run_phase`/`_run_phase_real` code path remains untested
- [ ] `python -m pytest -q` green; CI green

### Verification Steps
1. `python -m pytest tests/test_pipeline_orchestration.py -q`
2. `python -m pytest tests/test_autodirector.py -q` (stub assertions removed)
3. Manual: `brandly run <id> --execute --until validate` on a scratch project with a
   mocked provider, then kill/restart and confirm resume
4. `python -m brandly_cli run --help` shows the new flags

### Anti-Drift Rules
- Reuse `shot_runner`/`produce`; do not build a second generation path.
- Do not make `--execute` the default (existing scripts rely on current `run`).
- Do not wire the pipeline into the provider clients; orchestration stays in `cmd/`.
- If a phase cannot be implemented truthfully now, it must report "not implemented"
  and fail closed — never return a fabricated success payload.

### Estimated Effort
3–4 PRs (high): script/asset phases, re_edit/validate/publish phases, resume+gates,
stub removal.

## Goal 3: Explicit scene model + scene completeness gate

### Objective
Make scenes first-class data with stable ids, and add a gate that fails unless every
shot of a scene exists, is the current take, and passed its quality gate.

### Context
Scene numbers are positional (`shot_runner.py:270-271`, `:333-334`), filenames repeat
the scene number twice (`:104-114`), two acts each own their own `scene 1..N`
namespace (#50 patched names only, `:162-174`), and no `Scene` model exists in
`types.py`. No gate is scene-aware (`quality_gate.py` has no scene concept;
`cmd/tools.py:207-238` uses flat counts; `web/routes/gate.py:14-15` is per clip) —
F6, F7.

### Deliverables
- [ ] `Scene` (id, index, act, title, shot_ids, expected count) + `Shot.scene_id` in
      `types.py`; scene ids explicit and project-unique (`S01`, `S02`, …)
- [ ] `scenes.json` written atomically by `produce` (source of truth beside
      `production_plan.md`): scenes, their shots, filenames, gate status
- [ ] `brandly scenes status <id> [--json]` — per-scene matrix: expected / present /
      missing / stale / gate-failed
- [ ] `brandly gate <id> --scene S01` (and `--all-scenes`) → PASS only when every
      expected shot exists, is the current take, and passed the deterministic gate
- [ ] The scene gate blocks phase advance in G2 and is exposed in the studio
      (`web/routes/gate.py` + a scene panel)
- [ ] Backward compatibility: shot lists with only positional scenes keep working; the
      implicit mapping is written explicitly into `scenes.json` once
- [ ] README + `brandly produce --help` document the scene contract

### Definition of Done
- [ ] Test: a 3-shot scene with 1 missing clip → `gate --scene` exits non-zero and
      names the missing shot id
- [ ] Test: a scene whose clip is a superseded prior take → FAIL naming the stale file
- [ ] Test: all shots present + gate-passed → PASS, and `scenes status --json` reports
      `expected == present` per scene
- [ ] Two acts that both contain `scene 1` are distinct scenes in data (the #50
      ambiguity is resolved in data, not only in filenames)
- [ ] `tests/test_shot_runner.py`, `test_issue_49.py`, `test_issue_50.py` pass
      unchanged
- [ ] `python -m pytest -q` green

### Verification Steps
1. `python -m pytest tests/test_scenes.py -q`
2. `python -m pytest tests/test_shot_runner.py tests/test_issue_49.py tests/test_issue_50.py -q`
3. Manual: `brandly scenes status <id> --json` on a partially generated project
4. Manual: delete one clip, confirm `brandly gate <id> --scene S01` fails

### Anti-Drift Rules
- Scene ids are data, not a filename convention — do not re-encode policy in names
  (keep existing names for compatibility, but stop treating them as truth).
- Do not introduce a second manifest; extend the production-plan/`scenes.json` pair.
- Do not change `clip_filename()` output (assembly tooling and users depend on it).

### Estimated Effort
2–3 PRs (medium-high): model + manifest, gate + status, studio/doc wiring.

## Goal 4: Aspect-ratio cropping happens only in assembly/export

### Objective
Production produces source-aspect masters; cropping to a target ratio happens once, in
post-production assembly/export, with explicit crop-vs-fit semantics.

### Context
`shot_runner.py:424-426` documents "every freshly generated clip is cropped … after
naming (issue #40)" and `apply_aspect_ratio()` is called inside the shot loop
(`:752-772`); `cmd/production.py:442-446` exposes `produce --aspect-ratio` and the
`asset` phase hard-codes `aspect_ratio="16:9"` (1552). Post-production meanwhile only
scales/letterboxes (`cmd/post.py:181-205`, `export_platforms.py:163-186`) — two owners,
one irreversible decision taken at the most expensive point (F8).

### Deliverables
- [ ] Remove ratio cropping from the production path: `shot_runner` no longer calls
      `apply_aspect_ratio` in the shot loop; generated clips keep source aspect
- [ ] `brandly produce --aspect-ratio` deprecated: prints a one-line migration notice
      and defers the crop to assembly (kept as an alias for one release; removal
      tracked in the changelog)
- [ ] New post-production owner: `brandly stitch --ratio 2.39:1 --fit crop|pad`
      (single implementation in `stitch`/`edit`, reused by `export-platforms`)
- [ ] `export-platforms` uses the same ratio function with per-platform defaults
      (crop for feed aspects, pad only when explicitly requested)
- [ ] `_run_phase_real`'s `asset` phase stops passing `aspect_ratio` (1552)
- [ ] Docs: production vs post-production responsibility table; migration note in
      CHANGELOG (`Changed`)

### Definition of Done
- [ ] Test: after `produce`, every generated clip's probe dimensions equal the source
      aspect (no crop) even when `--aspect-ratio` was passed
- [ ] Test: `stitch --ratio` output probes to the exact target ratio
- [ ] Test: `export-platforms` for a 9:16 platform yields cropped output, and
      `--fit pad` yields letterboxed output — both from the same masters
- [ ] `grep -rn "apply_aspect_ratio" src/brandly_cli/shot_runner.py` shows no call in
      the shot loop; the function survives (or moves) with ≥1 direct unit test
- [ ] No double-crop: stitch→export pipeline test asserts dimensions are stable
- [ ] `python -m pytest -q` green; existing #40/#48 tests updated where they asserted
      production-time cropping (behaviour change is intentional and documented)

### Verification Steps
1. `python -m pytest tests/test_ratio_policy.py -q`
2. `python -m pytest tests/test_issue_48.py tests/test_stitch.py tests/test_export_platforms.py -q`
3. Manual: `brandly produce … --aspect-ratio 2.39:1` → clips un-cropped + notice;
   `brandly stitch … --ratio 2.39:1` → cropped master
4. `python -m brandly_cli stitch --help` shows `--ratio/--fit`

### Anti-Drift Rules
- One ratio implementation, in post-production. Do not leave a second crop path "for
  speed" in produce.
- Do not silently change `--aspect-ratio` semantics; emit the deprecation notice and
  document the migration.
- Do not introduce resolution downscaling in the same change (separate concern).

### Estimated Effort
1–2 PRs (medium): remove production crop + deprecation, add post ratio ownership, docs.

## Goal 5: Scope truth pass — claims, capability matrix, gap register

### Objective
Make every public claim match the code: honest README, a machine-readable capability
matrix, and tracked issues for each verified gap.

### Context
README:27-28 promise a multi-agent automated pipeline and a director orchestrator that
F3/F4 show are not implemented, and README:160-167/288 send users down that path (F5).
The persona table in the audit (F9) shows which capabilities are real, partial or
absent for filmmakers/creators/marketers.

### Deliverables
- [ ] `brandly capabilities --json` (+ text) emitting per-persona support status,
      derived from a single source list in code, not prose
- [ ] README "What is Brandly?" rewritten to the audited reality: what runs today vs
      what is planned, with links to the goal/issue that will change it
- [ ] `dev-notes/AUDIT-AGENTIC-PIPELINE.md` reachable from README (single source of
      truth for gaps)
- [ ] One GitHub issue per open gap (scene gate, publish/schedule, brand kit, metrics
      ingest), each referencing the audit finding id (F6/F7/F9)
- [ ] CI guard: a test asserts README does not claim unimplemented capabilities
      (checked against the capability list)

### Definition of Done
- [ ] `brandly capabilities --json` exits 0 and lists ≥1 row per persona
- [ ] Test: the capability list and README claims stay in sync (fails when a claim has
      no implementing capability entry)
- [ ] README has no statement that F3/F4/F7/F9 contradict (reviewed line by line)
- [ ] Issues created and linked from the audit file
- [ ] `python -m pytest tests/test_capabilities.py -q` green

### Verification Steps
1. `python -m brandly_cli capabilities --json | python -c "import json,sys; print(len(json.load(sys.stdin)['capabilities']))"`
2. `python -m pytest tests/test_capabilities.py -q`
3. `gh issue list --state open` shows the gap issues referencing F-ids
4. Manual: read README top-to-bottom, confirm no aspirational claim remains

### Anti-Drift Rules
- This goal does not implement features; it only makes claims true. Implementation
  goes to its own goal/issue.
- Do not delete honest roadmap content — mark planned work as planned.

### Estimated Effort
1 PR + issue creation (low-medium).

## Goal 6: Close the creator/marketer loop with a publish path

### Objective
Add a credential-gated, dry-run-first publishing path (upload/schedule per platform)
so creators and marketers can finish the job inside brandly instead of leaving the
tool after export.

### Context
`export`/`export-platforms` (`cmd/post.py:48`, `:362`) write files; `share`
(`sharing.py`) returns a link. Nothing uploads or schedules; there is no brand-kit
enforcement and `analyze` is a heuristic (`analyze`, audit F9). The audit's verdict is
that the generation half is strong and the last mile is missing — this goal is the
last mile, and it is deliberately **decision-gated** because it adds external-account
scope.

### Deliverables
- [ ] Decision record in `dev-notes/` — publish path in scope for v0.4 (yes/no), with
      the platform set chosen (start with 1–2)
- [ ] If yes: `brandly publish <id> --platform <p> [--schedule <iso>] [--dry-run]`
      over a small adapter interface, `--dry-run` the default until credentials are
      explicitly configured
- [ ] Credential storage via `brandly config` (no keys in `.env` sprawl — see F2),
      with a test asserting no secrets are written to project files
- [ ] `brandly brand <id>` — brand kit (logo/colour/font/claim lock) applied to
      thumbnails/exports, with a failing test proving a conflicting style is rejected
- [ ] Capability matrix (G5) updated to "supported" only when the e2e dry-run test
      passes

### Definition of Done
- [ ] Dry-run publishes render the exact request payload (snapshot test) and never
      hit the network
- [ ] A wrong/missing credential fails closed with an actionable message and a
      non-zero exit
- [ ] No secret material appears in any project artifact (test scans the project tree)
- [ ] `brandly capabilities --json` reports the publish row as supported
- [ ] `python -m pytest -q` green

### Verification Steps
1. `python -m pytest tests/test_publish.py tests/test_brand_kit.py -q`
2. Manual dry-run: `brandly publish <id> --platform <p> --dry-run --json` → payload
   only, no network
3. `python -m brandly_cli capabilities --json` → publish row supported
4. Credential scan: `grep -r "API_KEY" .brandly/<project>` → no hits

### Anti-Drift Rules
- One platform at a time; do not build a scheduler service or a UI.
- Never enable live posting by default; dry-run first, explicit credentials second.
- Do not add provider/account secrets to `.env` files (this is the F2 failure mode).

### Estimated Effort
2–3 PRs (medium-high), only after the decision record says yes.

---

## Program-level Definition of Done

- [ ] G1–G6 each meet their own Definition of Done; no goal is "closed" on partials
- [ ] `python -m pytest -q` green on `main` and CI green for every merged PR
- [ ] An external agent can drive a full project (idea → stitched, scene-gated,
      ratio-correct output) using only brandly tools — demonstrated in a test harness
      (G1 + G2 + G3)
- [ ] No production-time cropping remains (G4); no README claim exceeds the code (G5)
- [ ] Audit findings F1–F9 each mapped to a merged PR or an open issue with an F-id
- [ ] `dev-notes/AUDIT-AGENTIC-PIPELINE.md` updated with the closing evidence

## Program-level Verification

1. `python -m pytest -q` (full suite) — no skipped/xfailed tests introduced
2. `python -m pytest tests/test_agent_surface.py tests/test_pipeline_orchestration.py tests/test_scenes.py tests/test_ratio_policy.py tests/test_capabilities.py -q`
3. `python -m ruff check src tests && python -m mypy src/brandly_cli && python -m lint_imports`
4. `gh run list --branch main --limit 3` → all `success`
5. Manual acceptance: `brandly init … && brandly run <id> --execute` → finished,
   scene-gated, ratio-correct output

## Program Anti-Drift Rules

- One goal at a time, in the documented order; do not reorder G2 before G3 (scenes are
  the data model G2 consumes).
- TDD is mandatory (RED → GREEN → REFACTOR). Bug fixes start with a regression test.
- Every PR follows the PRIDES taxonomy: `feature/`, `fix/`, `chore/` branch →
  rebase → PR → review → merge; no direct pushes to `main`.
- Do not add new provider integrations, new UI surface, or new abstractions while
  closing these gaps.
- Do not delete existing tests to make a goal pass; update them only when the
  behaviour change is documented in the same PR's changelog entry.
- Respect the documented non-goal from #72: `brandly init` continues to use the current
  Brandly project context.

## Tradeoffs surfaced (not decided unilaterally)

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| Agent transport | MCP stdio server | CLI-only + instructions | MCP: LLMs already speak it; CLI remains the fallback (G1) |
| `produce --aspect-ratio` | Keep as alias (warn) for one release | Remove immediately | Alias: avoids breaking existing pipelines (G4) |
| `autodirector.auto_direct` | Delete | Delegate to real pipeline | Delete: it is unreachable and locks a stub in tests (G2) |
| Publish path | Build now | Decide first | Decide first (G6 is decision-gated) |
| Studio pipeline control | Add now | After G2 CLI works | After: one orchestration implementation (G2/G3) |

## Execution log

- 2026-09-24 — Deep audit completed (`dev-notes/AUDIT-AGENTIC-PIPELINE.md`), 9 findings
  with file:line evidence; this goal document written from it.
- 2026-09-24 — Phantom project trees from the pre-#75 bug removed from the working
  tree: `.brandly/untitled/` and `.brandly/undefined/` (21 stale files, git-ignored).
  `.brandly/` now contains only `passport-rush-taxi-chase`.
- 2026-09-24 — Awaiting approval to start G1.
- 2026-09-25 — G4 implemented on `feature/ratio-policy-assembly`: the shot loop no
  longer calls `apply_aspect_ratio` (the function survives as the manual/post-
  processing crop tool, still covered by `tests/test_issue_48.py`); `stitch`
  gained `--ratio/--fit` with the single shared filter implementation
  (`ratio_crop_filter` / `ratio_pad_filter` in `stitch.py`); `export-platforms`
  gained `--fit` (crop default, pad on request) reusing the same builders, and
  a source already within 2% of the target ratio is a no-op (no double-crop);
  `produce --aspect-ratio` is now a deprecated no-op alias that prints a one-line
  migration notice (removal tracked in CHANGELOG). 19 new tests in
  `tests/test_ratio_policy.py`; full suite green.
- 2026-09-25 — G5 executed on `chore/scope-truth`: `brandly capabilities`
  command + `brandly_cli/capabilities.py` single source of truth (per-persona
  rows, machine-readable via `--json`); README "What is Brandly?" rewritten to
  the audited reality (what runs today vs planned, linked to the audit);
  `tests/test_capabilities.py` CI guard fails when a README claim has no
  capability entry; open F9 gaps filed as issues #97 (publish/schedule, G6
  decision-gated), #98 (brand kit), #99 (metrics ingest) and linked from the
  audit's new gap register (scene gate noted as closed by G3 — no issue).
- 2026-09-25 — G6 PR 1/3 on `feature/publish-dry-run`: decision record
  DEV-G6-001 (yes, YouTube first, dry-run-first, credential-gated);
  `brandly publish` over a small `Adapter` interface (pure payload builder +
  live executor, fail-closed without credentials); `brandly config
  set/get/list` user-level credential store (no secrets in project files or
  `.env` — F2); capability row `publish_schedule` moved absent→partial.
  Live-proof and TikTok/IG adapters remain G6 PRs 2–3.




