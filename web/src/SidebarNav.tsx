import { useAppStore } from './store';
import { PANEL_SHORTCUTS, PANEL_LABELS } from './panelLabels';
import type { PanelKind } from './types';

/** `key` is the keyboard-shortcut hint rendered on the row (design §6). */
const PANELS: { kind: PanelKind; label: string; icon: string; badge?: string; key: string }[] = [
  { kind: 'preview', label: PANEL_LABELS.preview, icon: 'videocam', key: PANEL_SHORTCUTS.preview },
  { kind: 'timeline', label: PANEL_LABELS.timeline, icon: 'view_timeline', key: PANEL_SHORTCUTS.timeline },
  { kind: 'asset_manifest', label: PANEL_LABELS.asset_manifest, icon: 'folder_zip', badge: 'clips', key: PANEL_SHORTCUTS.asset_manifest },
  { kind: 'props', label: PANEL_LABELS.props, icon: 'tune', key: PANEL_SHORTCUTS.props },
  { kind: 'render', label: PANEL_LABELS.render, icon: 'cloud_sync', key: PANEL_SHORTCUTS.render },
  { kind: 'monitor', label: PANEL_LABELS.monitor, icon: 'monitor_heart', key: PANEL_SHORTCUTS.monitor },
  { kind: 'review', label: PANEL_LABELS.review, icon: 'fact_check', key: PANEL_SHORTCUTS.review },
  { kind: 'agnes_ai', label: PANEL_LABELS.agnes_ai, icon: 'auto_awesome', key: PANEL_SHORTCUTS.agnes_ai },
];

export default function SidebarNav() {
  const { activePanel, timeline, projects, activeProject, selectProject, setPanel, loading, error } = useAppStore();

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
          {loading && projects.length === 0 && (
            <div style={{ padding: '8px 10px', fontSize: 11, color: 'var(--md-on-surface-variant)', opacity: 0.7 }}>
              Loading projects…
            </div>
          )}
          {error && projects.length === 0 && (
            <div style={{ padding: '8px 10px', fontSize: 11, color: '#f87171' }} role="alert">
              Failed to load projects: {error}
            </div>
          )}
          {!loading && !error && projects.length === 0 && (
            <div style={{ padding: '8px 10px', fontSize: 11, color: 'var(--md-on-surface-variant)', opacity: 0.7 }}>
              No projects found
            </div>
          )}
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
              <span
                title={`${p.label} (${p.key})`}
                style={{
                  fontSize: 9,
                  fontFamily: 'var(--md-font-display-lg)',
                  color: 'var(--md-outline)',
                  border: '1px solid var(--md-surface-container-highest)',
                  borderRadius: 3,
                  padding: '1px 5px',
                  flexShrink: 0,
                }}
              >
                {p.key}
              </span>
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

      {/* Bottom: actions.
          The Worker/Mem/FPS telemetry block was removed here — the design
          moves live system state out of the sidebar (design §6). */}
      <div
        className="sidebar-footer"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 9,
          padding: 12,
          borderTop: '1px solid var(--md-surface-container-high)',
          background: 'var(--md-surface-container-lowest)',
          flexShrink: 0,
        }}
      >
        <button
          type="button"
          onClick={() => void navigator.clipboard?.writeText('brandly init').catch(() => undefined)}
          title="Create a project with: brandly init"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            background: 'var(--md-primary)',
            color: 'var(--md-on-primary)',
            border: 'none',
            borderRadius: 'var(--md-radius-sm)',
            padding: '9px 0',
            cursor: 'pointer',
            fontFamily: 'var(--md-font-display-lg)',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 14 }} aria-hidden>
            add
          </span>
          New Project
        </button>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px' }}>
          <span style={{ fontSize: 10, fontFamily: 'var(--md-font-body-md)', color: 'var(--md-on-surface-variant)', cursor: 'pointer' }}>
            Docs
          </span>
          <span style={{ fontSize: 10, fontFamily: 'var(--md-font-body-md)', color: 'var(--md-on-surface-variant)', cursor: 'pointer' }}>
            Shortcuts
          </span>
          <span style={{ fontSize: 10, fontFamily: 'var(--md-font-body-md)', color: 'var(--md-on-surface-variant)', cursor: 'pointer' }}>
            CLI
          </span>
        </div>
      </div>
    </nav>
  );
}
