import { useRef, useEffect } from 'react';
import { useAppStore, withToken } from '../../store';
import type { Clip } from '../../types';
import TransportControls from './TransportControls';

export default function PreviewPanel() {
  const { selectedClipId, timeline, activeProject, currentFrame, totalFrames, isPlaying, volume, setPlayhead } = useAppStore();
  const videoRef = useRef<HTMLVideoElement>(null);
  const clip = timeline?.clips.find((c: Clip) => c.id === selectedClipId) ?? null;

  // Sync video playback with store frame position
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onTime = () => {
      const fps = timeline?.fps ?? 24;
      const frame = Math.round(v.currentTime * fps);
      if (frame !== currentFrame) setPlayhead(frame);
    };
    const onEnded = () => {
      // Auto-advance: find next clip or loop
      if (!timeline) return;
      const idx = timeline.clips.findIndex((c: Clip) => c.id === selectedClipId);
      if (idx < timeline.clips.length - 1) {
        const next = timeline.clips[idx + 1];
        useAppStore.setState({ selectedClipId: next.id });
        if (videoRef.current) {
          videoRef.current.src = withToken(`/api/projects/${activeProject?.id}/clips/${encodeURIComponent(next.id)}/preview`);
          videoRef.current.play();
        }
      } else if (useAppStore.getState().loop) {
        const first = timeline.clips[0];
        useAppStore.setState({ selectedClipId: first.id });
        if (videoRef.current) {
          videoRef.current.src = withToken(`/api/projects/${activeProject?.id}/clips/${encodeURIComponent(first.id)}/preview`);
          videoRef.current.play();
        }
      } else {
        useAppStore.setState({ isPlaying: false });
      }
    };
    v.addEventListener('timeupdate', onTime);
    v.addEventListener('ended', onEnded);
    return () => {
      v.removeEventListener('timeupdate', onTime);
      v.removeEventListener('ended', onEnded);
    };
  }, [selectedClipId, timeline, activeProject, currentFrame, setPlayhead]);

  // Update volume
  useEffect(() => {
    if (videoRef.current) videoRef.current.volume = volume;
  }, [volume]);

  // Update video src when clip changes
  useEffect(() => {
    if (!clip || !activeProject) return;
    const v = videoRef.current;
    if (!v) return;
    const src = withToken(`/api/projects/${activeProject.id}/clips/${encodeURIComponent(clip.id)}/preview`);
    if (v.src !== src) {
      v.src = src;
      const fps = timeline?.fps ?? 24;
      v.currentTime = currentFrame / fps || 0;
      if (isPlaying) v.play().catch(() => {});
    }
  }, [clip, activeProject, currentFrame, isPlaying]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--md-surface-container-lowest)',
      overflow: 'hidden',
    }}>
      {/* Viewport Header */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {clip && (
            <>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--md-primary)', display: 'inline-block' }} />
              <span style={{ fontFamily: 'var(--md-font-code-inline)', fontSize: 10, color: 'var(--md-primary)', fontWeight: 700 }}>
                Composition{" "}
                <span style={{ opacity: 0.6 }}>&lt;</span>
                {activeProject?.slug || 'project'}
                <span style={{ opacity: 0.6 }}>&gt;</span>
              </span>
              <span style={{ color: 'var(--md-on-surface-variant)', opacity: 0.4 }}>/</span>
              <span style={{ fontFamily: 'var(--md-font-code-inline)', fontSize: 10, color: 'var(--md-on-surface)' }}>{clip.id}</span>
            </>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {/* Guide toggles */}
          <div style={{ display: 'flex', background: 'var(--md-surface-container-lowest)', border: '1px solid var(--md-surface-container-highest)', borderRadius: 3, overflow: 'hidden' }}>
            {(['safe', 'grid', 'wave'] as const).map((g) => (
              <button key={g} title={`${g.charAt(0).toUpperCase() + g.slice(1)} overlay`}
                style={{
                  padding: '2px 6px',
                  background: 'transparent',
                  border: 'none',
                  color: g === 'safe' ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
                  fontSize: 9,
                  fontFamily: 'var(--md-font-code-inline)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 3,
                }}>
                <span className="material-symbols-outlined" style={{ fontSize: 12 }}>{g === 'safe' ? 'crop_square' : g === 'grid' ? 'grid_4x4' : 'equalizer'}</span>
                {g.toUpperCase()}
              </button>
            ))}
          </div>
          <span style={{ fontFamily: 'var(--md-font-code-inline)', fontSize: 9, color: 'var(--md-on-surface-variant)', background: 'var(--md-surface-container-lowest)', padding: '2px 6px', borderRadius: 3, border: '1px solid var(--md-surface-container-highest)' }}>
            1920×1080
          </span>
        </div>
      </div>

      {/* Viewport Canvas */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        overflow: 'hidden',
        backgroundImage: 'radial-gradient(var(--md-surface-container) 1px, transparent 1px)',
        backgroundSize: '16px 16px',
      }}>
        {clip ? (
          <div style={{
            position: 'relative',
            width: '100%',
            maxWidth: 560,
            aspectRatio: '16/9',
            background: 'var(--md-surface-container-lowest)',
            border: '1px solid rgba(76,215,246,0.3)',
            boxShadow: '0 0 40px rgba(0,0,0,0.6), inset 0 0 60px rgba(0,0,0,0.3)',
            overflow: 'hidden',
          }}>
            {/* Title safe overlay */}
            <div style={{
              position: 'absolute', inset: '6%',
              border: '1px dashed rgba(76,215,246,0.2)',
              pointerEvents: 'none',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              padding: 2,
            }}>
              <span style={{ fontSize: 7, fontFamily: 'var(--md-font-code-inline)', color: 'rgba(76,215,246,0.4)', letterSpacing: '0.1em' }}>TITLE SAFE 90%</span>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 7, fontFamily: 'var(--md-font-code-inline)', color: 'rgba(76,215,246,0.3)' }}>ACTION SAFE 93%</span>
                <span style={{ fontSize: 7, fontFamily: 'var(--md-font-code-inline)', color: 'rgba(188,201,205,0.3)' }}>FR {currentFrame}/{totalFrames}</span>
              </div>
            </div>
            {/* Center crosshair */}
            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: 24, height: 1, background: 'rgba(76,215,246,0.2)' }} />
              <div style={{ width: 1, height: 24, background: 'rgba(76,215,246,0.2)', position: 'absolute' }} />
            </div>
            {/* Video */}
            <video
              ref={videoRef}
              src={withToken(`/api/projects/${activeProject?.id}/clips/${encodeURIComponent(clip.id)}/preview`)}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              onPlay={() => useAppStore.setState({ isPlaying: true })}
              onPause={() => useAppStore.setState({ isPlaying: false })}
            />
            {/* Canvas HUD badges */}
            <div style={{ position: 'absolute', top: 8, left: 8, display: 'flex', gap: 4, pointerEvents: 'none' }}>
              <span style={{ background: 'rgba(14,14,17,0.85)', border: '1px solid rgba(76,215,246,0.4)', fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)', padding: '2px 6px', fontWeight: 700 }}>
                SHOT {String(clip.scene).padStart(2, '0')}
              </span>
              <span style={{ background: 'rgba(14,14,17,0.85)', border: '1px solid var(--md-surface-container-highest)', fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-secondary)', padding: '2px 6px' }}>
                AGNES AI
              </span>
            </div>
            {/* Bottom callout */}
            <div style={{ position: 'absolute', bottom: 8, left: 8, right: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', pointerEvents: 'none' }}>
              <div style={{ background: 'rgba(14,14,17,0.85)', border: '1px solid var(--md-surface-container-highest)', padding: '4px 10px', fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--md-primary)', display: 'inline-block', animation: isPlaying ? 'ping 1s infinite' : 'none' }} />
                {clip.prompt.substring(0, 60)}{clip.prompt.length > 60 ? '...' : ''}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--md-on-surface-variant)', opacity: 0.5 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: 12, display: 'block' }}>videocam_off</span>
            <div style={{ fontFamily: 'var(--md-font-code-inline)', fontSize: 12 }}>Select a clip to preview</div>
          </div>
        )}
      </div>

      {/* Transport Controls */}
      <TransportControls />
    </div>
  );
}
