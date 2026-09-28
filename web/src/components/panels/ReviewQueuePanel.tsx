import { useCallback, useEffect, useState } from 'react';
import { useAppStore, withToken } from '../../store';
import type { ReviewItem } from '../../types';

const STAGES: { key: string; label: string }[] = [
  { key: '', label: 'All stages' },
  { key: 'storyboard', label: 'Storyboard' },
  { key: 'video', label: 'Video takes' },
  { key: 'reference', label: 'Reference sheets' },
];

const GATE_COLORS: Record<string, string> = {
  pass: '#4ade80',
  warn: '#facc15',
  fail: '#f87171',
};

function GateBadge({ item }: { item: ReviewItem }) {
  if (!item.gate) {
    return <span style={{ fontSize: 10, color: '#8899a6' }}>no gate score</span>;
  }
  return (
    <span style={{ color: GATE_COLORS[item.gate.status] || '#8899a6', fontWeight: 700, fontSize: 11 }}>
      {item.gate.score}/100 {item.gate.status}
    </span>
  );
}

function ReviewCard({
  item,
  projectId,
  onDecided,
}: {
  item: ReviewItem;
  projectId: string;
  onDecided: (itemId: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [showNote, setNoteOpen] = useState(false);

  const decide = useCallback(
    async (action: 'approve' | 'reject') => {
      setBusy(true);
      try {
        const res = await fetch(
          withToken(`/api/projects/${projectId}/review/${encodeURIComponent(item.item_id)}/${action}`),
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(action === 'reject' ? { note, reviewer: 'web-reviewer' } : { reviewer: 'web-reviewer' }),
          },
        );
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        onDecided(item.item_id);
      } catch {
        setBusy(false);
        return;
      }
      setBusy(false);
    },
    [item.item_id, note, onDecided, projectId],
  );

  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-outline-variant)',
      borderRadius: 'var(--md-radius-sm)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <button
        onClick={() => window.open(withToken(`/api/projects/${projectId}/review/${encodeURIComponent(item.item_id)}/media`), '_blank')}
        style={{ padding: 0, border: 'none', background: 'var(--md-surface-container-lowest)', cursor: 'zoom-in', aspectRatio: '16/9', display: 'block', width: '100%' }}
        title="Open full preview"
      >
        <img
          src={withToken(`/api/projects/${projectId}/review/${encodeURIComponent(item.item_id)}/media`)}
          alt={item.item_id}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.opacity = '0.15'; }}
        />
      </button>
      <div style={{ padding: '6px 8px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface-variant)', wordBreak: 'break-all' }}>
          {item.item_id}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
          <GateBadge item={item} />
          <span style={{ fontSize: 10, color: '#8899a6' }}>scene {item.scene ?? '-'}</span>
        </div>
        {showNote && (
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What didn't match?"
            style={{
              fontSize: 10, padding: '4px 6px', borderRadius: 3,
              border: '1px solid var(--md-outline-variant)',
              background: 'var(--md-surface-container-lowest)', color: 'var(--md-on-surface)',
              fontFamily: 'var(--md-font-body-md)',
            }}
          />
        )}
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            disabled={busy}
            onClick={() => void decide('approve')}
            style={{
              flex: 1, padding: '4px 0', fontSize: 11, cursor: 'pointer',
              border: '1px solid #4ade8055', borderRadius: 3,
              background: 'var(--md-surface-container-lowest)', color: '#4ade80', fontWeight: 700,
              fontFamily: 'var(--md-font-body-md)',
            }}
          >
            Approve
          </button>
          <button
            disabled={busy}
            onClick={() => { if (!showNote && !note) { setNoteOpen(true); return; } void decide('reject'); }}
            style={{
              flex: 1, padding: '4px 0', fontSize: 11, cursor: 'pointer',
              border: '1px solid #f8717155', borderRadius: 3,
              background: 'var(--md-surface-container-lowest)', color: '#f87171', fontWeight: 700,
              fontFamily: 'var(--md-font-body-md)',
            }}
          >
            Reject
          </button>
        </div>
        {item.shot_id && (
          <div style={{ fontSize: 9, color: '#8899a6', fontFamily: 'var(--md-font-code-inline)' }}>
            reject re-runs <span style={{ color: 'var(--md-primary)' }}>--only {item.shot_id}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReviewQueuePanel() {
  const { activeProject } = useAppStore();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [stage, setStage] = useState('');
  const [scene, setScene] = useState('');
  const [belowThreshold, setBelowThreshold] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const projectId = activeProject?.id;

  const fetchQueue = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (stage) params.set('stage', stage);
      if (scene) params.set('scene', scene);
      if (belowThreshold) params.set('below_threshold', '50');
      const qs = params.toString();
      const res = await fetch(withToken(`/api/projects/${projectId}/review/queue${qs ? `?${qs}` : ''}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId, stage, scene, belowThreshold]);

  useEffect(() => {
    if (!projectId) return;
    const boot = setTimeout(() => void fetchQueue(), 0);
    return () => clearTimeout(boot);
  }, [projectId, fetchQueue]);

  const onDecided = useCallback(
    (itemId: string) => {
      setItems((prev) => prev.filter((i) => i.item_id !== itemId));
    },
    [],
  );

  if (!projectId) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Select a project to review
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Filter bar */}
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <select
          value={stage}
          onChange={(e) => setStage(e.target.value)}
          style={{
            fontSize: 11, padding: '4px 6px', borderRadius: 3,
            border: '1px solid var(--md-outline-variant)',
            background: 'var(--md-surface-container-lowest)', color: 'var(--md-on-surface)',
          }}
        >
          {STAGES.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <input
          value={scene}
          onChange={(e) => setScene(e.target.value.replace(/[^0-9]/g, ''))}
          placeholder="scene #"
          style={{
            fontSize: 11, padding: '4px 6px', borderRadius: 3, width: 64,
            border: '1px solid var(--md-outline-variant)',
            background: 'var(--md-surface-container-lowest)', color: 'var(--md-on-surface)',
          }}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--md-on-surface-variant)', cursor: 'pointer' }}>
          <input type="checkbox" checked={belowThreshold} onChange={(e) => setBelowThreshold(e.target.checked)} />
          gate score below 50
        </label>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
          {loading ? 'loading…' : `${items.length} item${items.length === 1 ? '' : 's'} to review`}
        </span>
        {error && <span style={{ fontSize: 11, color: '#f87171' }} role="alert">queue error: {error}</span>}
      </div>

      {items.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          flex: 1, gap: 12, color: 'var(--md-on-surface-variant)', fontSize: 12,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.3 }}>fact_check</span>
          <div>Nothing waiting for review</div>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Auto-approved keyframes, takes and reference sheets land here after an agent run
          </div>
        </div>
      ) : (
        <div style={{
          flex: 1, overflow: 'auto', padding: '12px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 12,
          alignContent: 'start',
        }}>
          {items.map((item) => (
            <ReviewCard key={item.item_id} item={item} projectId={projectId} onDecided={onDecided} />
          ))}
        </div>
      )}
    </div>
  );
}
