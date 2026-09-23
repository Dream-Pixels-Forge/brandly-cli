import { useEffect } from 'react';
import { useAppStore, withToken } from './store';
import type { Clip } from './types';
import './index.css';

function App() {
  const { projects, activeProject, loading, error, fetchProjects, selectProject, timeline, selectedClipId, zoomLevel, updateClip, regenerateClip, exportProject, isPlaying } = useAppStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const fmtTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const clipStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      generated: '#4ade80',
      pending: '#facc15',
      generating: '#60a5fa',
      failed: '#f87171',
    };
    return colors[status] || '#6b7280';
  };

  const totalDuration = timeline?.clips.reduce((sum: number, c: Clip) => sum + c.duration, 0) ?? 0;

const handlePlay = () => {
    if (isPlaying) return;
    if (!timeline || timeline.clips.length === 0) return;
    let idx = 0;
    const playNext = () => {
      if (idx >= timeline.clips.length) return;
      useAppStore.setState({ selectedClipId: timeline.clips[idx].id });
      idx++;
    };
    playNext();
  };

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

  return (
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
          {error && <span style={{ fontSize: 11, color: '#f87171' }}>{error}</span>}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <button onClick={() => fetchProjects()} style={btnStyle}>Refresh</button>
            <button onClick={() => exportProject()} style={{ ...btnStyle, background: '#2563eb', borderColor: '#2563eb', color: '#fff' }}>Export</button>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Preview Panel */}
          <div style={{ width: 400, background: '#0d0d0d', borderRight: '1px solid #222', display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
              {selectedClipId && timeline ? (
                (() => {
                  const clip = timeline.clips.find((c: Clip) => c.id === selectedClipId);
                  if (!clip) return <div style={{ color: '#555', fontSize: 13 }}>Select a clip</div>;
                  return (
                    <video
                      src={withToken(`/api/projects/${activeProject?.id}/clips/${encodeURIComponent(clip.id)}/preview`)}
                      controls
                      style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 4, background: '#000' }}
                    />
                  );
                })()
              ) : (
                <div style={{ textAlign: 'center', color: '#444', fontSize: 13 }}><p>Select a clip to preview</p></div>
              )}
            </div>

            {selectedClipId && timeline && (
              <div style={{ padding: 16, borderTop: '1px solid #222' }}>
                <h3 style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, color: '#888', textTransform: 'uppercase' }}>Clip Properties</h3>
                {(() => {
                  const clip = timeline.clips.find((c: Clip) => c.id === selectedClipId);
                  if (!clip) return null;
                  return (
                    <>
                      <div style={{ marginBottom: 12 }}>
                        <label style={{ display: 'block', fontSize: 11, color: '#666', marginBottom: 4 }}>Duration (s)</label>
                        <input type="number" min={1} max={12} step={0.1} value={clip.duration}
                          onChange={(e) => updateClip(clip.id, { duration: parseFloat(e.target.value) })} style={inputStyle} />
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <label style={{ display: 'block', fontSize: 11, color: '#666', marginBottom: 4 }}>Transition</label>
                        <select value={clip.transition_in || ''}
                          onChange={(e) => updateClip(clip.id, { transition_in: e.target.value || null })} style={inputStyle}>
                          <option value="">None</option>
                          <option value="fade">Fade</option>
                          <option value="dissolve">Dissolve</option>
                          <option value="wipe">Wipe</option>
                          <option value="slide">Slide</option>
                        </select>
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <label style={{ display: 'block', fontSize: 11, color: '#666', marginBottom: 4 }}>Volume</label>
                        <input type="range" min={0} max={1} step={0.1} value={clip.volume}
                          onChange={(e) => updateClip(clip.id, { volume: parseFloat(e.target.value) })} style={{ width: '100%' }} />
                      </div>
                      <button onClick={() => regenerateClip(clip.id)} style={{ ...btnStyle, width: '100%' }}>Regenerate</button>
                    </>
                  );
                })()}
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

            <div style={{ flex: 1, overflowX: 'auto', overflowY: 'hidden', position: 'relative' }}>
              {timeline && timeline.clips.length > 0 ? (
                <div style={{ width: Math.max(totalDuration * zoomLevel, 800), height: '100%', position: 'relative', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ height: 24, background: '#111', borderBottom: '1px solid #222', position: 'relative' }}>
                    {Array.from({ length: Math.ceil(totalDuration) + 1 }, (_, i) => (
                      <span key={i} style={{ position: 'absolute', left: i * zoomLevel, fontSize: 10, color: '#555', bottom: 2 }}>{i}s</span>
                    ))}
                  </div>
                  <div style={{ flex: 1, position: 'relative', background: '#0d0d0d' }}>
                    {timeline.clips.map((clip: Clip) => {
                      const left = (clip.start_time ?? 0) * zoomLevel;
                      const width = clip.duration * zoomLevel;
                      const isSelected = selectedClipId === clip.id;
                      return (
                        <div
                          key={clip.id}
                          onClick={() => useAppStore.setState({ selectedClipId: clip.id })}
                          style={{
                            position: 'absolute',
                            left,
                            top: 10,
                            width,
                            height: 60,
                            background: clipStatusColor(clip.status),
                            borderRadius: 4,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            padding: '0 8px',
                            fontSize: 11,
                            fontWeight: 500,
                            border: isSelected ? '2px solid #2563eb' : '1px solid transparent',
                            overflow: 'hidden',
                          }}
                        >
                          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{clip.id}</span>
                          <span style={{ marginLeft: 'auto', fontSize: 9, opacity: 0.7 }}>{clip.duration}s</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#444', fontSize: 13 }}>
                  No clips in timeline
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
