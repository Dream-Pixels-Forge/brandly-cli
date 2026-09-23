# Plan: Brandly Studio — Full Timeline Editor Redesign

> **Target:** Transform the current basic timeline editor into a Remotion Studio-style production dashboard with 5 functional panels, multi-track timeline, color grading, audio mixer, and render dispatch.
> **Scope:** Full UI remaster. Single-track opaque clips model (no per-layer editing). Waveform backend added.

---

## 1. Current State

| Area | Current | Target |
|------|---------|--------|
| **Layout** | 2-panel (sidebar + preview + timeline strip) | 5-panel Remotion-style studio |
| **Typography** | system-ui | Hanken Grotesk + Space Mono |
| **Icons** | Unicode/emoji | Material Symbols Outlined |
| **Palette** | Hardcoded dark #0a0a0a | Material You tokens (cyan primary, orange tertiary) |
| **Timeline** | Seconds-based, single row, no playhead | Frame-based, multi-track, draggable playhead |
| **Preview** | Basic `<video>` element | Framed viewport with guide overlays |
| **Props** | Duration/transition/volume fields | Full schema inspector with live editing |
| **Audio** | None | Waveform visualization, VU meter, beat sync toggle |
| **Color** | None exposed | Lift/Gamma/Gain wheels + LUT selector |
| **Export** | Single button | Format presets, codec selection, concurrency |
| **Backend** | REST + WebSocket (regenerate only) | + waveform endpoint, + quality gate endpoint |

**Existing infrastructure to preserve:**
- `web/websocket.py` broadcast system ✅
- `web/state.py` TimelineState (load/save/reorder/trim) ✅
- `web/routes/clips.py` regenerate + PATCH ✅
- `web/routes/export.py` stitch + download ✅
- `web/routes/projects.py` project listing ✅
- `@dnd-kit` already installed for drag-to-reorder ✅
- 554 tests passing, all gates green ✅

---

## 2. Architecture

### 2.1 New Component Tree

```
web/src/
├── App.tsx                          # Shell: <DndContext> + panel router + Store provider
├── main.tsx                         # Entry (unchanged)
├── index.css                        # Rewrite: Google Fonts, Material Symbols, CSS vars
├── types.ts                         # Extend: FrameTime, PanelKind, WaveformPoint
├── store.ts                         # Rewrite: playhead, panel state, playback, ws
│
├── components/
│   ├── Shell.tsx                    # Full-page shell: <header> + <SidebarNav> + <PanelArea>
│   ├── Header.tsx                   # Top bar: project name, frame counter, WS/health indicators
│   ├── SidebarNav.tsx               # Left nav: icon buttons for each panel
│   │
│   ├── panels/
│   │   ├── PreviewPanel.tsx         # Viewport + <TransportControls>
│   │   ├── TransportControls.tsx    # Play/pause/step/loop/rate
│   │   ├── ShotListPanel.tsx        # Vertical clip list with status badges
│   │   ├── PropsInspectorPanel.tsx  # Editable clip properties form
│   │   ├── TimelinePanel.tsx        # Frame-accurate multi-track timeline
│   │   ├── ColorGradingPanel.tsx    # Lift/Gamma/Gain wheels + LUT selector
│   │   ├── AudioMixerPanel.tsx      # VU meters, voice persona, beat sync
│   │   └── RenderDispatchPanel.tsx  # Format presets, codec, concurrency
│   │
│   └── timeline/
│       ├── TimelineRuler.tsx        # Frame-based tick marks (every 30f = 1.25s @24fps)
│       ├── TimelineTrackHeader.tsx  # Fixed left panel: track names + M/S buttons
│       ├── TimelineTrack.tsx        # Scrollable area with clip blocks
│       ├── TimelineClip.tsx         # Clip block with status badge + trim handles
│       ├── Playhead.tsx             # Draggable vertical needle
│       └── TransitionZone.tsx       # 4px clickable zone between clips
│
└── hooks/
    ├── usePlayback.ts               # play/pause/step/seek state machine
    ├── usePlayhead.ts               # drag scrub + keyboard shortcuts
    ├── useWaveform.ts               # fetch + render waveform data
    └── useQualityGate.ts            # trigger quality check on clip
```

### 2.2 State Shape (Zustand)

```typescript
interface AppState {
  // Project & clips (existing, extended)
  projects: Project[];
  activeProject: Project | null;
  timeline: ProjectTimeline | null;
  selectedClipId: string | null;

  // Panel navigation
  activePanel: 'preview' | 'timeline' | 'props' | 'color' | 'audio' | 'render';

  // Playback
  isPlaying: boolean;
  currentFrame: number;        // 0-indexed frame position
  totalFrames: number;         // computed from timeline duration
  playbackRate: 0.5 | 1 | 2;
  loop: boolean;

  // WebSocket
  wsEvent: string | null;
  exportDone: boolean;

  // Waveform (per-clip, fetched lazily)
  waveforms: Record<string, WaveformPoint[]>;

  // Actions
  selectProject: (id: string) => Promise<void>;
  loadTimeline: () => Promise<void>;
  updateClip: (id: string, updates: Partial<Clip>) => Promise<void>;
  reorderClips: (order: string[]) => Promise<void>;
  regenerateClip: (id: string) => Promise<void>;
  exportProject: () => Promise<void>;
  setPanel: (panel: AppState['activePanel']) => void;
  setPlayhead: (frame: number) => void;
  togglePlay: () => void;
  stepFrame: (delta: number) => void;
}
```

### 2.3 New Backend Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/projects/{id}/clips/{clip_id}/waveform` | Returns `{points: [{x, amplitude}]}` sampled at ~200pts via ffmpeg audio analysis |
| `POST` | `/api/projects/{id}/clips/{clip_id}/gate` | Runs `verify_element()` and updates `quality_status` |
| `PATCH` | `/api/projects/{id}/clips/{clip_id}` | Already exists (extend with new fields) |
| `GET` | `/api/projects/{id}/timeline` | Already exists |

**Waveform implementation:** Use `ffmpeg` to extract audio stream, resample to mono 8kHz, compute RMS envelope at ~200 points. No new Python deps needed — reuse existing ffmpeg binary.

---

## 3. Implementation Phases

### Phase 1 — Shell & Design System
**Files:** `index.css`, `types.ts`, `store.ts`, `App.tsx` (rewrite)
- Install Google Fonts (Hanken Grotesk, Space Mono) via `index.css` `@import`
- Import Material Symbols Outlined via `<link>` in `index.html`
- Define CSS custom properties for Material You tokens (primary=cyan `#4cd7f6`, tertiary=orange `#ffb873`)
- Rewrite `types.ts`: add `FrameTime`, `PanelKind`, `WaveformPoint`, extend `Clip` with `waveform_url`
- Rewrite `store.ts`: add panel state, playhead, playback rate, loop, waveform map
- Create `Shell.tsx`, `Header.tsx`, `SidebarNav.tsx`
- Wire up panel navigation (clicking nav icon switches `activePanel`)

### Phase 2 — Preview & Shot List Panels
**Files:** `components/panels/PreviewPanel.tsx`, `TransportControls.tsx`, `ShotListPanel.tsx`
- Preview panel: framed viewport with checkerboard background, 16:9 aspect ratio container
- Guide overlays: title safe (90%), action safe (93%), center crosshair — all CSS-only
- Canvas HUD badges: shot number, engine label (e.g. "EEVEE 4.2 SPATIAL")
- Bottom callout: clip description + Agnes render buffer status
- Transport controls: first/prev/next/last frame buttons, play/pause, loop toggle, rate selector (0.5x/1x/2x), volume slider
- Shot list panel: vertical list of clips with border-left status indicator
  - Status badges: "Cached" (generated), "EEVEE Active" (selected), "Agnes 12s" (generating, with ping dot)
  - Frame range display (e.g. "90 → 240")
  - Click to select + switch to preview panel
  - Footer: "Add New Shot Sequence" button + "Synced with production_plan.md" indicator

### Phase 3 — Props Inspector Panel
**Files:** `components/panels/PropsInspectorPanel.tsx`
- Prompt textarea (3 rows, mono font)
- Model selector dropdown (agnes-ultra-v4.2, agnes-video-pro, blender-eevee-direct)
- Style preset selector dropdown
- Blender spatial params section (checkbox + Cam/Focal/Samples readout)
- Seed input (with lock icon when locked) + CFG guidance range slider
- Audio beat sync toggle with BPM readout
- "Update Shot Props (Hot Reload)" button → PATCH to API

### Phase 4 — Timeline with Playhead
**Files:** `components/timeline/*.tsx`, `hooks/usePlayhead.ts`, `hooks/usePlayback.ts`
- Frame-based ruler: labels every 30 frames (1.25s @ 24fps), fine hashmarks every 5f
- Track headers (pinned left, 200px): VIDEO track, A1: MiniMax VO, A2: BGM — each with M/S buttons
- Clip blocks: width = `(duration * ZOOM) / TOTAL_FRAMES * 100%`
  - Active clip: 2px cyan border-left + "ACTIVE CLIP" badge
  - Generating clip: diagonal stripe pattern + "Agnes ETA 12s"
  - Ready clip: standard border
- Playhead: vertical cyan line at `currentFrame / totalFrames * 100%`, draggable
  - Drag: updates `playheadFrame` in store, video seeks via `currentTime = frame / fps`
  - Keyboard: ←/→ step 1 frame, Space toggle play
- Trim handles: same pointer-drag logic as current implementation (left=trim start, right=trim end)
- Transition zones: 4px gap between clips, click opens transition popover (fade/dissolve/wipe/slide)
- Zoom: range slider 10x–100x (frames-per-pixel)

### Phase 5 — Bottom Deck: Color, Audio, Export
**Files:** `components/panels/ColorGradingPanel.tsx`, `AudioMixerPanel.tsx`, `RenderDispatchPanel.tsx`
- **Color Grading:** 3 color wheels (Lift/Gamma/Gain) using SVG `<circle>` elements with draggable pucks
  - LUT selector dropdown (Teal_Orange, Nordic_Neutral, Monochrome)
  - Color temp slider (3200K–8000K)
- **Audio Mixer:**
  - Voice persona dropdown (Marcus/Elena/Kaito)
  - Studio Clarity EQ toggle + Noise Gate floor readout
  - Stereo VU meter: dual channels, 0–100% filled bar with primary/tertiary/error color zones
- **Render Dispatch:**
  - Format preset grid: YouTube 4K, TikTok/Reels, Instagram (click to select)
  - Codec dropdown (H.264/ProRes/VP9) + Concurrency selector
  - CLI equivalent code snippet (copyable)
  - "Render Multi-Shot Composition" button → triggers `exportProject()`

### Phase 6 — Waveform Backend
**Files:** `src/brandly_cli/web/routes/waveform.py`, `server.py` (register), `state.py` (extend)
- New route: `GET /api/projects/{id}/clips/{clip_id}/waveform`
- Implementation: extract audio from clip via ffmpeg → compute RMS envelope → return 200-point array
- Fallback: if no audio track, return flat zeros
- Add to `routes/__init__.py` or register directly in `server.py`
- Update `Clip` type to include optional `waveform_url` field

### Phase 7 — Quality Gate Endpoint
**Files:** `src/brandly_cli/web/routes/gate.py`
- New route: `POST /api/projects/{id}/clips/{clip_id}/gate`
- Runs `verify_element()` with `use_ai=False` (deterministic pre-checks only)
- Updates `quality_status` on the clip
- Returns `{status: "pass"|"warn"|"fail", score: int}`
- Register in server

---

## 4. Files to Create/Modify

### New files
```
web/src/components/Shell.tsx
web/src/components/Header.tsx
web/src/components/SidebarNav.tsx
web/src/components/panels/PreviewPanel.tsx
web/src/components/panels/TransportControls.tsx
web/src/components/panels/ShotListPanel.tsx
web/src/components/panels/PropsInspectorPanel.tsx
web/src/components/panels/ColorGradingPanel.tsx
web/src/components/panels/AudioMixerPanel.tsx
web/src/components/panels/RenderDispatchPanel.tsx
web/src/components/timeline/TimelineRuler.tsx
web/src/components/timeline/TimelineTrackHeader.tsx
web/src/components/timeline/TimelineTrack.tsx
web/src/components/timeline/TimelineClip.tsx
web/src/components/timeline/Playhead.tsx
web/src/components/timeline/TransitionZone.tsx
web/src/hooks/usePlayback.ts
web/src/hooks/usePlayhead.ts
web/src/hooks/useWaveform.ts
web/src/hooks/useQualityGate.ts
src/brandly_cli/web/routes/waveform.py
src/brandly_cli/web/routes/gate.py
```

### Modified files
```
web/src/App.tsx          → rewrite (shell orchestrator only)
web/src/store.ts         → rewrite (new state shape)
web/src/types.ts         → extend (FrameTime, PanelKind, WaveformPoint)
web/src/index.css        → rewrite (fonts, tokens, base styles)
web/src/main.tsx         → minimal change (wrap in Shell)
src/brandly_cli/web/server.py  → register new routes
src/brandly_cli/web/__init__.py → export new modules
tests/test_web_sync.py   → add waveform + gate endpoint tests
```

---

## 5. Verification

```bash
# Frontend build
cd web && npm run build          # tsc clean + vite build succeeds

# Backend tests
PYTHONPATH=src python -m pytest tests/ -q   # 554+ existing + new tests
python -m ruff check src/brandly_cli/web/ tests/
python -m mypy src/brandly_cli/web/
python -c "from importlinter.cli import lint_imports; exit(lint_imports())"

# Frontend lint
cd web && npx oxlint src/

# Manual E2E
brandly init --name TestStudio --idea "test" --shots 5 --layout v2
brandly produce TestStudio --shots shots.json
brandly timeline                          # opens browser
# Verify: project selector → preview with transport → shot list with status badges
# → props inspector with all fields → timeline with frame ruler + playhead
# → color wheels + audio mixer + export dispatcher panels
# → drag clips to reorder, trim handles adjust duration
# → playhead scrubs video, keyboard shortcuts work
# → waveform renders on audio clips
# → quality gate triggers and updates badge
```

---

## 6. Key Design Decisions

1. **Single track, opaque clips**: No per-layer editing. Audio waveform is a visual overlay on the same track, not a separate editable layer. Matches brandly's MP4-based workflow.

2. **Frame-based timeline**: All timing is in frames (0-indexed). Duration displayed as `frames / fps`. Ruler labels every 30 frames (1.25s at 24fps). Maintains precision without floating-point drift.

3. **Material You design tokens**: Colors defined as CSS custom properties on `:root`. Primary = cyan (`#4cd7f6`), Tertiary = orange (`#ffb873`). Dark palette matches the reference screenshot.

4. **No new Python dependencies**: Waveform extraction uses ffmpeg CLI (already a hard dependency of brandly-cli). Material Symbols loaded via Google Fonts CDN in the HTML head.

5. **Progressive enhancement**: If ffmpeg is unavailable, waveform returns empty array. If AGNES_API_KEY is not set, quality gate uses only deterministic pre-checks (same as current `compute_quality_status`).

6. **Preserve existing API contract**: All existing endpoints (`/api/projects`, `/timeline`, `/clips/{id}`, `/export`) continue to work unchanged. New endpoints are additive.
