import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useAppStore, withToken } from './store';
import type { PanelKind } from './types';
import Header from './Header';
import SidebarNav from './SidebarNav';
import PreviewPanel from './components/panels/PreviewPanel';
import TransportControls from './components/panels/TransportControls';
import TimelinePanel from './components/timeline/TimelinePanel';
import ShotListPanel from './components/panels/ShotListPanel';
import PropsInspectorPanel from './components/panels/PropsInspectorPanel';
import ColorGradingPanel from './components/panels/ColorGradingPanel';
import AudioMixerPanel from './components/panels/AudioMixerPanel';
import RenderDispatchPanel from './components/panels/RenderDispatchPanel';
import './Shell.css';

type PanelComponent = () => ReactNode;

const PANELS: Record<PanelKind, PanelComponent> = {
  preview: () => (
    <>
      <PreviewPanel />
      <TransportControls />
    </>
  ),
  timeline: () => <TimelinePanel />,
  asset_manifest: () => <ShotListPanel />,
  props: () => <PropsInspectorPanel />,
  color: () => <ColorGradingPanel />,
  audio: () => <AudioMixerPanel />,
  render: () => <RenderDispatchPanel />,
  agnes_ai: () => <ShotListPanel />,
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
