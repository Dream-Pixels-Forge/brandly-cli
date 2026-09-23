import type { CSSProperties } from 'react';
import { useAppStore } from '../../store';

interface PlayheadProps {
  frame: number;
  totalFrames: number;
  onDrag: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerMove: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerUp: () => void;
  isDragging: boolean;
}

export function Playhead({ totalFrames, onDrag, onPointerMove, onPointerUp, isDragging }: PlayheadProps) {
  const { currentFrame } = useAppStore();
  const pct = totalFrames > 0 ? (currentFrame / totalFrames) * 100 : 0;

  const lineStyle: CSSProperties = {
    position: 'absolute',
    top: 0,
    left: `${pct}%`,
    width: 2,
    height: '100%',
    background: isDragging ? 'var(--md-primary)' : 'var(--md-primary)',
    boxShadow: isDragging ? '0 0 8px var(--md-primary), 0 0 16px var(--md-primary)' : 'none',
    zIndex: 20,
    cursor: isDragging ? 'grabbing' : 'grab',
    pointerEvents: 'none',
    transform: 'translateX(-50%)',
  };

  const badgeStyle: CSSProperties = {
    position: 'absolute',
    top: -20,
    left: '50%',
    transform: 'translateX(-50%)',
    background: 'var(--md-primary)',
    color: 'var(--md-on-primary)',
    fontSize: 9,
    fontWeight: 700,
    fontFamily: 'var(--md-font-code-inline)',
    padding: '1px 4px',
    borderRadius: 3,
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
  };

  const hitAreaStyle: CSSProperties = {
    position: 'absolute',
    top: 0,
    left: '50%',
    width: 16,
    height: '100%',
    transform: 'translateX(-50%)',
    cursor: 'grab',
    zIndex: 25,
  };

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      <div style={lineStyle}>
        <div style={badgeStyle}>{currentFrame}f</div>
      </div>
      <div
        style={hitAreaStyle}
        onPointerDown={onDrag}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      />
    </div>
  );
}
