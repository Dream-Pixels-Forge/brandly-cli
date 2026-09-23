import { useState, useCallback } from 'react';
import { useAppStore } from '../store';
import type { WaveformPoint } from '../types';

interface UseWaveformReturn {
  waveform: WaveformPoint[] | null;
  loading: boolean;
  fetch: () => void;
}

export function useWaveform(clipId: string): UseWaveformReturn {
  const [loading, setLoading] = useState(false);
  const waveforms = useAppStore((s) => s.waveforms);
  const setWaveform = useAppStore((s) => s.setWaveform);

  const waveform = waveforms[clipId] ?? null;

  const doFetch = useCallback(async () => {
    if (waveform !== null) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/clips/${clipId}/waveform`);
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
  }, [clipId, waveform, setWaveform]);

  return { waveform, loading, fetch: doFetch };
}
