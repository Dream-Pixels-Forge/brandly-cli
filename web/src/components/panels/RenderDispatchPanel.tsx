import { useState } from 'react';
import { useAppStore } from '../../store';
import type { FormatPreset, Codec } from '../../types';

const PRESETS: { key: FormatPreset; label: string; desc: string }[] = [
  { key: 'youtube-4k', label: 'YouTube 4K', desc: '16:9 · 60fps' },
  { key: 'tiktok', label: 'TikTok / Reels', desc: '9:16 Vertical' },
  { key: 'instagram', label: 'Instagram', desc: '4:5 Feed' },
];

const CODECS: { key: Codec; label: string; ext: string }[] = [
  { key: 'h264', label: 'H.264 MP4', ext: '.mp4' },
  { key: 'prores', label: 'ProRes 422HQ', ext: '.mov' },
  { key: 'vp9', label: 'VP9 WebM', ext: '.webm' },
];

const CLI_SNIPPET = 'npx remotion render Root LuminaEarphonesLaunch out/video.mp4 --props="./props.json"';

function CopyableSnippet({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div style={{ position: 'relative' }}>
      <code style={{
        display: 'block',
        fontSize: 10,
        fontFamily: 'var(--md-font-code-inline)',
        color: 'var(--md-primary)',
        background: 'var(--md-surface-container-lowest)',
        border: '1px solid var(--md-outline-variant)',
        borderRadius: 4,
        padding: '8px 10px',
        wordBreak: 'break-all',
        lineHeight: 1.5,
      }}>{text}</code>
      <button
        onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
        style={{
          position: 'absolute', top: 4, right: 4,
          background: 'var(--md-surface-container-highest)',
          border: '1px solid var(--md-outline-variant)',
          borderRadius: 3, color: '#8899a6', fontSize: 9,
          cursor: 'pointer', padding: '2px 6px',
          fontFamily: 'var(--md-font-code-inline)',
        }}
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
}

export default function RenderDispatchPanel() {
  const { formatPreset, codec, concurrency, exportDone, exportProject, setFormatPreset, setCodec } = useAppStore();

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
        <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)' }}>Remotion Render Dispatch</span>
        <span style={{
          fontSize: 8, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
          background: exportDone ? 'rgba(74,222,128,0.15)' : 'rgba(76,215,246,0.15)',
          color: exportDone ? '#4ade80' : 'var(--md-primary)',
          fontFamily: 'var(--md-font-code-inline)', letterSpacing: '0.04em',
        }}>
          {exportDone ? 'DONE' : 'READY'}
        </span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {/* Format preset grid */}
        <FieldLabel>Format Preset</FieldLabel>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 12 }}>
          {PRESETS.map((p) => (
            <button
              key={p.key}
              onClick={() => setFormatPreset(p.key)}
              style={{
                background: formatPreset === p.key ? 'var(--md-primary)' : 'var(--md-surface-container-lowest)',
                color: formatPreset === p.key ? 'var(--md-on-primary)' : '#bcc9cd',
                border: `1px solid ${formatPreset === p.key ? 'var(--md-primary)' : 'var(--md-surface-container-highest)'}`,
                borderRadius: 4,
                padding: '6px 4px',
                cursor: 'pointer',
                fontFamily: 'var(--md-font-code-inline)',
                fontSize: 9,
                fontWeight: formatPreset === p.key ? 700 : 400,
                textAlign: 'center',
                transition: 'all 150ms',
              }}
            >
              <div>{p.label}</div>
              <div style={{ opacity: 0.6, fontSize: 8, marginTop: 2 }}>{p.desc}</div>
            </button>
          ))}
        </div>

        {/* Codec */}
        <div style={{ marginBottom: 10 }}>
          <FieldLabel>Codec</FieldLabel>
          <select
            value={codec}
            onChange={(e) => setCodec(e.target.value as Codec)}
            style={{ width: '100%' }}
          >
            {CODECS.map((c) => <option key={c.key} value={c.key}>{c.label} ({c.ext.slice(1).toUpperCase()})</option>)}
          </select>
        </div>

        {/* Concurrency */}
        <div style={{ marginBottom: 10 }}>
          <FieldLabel>Concurrency</FieldLabel>
          <div style={{ display: 'flex', gap: 6 }}>
            {[8, 16, 1].map((n) => (
              <button
                key={n}
                onClick={() => useAppStore.setState({ concurrency: n })}
                style={{
                  flex: 1,
                  background: concurrency === n ? 'var(--md-primary)' : 'var(--md-surface-container-lowest)',
                  color: concurrency === n ? 'var(--md-on-primary)' : '#bcc9cd',
                  border: `1px solid ${concurrency === n ? 'var(--md-primary)' : 'var(--md-surface-container-highest)'}`,
                  borderRadius: 4,
                  padding: '5px 0',
                  cursor: 'pointer',
                  fontSize: 10,
                  fontFamily: 'var(--md-font-code-inline)',
                  fontWeight: concurrency === n ? 700 : 400,
                }}
              >
                {n === 1 ? 'Single' : `${n} Threads`}
              </button>
            ))}
          </div>
        </div>

        {/* CLI snippet */}
        <div style={{ marginBottom: 12 }}>
          <FieldLabel>CLI Equivalent</FieldLabel>
          <CopyableSnippet text={CLI_SNIPPET} />
        </div>
      </div>

      {/* Render button */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--md-surface-container-highest)', flexShrink: 0 }}>
        <button
          onClick={exportProject}
          disabled={exportDone}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: exportDone ? '#059669' : 'var(--md-primary)',
            color: exportDone ? '#d1fae5' : 'var(--md-on-primary)',
            border: 'none',
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            cursor: exportDone ? 'default' : 'pointer',
            fontFamily: 'var(--md-font-code-inline)',
            letterSpacing: '0.02em',
            transition: 'background 200ms',
          }}
        >
          {exportDone ? '✓ Render Complete' : 'Render Multi-Shot Composition'}
        </button>
      </div>
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
