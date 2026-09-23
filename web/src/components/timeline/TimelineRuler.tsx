import type { CSSProperties } from 'react';

interface TimelineRulerProps {
  totalFrames: number;
  zoomLevel: number;
}

const FPS = 24;
const TICK_INTERVAL = 30; // frames
const HASH_INTERVAL = 5; // frames

export function TimelineRuler({ totalFrames, zoomLevel }: TimelineRulerProps) {
  const totalSeconds = totalFrames / FPS;
  const containerWidth = Math.max(totalSeconds * zoomLevel, 800);

  const tickStyle: CSSProperties = {
    position: 'absolute',
    bottom: 0,
    width: 1,
    background: 'var(--md-outline)',
    opacity: 0.5,
  };

  const hashStyle: CSSProperties = {
    position: 'absolute',
    bottom: 0,
    width: 1,
    background: 'var(--md-outline)',
    opacity: 0.25,
  };

  const labelStyle: CSSProperties = {
    position: 'absolute',
    bottom: 4,
    fontSize: 10,
    fontFamily: 'var(--md-font-code-inline)',
    color: 'var(--md-on-surface-variant)',
    transform: 'translateX(-50%)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
  };

  return (
    <div
      style={{
        height: 28,
        background: 'var(--md-surface-container)',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        position: 'relative',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {Array.from({ length: Math.ceil(totalFrames / TICK_INTERVAL) + 1 }, (_, i) => {
        const frame = i * TICK_INTERVAL;
        const x = (frame / FPS) * zoomLevel;
        if (x > containerWidth) return null;
        return (
          <div key={frame}>
            <div style={{ ...tickStyle, left: x }} />
            <span style={{ ...labelStyle, left: x }}>
              {frame === 0 ? '0f' : `${frame}f`}
            </span>
          </div>
        );
      })}
      {Array.from({ length: Math.ceil(totalFrames / HASH_INTERVAL) + 1 }, (_, i) => {
        const frame = i * HASH_INTERVAL;
        if (frame % TICK_INTERVAL === 0) return null;
        const x = (frame / FPS) * zoomLevel;
        if (x > containerWidth) return null;
        return <div key={`h-${frame}`} style={{ ...hashStyle, left: x }} />;
      })}
    </div>
  );
}
