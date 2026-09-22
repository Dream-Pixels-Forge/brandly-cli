# brandly-cli — Architecture Diagram & Groundedness Assessment

Companion to `ARCHITECTURE.md`. Generated from a static import-graph analysis
of the 39 modules in `src/brandly_cli/` (AST-level, main branch after PRs #44/#45).
Machine-readable graph: `dev-notes/_arch.json`.

## 1. Dependency diagram (layered)

Arrows = module-level imports only; edges marked `···` are **deferred
(function-local) imports** — weaker coupling, no import-time risk.

```mermaid
graph TD
    subgraph L5["Orchestration (L5)"]
        CLI["cli.py · 4.8k lines · 64 commands<br/>fan-out 30 (god module)"]
        AGT["agent_tools"]
    end

    subgraph L4["Pipeline (L4)"]
        SR["shot_runner<br/>(pure logic: flatten, progress,<br/>retries, split, aspect-ratio)"]
        QG["quality_gate<br/>(pre-checks + AI verdict + policy)"]
        MGR["migrate (v2 layout)"]
        POST["stitch · edit · beat_sync · dubbing<br/>captions · thumbnails · sync · export_platforms<br/>(leaf-ish post-production)"]
    end

    subgraph L3["Prompting (L3)"]
        VP["video_prompts<br/>(8-layer schema, section model) — LEAF"]
        SP["style_presets → constants"]
        DIR["director<br/>fan-out 13 (second hub)"]
        CE["cinematic_enhancer · analyzer · autodirector"]
    end

    subgraph L2["Providers (L2)"]
        AC["agnes_client (primary)"]
        MMC["minimax_client"]
        ARC["ark_client"]
        AAC["audio_client"]
        IC["image_convert"]
    end

    subgraph L1["State (L1)"]
        PM["project_manager<br/>(+ sync_production_state)"]
        CT["cost_tracker"]
        MEM["memory · issue_tracker · sharing<br/>webhook · templates · trends"]
    end

    subgraph L0["Foundation (L0) — zero or near-zero deps"]
        LAY["layout (path SoT, v1+v2)"]
        CTS["constants (model registry)"]
        TYP["types (pydantic)"]
        UT["utils (plans, JSON, discovery)"]
    end

    CLI --> SR & QG & MGR & POST & DIR & CE & AGT
    CLI --> AC & MMC & ARC & AAC
    CLI --> PM & CT & MEM & SP
    CLI --> LAY & CTS & TYP & UT & VP

    DIR --> VP & SP & CTS
    DIR --> AC & ARC & AAC
    DIR -- ··deferred·· --> QG
    DIR --> PM & MEM & UT & TYP

    SR --> VP
    QG --> AC
    QG -- ··deferred·· --> CTS & LAY
    MGR --> LAY

    AC -- ··deferred·· --> SP
    ARC -- ··deferred·· --> SP
    AC <-.-> AGT

    PM --> LAY & TYP & UT
    CT --> UT & CTS
    UT --> LAY
    SP --> CTS
```

**Structural invariants observed:**
- Foundation layer (`layout`, `constants`, `types`, `video_prompts`, `stitch`)
  has **zero upward imports** — the hardest layers are leaves. That is the
  single most important property of a well-grounded package.
- Data flows strictly downward: orchestration → pipeline → providers →
  state → foundation. **No module-level import cycles.**
- The only cycle in the graph, `agent_tools ⇄ agnes_client`, is fully
  deferred (function-local imports both ways) — a *logical* coupling, not an
  import-time one. Fine today, watch it.

## 2. Coupling metrics (top of distribution)

| Module | Fan-out | Fan-in | Role |
|---|---|---|---|
| `cli` | **30** | 0 | orchestration hub (expected) |
| `director` | **13** | 1 | second hub (unexpected) |
| `utils` | 1 | **8** | shared helper (healthy) |
| `constants` | 0 | **6** | config registry (healthy) |
| `layout` | 0 | **5** | path source of truth (healthy) |
| `quality_gate` | 3 | 2 | pipeline stage |
| `shot_runner` | 1 | 1 | pure pipeline logic |

Read: fan-in concentrates exactly where it should (foundation/config), and the
only high fan-out nodes are the two orchestration modules.

## 3. Smells found (groundedness gaps)

Ranked by structural risk:

1. **`cli.py` is a 4.8k-line god module (fan-out 30, all 5 layers).**
   It works because every lower layer is clean, but it is where the next
   regressions will live: two produce paths, human gates, cost recording and
   layout selection are all entangled in one file. → *split into `cmd/`
   groups (production, references, post, providers) once PRs #44/#45 land.*
2. **`director.py` is a disguised orchestrator (fan-out 13).** It reaches
   providers, state, memory *and* the pipeline gate. → *either demote it to a
   prompt-composition module (drop provider/state deps) or rename it honestly
   as orchestration.*
3. **Providers import the prompting layer (deferred).** `agnes_client` /
   `ark_client` → `style_presets.apply_style_preset`. Weak (function-local)
   but wrong direction: a provider should be dumb. → *push the style
   application into the caller, or relocate the pure string-transform helpers
   to `constants`/`utils`.*
4. **`agent_tools ⇄ agnes_client` deferred cycle.** → *extract the shared
   job-polling helper so the arrow becomes one-way.*
5. **`utils.py` (fan-in 8) is becoming a kitchen sink** (JSON I/O, plans,
   discovery, filenames, timestamps). → *candidate split: `planning.py`
   (generation/production plans) vs `io.py`.*

## 4. Verdict

**The package is well-grounded at the layer level, with two hub risks at the
top.**

*Grounded (keep as-is):* strict downward dependency flow, leaf foundations,
no module-level cycles, state-management centralised in
`project_manager`/`cost_tracker`, prompt logic isolated in `video_prompts`,
resumability logic isolated in `shot_runner` (pure, no CLI deps — trivially
unit-testable). The issue #31–#43 work actually *improved* the grounding:
new concerns got new leaf modules (`migrate`) or stayed in their layer
(`quality_gate` policy, `shot_runner` retries) instead of leaking into `cli`.

*Needs adjustment (schedule, don't block):* the two items above that cost
real maintenance: (1) `cli.py` → `cmd/` split, (2) `director` demotion.
Items 3–5 are hygiene, one commit each.

**Health score: 8/10.** Structure is sound; the package will not break on
the next feature — but the `cli.py` split is the one refactor that pays for
itself on the feature *after* the split.

## 5. Suggested target shape (after adjustment)

```mermaid
graph LR
    subgraph target["brandly_cli/ (target)"]
        direction TB
        L0["foundation: layout · types · constants · io"]
        L1["state: project_manager · cost_tracker · memory"]
        L2["providers: agnes · minimax · ark · audio (dumb: no prompting deps)"]
        L3["prompts: video_prompts · style_presets · director(=prompt composer)"]
        L4["pipeline: shot_runner · quality_gate · migrate · post/ (stitch,edit,captions,…)"]
        L5["cmd/: production · references · post · gate · providers (thin Click wrappers)"]
        L0 --> L1 --> L2 --> L3 --> L4 --> L5
    end
```

Same layers as today; the changes are mechanical: move `cli.py` sections into
`cmd/*` (thin wrappers that call pipeline functions), strip provider imports
from prompting, and keep `cli.py` as the Click group + shared helpers.
