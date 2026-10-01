import { useAppStore } from '../../store';

const STEPS = ['Plan locked', 'Rendering', 'Encode', 'Publish'] as const;

/**
 * Render pipeline stepper — design §7 (artboard 03).
 *
 * Shows where the composition sits in the render pipeline.
 *
 * Data honesty: the only render state the store carries is `exportDone`, so
 * the stepper derives from that alone — it does not invent per-stage progress.
 */
export default function PipelineStepper() {
  const { exportDone } = useAppStore();
  // A project always has a locked plan; exportDone means render+encode finished.
  const doneCount = exportDone ? STEPS.length : 1;
  const activeIndex = exportDone ? -1 : 1;

  return (
    <div
      className="pipeline-stepper"
      role="list"
      aria-label="Render pipeline"
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
      {STEPS.map((step, i) => {
        const done = i < doneCount;
        const active = i === activeIndex;
        return (
          <div key={step} role="listitem" style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 9999,
                whiteSpace: 'nowrap',
                fontSize: 10,
                fontFamily: 'var(--md-font-display-lg)',
                fontWeight: active ? 700 : 400,
                background: done
                  ? 'rgba(74,222,128,0.12)'
                  : active
                    ? 'var(--md-primary)'
                    : 'var(--md-surface-container-lowest)',
                color: done
                  ? 'var(--md-success, #4ade80)'
                  : active
                    ? 'var(--md-on-primary)'
                    : 'var(--md-on-surface-variant)',
                border: `1px solid ${done ? 'rgba(74,222,128,0.3)' : active ? 'var(--md-primary)' : 'var(--md-surface-container-highest)'}`,
              }}
            >
              {done && (
                <span className="material-symbols-outlined" style={{ fontSize: 12 }} aria-hidden>
                  check
                </span>
              )}
              {step}
            </div>
            {i < STEPS.length - 1 && (
              <span style={{ width: 14, height: 1, background: 'var(--md-surface-container-highest)', flexShrink: 0 }} />
            )}
          </div>
        );
      })}
      <div style={{ flex: 1 }} />
      <span
        style={{
          fontSize: 9,
          fontFamily: 'var(--md-font-code-inline)',
          color: 'var(--md-on-surface-variant)',
          flexShrink: 0,
        }}
      >
        {exportDone ? 'RENDER COMPLETE' : 'IN PROGRESS'}
      </span>
    </div>
  );
}
