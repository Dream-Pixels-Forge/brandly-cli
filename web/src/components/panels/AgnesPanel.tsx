import { useEffect, useState } from 'react';
import { useAppStore, withToken } from '../../store';
import type { Clip } from '../../types';

/** Design §6 screen 06 — Agnes AI Synthesizer.
 *
 * Generation console (prompt box, style-preset chips, aspect/fit/seed params,
 * credit-budget bar, Synthesize/Queue actions) + 2×2 results grid (one
 * selected variant) + run-summary footer.
 *
 * Data honesty (DESIGN-STUDIO-SHELL.md §5): everything renders from the real
 * project / clip / store data. Un-generated variants, the credit budget and
 * queued runs are labelled honestly — never fabricated.
 */

const STYLE_PRESETS = ['cinematic-commercial', 'anime-illustration', 'photorealistic-raw', 'minimal-editorial'] as const;
const ASPECTS = ['16:9', '9:16', '1:1', '4:5'] as const;
const FITS = ['fill', 'fit', 'crop'] as const;

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 9, fontFamily: 'var(--md-font-display-lg)', color: 'var(--md-on-surface-variant)', letterSpacing: '0.1em', marginBottom: 4 }}>{children}</div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        fontSize: 10,
        fontFamily: 'var(--md-font-code-inline)',
        padding: '3px 9px',
        borderRadius: 9999,
        cursor: 'pointer',
        background: active ? 'var(--md-primary)' : 'var(--md-surface-container-lowest)',
        color: active ? 'var(--md-on-primary)' : 'var(--md-on-surface-variant)',
        border: `1px solid ${active ? 'var(--md-primary)' : 'var(--md-surface-container-highest)'}`,
        fontWeight: active ? 700 : 400,
        transition: 'all var(--md-transition-fast)',
      }}
    >
      {children}
    </button>
  );
}

export default function AgnesPanel() {
  const { activeProject, timeline, selectedClipId, updateClip, regenerateClip, wsEvent } = useAppStore();
  const clip: Clip | null =
    timeline?.clips.find((c) => c.id === selectedClipId) ?? timeline?.clips[0] ?? null;

  // Transient generation config (client-side preferences — not persisted).
  const [draft, setDraft] = useState('');
  const [styleSel, setStyleSel] = useState<string>(STYLE_PRESETS[0]);
  const [aspectSel, setAspectSel] = useState<string>(ASPECTS[0]);
  const [fitSel, setFitSel] = useState<string>('fill');
  const [seed, setSeed] = useState('');
  const [selectedVariant, setSelectedVariant] = useState(0);

  // Keep the console in sync with the selected clip (real data).
  useEffect(() => {
    setDraft(clip?.prompt ?? '');
    setStyleSel(clip?.style || STYLE_PRESETS[0]);
    setAspectSel(clip?.aspect_ratio || ASPECTS[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clip?.id]);

  const clipGenerated = clip?.status === 'generated';
  const mediaUrl =
    clip && activeProject
      ? withToken(`/api/projects/${activeProject.id}/clips/${encodeURIComponent(clip.id)}/preview`)
      : null;

  if (!activeProject) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--md-on-surface-variant)', fontSize: 12, fontFamily: 'var(--md-font-code-inline)' }}>
        No project selected — choose one from the sidebar
      </div>
    );
  }

  return (
    <div style={{ height: '100%', background: 'var(--md-surface-container)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ height: 36, padding: '0 14px', borderBottom: '1px solid var(--md-surface-container-highest)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--md-surface-container-low)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--md-primary)' }}>auto_awesome</span>
          <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)' }}>AGNES AI SYNTHESIZER</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {activeProject.current_phase ? (
            <span style={{ fontSize: 9, fontFamily: 'var(--md-font-code-inline)', fontWeight: 700, padding: '2px 8px', borderRadius: 3, background: 'var(--md-primary)', color: 'var(--md-on-primary)' }}>
              {String(activeProject.current_phase).toUpperCase()}
            </span>
          ) : null}
          <span style={{ fontSize: 8, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface-variant)' }}>generation console</span>
        </div>
      </div>
      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', gap: 12, padding: 12, boxSizing: 'border-box' }}>
        {/* Generation console */}
        <div style={{ flex: 1, minWidth: 240, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <Label>PROMPT</Label>
            {clip ? (
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
                style={{ width: '100%', background: 'var(--md-surface-container-lowest)', border: '1px solid var(--md-outline-variant)', borderRadius: 4, padding: '8px 10px', fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface)', resize: 'vertical', boxSizing: 'border-box' }}
              />
            ) : (
              <div style={{ padding: '14px 10px', border: '1px dashed var(--md-surface-container-highest)', borderRadius: 4, fontSize: 11, color: 'var(--md-on-surface-variant)', textAlign: 'center' }}>
                Select a clip to synthesize
              </div>
            )}
          </div>
          <div>
            <Label>STYLE PRESET</Label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {STYLE_PRESETS.map((s) => (
                <Chip key={s} active={styleSel === s} onClick={() => setStyleSel(s)}>{s}</Chip>
              ))}
            </div>
          </div>
          <div>
            <Label>ASPECT · FIT · SEED</Label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 6 }}>
              {ASPECTS.map((a) => (
                <Chip key={a} active={aspectSel === a} onClick={() => setAspectSel(a)}>{a}</Chip>
              ))}
              {FITS.map((f) => (
                <Chip key={f} active={fitSel === f} onClick={() => setFitSel(f)}>{f}</Chip>
              ))}
            </div>
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="seed (local, not persisted)"
              style={{ width: '100%', background: 'var(--md-surface-container-lowest)', border: '1px solid var(--md-outline-variant)', borderRadius: 4, padding: '6px 10px', fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface)', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <Label>CREDIT BUDGET</Label>
            <div style={{ height: 8, background: 'var(--md-surface-container-lowest)', border: '1px solid var(--md-surface-container-highest)', borderRadius: 9999, overflow: 'hidden' }}>
              <div style={{ width: 0, height: '100%', background: 'var(--md-primary)' }} />
            </div>
            <div style={{ fontSize: 9, color: 'var(--md-on-surface-variant)', marginTop: 4 }}>no credit data — not wired</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={() => {
                if (!clip) return;
                if (draft.trim() && draft !== clip.prompt) void updateClip(clip.id, { prompt: draft });
                void regenerateClip(clip.id);
              }}
              style={{ flex: 1, padding: '9px 0', background: 'var(--md-primary)', color: 'var(--md-on-primary)', border: 'none', borderRadius: 4, fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', cursor: clip ? 'pointer' : 'not-allowed', opacity: clip ? 1 : 0.5, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>auto_awesome</span>
              Synthesize
            </button>
            <button
              type="button"
              disabled
              title="Queueing not wired yet"
              style={{ flex: 1, padding: '9px 0', background: 'transparent', color: 'var(--md-on-surface-variant)', border: '1px solid var(--md-surface-container-highest)', borderRadius: 4, fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', cursor: 'not-allowed', opacity: 0.6 }}
            >
              Queue
            </button>
          </div>
        </div>
        {/* 2×2 results grid (one selected variant) */}
        <div style={{ flex: 1, minWidth: 240, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Label>RESULTS — 2×2 VARIANTS</Label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[0, 1, 2, 3].map((i) => {
              const isReal = i === 0 && clipGenerated && mediaUrl !== null;
              const selected = selectedVariant === i;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => setSelectedVariant(i)}
                  style={{
                    aspectRatio: '16 / 9',
                    position: 'relative',
                    overflow: 'hidden',
                    borderRadius: 4,
                    cursor: 'pointer',
                    background: 'var(--md-surface-container-lowest)',
                    border: selected ? '2px solid var(--md-primary)' : '1px solid var(--md-surface-container-highest)',
                    padding: 0,
                    width: '100%',
                  }}
                >
                  {isReal ? (
                    <video
                      src={mediaUrl ?? undefined}
                      muted
                      preload="metadata"
                      style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                    />
                  ) : (
                    <span style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, color: 'var(--md-on-surface-variant)', fontSize: 9, fontFamily: 'var(--md-font-code-inline)' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, opacity: 0.4 }}>movie</span>
                      {i === 0 ? 'not generated yet' : `variant ${i + 1} — not generated`}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Run-summary footer */}
      <div style={{ padding: '8px 14px', borderTop: '1px solid var(--md-surface-container-highest)', background: 'var(--md-surface-container-low)', fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface-variant)', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 9, color: 'var(--md-outline)', textTransform: 'uppercase' }}>run</span>
        {wsEvent ? (
          <span style={{ color: 'var(--md-primary)' }}>{wsEvent}</span>
        ) : clip ? (
          <span>last state: {clip.status} · {clip.prompt.slice(0, 40)}{clip.prompt.length > 40 ? '…' : ''}</span>
        ) : (
          <span>No runs yet — Synthesize to start</span>
        )}
      </div>
    </div>
  );
}
