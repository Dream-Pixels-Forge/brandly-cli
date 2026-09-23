import type { CSSProperties } from 'react';
import { useAppStore } from '../../store';
import type { Clip } from '../../types';

interface TimelineTrackHeaderProps {
  clips: Clip[];
}

function MuteSoloBtn({
  mode,
  isMuted,
  isSolo,
  onClick,
}: {
  mode: 'M' | 'S';
  isMuted: boolean;
  isSolo: boolean;
  onClick: () => void;
}) {
  const active = mode === 'M' ? isMuted : isSolo;
  const style: CSSProperties = {
    width: 22,
    height: 22,
    borderRadius: 4,
    border: '1px solid var(--md-outline)',
    background: active ? 'var(--md-primary)' : 'var(--md-surface-container-highest)',
    color: active ? 'var(--md-on-primary)' : 'var(--md-on-surface-variant)',
    fontSize: 9,
    fontWeight: 700,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--md-font-code-inline)',
    transition: 'all 150ms ease',
    padding: 0,
    lineHeight: 1,
  };
  return <button style={style} onClick={onClick}>{mode}</button>;
}

function TrackRow({
  label,
  muted,
  solo,
  onToggleMute,
  onToggleSolo,
}: {
  label: string;
  muted: boolean;
  solo: boolean;
  onToggleMute: () => void;
  onToggleSolo: () => void;
}) {
  const style: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    height: 64,
    paddingRight: 12,
    borderBottom: '1px solid var(--md-surface-container-highest)',
  };
  const labelStyle: CSSProperties = {
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--md-on-surface-variant)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontFamily: 'var(--md-font-code-inline)',
    minWidth: 48,
  };
  return (
    <div style={style}>
      <span style={labelStyle}>{label}</span>
      <MuteSoloBtn mode="M" isMuted={muted} isSolo={solo} onClick={onToggleMute} />
      <MuteSoloBtn mode="S" isMuted={muted} isSolo={solo} onClick={onToggleSolo} />
    </div>
  );
}

export function TimelineTrackHeader(_props: TimelineTrackHeaderProps) {
  const { timeline } = useAppStore();
  const clips = timeline?.clips ?? [];

  return (
    <div
      style={{
        width: 200,
        flexShrink: 0,
        background: 'var(--md-surface-container)',
        borderRight: '1px solid var(--md-surface-container-highest)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: 28,
          borderBottom: '1px solid var(--md-surface-container-highest)',
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 12,
          fontSize: 10,
          fontWeight: 700,
          color: 'var(--md-on-surface-variant)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          fontFamily: 'var(--md-font-code-inline)',
        }}
      >
        Tracks · {clips.length} clips
      </div>
      <TrackRow label="VIDEO" muted={false} solo={false} onToggleMute={() => {}} onToggleSolo={() => {}} />
      <TrackRow label="A1" muted={false} solo={false} onToggleMute={() => {}} onToggleSolo={() => {}} />
      <TrackRow label="A2" muted={false} solo={false} onToggleMute={() => {}} onToggleSolo={() => {}} />
    </div>
  );
}
