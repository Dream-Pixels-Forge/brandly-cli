import { useAppStore } from './store';

interface HeaderProps {
  wsReady: boolean;
  wsEvent: string | null;
}

export default function Header({ wsReady, wsEvent }: HeaderProps) {
  const { activeProject, currentFrame, totalFrames, zoomLevel, exportProject, exportDone } = useAppStore();

  const totalDuration = activeProject ? (totalFrames / 24).toFixed(1) : '0.0';
  const zoomDisplay = (zoomLevel / 100).toFixed(1);
  const projectPath = activeProject?.slug
    ? `~/brandly/projects/${activeProject.slug}`
    : 'No project selected';

  const handleCopyCli = async () => {
    const cmd = activeProject
      ? `brandly studio --project ${activeProject.slug}`
      : 'brandly studio';
    try { await navigator.clipboard.writeText(cmd); } catch { /* ignore */ }
  };

  return (
    <header className="header" style={{
      position: 'fixed',
      top: 0, left: 0, right: 0,
      height: '3.5rem',
      background: 'var(--md-surface-container-low)',
      borderBottom: '1px solid var(--md-surface-container-highest)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 1rem',
      gap: '1rem',
      zIndex: 100,
    }}>
      {/* Left: Logo + project path */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="material-symbols-outlined" style={{
            fontSize: 20,
            color: 'var(--md-primary)',
            fontWeight: 700,
          }}>movie_edit</span>
          <span style={{
            fontFamily: 'var(--md-font-display-lg)',
            fontSize: 13,
            fontWeight: 700,
            color: 'var(--md-on-surface)',
            letterSpacing: '0.02em',
          }}>
            Brandly
          </span>
          <span style={{
            background: 'var(--md-primary)',
            color: 'var(--md-on-primary)',
            fontSize: 9,
            fontFamily: 'var(--md-font-display-lg)',
            fontWeight: 700,
            padding: '1px 5px',
            borderRadius: 3,
            letterSpacing: '0.08em',
          }}>
            STUDIO
          </span>
        </div>
        {activeProject && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--md-surface-container)',
            padding: '3px 10px',
            borderRadius: 'var(--md-radius-sm)',
            fontSize: 11,
            fontFamily: 'var(--md-font-code-inline)',
            color: 'var(--md-on-surface-variant)',
            maxWidth: 280,
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 14, opacity: 0.6 }}>folder</span>
            <span title={projectPath}>{projectPath}</span>
          </div>
        )}
      </div>

      {/* Center: Frame counter + duration + zoom */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        marginLeft: 'auto',
        marginRight: 'auto',
        flexShrink: 1,
        minWidth: 0,
        justifyContent: 'center',
      }}>
        {activeProject ? (
          <>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'var(--md-surface-container)',
              padding: '4px 10px',
              borderRadius: 'var(--md-radius-sm)',
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--md-primary)' }}>frame_support</span>
              <span style={{
                fontFamily: 'var(--md-font-display-lg)',
                fontSize: 11,
                color: 'var(--md-on-surface)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                FRAME:{' '}
                <span style={{ color: 'var(--md-primary)' }}>{currentFrame}</span>
                <span style={{ color: 'var(--md-on-surface-variant)', opacity: 0.6 }}>/</span>
                <span style={{ color: 'var(--md-on-surface-variant)', opacity: 0.6 }}>{totalFrames}</span>
              </span>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: 'var(--md-on-surface-variant)',
              fontFamily: 'var(--md-font-display-lg)',
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>schedule</span>
              <span>{totalDuration}s</span>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: 'var(--md-on-surface-variant)',
              fontFamily: 'var(--md-font-display-lg)',
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>zoom_in_map</span>
              <span>{zoomDisplay}x</span>
            </div>
          </>
        ) : (
          <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 11, color: 'var(--md-on-surface-variant)', opacity: 0.5 }}>
            No project loaded
          </span>
        )}
      </div>

      {/* Right: WS health, Copy CLI, Render, Avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        {wsEvent && (
          <span style={{
            fontSize: 10,
            fontFamily: 'var(--md-font-display-lg)',
            color: 'var(--md-tertiary)',
            background: 'rgba(255,184,115,0.12)',
            border: '1px solid rgba(255,184,115,0.3)',
            padding: '2px 8px',
            borderRadius: 9999,
          }}>
            {wsEvent}
          </span>
        )}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 11,
          color: 'var(--md-on-surface-variant)',
          fontFamily: 'var(--md-font-display-lg)',
        }}>
          <span style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: wsReady ? '#4ade80' : '#f87171',
            display: 'inline-block',
            boxShadow: wsReady ? '0 0 6px #4ade80' : '0 0 6px #f87171',
          }} />
          <span>Agnes: {wsReady ? 'Ready' : 'Offline'}</span>
        </div>
        <button
          onClick={handleCopyCli}
          title="Copy CLI command"
          style={{
            background: 'transparent',
            border: '1px solid var(--md-surface-container-highest)',
            color: 'var(--md-on-surface-variant)',
            borderRadius: 'var(--md-radius-sm)',
            padding: '4px 8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 11,
            fontFamily: 'var(--md-font-code-inline)',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 15 }}>terminal</span>
          CLI
        </button>
        <button
          onClick={() => exportProject()}
          style={{
            background: exportDone ? 'var(--md-primary-fixed-dim)' : 'var(--md-primary)',
            border: 'none',
            color: exportDone ? 'var(--md-on-primary)' : 'var(--md-on-primary)',
            borderRadius: 'var(--md-radius-sm)',
            padding: '5px 14px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12,
            fontFamily: 'var(--md-font-display-lg)',
            fontWeight: 600,
            transition: 'background var(--md-transition-fast)',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 15 }}>cloud_upload</span>
          {exportDone ? '✓ Done' : 'Render Video'}
        </button>
        <div style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: 'var(--md-primary-container)',
          color: 'var(--md-on-primary-container)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          fontFamily: 'var(--md-font-display-lg)',
          fontWeight: 700,
          cursor: 'pointer',
          border: '1px solid var(--md-surface-container-highest)',
        }}>
          DP
        </div>
      </div>
    </header>
  );
}
