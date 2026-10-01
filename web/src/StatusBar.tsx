import { useAppStore } from './store';

/**
 * Status bar — design: `dev-notes/DESIGN-STUDIO-SHELL.md` §5.
 *
 * Replaces the sidebar's telemetry block (it moved here per the design).
 *
 * Data honesty: every value is read from the zustand store. Anything the
 * store does not carry (gate score, credit budget, worker/RSS) is omitted
 * rather than rendered as fabricated live telemetry.
 */
export default function StatusBar() {
  const { activeProject, timeline, zoomLevel, currentFrame, totalFrames, selectedClipId } = useAppStore();

  const phase = activeProject?.current_phase;
  const shots = activeProject?.shot_count;
  const fps = timeline?.fps;
  const aspect = timeline?.aspect_ratio;
  const clipCount = timeline?.clips.length ?? 0;
  const selectedShot = selectedClipId
    ? timeline?.clips.find((c) => c.id === selectedClipId)?.shot_id
    : undefined;

  const group: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 12 };
  const muted: React.CSSProperties = {
    fontSize: 9,
    fontFamily: 'var(--md-font-code-inline)',
    color: 'var(--md-on-surface-variant)',
  };

  return (
    <div
      className="status-bar"
      role="status"
      aria-label="Workspace status"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 28,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        padding: '0 16px',
        background: 'var(--md-surface-container-lowest)',
        borderTop: '1px solid var(--md-surface-container-high)',
        zIndex: 100,
        boxSizing: 'border-box',
      }}
    >
      {/* Left: where the pipeline is */}
      <div style={group}>
        {phase ? (
          <span
            style={{
              fontSize: 9,
              fontFamily: 'var(--md-font-code-inline)',
              fontWeight: 700,
              letterSpacing: '0.06em',
              color: 'var(--md-on-primary)',
              background: 'var(--md-primary)',
              padding: '1px 7px',
              borderRadius: 3,
            }}
          >
            PHASE · {String(phase).toUpperCase()}
          </span>
        ) : (
          <span style={muted}>NO PROJECT</span>
        )}
        {shots !== undefined && shots !== null && (
          <span style={muted}>{shots} SHOTS</span>
        )}
        {clipCount > 0 && <span style={muted}>{clipCount} CLIPS</span>}
      </div>

      {/* Centre: timeline facts */}
      <div style={group}>
        {fps !== undefined && <span style={muted}>FPS {fps}</span>}
        {aspect && <span style={muted}>{aspect}</span>}
        {selectedShot && (
          <span
            style={{ ...muted, color: 'var(--md-on-surface)', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            SEL {selectedShot}
          </span>
        )}
      </div>

      {/* Right: viewport state */}
      <div style={group}>
        <span style={muted}>ZOOM {(zoomLevel / 100).toFixed(1)}×</span>
        <span style={muted}>
          FR {String(currentFrame).padStart(4, '0')} / {String(totalFrames).padStart(4, '0')}
        </span>
      </div>
    </div>
  );
}
