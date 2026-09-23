import { useAppStore } from '../../store';
import type { Clip } from '../../types';

export default function ShotListPanel() {
  const { timeline, selectedClipId, setSelectedClip, setPanel, regenerateClip, loading } = useAppStore();

  if (loading && (!timeline || timeline.clips.length === 0)) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%',
        color: 'var(--md-on-surface-variant)', fontSize: 12, fontFamily: 'var(--md-font-code-inline)',
      }}>
        Loading...
      </div>
    );
  }

  if (!timeline || timeline.clips.length === 0) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%',
        gap: 12, color: 'var(--md-on-surface-variant)', fontSize: 12,
      }}>
        <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.3 }}>videocam_off</span>
        <div>No shots yet</div>
        <div style={{ fontSize: 11, opacity: 0.6 }}>Run <code style={{ background: 'var(--md-surface-container-highest)', padding: '2px 6px', borderRadius: 3, fontFamily: 'var(--md-font-code-inline)' }}>brandly produce</code> to generate shots</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 15, color: 'var(--md-primary)' }}>video_library</span>
          <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface)' }}>Shots & Sequences</span>
        </div>
        <span style={{
          fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)',
          background: 'rgba(76,215,246,0.12)', border: '1px solid rgba(76,215,246,0.3)',
          padding: '1px 6px', borderRadius: 9999, fontWeight: 700,
        }}>
          {timeline.clips.length} SHOTS
        </span>
      </div>

      {/* Clip list */}
      <div style={{ flex: 1, overflowY: 'auto', borderTop: '1px solid var(--md-surface-container-highest)' }}>
        {timeline.clips.map((clip: Clip, idx: number) => {
          const isActive = selectedClipId === clip.id;
          const isGenerating = clip.status === 'generating';
          const isReady = clip.status === 'generated';

          return (
            <div
              key={clip.id}
              onClick={() => { setSelectedClip(clip.id); setPanel('preview'); }}
              style={{
                padding: '10px 12px',
                borderLeft: `3px solid ${isActive ? 'var(--md-primary)' : isGenerating ? 'var(--md-tertiary)' : 'transparent'}`,
                background: isActive ? 'var(--md-surface-container)' : 'transparent',
                cursor: 'pointer',
                transition: 'background var(--md-transition-fast)',
              }}
              onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'var(--md-surface-container-low)'; }}
              onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    fontFamily: 'var(--md-font-code-inline)',
                    fontSize: 11,
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? 'var(--md-primary)' : 'var(--md-on-surface)',
                  }}>
                    {String(idx + 1).padStart(2, '0')}: {clip.id}
                  </span>
                  {isGenerating && (
                    <span style={{
                      display: 'flex', alignItems: 'center', gap: 4,
                      fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-tertiary)',
                      background: 'rgba(255,184,115,0.12)', border: '1px solid rgba(255,184,115,0.3)',
                      padding: '1px 6px', borderRadius: 3,
                    }}>
                      <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--md-tertiary)', animation: 'ping 1s infinite' }} />
                      Agnes
                    </span>
                  )}
                  {isReady && (
                    <span style={{
                      fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-secondary)',
                      background: 'var(--md-surface-container-lowest)', border: '1px solid var(--md-surface-container-highest)',
                      padding: '1px 6px', borderRadius: 3,
                    }}>
                      Cached
                    </span>
                  )}
                </div>
                <span style={{ fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface-variant)' }}>
                  {Math.round(clip.duration * (timeline.fps ?? 24))}f
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 10, color: 'var(--md-on-surface-variant)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60%' }}>
                  {clip.prompt.substring(0, 40)}{clip.prompt.length > 40 ? '...' : ''}
                </span>
                <span style={{
                  fontSize: 9,
                  fontFamily: 'var(--md-font-code-inline)',
                  color: isActive ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
                }}>
                  {idx === 0 ? '0' : Math.round(timeline.clips.slice(0, idx).reduce((s, c) => s + c.duration, 0) * (timeline.fps ?? 24))} → {Math.round((clip.start_time ?? 0) * (timeline.fps ?? 24) + clip.duration * (timeline.fps ?? 24))}f
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 12px',
        borderTop: '1px solid var(--md-surface-container-highest)',
        background: 'var(--md-surface-container)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        flexShrink: 0,
      }}>
        <button
          onClick={() => regenerateClip(selectedClipId ?? timeline.clips[0]?.id)}
          style={{
            width: '100%',
            height: 30,
            background: 'var(--md-surface-container-lowest)',
            border: '1px solid var(--md-surface-container-highest)',
            color: 'var(--md-on-surface)',
            borderRadius: 4,
            fontSize: 10,
            fontFamily: 'var(--md-font-code-inline)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--md-primary)' }}>add</span>
          Regenerate Selected Shot
        </button>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 9,
          fontFamily: 'var(--md-font-code-inline)',
          color: 'var(--md-on-surface-variant)',
        }}>
          <span>Synced with <span style={{ color: 'var(--md-on-surface)', fontWeight: 600 }}>production_plan.md</span></span>
        </div>
      </div>
    </div>
  );
}
