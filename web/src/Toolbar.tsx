import { useAppStore } from './store';
import { PANEL_LABELS } from './panelLabels';

/**
 * Context toolbar — design: `dev-notes/DESIGN-STUDIO-SHELL.md` §4.
 *
 * Sits between the Header and the Body: breadcrumb on the left (where am I),
 * global affordances on the right.
 *
 * Data honesty: actions with no store/CLI support yet are rendered `disabled`
 * rather than wired to a no-op handler.
 */
export default function Toolbar() {
  const { activeProject, activePanel } = useAppStore();
  const panelLabel = PANEL_LABELS[activePanel];

  const handleCopyCli = () => {
    const cmd = activeProject
      ? `brandly studio --project ${activeProject.slug}`
      : 'brandly studio';
    void navigator.clipboard?.writeText(cmd).catch(() => undefined);
  };

  const iconBtn: React.CSSProperties = {
    width: 26,
    height: 26,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 'var(--md-radius-sm)',
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--md-on-surface-variant)',
    padding: 0,
  };

  const actionBtn: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    border: '1px solid var(--md-outline)',
    borderRadius: 'var(--md-radius-sm)',
    padding: '5px 10px',
    background: 'transparent',
    cursor: 'pointer',
    color: 'var(--md-on-surface-variant)',
    fontSize: 11,
    fontFamily: 'var(--md-font-body-md)',
  };

  return (
    <div
      className="studio-toolbar"
      role="toolbar"
      aria-label="Project context"
      style={{
        position: 'fixed',
        top: 52,
        left: 0,
        right: 0,
        height: 40,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 16px',
        background: 'var(--md-surface-container-low)',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        zIndex: 99,
        boxSizing: 'border-box',
      }}
    >
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <span
          style={{
            fontSize: 12,
            fontFamily: 'var(--md-font-body-md)',
            color: 'var(--md-on-surface-variant)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {activeProject ? activeProject.name || activeProject.slug : 'No project'}
        </span>
        <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--md-outline)' }} aria-hidden>
          chevron_right
        </span>
        <span
          style={{
            fontSize: 12,
            fontFamily: 'var(--md-font-body-md)',
            fontWeight: 600,
            color: 'var(--md-primary)',
            whiteSpace: 'nowrap',
          }}
        >
          {panelLabel}
        </span>
      </nav>

      <div style={{ flex: 1 }} />

      {/* Command search */}
      <div
        role="search"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          width: 280,
          background: 'var(--md-surface-container-lowest)',
          border: '1px solid var(--md-outline)',
          borderRadius: 'var(--md-radius-sm)',
          padding: '5px 10px',
        }}
      >
        <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--md-outline)' }} aria-hidden>
          search
        </span>
        <span style={{ flex: 1, fontSize: 11, fontFamily: 'var(--md-font-body-md)', color: 'var(--md-outline)' }}>
          Search shots, commands…
        </span>
        <span
          style={{
            fontSize: 9,
            fontFamily: 'var(--md-font-code-inline)',
            color: 'var(--md-on-surface-variant)',
            border: '1px solid var(--md-outline)',
            borderRadius: 3,
            padding: '1px 5px',
          }}
        >
          ⌘K
        </span>
      </div>

      <span style={{ width: 1, height: 18, background: 'var(--md-surface-container-highest)' }} />

      {/* Undo / redo — not supported by the store yet, therefore disabled */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <button type="button" style={iconBtn} disabled title="Undo (not available yet)" aria-label="Undo">
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            undo
          </span>
        </button>
        <button type="button" style={{ ...iconBtn, opacity: 0.4 }} disabled title="Redo (not available yet)" aria-label="Redo">
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            redo
          </span>
        </button>
      </div>

      <span style={{ width: 1, height: 18, background: 'var(--md-surface-container-highest)' }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button type="button" onClick={handleCopyCli} title="Copy CLI command for this project" style={actionBtn}>
          <span className="material-symbols-outlined" style={{ fontSize: 14 }} aria-hidden>
            share
          </span>
          Share
        </button>
        <button
          type="button"
          style={{ ...iconBtn, border: '1px solid var(--md-outline)', borderRadius: '50%', fontFamily: 'var(--md-font-code-inline)', fontSize: 11 }}
          title="Keyboard shortcuts"
          aria-label="Help and shortcuts"
        >
          ?
        </button>
      </div>
    </div>
  );
}
