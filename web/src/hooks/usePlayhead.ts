import { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '../store';

export interface PlayheadHandlers {
  isDragging: boolean;
  handlePointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
  handlePointerMove: (e: React.PointerEvent<HTMLDivElement>) => void;
  handlePointerUp: () => void;
  setContainerRef: (ref: HTMLDivElement | null) => void;
}

export function usePlayhead(): PlayheadHandlers {
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { setPlayhead, stepFrame, togglePlay } = useAppStore();

  const setContainerRef = useCallback((ref: HTMLDivElement | null) => {
    containerRef.current = ref;
  }, []);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(true);
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const width = rect.width;
      const { totalFrames } = useAppStore.getState();
      const frame = Math.round((x / width) * totalFrames);
      setPlayhead(frame);
    },
    [isDragging, setPlayhead],
  );

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          stepFrame(-1);
          break;
        case 'ArrowRight':
          e.preventDefault();
          stepFrame(1);
          break;
        case ' ':
          e.preventDefault();
          togglePlay();
          break;
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [stepFrame, togglePlay]);

  return { isDragging, handlePointerDown, handlePointerMove, handlePointerUp, setContainerRef };
}
