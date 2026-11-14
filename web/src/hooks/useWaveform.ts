import { useState, useCallback } from 'react';
import { useAppStore, API } from '../store';
import type { WaveformPoint } from '../types';

interface UseWaveformReturn {
  waveform: WaveformPoint[] | null;
  loading: boolean;
  fetch: () => void;
}

export function useWaveform(clipId: string): UseWaveformReturn {
  const [loading, setLoading] = useState(false);
  const { activeProject } = useAppStore();
  const waveforms = useAppStore((s) => s.waveforms);
  const setWaveform = useAppStore((s) => s.setWaveform);

  const waveform = waveforms[clipId] ?? null;
  const projectId = activeProject?.id;

  const doFetch = useCallback(async () => {
    if (waveform !== null || !projectId) return;
    setLoading(true);
    try {
      const res = await fetch(API(`/projects/${projectId}/clips/${clipId}/waveform`));
      if (!res.ok) {
        setLoading(false);
        return;
      }
      const data: WaveformPoint[] = await res.json();
      setWaveform(clipId, data);
    } catch {
      // waveform unavailable — stays null
    } finally {
      setLoading(false);
    }
  }, [clipId, waveform, setWaveform, projectId]);

  return { waveform, loading, fetch: doFetch };
}
