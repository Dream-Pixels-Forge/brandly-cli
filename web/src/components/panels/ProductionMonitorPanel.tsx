import { useCallback, useEffect, useState } from 'react';
import { useAppStore, withToken } from '../../store';
import PhaseStepper from './PhaseStepper';
import type { MonitorRow, MonitorSnapshot } from '../../types';

const STATUS_COLORS: Record<string, string> = {
  OK: '#4ade80',
  FAIL: '#f87171',
  RETRY: '#facc15',
  pending: '#8899a6',
};

const PROVIDER_STATES: Record<string, { label: string; color: string }> = {
  ok: { label: 'Provider OK', color: '#4ade80' },
  rate_limit: { label: 'Rate storm (429)', color: '#facc15' },
  server_error: { label: 'Service degraded (5xx)', color: '#f87171' },
  failed: { label: 'Shot failure', color: '#f87171' },
  quota_exhausted: { label: 'Quota exhausted', color: '#f87171' },
};

const GATE_COLORS: Record<string, string> = {
  pass: '#4ade80',
  warn: '#facc15',
  fail: '#f87171',
};

function StatusChip({ status }: { status: string }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '1px 8px',
      borderRadius: 9999,
      fontSize: 10,
      fontFamily: 'var(--md-font-display-lg)',
      fontWeight: 700,
      color: STATUS_COLORS[status] || '#8899a6',
      background: 'var(--md-surface-container-lowest)',
      border: `1px solid ${STATUS_COLORS[status] || '#8899a6'}55`,
    }}>
      {status}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      style={{
        background: 'var(--md-surface-container-highest)',
        border: '1px solid var(--md-outline-variant)',
        borderRadius: 3,
        color: '#8899a6',
        fontSize: 9,
        cursor: 'pointer',
        padding: '2px 6px',
        fontFamily: 'var(--md-font-code-inline)',
        whiteSpace: 'nowrap',
      }}
      title={text}
    >
      {copied ? 'Copied' : 'Copy resume'}
    </button>
  );
}

export default function ProductionMonitorPanel() {
  const { activeProject, wsEvent } = useAppStore();
  const [snapshot, setSnapshot] = useState<MonitorSnapshot | null>(null);
  const [tailLines, setTailLines] = useState<Record<string, string[]>>({});
  const [error, setError] = useState<string | null>(null);

  const projectId = activeProject?.id;

  const fetchSnapshot = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await fetch(withToken(`/api/projects/${projectId}/monitor`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as MonitorSnapshot;
      setSnapshot(data);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, [projectId]);

  // Boot + poll: long produce runs stream continuously, so refresh the
  // snapshot on an interval and immediately on generation_* ws events.
  // The boot fetch is deferred a tick (set-state-in-effect): fetching is the
  // external-system sync this effect exists for, but scheduling it keeps the
  // first paint render-only.
  useEffect(() => {
    if (!projectId) return;
    const boot = setTimeout(() => void fetchSnapshot(), 0);
    const timer = setInterval(() => void fetchSnapshot(), 4000);
    return () => {
      clearTimeout(boot);
      clearInterval(timer);
    };
  }, [projectId, fetchSnapshot, wsEvent]);

  // Live tail: Shell forwards /ws/{project_id} monitor_tail messages here.
  useEffect(() => {
    const handler = (ev: Event) => {
      const detail = (ev as CustomEvent).detail as { stage?: string; lines?: string[] };
      const stage = detail?.stage;
      const lines = detail?.lines;
      if (!stage || !lines?.length) return;
      setTailLines((prev) => ({
        ...prev,
        [stage]: [...(prev[stage] ?? []), ...lines].slice(-200),
      }));
    };
    window.addEventListener('brandly-monitor-tail', handler as EventListener);
    return () => window.removeEventListener('brandly-monitor-tail', handler as EventListener);
  }, []);

  if (!projectId) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Select a project to monitor
      </div>
    );
  }

  const shots = snapshot?.shots ?? [];
  const provider = snapshot?.provider;
  const providerState = PROVIDER_STATES[provider?.status ?? ''] ?? PROVIDER_STATES.ok;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Director phase stepper — design §7 (artboard 04) */}
      <PhaseStepper />

      {/* Provider health strip */}
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--md-on-surface)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: providerState.color, boxShadow: `0 0 5px ${providerState.color}` }} />
          {providerState.label}
        </span>
        {provider && (
          <span style={{ fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
            video-seconds today: <strong>{provider.video_seconds_today}s</strong> / {provider.quota_seconds}s ({provider.records} generation{provider.records === 1 ? '' : 's'})
          </span>
        )}
        {provider?.last_error && (
          <span style={{ fontSize: 11, color: '#f87171' }} role="alert">
            last error [{provider.last_error.shot_id}]{provider.last_error.http_status ? ` HTTP ${provider.last_error.http_status}` : ''}: {provider.last_error.note}
          </span>
        )}
        {error && <span style={{ fontSize: 11, color: '#f87171' }}>monitor error: {error}</span>}
      </div>

      {shots.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          flex: 1, gap: 12, color: 'var(--md-on-surface-variant)', fontSize: 12,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.3 }}>monitor_heart</span>
          <div>No shots to monitor</div>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Run <code style={{ background: 'var(--md-surface-container-highest)', padding: '2px 6px', borderRadius: 3, fontFamily: 'var(--md-font-code-inline)' }}>brandly produce</code> — progress streams here live
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto', padding: '8px 12px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: 'var(--md-font-body-md)' }}>
            <thead>
              <tr style={{ color: 'var(--md-on-surface-variant)', textAlign: 'left' }}>
                <th style={{ padding: '4px 6px', fontWeight: 600 }}>Shot</th>
                <th style={{ padding: '4px 6px', fontWeight: 600 }}>Storyboard</th>
                <th style={{ padding: '4px 6px', fontWeight: 600 }}>Produce</th>
                <th style={{ padding: '4px 6px', fontWeight: 600 }}>Attempts</th>
                <th style={{ padding: '4px 6px', fontWeight: 600 }}>Gate</th>
                <th style={{ padding: '4px 6px', fontWeight: 600 }}>Note</th>
                <th style={{ padding: '4px 6px' }} />
              </tr>
            </thead>
            <tbody>
              {shots.map((row) => (
                <MonitorRowView key={row.shot_id} row={row} />
              ))}
            </tbody>
          </table>
          {(['produce', 'storyboard'] as const).map((stage) => (
            <LiveTail key={stage} stage={stage} lines={tailLines[stage] ?? []} />
          ))}
        </div>
      )}
    </div>
  );
}

function MonitorRowView({ row }: { row: MonitorRow }) {
  return (
    <tr style={{ borderTop: '1px solid var(--md-surface-container-highest)' }}>
      <td style={{ padding: '4px 6px', fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-on-surface)' }}>{row.shot_id}</td>
      <td style={{ padding: '4px 6px' }}><StatusChip status={row.storyboard} /></td>
      <td style={{ padding: '4px 6px' }}><StatusChip status={row.produce} /></td>
      <td style={{ padding: '4px 6px', color: 'var(--md-on-surface-variant)' }}>
        {row.attempts === 0
          ? '-'
          : `${row.attempts}${row.retries > 0 ? ` (${row.retries} retry${row.retries === 1 ? '' : 's'}${row.backoff ? `, backoff ${row.backoff}` : ''})` : ''}`}
      </td>
      <td style={{ padding: '4px 6px' }}>
        {row.gate ? (
          <span style={{ color: GATE_COLORS[row.gate.status] || '#8899a6', fontWeight: 700 }} title={row.gate.issues.join('\n')}>
            {row.gate.score}/100 {row.gate.status}
          </span>
        ) : <span style={{ color: '#8899a6' }}>-</span>}
      </td>
      <td style={{ padding: '4px 6px', color: 'var(--md-on-surface-variant)', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.note}>
        {row.note || '-'}
      </td>
      <td style={{ padding: '4px 6px', textAlign: 'right' }}>
        {row.resume_command && <CopyButton text={row.resume_command} />}
      </td>
    </tr>
  );
}

function LiveTail({ stage, lines }: { stage: string; lines: string[] }) {
  if (lines.length === 0) return null;
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 10, fontFamily: 'var(--md-font-display-lg)', color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
        {stage} progress — live
      </div>
      <div style={{
        background: 'var(--md-surface-container-lowest)',
        border: '1px solid var(--md-outline-variant)',
        borderRadius: 4,
        padding: '6px 8px',
        maxHeight: 160,
        overflowY: 'auto',
        fontFamily: 'var(--md-font-code-inline)',
        fontSize: 10,
        lineHeight: 1.6,
        color: 'var(--md-on-surface-variant)',
      }}>
        {lines.map((line, idx) => (
          <div key={`${idx}-${line}`} style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{line}</div>
        ))}
      </div>
    </div>
  );
}
