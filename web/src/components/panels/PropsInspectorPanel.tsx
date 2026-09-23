import { useState } from 'react';
import { useAppStore } from '../../store';
import type { Clip } from '../../types';

const MODELS = ['agnes-ultra-v4.2', 'agnes-video-pro', 'blender-eevee-direct'] as const;
const STYLE_PRESETS = ['cinematic-commercial', 'photorealistic-raw', 'minimal-editorial'] as const;
const TRANSITIONS = ['', 'fade', 'dissolve', 'wipe', 'slide'] as const;

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ display: 'block', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8899a6', marginBottom: 4 }}>
      {children}
    </label>
  );
}

function ControlRow({ label, children, right }: { label: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 10 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <FieldLabel>{label}</FieldLabel>
        {children}
      </div>
      {right && <div style={{ flexShrink: 0, paddingTop: 18, fontSize: 10, color: '#4cd7f6', fontVariantNumeric: 'tabular-nums' }}>{right}</div>}
    </div>
  );
}

function lockIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" style={{ opacity: 0.6 }}>
      <path d="M8 1a5 5 0 0 0-5 5v3H2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V10a1 1 0 0 0-1-1h-1V6a5 5 0 0 0-5-5zm3 8H5V6a3 3 0 1 1 6 0v3z"/>
    </svg>
  );
}

export default function PropsInspectorPanel() {
  const { selectedClipId, updateClip, timeline } = useAppStore();
  const clip = timeline?.clips.find((c: Clip) => c.id === selectedClipId) ?? null;
  const [seedLocked, setSeedLocked] = useState(true);
  const [spatialChecked, setSpatialChecked] = useState(false);
  const [beatSync, setBeatSync] = useState(false);

  if (!clip) {
    return (
      <div style={{
        height: '100%',
        background: 'var(--md-surface-container)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '10px 14px',
          borderBottom: '1px solid var(--md-surface-container-highest)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)' }}>&lt;ShotProps /&gt;</span>
          <span style={{ fontSize: 9, color: '#666', fontFamily: 'var(--md-font-code-inline)' }}>zod: ClipPropsSchema</span>
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
          <p style={{ color: '#4a5568', fontSize: 12, textAlign: 'center' }}>Select a clip to edit</p>
        </div>
      </div>
    );
  }

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)' }}>&lt;ShotProps /&gt;</span>
          <span style={{ fontSize: 9, color: '#666', fontFamily: 'var(--md-font-code-inline)' }}>zod: ClipPropsSchema</span>
        </div>
        <span style={{ fontSize: 9, color: '#4a5568', fontFamily: 'var(--md-font-code-inline)' }}>{clip.id}</span>
      </div>

      {/* Scrollable form */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {/* Prompt */}
        <ControlRow label="Prompt">
          <textarea
            value={clip.prompt}
            onChange={(e) => updateClip(clip.id, { prompt: e.target.value })}
            rows={3}
            style={{
              width: '100%',
              resize: 'vertical',
              background: 'var(--md-surface-container-lowest)',
              border: '1px solid var(--md-surface-container-highest)',
              borderRadius: 4,
              color: '#e4e1e6',
              fontFamily: 'var(--md-font-code-inline)',
              fontSize: 10,
              padding: '6px 8px',
              outline: 'none',
              lineHeight: 1.5,
            }}
          />
        </ControlRow>

        {/* Model */}
        <ControlRow label="Model">
          <select
            value={clip.style || 'agnes-ultra-v4.2'}
            onChange={(e) => updateClip(clip.id, { style: e.target.value })}
            style={{ width: '100%' }}
          >
            {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </ControlRow>

        {/* Style Preset */}
        <ControlRow label="Style Preset">
          <select
            value={clip.aspect_ratio || 'cinematic-commercial'}
            onChange={(e) => updateClip(clip.id, { aspect_ratio: e.target.value })}
            style={{ width: '100%' }}
          >
            {STYLE_PRESETS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </ControlRow>

        {/* Blender Spatial */}
        <div style={{ marginBottom: 10 }}>
          <FieldLabel>Blender Spatial Anchors</FieldLabel>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 11, color: '#bcc9cd', marginTop: 2 }}>
            <input type="checkbox" checked={spatialChecked} onChange={(e) => setSpatialChecked(e.target.checked)}
              style={{ accentColor: 'var(--md-primary)' }} />
            Enable spatial reference frame
          </label>
          {spatialChecked && (
            <div style={{ marginTop: 6, padding: '6px 8px', background: 'var(--md-surface-container-lowest)', borderRadius: 4, border: '1px solid var(--md-outline-variant)', fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: '#4cd7f6', lineHeight: 1.7 }}>
              <div>Cam: 120° CCW</div>
              <div>Focal: 50mm</div>
              <div>Samples: 128</div>
            </div>
          )}
        </div>

        {/* Seed */}
        <ControlRow label="Seed" right={seedLocked ? 'LOCKED' : 'FREE'}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="number"
              value={42}
              disabled
              style={{ flex: 1, opacity: seedLocked ? 1 : 0.5, cursor: seedLocked ? 'not-allowed' : 'text' }}
            />
            <button
              onClick={() => setSeedLocked((v) => !v)}
              style={{
                background: seedLocked ? 'var(--md-primary)' : 'var(--md-surface-container-highest)',
                border: 'none',
                borderRadius: 4,
                padding: '4px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                color: seedLocked ? 'var(--md-on-primary)' : '#888',
              }}
              title={seedLocked ? 'Unlock seed' : 'Lock seed'}
            >
              {lockIcon()}
            </button>
          </div>
        </ControlRow>

        {/* CFG Guidance */}
        <ControlRow label="CFG Guidance">
          <CfgSlider
            value={1.5}
            onChange={(v) => updateClip(clip.id, { volume: v })}
          />
        </ControlRow>

        {/* Audio Beat Sync */}
        <div style={{ marginBottom: 10 }}>
          <FieldLabel>Audio Beat Sync</FieldLabel>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 11, color: '#bcc9cd', marginTop: 2 }}>
            <input type="checkbox" checked={beatSync} onChange={(e) => setBeatSync(e.target.checked)}
              style={{ accentColor: 'var(--md-primary)' }} />
            Enable beat sync
          </label>
          {beatSync && (
            <div style={{ marginTop: 6, fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: '#4cd7f6', padding: '4px 8px', background: 'var(--md-surface-container-lowest)', borderRadius: 4, border: '1px solid var(--md-outline-variant)' }}>
              BPM: 120 · Bar: 4/4
            </div>
          )}
        </div>

        {/* Duration */}
        <ControlRow label="Duration (s)">
          <input
            type="number"
            min={1}
            max={12}
            step={0.1}
            value={clip.duration}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v)) updateClip(clip.id, { duration: Math.max(1, Math.min(12, v)) });
            }}
            style={{ width: '100%' }}
          />
        </ControlRow>

        {/* Transition */}
        <ControlRow label="Transition In">
          <select
            value={clip.transition_in || ''}
            onChange={(e) => updateClip(clip.id, { transition_in: e.target.value || null })}
            style={{ width: '100%' }}
          >
            {TRANSITIONS.map((t) => <option key={t} value={t}>{t || 'None'}</option>)}
          </select>
        </ControlRow>

        {/* Volume */}
        <ControlRow label="Volume">
          <VolumeSlider
            value={clip.volume}
            onChange={(v) => updateClip(clip.id, { volume: v })}
          />
        </ControlRow>
      </div>

      {/* Footer */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--md-surface-container-highest)', flexShrink: 0 }}>
        <button
          onClick={() => updateClip(clip.id, {
            prompt: clip.prompt,
            duration: clip.duration,
            volume: clip.volume,
            transition_in: clip.transition_in,
          })}
          style={{
            width: '100%',
            padding: '8px 12px',
            background: 'var(--md-primary)',
            color: 'var(--md-on-primary)',
            border: 'none',
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'var(--md-font-code-inline)',
          }}
        >
          Update Shot Props (Hot Reload)
        </button>
      </div>
    </div>
  );
}

function CfgSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input
        type="range"
        min={1}
        max={15}
        step={0.5}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ flex: 1 }}
      />
      <span style={{ fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)', minWidth: 28, textAlign: 'right' }}>
        {value.toFixed(1)}
      </span>
    </div>
  );
}

function VolumeSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ flex: 1 }}
      />
      <span style={{ fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)', minWidth: 32, textAlign: 'right' }}>
        {(value * 100).toFixed(0)}%
      </span>
    </div>
  );
}
