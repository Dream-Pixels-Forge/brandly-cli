import { create } from 'zustand';
import type { Clip, FormatPreset, Codec, PanelKind, Project, ProjectTimeline, WaveformPoint } from './types';

interface AppState {
  // Projects
  projects: Project[];
  activeProject: Project | null;
  loading: boolean;
  error: string | null;

  // Timeline
  timeline: ProjectTimeline | null;
  selectedClipId: string | null;
  zoomLevel: number;          // frames per 100px (default 100)
  totalFrames: number;

  // Playback
  isPlaying: boolean;
  currentFrame: number;
  playbackRate: 0.5 | 1 | 2;
  loop: boolean;
  volume: number;

  // Panel navigation
  activePanel: PanelKind;

  // WebSocket
  wsEvent: string | null;

  // Export
  exportDone: boolean;

  // Waveforms (fetched lazily per clip)
  waveforms: Record<string, WaveformPoint[]>;

  // Render dispatch
  formatPreset: FormatPreset;
  codec: Codec;
  concurrency: number;

  // Actions
  fetchProjects: () => Promise<void>;
  selectProject: (id: string) => Promise<void>;
  loadTimeline: () => Promise<void>;
  setSelectedClip: (id: string | null) => void;
  setZoom: (level: number) => void;
  setPanel: (panel: PanelKind) => void;
  updateClip: (clipId: string, updates: Partial<Clip>) => Promise<void>;
  reorderClips: (order: string[]) => Promise<void>;
  regenerateClip: (clipId: string) => Promise<void>;
  exportProject: () => Promise<void>;
  setPlayhead: (frame: number) => void;
  togglePlay: () => void;
  stepFrame: (delta: number) => void;
  setPlaybackRate: (rate: 0.5 | 1 | 2) => void;
  setLoop: (loop: boolean) => void;
  setWaveform: (clipId: string, points: WaveformPoint[]) => void;
  setFormatPreset: (p: FormatPreset) => void;
  setCodec: (c: Codec) => void;
  setVolume: (v: number) => void;
}

const TOKEN = new URLSearchParams(window.location.search).get('token');

export const withToken = (path: string) =>
  TOKEN ? `${path}${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(TOKEN)}` : path;

const API = (path: string) => withToken(`/api${path}`);

function notifySave() {
  window.dispatchEvent(new Event('brandly-save'));
}

export const useAppStore = create<AppState>((set, get) => ({
  projects: [],
  activeProject: null,
  loading: false,
  error: null,
  timeline: null,
  selectedClipId: null,
  zoomLevel: 100,
  totalFrames: 0,
  isPlaying: false,
  currentFrame: 0,
  playbackRate: 1,
  loop: false,
  volume: 0.85,
  activePanel: 'preview',
  wsEvent: null,
  exportDone: false,
  waveforms: {},
  formatPreset: 'youtube-4k',
  codec: 'h264',
  concurrency: 8,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API('/projects'));
      const data = await res.json();
      set({ projects: data.projects || [], loading: false });
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },

  selectProject: async (id) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API(`/projects/${id}`));
      const data = await res.json();
      set({ activeProject: data, loading: false });
      await get().loadTimeline();
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },

  loadTimeline: async () => {
    const { activeProject } = get();
    if (!activeProject) return;
    try {
      const res = await fetch(API(`/projects/${activeProject.id}/timeline`));
      const data = await res.json();
      if (data.timeline) {
        const tl = data.timeline;
        const totalFrames = Math.ceil(tl.clips.reduce((s: number, c: Clip) => s + c.duration, 0) * (tl.fps || 24));
        set({ timeline: tl, totalFrames, error: null });
      }
    } catch (e) {
      set({ error: String(e) });
    }
  },

  setSelectedClip: (id) => set({ selectedClipId: id }),
  setZoom: (level) => set({ zoomLevel: level }),
  setPanel: (panel) => set({ activePanel: panel }),
  setPlaybackRate: (rate) => set({ playbackRate: rate }),
  setLoop: (loop) => set({ loop }),
  setWaveform: (clipId, points) => set((s) => ({ waveforms: { ...s.waveforms, [clipId]: points } })),
  setFormatPreset: (p) => set({ formatPreset: p }),
  setCodec: (c) => set({ codec: c }),
  setVolume: (v: number) => set({ volume: v }),

  setPlayhead: (frame) => {
    const { totalFrames } = get();
    set({ currentFrame: Math.max(0, Math.min(frame, totalFrames)) });
  },

  togglePlay: () => {
    const { isPlaying } = get();
    set({ isPlaying: !isPlaying });
  },

  stepFrame: (delta) => {
    const { currentFrame } = get();
    get().setPlayhead(currentFrame + delta);
  },

  updateClip: async (clipId, updates) => {
    const { activeProject } = get();
    if (!activeProject) return;
    try {
      await fetch(
        API(`/projects/${activeProject.id}/clips/${clipId}`),
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates) }
      );
      set((state) => ({
        timeline: state.timeline
          ? {
              ...state.timeline,
              clips: state.timeline.clips.map((c: Clip) =>
                c.id === clipId ? { ...c, ...updates } : c
              ),
            }
          : null,
      }));
      await get().loadTimeline();
      notifySave();
    } catch (e) {
      set({ error: String(e) });
    }
  },

  reorderClips: async (order) => {
    const { timeline, activeProject } = get();
    if (!timeline || !activeProject) return;
    try {
      const ordered = order.map((id) => timeline.clips.find((c: Clip) => c.id === id)).filter(Boolean) as Clip[];
      const remaining = timeline.clips.filter((c: Clip) => !order.includes(c.id));
      const reordered = [...ordered, ...remaining];
      await fetch(
        API(`/projects/${activeProject.id}/timeline`),
        { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ clips: reordered, color_grade: timeline.color_grade }) }
      );
      set({ timeline: { ...timeline, clips: reordered } });
      notifySave();
    } catch (e) {
      set({ error: String(e) });
    }
  },

  regenerateClip: async (clipId) => {
    const { activeProject } = get();
    if (!activeProject) return;
    try {
      const res = await fetch(
        API(`/projects/${activeProject.id}/clips/${clipId}/regenerate`),
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.status === 'completed') await get().loadTimeline();
      else set({ error: data.error || 'Generation failed' });
    } catch (e) {
      set({ error: String(e) });
    }
  },

  exportProject: async () => {
    const { activeProject } = get();
    if (!activeProject) return;
    try {
      const res = await fetch(
        API(`/projects/${activeProject.id}/export`),
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.error) {
        set({ error: data.error });
      } else {
        const dlUrl = withToken(`/api/projects/${activeProject.id}/export/download`);
        window.open(dlUrl, '_blank');
        set({ exportDone: true });
        setTimeout(() => set({ exportDone: false }), 3000);
      }
    } catch (e) {
      set({ error: String(e) });
    }
  },
}));
