import { useAppStore } from '../../store';

const PHASES = [
  { key: 'P', name: 'Prototype' },
  { key: 'R', name: 'Review' },
  { key: 'I', name: 'Implement' },
  { key: 'D', name: 'Deploy' },
  { key: 'E', name: 'Evaluate' },
  { key: 'S', name: 'Secure' },
] as const;

/**
 * Director phase stepper — design §7 (artboard 04).
 *
 * Renders the PRIDES chain as pipeline context alongside the project's real
 * `current_phase`.
 *
 * Data honesty: `current_phase` is a free-form CLI phase name (init,
 * storyboard, video, …) with no guaranteed mapping onto a PRIDES index, so the
 * chain is NOT marked with a fabricated "current" step — the real phase is
 * surfaced as a pill instead. Director phases advance with per-phase gates and
 * human approval, never autonomously.
 */
export default function PhaseStepper() {
  const { activeProject } = useAppStore();
  const phase = activeProject?.current_phase;

  return (
    <div
      className="phase-stepper"
      role="list"
      aria-label="Director phases"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '9px 14px',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        background: 'var(--md-surface-container-low)',
        flexShrink: 0,
        overflowX: 'auto',
      }}
    >
      <span
        style={{
          fontSize: 9,
          fontFamily: 'var(--md-font-display-lg)',
          color: 'var(--md-on-surface-variant)',
          letterSpacing: '0.1em',
          flexShrink: 0,
        }}
      >
        DIRECTOR
      </span>
      <span style={{ width: 1, height: 16, background: 'var(--md-surface-container-highest)', flexShrink: 0 }} />

      {phase ? (
        <span
          style={{
            fontSize: 9,
            fontFamily: 'var(--md-font-code-inline)',
            fontWeight: 700,
            letterSpacing: '0.06em',
            padding: '2px 8px',
            borderRadius: 3,
            background: 'var(--md-primary)',
            color: 'var(--md-on-primary)',
            flexShrink: 0,
          }}
        >
          PHASE · {String(phase).toUpperCase()}
        </span>
      ) : (
        <span
          style={{
            fontSize: 9,
            fontFamily: 'var(--md-font-code-inline)',
            color: 'var(--md-on-surface-variant)',
            flexShrink: 0,
          }}
        >
          NO PROJECT
        </span>
      )}

      <span style={{ width: 1, height: 16, background: 'var(--md-surface-container-highest)', flexShrink: 0 }} />

      {PHASES.map((p, i) => (
        <div key={p.key} role="listitem" style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '3px 9px',
              borderRadius: 9999,
              whiteSpace: 'nowrap',
              background: 'var(--md-surface-container-lowest)',
              border: '1px solid var(--md-surface-container-highest)',
            }}
          >
            <span
              style={{
                fontSize: 9,
                fontFamily: 'var(--md-font-display-lg)',
                fontWeight: 700,
                color: 'var(--md-primary)',
              }}
            >
              {p.key}
            </span>
            <span style={{ fontSize: 10, fontFamily: 'var(--md-font-body-md)', color: 'var(--md-on-surface-variant)' }}>
              {p.name}
            </span>
          </div>
          {i < PHASES.length - 1 && (
            <span style={{ width: 10, height: 1, background: 'var(--md-surface-container-highest)', flexShrink: 0 }} />
          )}
        </div>
      ))}

      <div style={{ flex: 1 }} />
      <span
        style={{
          fontSize: 9,
          fontFamily: 'var(--md-font-code-inline)',
          color: 'var(--md-on-surface-variant)',
          flexShrink: 0,
        }}
      >
        GATE-GATED · MANUAL APPROVAL
      </span>
    </div>
  );
}
