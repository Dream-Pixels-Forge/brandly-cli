import { useEffect, useRef, useState } from 'react';
import { DndContext, DragOverlay, closestCorners, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, rectSortingStrategy } from '@dnd-kit/sortable';
import { useAppStore } from '../../store';
import type { Clip } from '../../types';
import { Playhead } from './Playhead';
import { TimelineRuler } from './TimelineRuler';
import { TimelineTrackHeader } from './TimelineTrackHeader';
import { TimelineClip } from './TimelineClip';
import { usePlayhead } from '../../hooks/usePlayhead';

export default function TimelinePanel() {
  const { timeline, selectedClipId, zoomLevel, setZoom, reorderClips, setPlayhead, currentFrame, totalFrames } = useAppStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const { isDragging, handlePointerDown, handlePointerMove, handlePointerUp, setContainerRef } = usePlayhead();
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  // Sync playhead drag to container ref
  useEffect(() => {
    if (containerRef.current) setContainerRef(containerRef.current);
  }, [setContainerRef]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const totalDuration = timeline?.clips.reduce((s: number, c: Clip) => s + c.duration, 0) ?? 0;
  const fps = timeline?.fps ?? 24;

  const handleDragStart = (e: any) => {
    setDragOverId(e.active.id as string);
  };

  const handleDragOver = (e: any) => {
    const { over } = e;
    if (!over) return;
    setDragOverId(over.id as string);
  };

  const handleDragEnd = (e: any) => {
    const { active, over } = e;
    if (!over) { setDragOverId(null); return; }
    const clips = useAppStore.getState().timeline?.clips;
    if (!clips) { setDragOverId(null); return; }
    const oldIndex = clips.findIndex((c: Clip) => c.id === (active.id as string));
    const newIndex = clips.findIndex((c: Clip) => c.id === (over.id as string));
    if (oldIndex !== newIndex && oldIndex >= 0 && newIndex >= 0) {
      const reordered = arrayMove([...clips], oldIndex, newIndex);
      reorderClips(reordered.map((c: Clip) => c.id));
    }
    setDragOverId(null);
  };

  const handleDragCancel = () => setDragOverId(null);

  const handleSeek = (frame: number) => {
    setPlayhead(frame);
  };

  const handleTrimEnd = (clipId: string, newDuration: number) => {
    const { timeline: tl, updateClip } = useAppStore.getState();
    if (!tl) return;
    const clip = tl.clips.find((c: Clip) => c.id === clipId);
    if (clip) updateClip(clipId, { duration: Math.max(1, Math.min(12, newDuration)) });
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Timeline header */}
        <div style={{
          height: 36,
          padding: '0 12px',
          borderBottom: '1px solid var(--md-surface-container-highest)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--md-surface-container)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--md-primary)' }}>view_timeline</span>
            <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface)' }}>Timeline Sequencer</span>
            <span style={{ fontSize: 10, color: 'var(--md-on-surface-variant)', fontFamily: 'var(--md-font-code-inline)' }}>
              Snap: 1f · Duration: <span style={{ color: 'var(--md-primary)', fontWeight: 700 }}>{totalFrames}f ({(totalDuration).toFixed(1)}s)</span>
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--md-font-code-inline)', fontSize: 10 }}>
            <button onClick={() => setZoom(Math.max((zoomLevel / 1.5) | 0, 25))}
              style={zoomBtnStyle}>−</button>
            <span style={{ color: 'var(--md-on-surface-variant)', minWidth: 36, textAlign: 'center' }}>{(zoomLevel / 100).toFixed(1)}x</span>
            <button onClick={() => setZoom(Math.min(Math.round(zoomLevel * 1.5), 400))}
              style={zoomBtnStyle}>+</button>
          </div>
        </div>

        {/* Timeline workspace */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
          <SortableContext items={timeline?.clips.map((c: Clip) => c.id) ?? []} strategy={rectSortingStrategy}>
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}>
              {/* Track headers */}
              <TimelineTrackHeader clips={timeline?.clips ?? []} />
              {/* Clip track + ruler */}
              <div ref={(el) => { containerRef.current = el; }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerUp}
                style={{ flex: 1, overflowX: 'auto', overflowY: 'hidden', position: 'relative', minWidth: 0 }}>
                <div style={{ width: Math.max(totalDuration * zoomLevel, 800), minHeight: '100%' }}>
                  {/* Frame ruler */}
                  <TimelineRuler totalFrames={totalFrames} zoomLevel={zoomLevel} />
                  {/* Video track */}
                  <div style={{ height: 64, borderBottom: '1px solid var(--md-surface-container-highest)', position: 'relative', padding: '4px 8px', display: 'flex', gap: 2 }}>
                    {timeline?.clips.map((clip: Clip) => {
                      const startFrame = Math.round((clip.start_time ?? 0) * fps);
                      return (
                        <TimelineClip
                          key={clip.id}
                          clip={clip}
                          isActive={selectedClipId === clip.id}
                          isGenerating={clip.status === 'generating'}
                          isSelected={selectedClipId === clip.id}
                          zoomLevel={zoomLevel}
                          startFrame={startFrame}
                          onTrimStart={() => {}}
                          onTrimEnd={handleTrimEnd}
                          onSeek={handleSeek}
                        />
                      );
                    })}
                    {/* Playhead */}
                    <Playhead
                      frame={currentFrame}
                      totalFrames={totalFrames}
                      onDrag={handlePointerDown}
                      onPointerMove={handlePointerMove}
                      onPointerUp={handlePointerUp}
                      isDragging={isDragging}
                    />
                  </div>
                  {/* Audio placeholder tracks */}
                  <AudioTrackRow label="A1: MiniMax VO" waveform={[]} />
                  <AudioTrackRow label="A2: BGM 124BPM" waveform={[]} />
                </div>
              </div>
            </div>
          </SortableContext>
        </div>

        {/* Drag overlay */}
        <DragOverlay>
          {dragOverId && timeline ? (
            (() => {
              const clip = timeline.clips.find((c: Clip) => c.id === dragOverId);
              if (!clip) return null;
              return (
                <div style={{
                  background: 'var(--md-primary-container)',
                  border: '1px solid var(--md-primary)',
                  borderRadius: 4,
                  padding: '4px 12px',
                  height: 56,
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: 11,
                  fontWeight: 700,
                  fontFamily: 'var(--md-font-code-inline)',
                  color: 'var(--md-on-primary-container)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                }}>
                  {clip.id} · {clip.duration.toFixed(1)}s
                </div>
              );
            })()
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
}

function AudioTrackRow({ label, waveform }: { label: string; waveform: { x: number; amplitude: number }[] }) {
  return (
    <div style={{
      height: 40,
      borderBottom: '1px solid var(--md-surface-container-highest)',
      padding: '0 8px',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      background: 'var(--md-surface-container-lowest)',
    }}>
      <span style={{ fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface-variant)', flexShrink: 0, minWidth: 120 }}>
        <span className="material-symbols-outlined" style={{ fontSize: 13, marginRight: 4, verticalAlign: 'middle' }}>graphic_eq</span>
        {label}
      </span>
      {waveform.length > 0 ? (
        <svg style={{ flex: 1, height: 24, opacity: 0.6 }} viewBox="0 0 500 24" preserveAspectRatio="none">
          <path d={`M0,12 ${waveform.map((p) => `L${(p.x / 7.5) * 500},${12 - p.amplitude * 10}`).join(' ')}`}
            fill="none" stroke="var(--md-tertiary)" strokeWidth="1.5" />
        </svg>
      ) : (
        <div style={{ flex: 1, height: 2, background: 'var(--md-surface-container-highest)', borderRadius: 1 }} />
      )}
    </div>
  );
}

const zoomBtnStyle: React.CSSProperties = {
  width: 24, height: 24,
  background: 'var(--md-surface-container-lowest)',
  border: '1px solid var(--md-surface-container-highest)',
  borderRadius: 4,
  color: 'var(--md-on-surface-variant)',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 14,
  fontFamily: 'monospace',
};
