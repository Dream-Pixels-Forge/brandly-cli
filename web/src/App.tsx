import { useEffect, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useAppStore, withToken } from './store';
import type { Clip } from './types';
import './index.css';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MIN_DURATION = 1;
const MAX_DURATION = 12;
const HANDLE_W = 8;

// ---------------------------------------------------------------------------
// Sortable clip with trim handles
// ---------------------------------------------------------------------------

function SortableClip({
  clip,
  zoomLevel,
  selectedClipId,
}: {
  clip: Clip;
  zoomLevel: number;
  selectedClipId: string | null;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: clip.id });
  const isSelected = selectedClipId === clip.id;

  const qColor = clip.quality_status === 'pass' ? '#4ade80'
    : clip.quality_status === 'warn' ? '#facc15'
    : clip.quality_status === 'fail' ? '#f87171'
    : null;

  const style: React.CSSProperties = {
    position: 'absolute',
    left: (clip.start_time ?? 0) * zoomLevel,
    top: 10,
    width: clip.duration * zoomLevel,
    height: 60,
    background: statusColor(clip.status),
    borderRadius: 4,
    cursor: isDragging ? 'grabbing' : 'grab',
    display: 'flex',
    alignItems: 'center',
    padding: '0 8px',
    fontSize: 11,
    fontWeight: 500,
    border: isSelected ? '2px solid #2563eb' : '1px solid transparent',
    overflow: 'hidden',
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 10 : 1,
    userSelect: 'none',
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {/* Left trim handle */}
      <TrimHandle
        side="start"
        clipId={clip.id}
        duration={clip.duration}
        width={HANDLE_W}
        isSelected={isSelected}
        startZoomLevel={zoomLevel}
      />

      <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', paddingLeft: 4, paddingRight: 4, flex: 1 }}>
        {clip.id}
      </span>
      {qColor && (
        <span style={{ fontSize: 9, fontWeight: 700, color: qColor, marginRight: 4, textTransform: 'uppercase' }}>
          {clip.quality_status}
        </span>
      )}
      <span style={{ fontSize: 9, opacity: 0.7, paddingRight: 4 }}>{clip.duration.toFixed(1)}s</span>

      {/* Right trim handle */}
      <TrimHandle
        side="end"
        clipId={clip.id}
        duration={clip.duration}
        width={HANDLE_W}
        isSelected={isSelected}
        startZoomLevel={zoomLevel}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trim handle — pointer-drag to adjust duration
// ---------------------------------------------------------------------------

function TrimHandle({
  side,
  clipId,
  duration,
  width,
  isSelected,
  startZoomLevel,
}: {
  side: 'start' | 'end';
  clipId: string;
  duration: number;
  width: number;
  isSelected: boolean;
  startZoomLevel: number;
}) {
  const [dragging, setDragging] = useState(false);

  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);

    const startX = e.clientX;
    const startDuration = duration;
    const zoom = startZoomLevel;

    const onMove = (ev: PointerEvent) => {
      const dxPx = ev.clientX - startX;
      const dx = dxPx / zoom;
      let newDuration: number;
      if (side === 'end') {
        newDuration = Math.max(MIN_DURATION, Math.min(MAX_DURATION, startDuration + dx));
      } else {
        // Start handle: moving right shortens, moving left lengthens
        newDuration = Math.max(MIN_DURATION, Math.min(MAX_DURATION, startDuration - dx));
      }
      // Optimistic update
      useAppStore.setState((s) => ({
        timeline: s.timeline
          ? {
              ...s.timeline,
              clips: s.timeline.clips.map((c: Clip) =>
                c.id === clipId ? { ...c, duration: newDuration } : c
              ),
            }
          : null,
      }));
    };

    const onUp = () => {
      setDragging(false);
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      // Persist to server
      const state = useAppStore.getState();
      const current = state.timeline?.clips.find((c: Clip) => c.id === clipId);
      if (current && current.duration !== duration) {
        state.updateClip(clipId, { duration: current.duration });
      }
    };

    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
  };

  return (
    <div
      data-trim-handle="1"
      onPointerDown={handlePointerDown}
      style={{
        position: 'absolute',
        left: side === 'start' ? 0 : undefined,
        right: side === 'end' ? 0 : undefined,
        top: 0,
        bottom: 0,
        width,
        cursor: 'ew-resize',
        background: isSelected ? 'rgba(37,99,235,0.3)' : dragging ? 'rgba(37,99,235,0.5)' : 'rgba(0,0,0,0.2)',
        borderRadius: side === 'start' ? '4px 0 0 4px' : '0 4px 4px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ width: 2, height: 16, background: isSelected ? '#60a5fa' : '#aaa', borderRadius: 1 }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function statusColor(status: string) {
  return {
    generated: '#4ade80',
    pending: '#facc15',
    generating: '#60a5fa',
    failed: '#f87171',
  }[status] || '#6b7280';
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

function App() {
  const {
    projects, activeProject, loading, error, fetchProjects, selectProject,
    timeline, selectedClipId, zoomLevel, updateClip, reorderClips,
    regenerateClip, exportProject, isPlaying, wsEvent, exportDone,
  } = useAppStore();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const [dragOverId, setDragOverId] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Connect WebSocket when a project is selected
  useEffect(() => {
    if (!activeProject) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/${activeProject.id}`;
    const ws = new WebSocket(withToken(wsUrl).replace(window.location.origin, ''));
    ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data);
        const eventType = msg.type || '';
        if (eventType.startsWith('generation_')) {
          useAppStore.setState({ wsEvent: `${eventType} · ${msg.phase || ''}` });
          setTimeout(() => useAppStore.setState({ wsEvent: null }), 2000);
        }
      } catch { /* ignore */ }
    };
    ws.onerror = () => ws.close();
    return () => { ws.close(); };
  }, [activeProject?.id]);

  const handleDragStart = (event: DragStartEvent) => {
    setDragOverId(event.active.id as string);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;
    if (!over) return;
    setDragOverId(over.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) { setDragOverId(null); return; }
    const activeId = active.id as string;
    const overId = over.id as string;
    const clips = useAppStore.getState().timeline?.clips;
    if (!clips) { setDragOverId(null); return; }
    const oldIndex = clips.findIndex((c: Clip) => c.id === activeId);
    const newIndex = clips.findIndex((c: Clip) => c.id === overId);
    if (oldIndex !== newIndex && oldIndex >= 0 && newIndex >= 0) {
      const newClips = arrayMove([...clips], oldIndex, newIndex);
      reorderClips(newClips.map((c: Clip) => c.id));
    }
    setDragOverId(null);
  };

  const handleDragCancel = () => setDragOverId(null);

  const btnStyle: React.CSSProperties = {
    padding: '6px 12px',
    borderRadius: 4,
    border: '1px solid #333',
    background: '#1a1a1a',
    color: '#e0e0e0',
    fontSize: 12,
    cursor: 'pointer',
  };

  const playBtnStyle: React.CSSProperties = { ...btnStyle, width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center' };
  const inputStyle: React.CSSProperties = { width: '100%', padding: '6px 8px', background: '#1a1a1a', border: '1px solid #333', borderRadius: 4, color: '#e0e0e0', fontSize: 12 };

  const totalDuration = timeline?.clips.reduce((sum: number, c: Clip) => sum + c.duration, 0) ?? 0;

  const handlePlay = () => {
    if (isPlaying) return;
    if (!timeline || timeline.clips.length === 0) return;
    useAppStore.setState({ selectedClipId: timeline.clips[0].id });
  };

  const selectedClip = timeline?.clips.find((c: Clip) => c.id === selectedClipId) ?? null;

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div style={{ display: 'flex', height: '100vh', background: '#0a0a0a', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', margin: 0, padding: 0 }}>
        {/* Sidebar */}
        <aside style={{ width: 240, background: '#111', borderRight: '1px solid #222', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: 16, borderBottom: '1px solid #222' }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>Projects</h2>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
            {loading && projects.length === 0 ? (
              <div style={{ padding: 16, color: '#555', fontSize: 13 }}>Loading...</div>
            ) : projects.length === 0 ? (
              <div style={{ padding: 16, color: '#444', fontSize: 13 }}>No projects found</div>
            ) : (
              projects.map((p) => (
                <div
                  key={p.id}
                  onClick={() => selectProject(p.id)}
                  style={{
                    padding: 12,
                    background: activeProject?.id === p.id ? '#1a3a5c' : '#1a1a1a',
                    borderRadius: 6,
                    marginBottom: 8,
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{p.name || p.id}</div>
                  <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 6px',
                      borderRadius: 3,
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      background: p.status === 'completed' ? '#052e16' : p.status === 'running' ? '#1e3a5f' : '#374151',
                      color: p.status === 'completed' ? '#4ade80' : p.status === 'running' ? '#60a5fa' : '#9ca3af',
                    }}>{p.status}</span>
                    {p.shot_count > 0 && ` · ${p.shot_count} shots`}
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Main */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Top bar */}
          <div style={{ height: 48, background: '#111', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', padding: '0 16px', gap: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: '#fff' }}>{activeProject?.name || 'Select a project'}</span>
            {wsEvent && (
              <span style={{ fontSize: 11, color: '#facc15', fontVariantNumeric: 'tabular-nums', background: '#1e3a5f', padding: '2px 8px', borderRadius: 3 }}>
                {wsEvent}
              </span>
            )}
            {error && <span style={{ fontSize: 11, color: '#f87171' }}>{error}</span>}
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <button onClick={() => fetchProjects()} style={btnStyle}>Refresh</button>
              <button onClick={() => exportProject()} style={{ ...btnStyle, background: exportDone ? '#059669' : '#2563eb', borderColor: exportDone ? '#059669' : '#2563eb', color: '#fff' }}>
                {exportDone ? '✓ Exported' : 'Export'}
              </button>
            </div>
          </div>

          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {/* Preview Panel */}
            <div style={{ width: 400, background: '#0d0d0d', borderRight: '1px solid #222', display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
                {selectedClip ? (
                  <video
                    src={withToken(`/api/projects/${activeProject?.id}/clips/${encodeURIComponent(selectedClip.id)}/preview`)}
                    controls
                    style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 4, background: '#000' }}
                  />
                ) : (
                  <div style={{ textAlign: 'center', color: '#444', fontSize: 13 }}><p>Select a clip to preview</p></div>
                )}
              </div>

              {selectedClip && (
                <div style={{ padding: 16, borderTop: '1px solid #222' }}>
                  <h3 style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, color: '#888', textTransform: 'uppercase' }}>Clip Properties</h3>
                  <div style={{ marginBottom: 12 }}>
                    <label style={{ display: 'block', fontSize: 11, color: '#666', marginBottom: 4 }}>Duration (s)</label>
                    <input type="number" min={MIN_DURATION} max={MAX_DURATION} step={0.1} value={selectedClip.duration}
                      onChange={(e) => updateClip(selectedClip.id, { duration: parseFloat(e.target.value) })} style={inputStyle} />
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <label style={{ display: 'block', fontSize: 11, color: '#666', marginBottom: 4 }}>Transition</label>
                    <select value={selectedClip.transition_in || ''}
                      onChange={(e) => updateClip(selectedClip.id, { transition_in: e.target.value || null })} style={inputStyle}>
                      <option value="">None</option>
                      <option value="fade">Fade</option>
                      <option value="dissolve">Dissolve</option>
                      <option value="wipe">Wipe</option>
                      <option value="slide">Slide</option>
                    </select>
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <label style={{ display: 'block', fontSize: 11, color: '#666', marginBottom: 4 }}>Volume</label>
                    <input type="range" min={0} max={1} step={0.1} value={selectedClip.volume}
                      onChange={(e) => updateClip(selectedClip.id, { volume: parseFloat(e.target.value) })} style={{ width: '100%' }} />
                  </div>
                  <button onClick={() => regenerateClip(selectedClip.id)} style={{ ...btnStyle, width: '100%' }}>Regenerate</button>
                </div>
              )}
            </div>

            {/* Timeline Area */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#0a0a0a' }}>
              <div style={{ height: 40, background: '#111', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', padding: '0 16px', gap: 12 }}>
                <button onClick={handlePlay} style={playBtnStyle}>{isPlaying ? '⏸' : '▶'}</button>
                <span style={{ fontSize: 11, color: '#666', fontVariantNumeric: 'tabular-nums' }}>{fmtTime(totalDuration)}</span>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                  <button onClick={() => useAppStore.setState(s => ({ zoomLevel: Math.max(s.zoomLevel / 1.5, 25) }))} style={playBtnStyle}>−</button>
                  <span style={{ fontSize: 11, color: '#666', minWidth: 30, textAlign: 'center' }}>{(zoomLevel / 100).toFixed(1)}x</span>
                  <button onClick={() => useAppStore.setState(s => ({ zoomLevel: Math.min(s.zoomLevel * 1.5, 400) }))} style={playBtnStyle}>+</button>
                </div>
              </div>

              <SortableContext items={timeline?.clips.map((c: Clip) => c.id) ?? []} strategy={rectSortingStrategy}>
                <div style={{
                  flex: 1,
                  overflowX: 'auto',
                  overflowY: 'hidden',
                  position: 'relative',
                }}>
                  {timeline && timeline.clips.length > 0 ? (
                    <div style={{ width: Math.max(totalDuration * zoomLevel, 800), height: '100%', display: 'flex', flexDirection: 'column' }}>
                      {/* Time ruler */}
                      <div style={{ height: 24, background: '#111', borderBottom: '1px solid #222', position: 'relative' }}>
                        {Array.from({ length: Math.ceil(totalDuration) + 1 }, (_, i) => (
                          <span key={i} style={{ position: 'absolute', left: i * zoomLevel, fontSize: 10, color: '#555', bottom: 2 }}>{i}s</span>
                        ))}
                      </div>
                      {/* Clip track */}
                      <div style={{ flex: 1, position: 'relative', background: '#0d0d0d', padding: '8px 0' }}>
                        {timeline.clips.map((clip: Clip) => (
                          <SortableClip
                            key={clip.id}
                            clip={clip}
                            zoomLevel={zoomLevel}
                            selectedClipId={selectedClipId}
                          />
                        ))}
                        {/* Drop indicator */}
                        {dragOverId && (() => {
                          const idx = timeline.clips.findIndex((c: Clip) => c.id === dragOverId);
                          if (idx < 0) return null;
                          const c = timeline.clips[idx];
                          const left = (c.start_time ?? 0) * zoomLevel + c.duration * zoomLevel;
                          return (
                            <div style={{
                              position: 'absolute',
                              left,
                              top: 8,
                              bottom: 8,
                              width: 2,
                              background: '#facc15',
                              zIndex: 20,
                            }} />
                          );
                        })()}
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#444', fontSize: 13 }}>
                      No clips in timeline
                    </div>
                  )}
                </div>
              </SortableContext>
            </div>
          </div>
        </main>

        <SaveToast />
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {dragOverId && timeline ? (
          (() => {
            const clip = timeline.clips.find((c: Clip) => c.id === dragOverId);
            if (!clip) return null;
            return (
              <div style={{
                background: statusColor(clip.status),
                borderRadius: 4,
                padding: '0 12px',
                height: 60,
                display: 'flex',
                alignItems: 'center',
                fontSize: 12,
                fontWeight: 600,
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                opacity: 0.9,
              }}>
                {clip.id} · {clip.duration.toFixed(1)}s
              </div>
            );
          })()
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

// ---------------------------------------------------------------------------
// Save toast
// ---------------------------------------------------------------------------

function SaveToast() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const handler = () => { setVisible(true); setTimeout(() => setVisible(false), 1200); };
    window.addEventListener('brandly-save', handler as EventListener);
    return () => window.removeEventListener('brandly-save', handler as EventListener);
  }, []);
  if (!visible) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24,
      background: '#1a3a5c', border: '1px solid #2563eb',
      borderRadius: 6, padding: '8px 16px', fontSize: 12,
      color: '#93c5fd', zIndex: 100,
      boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
    }}>
      ✓ Changes saved
    </div>
  );
}

export default App;
