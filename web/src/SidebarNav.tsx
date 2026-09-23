import { useAppStore } from './store';
import type { PanelKind } from './types';

const PANELS: { kind: PanelKind; label: string; icon: string; badge?: string }[] = [
  { kind: 'preview', label: 'Preview Player', icon: 'videocam' },
  { kind: 'timeline', label: 'Timeline Sequencer', icon: 'view_timeline' },
  { kind: 'asset_manifest', label: 'Asset Manifest', icon: 'folder_zip', badge: 'clips' },
  { kind: 'props', label: 'Props Inspector', icon: 'tune' },
  { kind: 'render', label: 'Render Queue', icon: 'cloud_sync' },
  { kind: 'agnes_ai', label: 'Agnes AI Synthesizer', icon: 'auto_awesome' },
];

export default function SidebarNav() {
  const { activePanel, timeline, projects, activeProject, selectProject, setPanel } = useAppStore();

  return (
    <nav className="sidebar" style={{
      position: 'fixed',
      top: '3.5rem',
      left: 0,
      bottom: 0,
      width: '16rem',
      background: 'var(--md-surface-container-lowest)',
      borderRight: '1px solid var(--md-surface-container-high)',
      display: 'flex',
      flexDirection: 'column',
      overflowY: 'auto',
      overflowX: 'hidden',
      zIndex: 90,
    }}>
      {/* Project selector */}
      <div style={{
        padding: '12px 12px 8px',
        borderBottom: '1px solid var(--md-surface-container-high)',
      }}>
        <div style={{
          fontSize: 10,
          fontFamily: 'var(--md-font-display-lg)',
          color: 'var(--md-on-surface-variant)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 8,
          paddingLeft: 4,
        }}>
          Projects
        </div>
        <div style={{ maxHeight: 120, overflowY: 'auto' }}>
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => selectProject(p.id)}
              style={{
                padding: '8px 10px',
                background: activeProject?.id === p.id ? 'var(--md-surface-container)' : 'transparent',
                borderRadius: 'var(--md-radius-sm)',
                cursor: 'pointer',
                marginBottom: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'background var(--md-transition-fast)',
              }}
              onMouseEnter={(e) => {
                if (activeProject?.id !== p.id) (e.currentTarget as HTMLDivElement).style.background = 'var(--md-surface-container-low)';
              }}
              onMouseLeave={(e) => {
                if (activeProject?.id !== p.id) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{
                  fontSize: 12,
                  fontWeight: 500,
                  color: activeProject?.id === p.id ? 'var(--md-primary)' : 'var(--md-on-surface)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {p.name || p.slug || p.id}
                </div>
                <div style={{ fontSize: 10, color: 'var(--md-on-surface-variant)', marginTop: 1 }}>
                  {p.shot_count} shots · {p.current_phase}
                </div>
              </div>
              <span style={{
                fontSize: 9,
                padding: '1px 6px',
                borderRadius: 9999,
                background: p.status === 'completed' ? 'rgba(74,222,128,0.15)' : p.status === 'running' ? 'rgba(96,165,250,0.15)' : 'rgba(156,163,175,0.15)',
                color: p.status === 'completed' ? '#4ade80' : p.status === 'running' ? '#60a5fa' : '#9ca3af',
                fontFamily: 'var(--md-font-display-lg)',
                fontWeight: 600,
                flexShrink: 0,
                marginLeft: 6,
              }}>
                {p.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Panel navigation */}
      <div style={{ padding: '12px 12px 4px', flex: 1 }}>
        <div style={{
          fontSize: 10,
          fontFamily: 'var(--md-font-display-lg)',
          color: 'var(--md-on-surface-variant)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 8,
          paddingLeft: 4,
        }}>
          Panels
        </div>
        {PANELS.map((p) => {
          const isActive = activePanel === p.kind;
          return (
            <button
              key={p.kind}
              onClick={() => setPanel(p.kind)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 10px',
                background: isActive ? 'var(--md-surface-container)' : 'transparent',
                border: 'none',
                borderLeft: isActive ? '2px solid var(--md-primary)' : '2px solid transparent',
                borderRadius: isActive ? '0 var(--md-radius-sm) var(--md-radius-sm) 0' : 0,
                color: isActive ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
                cursor: 'pointer',
                fontSize: 12,
                fontFamily: 'var(--md-font-body-md)',
                textAlign: 'left',
                transition: 'all var(--md-transition-fast)',
                marginBottom: 1,
              }}
              onMouseEnter={(e) => {
                if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--md-surface-container-low)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18, flexShrink: 0 }}>
                {p.icon}
              </span>
              <span style={{ flex: 1, fontWeight: isActive ? 700 : 400 }}>{p.label}</span>
              {p.badge && timeline && (
                <span style={{
                  background: 'var(--md-primary-container)',
                  color: 'var(--md-on-primary-container)',
                  fontSize: 10,
                  fontFamily: 'var(--md-font-display-lg)',
                  padding: '1px 6px',
                  borderRadius: 9999,
                  fontWeight: 600,
                }}>
                  {timeline.clips.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom: Engine status */}
      <div style={{
        padding: '12px',
        borderTop: '1px solid var(--md-surface-container-high)',
        background: 'var(--md-surface-container-lowest)',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 6,
        }}>
          <EngineStatus label="Worker" ok={true} />
          <EngineStatus label="Mem" ok={true} value="2.1G" />
          <EngineStatus label="FPS" ok={true} value="24" />
        </div>
      </div>
    </nav>
  );
}

function EngineStatus({ label, ok, value }: { label: string; ok: boolean; value?: string }) {
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      borderRadius: 'var(--md-radius-sm)',
      padding: '6px 8px',
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 10,
        color: 'var(--md-on-surface-variant)',
        fontFamily: 'var(--md-font-display-lg)',
      }}>
        <span style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: ok ? '#4ade80' : '#f87171',
          display: 'inline-block',
          boxShadow: ok ? '0 0 4px #4ade80' : '0 0 4px #f87171',
        }} />
        {label}
      </div>
      {value && (
        <div style={{ fontSize: 11, color: 'var(--md-on-surface)', fontFamily: 'var(--md-font-display-lg)', fontWeight: 600 }}>
          {value}
        </div>
      )}
    </div>
  );
}
