import { useState } from 'react';
import type { CSSProperties } from 'react';
import type { Clip } from '../../types';

interface TimelineClipProps {
  clip: Clip;
  isActive: boolean;
  isGenerating: boolean;
  isSelected: boolean;
  onTrimStart: (clipId: string, delta: number) => void;
  onTrimEnd: (clipId: string, delta: number) => void;
  onSeek: (frame: number) => void;
  zoomLevel: number;
  startFrame: number;
}

const MIN_DURATION = 1;
const MAX_DURATION = 12;
const HANDLE_W = 8;

function qualityBadgeColor(status: string | null) {
  switch (status) {
    case 'pass': return '#4ade80';
    case 'warn': return '#facc15';
    case 'fail': return '#f87171';
    default: return null;
  }
}

export function TimelineClip({
  clip,
  isActive,
  isGenerating,
  isSelected,
  onTrimStart,
  onTrimEnd,
  onSeek,
  zoomLevel,
  startFrame,
}: TimelineClipProps) {
  const [dragging, setDragging] = useState<'start' | 'end' | null>(null);

  const leftPx = (startFrame / 24) * zoomLevel;
  const widthPx = clip.duration * zoomLevel;

  const style: CSSProperties = {
    position: 'absolute',
    left: leftPx,
    top: 0,
    width: widthPx,
    height: '100%',
    background: isGenerating
      ? 'repeating-linear-gradient(135deg, var(--md-tertiary-container) 0px, var(--md-tertiary-container) 4px, var(--md-surface-container-high) 4px, var(--md-surface-container-high) 8px)'
      : isActive
        ? 'var(--md-primary-container)'
        : 'var(--md-surface-container-high)',
    border: isSelected
      ? '2px solid var(--md-primary)'
      : isGenerating
        ? `2px solid var(--md-tertiary)`
        : '1px solid var(--md-outline-variant, #3d494c)',
    borderRadius: 4,
    cursor: 'grab',
    display: 'flex',
    alignItems: 'center',
    padding: '0 8px',
    overflow: 'hidden',
    userSelect: 'none',
    transition: dragging ? 'none' : 'border-color 150ms ease, background 150ms ease',
    zIndex: isSelected || dragging ? 5 : 1,
  };

  const handleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).dataset.trimHandle) return;
    onSeek(startFrame);
  };

  const handleTrimStartDown = (e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging('start');
    const startX = e.clientX;
    const startDuration = clip.duration;
    const zoom = zoomLevel;
    const onMove = (ev: PointerEvent) => {
      const dx = (ev.clientX - startX) / zoom;
      const newDur = Math.max(MIN_DURATION, Math.min(MAX_DURATION, startDuration + dx));
      onTrimStart(clip.id, newDur - startDuration);
    };
    const onUp = () => {
      setDragging(null);
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
    };
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
  };

  const handleTrimEndDown = (e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging('end');
    const startX = e.clientX;
    const startDuration = clip.duration;
    const zoom = zoomLevel;
    const onMove = (ev: PointerEvent) => {
      const dx = (ev.clientX - startX) / zoom;
      const newDur = Math.max(MIN_DURATION, Math.min(MAX_DURATION, startDuration + dx));
      onTrimEnd(clip.id, newDur - startDuration);
    };
    const onUp = () => {
      setDragging(null);
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
    };
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
  };

  const qColor = qualityBadgeColor(clip.quality_status);

  const infoStyle: CSSProperties = {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    fontSize: 11,
    fontWeight: 500,
    color: 'var(--md-on-surface)',
    flex: 1,
    minWidth: 0,
  };

  const badgeStyle = (bg: string, color: string): CSSProperties => ({
    fontSize: 9,
    fontWeight: 700,
    color,
    background: bg,
    padding: '1px 4px',
    borderRadius: 3,
    textTransform: 'uppercase',
    marginLeft: 4,
    flexShrink: 0,
  });

  return (
    <div style={style} onClick={handleClick} data-clip-id={clip.id}>
      <TrimHandle
        side="start"
        onPointerDown={handleTrimStartDown}
        isSelected={isSelected || dragging === 'start'}
      />
      <span style={infoStyle}>
        #{clip.index_in_scene + 1} {clip.prompt.slice(0, 20)}{clip.prompt.length > 20 ? '…' : ''}
      </span>
      {qColor && (
        <span style={badgeStyle(`${qColor}22`, qColor)}>{clip.quality_status}</span>
      )}
      {isGenerating && (
        <span style={badgeStyle('var(--md-tertiary-container)', 'var(--md-on-tertiary-container)')}>
          Agnes ETA
        </span>
      )}
      <span style={{ fontSize: 9, color: 'var(--md-on-surface-variant)', paddingRight: 4, flexShrink: 0 }}>
        {clip.duration.toFixed(1)}s
      </span>
      <TrimHandle
        side="end"
        onPointerDown={handleTrimEndDown}
        isSelected={isSelected || dragging === 'end'}
      />
    </div>
  );
}

function TrimHandle({
  side,
  onPointerDown,
  isSelected,
}: {
  side: 'start' | 'end';
  onPointerDown: (e: React.PointerEvent) => void;
  isSelected: boolean;
}) {
  const style: CSSProperties = {
    position: 'absolute',
    left: side === 'start' ? 0 : undefined,
    right: side === 'end' ? 0 : undefined,
    top: 0,
    bottom: 0,
    width: HANDLE_W,
    cursor: 'ew-resize',
    background: isSelected ? 'rgba(76,215,246,0.3)' : 'rgba(0,0,0,0.3)',
    borderRadius: side === 'start' ? '4px 0 0 4px' : '0 4px 4px 0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  };
  return (
    <div data-trim-handle="1" onPointerDown={onPointerDown} style={style}>
      <div style={{ width: 2, height: 16, background: isSelected ? 'var(--md-primary)' : '#aaa', borderRadius: 1 }} />
    </div>
  );
}
