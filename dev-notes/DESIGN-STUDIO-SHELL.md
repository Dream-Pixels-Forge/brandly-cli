# DESIGN — Brandly Studio Shell (Paper-sourced, FROZEN)

> **Source of truth:** Paper file `01M3VWT0PHVWKPN9JSECCES8T4`, page `p-3-0`
> (“Brandly Studio — Web UI”), artboards `01 · Timeline Sequencer` (`8R-0`),
> `02 · Shot List` (`8S-0`), `03 · Render Queue` (`8T-0`),
> `04 · Production Monitor` (`8U-0`), `07 · Preview Player` (`2NA-0`).
> **Status:** FROZEN. Implement exactly this; do not improvise layout.

## 1. Scope

**In scope**
- App shell: **Toolbar** (new) + **Status Bar** (new) + sidebar restructure.
- Artboards 01–04 structural/UX deltas (below).

**Out of scope — do NOT build**
- New API endpoints, new providers, or new data models.

**Screen 05 / 06 (Review Queue / Agnes AI Synthesizer) — now DESIGNED**
- Paper artboards `05 · Review Queue` (`1T8-0`) and `06 · Agnes AI
  Synthesizer` (`1T9-0`) are populated with the shared shell; screen
  deltas are in §7. The SPA code contract tests for these two panels are
  still pending (no JS test runner in CI; see issue #61) — this pass is
  design-only; code is a separate TDD increment.

**Screen 01 ↔ 07 split — now DESIGNED (Round 22)**
- The original `01 · Preview Player` is reframed as `01 · Timeline
  Sequencer` (`8R-0`): the timeline-heavy editing surface (transport
  overlay + 300px Clip Inspector rail + 3-track V2/V1/A1 timeline). Its
  artboard name, toolbar breadcrumb, and active sidebar nav row all moved
  from “Preview Player” to “Timeline Sequencer”.
- A new `07 · Preview Player` (`2NA-0`) is a dedicated, **clean** playback
  surface: a large centered 16:9 stage reusing the exact transport
  overlay, plus a slim preview control strip — and **no timeline, no
  Clip Inspector**. The shared sidebar already carries both “Preview
  Player” and “Timeline Sequencer” nav items, so navigation stays
  consistent. Design-only this pass; the code contract is a separate
  increment (issue #61).

## 2. Shell metrics (1440×900 reference)

| Region | Metric |
|---|---|
| Header | 52px, fixed (unchanged) |
| **Toolbar** | **40px, new** — sits directly under Header |
| Body | `flex:1`, row |
| ↳ Sidebar | 248px fixed (`16rem` today → 248px) |
| ↳ Main | `flex:1`, `padding:14px`, `gap:12px` |
| **Status Bar** | **28px, new** — pinned bottom |

Stack: `0–52` Header · `52–92` Toolbar · `92–872` Body · `872–900` Status Bar.
Body inner width = `1440 − 248 = 1192`; Main content = `1192 − 28 = 1164`.

## 3. Token contract — reuse MD3, do not fork

The Paper `--studio-*` tokens are **aliases** of the existing MD3 variables.
Do **not** add a second token namespace. Instead **define the variables that
are referenced but missing today** in `web/index.html` (`:root`):

```
--md-radius-sm: 4px;  --md-radius-md: 8px;  --md-radius-lg: 12px;
--md-transition-fast: 150ms;
--md-font-display-lg: 'Space Mono', monospace;
--md-font-code-inline: 'Space Mono', monospace;
--md-font-body-md:    'Hanken Grotesk', sans-serif;
```

Alias map (studio → existing md):

| Paper token | Code variable |
|---|---|
| `--studio-bg` | `--md-surface` (#131316) |
| `--studio-surface-low/-lowest/-high/-highest` | `--md-surface-container-low` / `-lowest` / `-high` / `-highest` |
| `--studio-border` | `--md-surface-container-highest` |
| `--studio-primary` | `--md-primary` |
| `--studio-text` / `--studio-text-muted` | `--md-on-surface` / `--md-on-surface-variant` |
| `--studio-success / warning / danger` | `#4ade80` / `#facc15` / `#f87171` |

## 4. Toolbar (new, 40px)

`[breadcrumb: project name › panel label] · spacer · [search "Search shots, commands…  ⌘K", width 280] · [undo, redo] · [Share, ?]`

## 5. Status Bar (new, 28px)

- **Left:** `PHASE n · <phase>` pill (from `activeProject.current_phase`), gate,
  budget.
- **Centre:** worker / mem / fps.
- **Right:** zoom · selection · frame · version.

**Data-honesty rule:** render only values the store actually has; omit or show
an em-dash otherwise. Never fabricate telemetry as if it were live.

## 6. Sidebar restructure

1. **Remove** the `Engine Status` telemetry block (moves to Status Bar).
2. **Add** `SidebarFooter`: primary “New Project” CTA + `Docs · Shortcuts · v{version}`.
3. **Add** keyboard-shortcut chips to nav rows:
   `P` Preview · `T` Timeline · `A` Asset Manifest · `I` Props ·
   `R` Render · `M` Monitor · `Q` Review · `G` Agnes AI.
4. **Keep** `fetchProjects` boot + `loading`/`error` surfacing
   (pinned by `tests/test_web_shell_boot.py`).

## 7. Screen deltas (01–04)

| # | Screen | Delta |
|---|---|---|
| 01 | Timeline Sequencer | sequence-editor view: transport **overlay** on the frame + **300px Clip Inspector rail** + **206px 3-track timeline** (V2/V1/A1) — the timeline-heavy editing surface |
| 02 | Shot List | Shot Inspector **tabs** (Overview/Prompt/Gate); row **checkboxes** + **Selection Bar** |
| 03 | Render Queue | **PipelineStepper** (Plan locked → Rendering → Encode → Publish); settings column fixed **440px** |
| 04 | Monitor | **PhaseStepper** (P R I D E S) |
| 05 | Review Queue | **status-filter** (All/Awaiting/Passed/Flagged) + 8-item list (thumbnail · provider line · G1–G3 gate bar · cost · status pill · approve/reject) + **300px review-detail rail** (prompt, gate checklist, approve/reject) + summary footer |
| 06 | Agnes AI | **generation console** (prompt box, style-preset chips, aspect/fit/seed params, credit-budget bar, Synthesize/Queue actions) + **2×2 results grid** (one selected variant) + run-summary footer |
| 07 | Preview Player | dedicated clean playback: **large centered 16:9 stage** with the transport **overlay** (play/pause · prev/next · scrubber · time · volume · fullscreen) + a **slim preview control strip** (shot name + PREVIEW chip + codec/fps · Loop toggle · “Open in Timeline” action); **no timeline, no Clip Inspector** |

### 7.1 Preview stage empty states (added 2026-10-05)

The 16:9 stage has **two** distinct empty states. They are not
interchangeable, and the first is **not** in the Paper artboards — it is
recorded here so the layout is not undocumented:

| State | Condition | Stage renders |
|---|---|---|
| **No footage yet** | `!timeline \|\| timeline.clips.length === 0` | the still plate `web/public/preview.jpg` (`object-fit: cover`, `opacity: 0.55`), overlaid with a `NO FOOTAGE YET` chip (`--md-primary`) + a `Placeholder still — generate shots to see them here` caption |
| **Nothing selected** | clips exist, `selectedClipId` unset | the existing `videocam_off` glyph + `Select a clip to preview` hint |

**Data honesty (AGENTS.md §5):** the plate is a *placeholder*, never
generated footage, so it is always labelled. Do not remove the chip to "clean
up" the frame — a bare still in a video stage reads as real output.

Tokens: `--md-primary`, `--md-on-surface-variant`,
`--md-surface-container-highest`, `--md-font-code-inline` only — no new token
namespace. Pinned by `tests/test_web_empty_state_preview.py`.

The plate ships from `web/public/` (not the build output) because
`vite.config.ts` sets `emptyOutDir: true`, which wipes
`src/brandly_cli/web/static/` on every build.

## 8. Verification gates

| Gate | Command |
|---|---|
| Source contract | `python -m pytest tests/test_web_studio_shell.py -v` |
| Existing SPA contracts | `python -m pytest tests/test_web_panels_wired.py tests/test_web_shell_boot.py tests/test_web.py -v` |
| Frontend lint | `npm --prefix web run lint` |
| Frontend build | `npm --prefix web run build` (emits into `src/brandly_cli/web/static`) |
| Bundle freshness | `git diff --exit-code -- src/brandly_cli/web/static/` (CI `web-quality`) |
| Python suite | `python -m pytest tests/ -q` |
