export interface Project {
  id: string;
  name: string | null;
  slug: string | null;
  status: string;
  style: string;
  shot_count: number;
  current_phase: string;
  has_timeline: boolean;
}

export interface WaveformPoint {
  x: number;
  amplitude: number;
}

export interface Clip {
  id: string;
  shot_id: string;
  scene: number;
  index_in_scene: number;
  clip_path: string;
  prompt: string;
  duration: number;
  actual_duration: number | null;
  style: string;
  transition_in: string | null;
  transition_duration: number;
  volume: number;
  status: 'pending' | 'generating' | 'generated' | 'failed';
  aspect_ratio: string;
  quality_status: 'pass' | 'warn' | 'fail' | null;
  start_time?: number;
  waveform_url?: string | null;
  color_grade?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTimeline {
  project_id: string;
  clips: Clip[];
  aspect_ratio: string;
  fps: number;
  color_grade: string;
  created_at: string;
  updated_at: string;
}

export type PanelKind = 'preview' | 'timeline' | 'asset_manifest' | 'props' | 'color' | 'audio' | 'render' | 'agnes_ai';

export type TransitionType = 'fade' | 'dissolve' | 'wipe' | 'slide';

export type FormatPreset = 'youtube-4k' | 'tiktok' | 'instagram';
export type Codec = 'h264' | 'prores' | 'vp9';
