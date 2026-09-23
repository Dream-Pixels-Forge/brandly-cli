import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useAppStore, withToken } from './store';
import type { PanelKind } from './types';
import Header from './Header';
import SidebarNav from './SidebarNav';
import PreviewPanel from './components/panels/PreviewPanel';
import TransportControls from './components/panels/TransportControls';
import './Shell.css';

type PanelComponent = () => ReactNode;

const PANELS: Record<PanelKind, PanelComponent> = {
  preview: () => (
    <>
      <PreviewPanel />
      <TransportControls />
    </>
  ),
  timeline: () => <TimelinePlaceholder />,
  asset_manifest: () => <AssetManifestPlaceholder />,
  props: () => <PropsPlaceholder />,
  color: () => <ColorPlaceholder />,
  audio: () => <AudioPlaceholder />,
  render: () => <RenderPlaceholder />,
  agnes_ai: () => <AgnesPlaceholder />,
};

function TimelinePlaceholder() {
  const { timeline, zoomLevel } = useAppStore();
  const totalDuration = timeline?.clips.reduce((s: number, c) => s + c.duration, 0) ?? 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 1200 }}>
      <div style={{
        background: 'var(--md-surface-container)',
        border: '1px solid var(--md-surface-container-high)',
        borderRadius: 'var(--md-radius-md)',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-primary)' }}>view_timeline</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
          {timeline?.clips.length ?? 0} clips · {totalDuration.toFixed(1)}s · zoom {zoomLevel / 100}x
        </span>
      </div>
      <div style={{
        background: 'var(--md-surface-container-lowest)',
        border: '1px dashed var(--md-surface-container-high)',
        borderRadius: 'var(--md-radius-md)',
        padding: '48px',
        textAlign: 'center',
        color: 'var(--md-on-surface-variant)',
        fontSize: 13,
      }}>
        <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.4, marginBottom: 8, display: 'block' }}>
          view_in_ar
        </span>
        Timeline Sequencer — visual scrubbing and clip arrangement view
      </div>
    </div>
  );
}

function AssetManifestPlaceholder() {
  const { timeline } = useAppStore();
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-surface-container-high)',
      borderRadius: 'var(--md-radius-md)',
      padding: 24,
      color: 'var(--md-on-surface)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-tertiary)' }}>folder_zip</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 13, fontWeight: 600 }}>Asset Manifest</span>
        <span style={{ marginLeft: 'auto', background: 'var(--md-primary-container)', color: 'var(--md-on-primary-container)', fontSize: 11, padding: '2px 8px', borderRadius: 9999, fontWeight: 600 }}>
          {timeline?.clips.length ?? 0} assets
        </span>
      </div>
      <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Complete asset registry for the current project. Generated on project load.
      </div>
    </div>
  );
}

function PropsPlaceholder() {
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-surface-container-high)',
      borderRadius: 'var(--md-radius-md)',
      padding: 24,
      color: 'var(--md-on-surface)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-primary)' }}>tune</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 13, fontWeight: 600 }}>Props Inspector</span>
      </div>
      <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Select a clip in the Preview panel to inspect its properties here.
      </div>
    </div>
  );
}

function ColorPlaceholder() {
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-surface-container-high)',
      borderRadius: 'var(--md-radius-md)',
      padding: 24,
      color: 'var(--md-on-surface)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-primary)' }}>palette</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 13, fontWeight: 600 }}>Color Grade</span>
      </div>
      <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Global color grading controls for the project.
      </div>
    </div>
  );
}

function AudioPlaceholder() {
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-surface-container-high)',
      borderRadius: 'var(--md-radius-md)',
      padding: 24,
      color: 'var(--md-on-surface)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-primary)' }}>graphic_eq</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 13, fontWeight: 600 }}>Audio Mixer</span>
      </div>
      <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Per-clip volume and waveform visualization.
      </div>
    </div>
  );
}

function RenderPlaceholder() {
  const { formatPreset, codec, concurrency } = useAppStore();
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-surface-container-high)',
      borderRadius: 'var(--md-radius-md)',
      padding: 24,
      color: 'var(--md-on-surface)',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-primary)' }}>cloud_sync</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 13, fontWeight: 600 }}>Render Queue</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 12 }}>
        <div style={{ background: 'var(--md-surface-container-highest)', padding: '8px 12px', borderRadius: 'var(--md-radius-sm)' }}>
          <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 10, marginBottom: 2 }}>FORMAT</div>
          <div style={{ fontFamily: 'var(--md-font-display-lg)', textTransform: 'uppercase' }}>{formatPreset.replace('-', ' ')}</div>
        </div>
        <div style={{ background: 'var(--md-surface-container-highest)', padding: '8px 12px', borderRadius: 'var(--md-radius-sm)' }}>
          <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 10, marginBottom: 2 }}>CODEC</div>
          <div style={{ fontFamily: 'var(--md-font-display-lg)', textTransform: 'uppercase' }}>{codec}</div>
        </div>
        <div style={{ background: 'var(--md-surface-container-highest)', padding: '8px 12px', borderRadius: 'var(--md-radius-sm)' }}>
          <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 10, marginBottom: 2 }}>CONCURRENCY</div>
          <div style={{ fontFamily: 'var(--md-font-display-lg)' }}>{concurrency} threads</div>
        </div>
      </div>
    </div>
  );
}

function AgnesPlaceholder() {
  return (
    <div style={{
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-surface-container-high)',
      borderRadius: 'var(--md-radius-md)',
      padding: 24,
      color: 'var(--md-on-surface)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span className="material-symbols-outlined" style={{ color: 'var(--md-tertiary)' }}>auto_awesome</span>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 13, fontWeight: 600 }}>Agnes AI Synthesizer</span>
      </div>
      <div style={{ color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Generate shots, variations, and scene extensions with Agnes AI.
      </div>
    </div>
  );
}

export default function Shell() {
  const { activePanel, activeProject, wsEvent } = useAppStore();
  const [wsReady, setWsReady] = useState(false);

  useEffect(() => {
    if (!activeProject) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/${activeProject.id}`;
    const cleanUrl = withToken(wsUrl).replace(window.location.origin, '');
    const ws = new WebSocket(cleanUrl);

    ws.onopen = () => setWsReady(true);
    ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data);
        const type = msg.type || '';
        if (type.startsWith('generation_')) {
          useAppStore.setState({ wsEvent: `${type} · ${msg.phase || ''}` });
          setTimeout(() => useAppStore.setState({ wsEvent: null }), 3000);
        }
      } catch { /* ignore */ }
    };
    ws.onerror = () => setWsReady(false);
    ws.onclose = () => setWsReady(false);

    return () => { ws.close(); };
  }, [activeProject?.id]);

  const Panel = PANELS[activePanel];

  return (
    <div className="shell-root">
      <Header wsReady={wsReady} wsEvent={wsEvent} />
      <SidebarNav />
      <main className="main">
        {activeProject ? (
          <div key={activePanel} style={{ animation: 'panelFade 200ms ease' }}>
            <Panel />
          </div>
        ) : (
          <NoProjectSelected />
        )}
      </main>
      <SaveToast />
      <style>{`@keyframes panelFade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } } @keyframes ping { 0% { opacity: 1; transform: scale(1); } 100% { opacity: 0; transform: scale(1.8); } }`}</style>
    </div>
  );
}

function NoProjectSelected() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      gap: 16,
      color: 'var(--md-on-surface-variant)',
    }}>
      <span className="material-symbols-outlined" style={{ fontSize: 48, opacity: 0.3 }}>movie_edit</span>
      <div style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 14, color: 'var(--md-on-surface)' }}>Select a Project</div>
      <div style={{ fontSize: 12, opacity: 0.7 }}>Choose a project from the sidebar to begin editing</div>
    </div>
  );
}

function SaveToast() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const handler = () => { setVisible(true); setTimeout(() => setVisible(false), 1400); };
    window.addEventListener('brandly-save', handler as EventListener);
    return () => window.removeEventListener('brandly-save', handler as EventListener);
  }, []);
  if (!visible) return null;
  return (
    <div style={{
      position: 'fixed',
      bottom: 20,
      right: 20,
      background: 'var(--md-surface-container-high)',
      border: '1px solid var(--md-primary)',
      borderRadius: 'var(--md-radius-md)',
      padding: '8px 16px',
      fontSize: 12,
      fontFamily: 'var(--md-font-display-lg)',
      color: 'var(--md-primary)',
      zIndex: 9999,
      boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    }}>
      <span className="material-symbols-outlined filled" style={{ fontSize: 16 }}>check_circle</span>
      Changes saved
    </div>
  );
}
