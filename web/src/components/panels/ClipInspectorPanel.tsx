import { useState } from 'react';
import { useAppStore } from '../../store';

const TRANSITIONS = ['fade', 'dissolve', 'wipe'] as const;

function Row({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        height: 26,
        borderBottom: '1px solid var(--md-surface-container-highest)',
      }}
    >
      <span style={{ fontSize: 11, color: 'var(--md-on-surface-variant)', whiteSpace: 'nowrap' }}>{label}</span>
      <span
        title={value}
        style={{
          fontFamily: 'var(--md-font-code-inline)',
          fontSize: 10,
          color: accent ?? 'var(--md-on-surface)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          maxWidth: 190,
        }}
      >
        {value}
      </span>
    </div>
  );
}

const LABEL: React.CSSProperties = {
  fontSize: 9,
  fontFamily: 'var(--md-font-display-lg)',
  color: 'var(--md-on-surface-variant)',
  letterSpacing: '0.1em',
};

/**
 * Clip Inspector rail (300px) — design §7 of DESIGN-STUDIO-SHELL.md.
 * Fills the dead space either side of the 16:9 viewport.
 *
 * Data honesty: fields come from the clip record. "Approve" has no API in
 * the store, so it renders disabled rather than faking an action;
 * "Regenerate" and the transition chips are real store actions.
 */
export default function ClipInspectorPanel() {
  const { timeline, selectedClipId, updateClip, regenerateClip } = useAppStore();
  const clip = timeline?.clips.find((c) => c.id === selectedClipId) ?? null;
  const [tab, setTab] = useState<'overview' | 'prompt' | 'gate'>('overview');

  const qc =
    clip?.quality_status === 'pass'
      ? 'var(--md-success, #4ade80)'
      : clip?.quality_status === 'warn'
        ? 'var(--md-warning, #facc15)'
        : clip?.quality_status === 'fail'
          ? 'var(--md-danger, #f87171)'
          : undefined;

  return (
    <aside className="clip-inspector" aria-label="Clip inspector">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 38,
          padding: '0 12px',
          borderBottom: '1px solid var(--md-surface-container-highest)',
          background: 'var(--md-surface-container)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 15, color: 'var(--md-primary)' }} aria-hidden>
            tune
          </span>
          <span style={{ fontSize: 11, fontFamily: 'var(--md-font-display-lg)', fontWeight: 700, color: 'var(--md-on-surface)' }}>
            Clip Inspector
          </span>
        </div>
        {clip && (
          <span
            style={{
              fontSize: 9,
              fontFamily: 'var(--md-font-display-lg)',
              fontWeight: 700,
              textTransform: 'uppercase',
              padding: '1px 7px',
              borderRadius: 9999,
              background: 'var(--md-surface-container-lowest)',
              border: '1px solid var(--md-surface-container-highest)',
              color: 'var(--md-on-surface-variant)',
            }}
          >
            {clip.status}
          </span>
        )}
      </div>

      {clip && (
        <div
          className="inspector-tabs"
          role="tablist"
          aria-label="Inspector sections"
          style={{
            display: 'flex',
            alignItems: 'stretch',
            gap: 0,
            height: 32,
            padding: '0 8px',
            background: 'var(--md-surface-container-low)',
            borderBottom: '1px solid var(--md-surface-container-highest)',
            flexShrink: 0,
          }}
        >
          {([
            ['overview', 'Overview'],
            ['prompt', 'Prompt'],
            ['gate', 'Gate'],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              style={{
                padding: '0 12px',
                fontSize: 11,
                fontFamily: 'var(--md-font-body-md)',
                fontWeight: tab === key ? 600 : 400,
                color: tab === key ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
                background: 'transparent',
                border: 'none',
                borderBottom: tab === key ? '2px solid var(--md-primary)' : '2px solid transparent',
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {!clip ? (
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            padding: 16,
            color: 'var(--md-on-surface-variant)',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.3 }} aria-hidden>
            tune
          </span>
          <span style={{ fontSize: 11, fontFamily: 'var(--md-font-code-inline)' }}>Select a clip</span>
          <span style={{ fontSize: 10, opacity: 0.7, textAlign: 'center' }}>
            Click a shot or timeline clip to inspect it
          </span>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: 12 }}>
          {tab === 'overview' && (
          <>
          <div style={{ ...LABEL, marginBottom: 8 }}>PROPERTIES</div>
          <div style={{ marginBottom: 14 }}>
            <Row label="Shot" value={clip.shot_id} />
            <Row label="Scene" value={String(clip.scene)} />
            <Row label="Duration" value={`${clip.duration}s`} />
            <Row label="Aspect" value={clip.aspect_ratio} />
            <Row label="Style" value={clip.style} />
            <Row label="Grade" value={clip.color_grade ?? '—'} />
            <Row label="Transition" value={clip.transition_in ?? '—'} />
            <Row label="Quality" value={clip.quality_status ? clip.quality_status.toUpperCase() : '—'} accent={qc} />
          </div>
          <div style={{ ...LABEL, marginBottom: 8 }}>TRANSITION IN</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {TRANSITIONS.map((t) => {
              const active = clip.transition_in === t;
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => void updateClip(clip.id, { transition_in: t })}
                  style={{
                    flex: 1,
                    padding: '6px 0',
                    fontSize: 10,
                    fontFamily: 'var(--md-font-display-lg)',
                    fontWeight: active ? 700 : 400,
                    cursor: 'pointer',
                    borderRadius: 'var(--md-radius-sm)',
                    background: active ? 'var(--md-primary)' : 'var(--md-surface-container-lowest)',
                    color: active ? 'var(--md-on-primary)' : 'var(--md-on-surface-variant)',
                    border: `1px solid ${active ? 'var(--md-primary)' : 'var(--md-surface-container-highest)'}`,
                  }}
                >
                  {t}
                </button>
              );
            })}
          </div>

          </>
          )}
          {tab === 'prompt' && (
          <>
          <div style={{ ...LABEL, margin: '14px 0 6px' }}>PROMPT</div>
          <div
            style={{
              background: 'var(--md-surface-container-lowest)',
              border: '1px solid var(--md-outline)',
              borderRadius: 'var(--md-radius-sm)',
              padding: '8px 10px',
              fontFamily: 'var(--md-font-code-inline)',
              fontSize: 10,
              lineHeight: 1.5,
              color: 'var(--md-on-surface-variant)',
            }}
          >
            {clip.prompt || '—'}
          </div>
          </>
          )}
          {tab === 'gate' && (
            <div>
              <div style={{ ...LABEL, marginBottom: 8 }}>QUALITY</div>
              <div style={{ marginBottom: 14 }}>
                <Row
                  label="Quality"
                  value={clip.quality_status ? clip.quality_status.toUpperCase() : '—'}
                  accent={qc}
                />
              </div>
              <div style={{ ...LABEL, marginBottom: 6 }}>GATE SCORE</div>
              <div
                style={{
                  fontSize: 10,
                  fontFamily: 'var(--md-font-code-inline)',
                  color: 'var(--md-on-surface-variant)',
                  lineHeight: 1.5,
                }}
              >
                No gate score on the clip record — gate scores come from the
                Production Monitor (`brandly gate`).
              </div>
            </div>
          )}
        </div>
      )}
      {clip && (
        <div
          style={{
            display: 'flex',
            gap: 8,
            padding: 12,
            borderTop: '1px solid var(--md-surface-container-highest)',
            background: 'var(--md-surface-container-low)',
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            disabled
            title="Approve requires the review API (not wired yet)"
            style={{
              flex: 1,
              padding: '9px 0',
              fontSize: 10,
              fontFamily: 'var(--md-font-display-lg)',
              fontWeight: 700,
              cursor: 'not-allowed',
              opacity: 0.55,
              borderRadius: 'var(--md-radius-sm)',
              background: 'transparent',
              border: '1px solid var(--md-outline)',
              color: 'var(--md-on-surface-variant)',
            }}
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => void regenerateClip(clip.id)}
            title="Regenerate this clip"
            style={{
              flex: 1,
              padding: '10px 0',
              fontSize: 10,
              fontFamily: 'var(--md-font-display-lg)',
              fontWeight: 700,
              cursor: 'pointer',
              borderRadius: 'var(--md-radius-sm)',
              background: 'var(--md-primary)',
              border: 'none',
              color: 'var(--md-on-primary)',
            }}
          >
            Regenerate
          </button>
        </div>
      )}
    </aside>
  );
}
