import { useState } from 'react';

const PERSONAS = ['Marcus', 'Elena', 'Kaito'] as const;

function VUMeter({ levelLeft, levelRight, peak }: { levelLeft: number; levelRight: number; peak: number | null }) {
  const barH = 80;
  const segments = 20;

  const fillSegments = (level: number) => {
    const filled = Math.round(level * segments);
    return Array.from({ length: segments }, (_, i) => ({
      i,
      active: i < filled,
      clipping: i >= segments - 2 && level > 0.9,
    }));
  };

  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', height: barH + 20 }}>
      {/* Left channel */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flex: 1 }}>
        <span style={{ fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: '#4cd7f6' }}>L</span>
        <div style={{ display: 'flex', flexDirection: 'column-reverse', gap: 1, height: barH, background: 'var(--md-surface-container-highest)', borderRadius: 2, padding: 2 }}>
          {fillSegments(levelLeft).map(({ i, active, clipping }) => (
            <div key={i} style={{
              flex: 1,
              borderRadius: 1,
              background: clipping ? '#f87171' : active ? 'var(--md-primary)' : 'var(--md-surface-container-lowest)',
              transition: 'background 60ms',
            }} />
          ))}
        </div>
      </div>
      {/* Right channel */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flex: 1 }}>
        <span style={{ fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: '#4cd7f6' }}>R</span>
        <div style={{ display: 'flex', flexDirection: 'column-reverse', gap: 1, height: barH, background: 'var(--md-surface-container-highest)', borderRadius: 2, padding: 2 }}>
          {fillSegments(levelRight).map(({ i, active, clipping }) => (
            <div key={i} style={{
              flex: 1,
              borderRadius: 1,
              background: clipping ? '#f87171' : active ? 'var(--md-primary)' : 'var(--md-surface-container-lowest)',
              transition: 'background 60ms',
            }} />
          ))}
        </div>
      </div>
      {/* Peak readout */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 4, minWidth: 40 }}>
        <span style={{ fontSize: 11, fontFamily: 'var(--md-font-code-inline)', color: peak !== null && peak > 0 ? '#f87171' : 'var(--md-primary)', fontWeight: 700 }}>
          {peak !== null ? `${peak.toFixed(1)} dB` : '—'}
        </span>
        <span style={{ fontSize: 8, color: '#556', marginTop: 2 }}>PEAK</span>
      </div>
    </div>
  );
}

export default function AudioMixerPanel() {
  const [persona, setPersona] = useState<'Marcus' | 'Elena' | 'Kaito'>(PERSONAS[0]);
  const [studioClarity, setStudioClarity] = useState(false);
  // Data honesty: no live audio metering backend yet, so the VU meter shows an
  // honest idle state (flat, no peak) instead of simulated random movement.
  const vuL = 0;
  const vuR = 0;
  const peak: number | null = null;

  return (
    <div style={{
      height: '100%',
      background: 'var(--md-surface-container)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)' }}>Audio DSP & Mixer</span>
        <span style={{
          fontSize: 8, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
          background: 'rgba(255,184,115,0.15)', color: 'var(--md-tertiary)',
          fontFamily: 'var(--md-font-code-inline)', letterSpacing: '0.04em',
        }}>MiniMax Engine V2</span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {/* Voice Persona */}
        <ControlRow label="Voice Synthesis Persona">
          <select
            value={persona}
            onChange={(e) => setPersona(e.target.value as 'Marcus' | 'Elena' | 'Kaito')}
            style={{ width: '100%' }}
          >
            {PERSONAS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </ControlRow>

        {/* Studio Clarity */}
        <div style={{ marginBottom: 10 }}>
          <FieldLabel>Studio Clarity EQ</FieldLabel>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 11, color: '#bcc9cd', marginTop: 2 }}>
            <input type="checkbox" checked={studioClarity} onChange={(e) => setStudioClarity(e.target.checked)}
              style={{ accentColor: 'var(--md-primary)' }} />
            Apply de-esser + EQ pass
          </label>
          {studioClarity && (
            <div style={{ marginTop: 6, fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: '#4cd7f6', padding: '4px 8px', background: 'var(--md-surface-container-lowest)', borderRadius: 4, border: '1px solid var(--md-outline-variant)' }}>
              {/* #253: local preference only — the de-esser/EQ pass is not implemented; no fabricated telemetry */}
              Marked locally — the de-esser/EQ pass is not implemented yet
            </div>
          )}
        </div>

        {/* Noise Gate */}
        <ControlRow label="Noise Gate Floor" right="-18.0 dB">
          <div style={{ width: '100%', height: 4, background: 'var(--md-surface-container-highest)', borderRadius: 2, position: 'relative' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--md-primary)', position: 'absolute', top: -2, left: '30%' }} />
          </div>
        </ControlRow>

        {/* Smart Ducking */}
        <ControlRow label="Smart Ducking" right="A1 &gt; A2 −12dB">
          <div style={{ fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: '#8899a6', padding: '4px 0' }}>
            Sidechain: Voice &gt; BGM
          </div>
        </ControlRow>

        {/* VU Meter */}
        <div style={{ marginBottom: 8 }}>
          <FieldLabel>Master Stereo VU</FieldLabel>
          <VUMeter levelLeft={vuL} levelRight={vuR} peak={peak} />
          <div style={{ marginTop: 4, fontSize: 9, color: '#556', fontFamily: 'var(--md-font-code-inline)' }}>No live metering — idle</div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '8px 14px',
        borderTop: '1px solid var(--md-surface-container-highest)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
        gap: 8,
      }}>
        <span style={{ fontSize: 9, color: '#556', fontFamily: 'var(--md-font-code-inline)' }}>48,000 Hz / 24-bit</span>
        <button
          type="button"
          disabled
          title="No audio audition endpoint yet"
          style={{
            background: 'var(--md-surface-container-highest)',
            color: 'var(--md-on-surface-variant)',
            border: '1px solid var(--md-outline)',
            borderRadius: 4,
            fontSize: 10,
            fontWeight: 600,
            cursor: 'not-allowed',
            opacity: 0.6,
            padding: '5px 10px',
            fontFamily: 'var(--md-font-code-inline)',
          }}
        >
          Audition Voice
        </button>
      </div>
    </div>
  );
}

function ControlRow({ label, children, right }: { label: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 10 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <FieldLabel>{label}</FieldLabel>
        {children}
      </div>
      {right && <div style={{ flexShrink: 0, paddingTop: 18, fontSize: 10, color: '#4cd7f6', fontFamily: 'var(--md-font-code-inline)', fontVariantNumeric: 'tabular-nums' }}>{right}</div>}
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ display: 'block', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8899a6', marginBottom: 4 }}>
      {children}
    </label>
  );
}
