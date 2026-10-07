import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useAppStore, withToken } from './store';
import type { PanelKind } from './types';
import Header from './Header';
import Toolbar from './Toolbar';
import SidebarNav from './SidebarNav';
import StatusBar from './StatusBar';
import PreviewPanel from './components/panels/PreviewPanel';
import ClipInspectorPanel from './components/panels/ClipInspectorPanel';
import TimelinePanel from './components/timeline/TimelinePanel';
import ShotListPanel from './components/panels/ShotListPanel';
import PropsInspectorPanel from './components/panels/PropsInspectorPanel';
import ColorGradingPanel from './components/panels/ColorGradingPanel';
import AudioMixerPanel from './components/panels/AudioMixerPanel';
import RenderDispatchPanel from './components/panels/RenderDispatchPanel';
import ProductionMonitorPanel from './components/panels/ProductionMonitorPanel';
import ReviewQueuePanel from './components/panels/ReviewQueuePanel';
import AgnesPanel from './components/panels/AgnesPanel';
import './Shell.css';

type PanelComponent = () => ReactNode;

const PANELS: Record<PanelKind, PanelComponent> = {
  preview: () => (
    <div className="preview-workspace">
      <div className="preview-stage-host">
        <PreviewPanel />
      </div>
      <ClipInspectorPanel />
    </div>
  ),
  timeline: () => <TimelinePanel />,
  asset_manifest: () => (
    <div className="shot-workspace">
      <div className="preview-stage-host">
        <ShotListPanel />
      </div>
      <ClipInspectorPanel />
    </div>
  ),
  props: () => <PropsInspectorPanel />,
  color: () => <ColorGradingPanel />,
  audio: () => <AudioMixerPanel />,
  render: () => <RenderDispatchPanel />,
  monitor: () => <ProductionMonitorPanel />,
  review: () => <ReviewQueuePanel />,
  agnes_ai: () => <AgnesPanel />,
};

export default function Shell() {
  const { activePanel, activeProject, wsEvent, fetchProjects } = useAppStore();
  const [wsReady, setWsReady] = useState(false);

  // Boot: load the project list once on mount so the sidebar is
  // populated on first paint (issue #58). Panel switches must not
  // re-trigger this — empty dep array, stable zustand action ref.
  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  const activeProjectId = activeProject?.id;

  useEffect(() => {
    if (!activeProjectId) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/${activeProjectId}`;
    const cleanUrl = withToken(wsUrl).replace(window.location.origin, '');
    const ws = new WebSocket(cleanUrl);

    ws.onopen = () => setWsReady(true);
    ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data);
        const type = msg.type || '';
        if (type === 'monitor_tail') {
          // Issue #126: forward live progress lines to the monitor panel.
          window.dispatchEvent(new CustomEvent('brandly-monitor-tail', { detail: msg }));
        } else if (type.startsWith('generation_')) {
          useAppStore.setState({ wsEvent: `${type} · ${msg.phase || ''}` });
          setTimeout(() => useAppStore.setState({ wsEvent: null }), 3000);
        }
      } catch { /* ignore */ }
    };
    ws.onerror = () => setWsReady(false);
    ws.onclose = () => setWsReady(false);

    return () => { ws.close(); };
  }, [activeProjectId]);

  const Panel = PANELS[activePanel];

  return (
    <div className="shell-root">
      <Header wsReady={wsReady} wsEvent={wsEvent} />
      <Toolbar />
      <SidebarNav />
      <main className="main">
        {activeProject ? (
          <div key={activePanel} className="panel-host" style={{ animation: 'panelFade 200ms ease' }}>
            <Panel />
          </div>
        ) : (
          <NoProjectSelected />
        )}
      </main>
      <StatusBar />
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
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          backgroundImage: 'url(/static/preview.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.6,
          zIndex: 0,
        }}
      />
      <div style={{
        position: 'relative',
        zIndex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        textAlign: 'center',
        padding: '20px',
        background: 'rgba(14, 14, 17, 0.4)',
        backdropFilter: 'blur(2px)',
      }}>
        <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: 12, display: 'block', color: 'var(--md-on-surface)', opacity: 0.8 }}>movie_edit</span>
        <div style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 18, fontWeight: 600, color: 'var(--md-on-surface)', marginBottom: 8 }}>Select a Project</div>
        <div style={{ fontSize: 14, opacity: 0.8, maxWidth: '400px', lineHeight: 1.5 }}>
          Choose a project from the sidebar to begin editing<br/>
          <span style={{ opacity: 0.6, fontSize: 12, marginTop: 8, display: 'block' }}>
            Preview shows sample content when no project is loaded
          </span>
        </div>
      </div>
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
