import { create } from 'zustand';
import type { Clip, Project, ProjectTimeline } from './types';

interface AppState {
  projects: Project[];
  activeProject: Project | null;
  loading: boolean;
  error: string | null;
  timeline: ProjectTimeline | null;
  selectedClipId: string | null;
  zoomLevel: number;
  isPlaying: boolean;

  fetchProjects: () => Promise<void>;
  selectProject: (id: string) => Promise<void>;
  loadTimeline: () => Promise<void>;
  setSelectedClip: (id: string | null) => void;
  setZoom: (level: number) => void;
  updateClip: (clipId: string, updates: Partial<Clip>) => Promise<void>;
  reorderClips: (order: string[]) => Promise<void>;
  regenerateClip: (clipId: string) => Promise<void>;
  exportProject: () => Promise<void>;
}

const TOKEN = new URLSearchParams(window.location.search).get('token');

/** Append the per-run token to an API/media URL so the local guard accepts it. */
export const withToken = (path: string) =>
  TOKEN ? `${path}${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(TOKEN)}` : path;

const API = (path: string) => withToken(`/api${path}`);

export const useAppStore = create<AppState>((set, get) => ({
  projects: [],
  activeProject: null,
  loading: false,
  error: null,
  timeline: null,
  selectedClipId: null,
  zoomLevel: 100,
  isPlaying: false,

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
      if (data.timeline) set({ timeline: data.timeline, error: null });
    } catch (e) {
      set({ error: String(e) });
    }
  },

  setSelectedClip: (id) => set({ selectedClipId: id }),
  setZoom: (level) => set({ zoomLevel: level }),

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
      if (data.error) alert('Export failed: ' + data.error);
      else alert('Export complete: ' + data.output_path);
    } catch (e) {
      set({ error: String(e) });
    }
  },
}));
