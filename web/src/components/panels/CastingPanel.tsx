import { useCallback, useEffect, useState } from 'react';
import { useAppStore, withToken } from '../../store';
import type { PanelCastItem } from '../../types';

interface CastCardProps {
  item: PanelCastItem;
}

function CastCard({ item }: CastCardProps) {
  const [zoomed, setZoomed] = useState(false);
  const src = withToken(`/api/projects/${activeProjectId}/cast/media/${item.category}/${encodeURIComponent(item.filename)}`);

  return (
    <div
      onClick={() => setZoomed((z) => !z)}
      onKeyDown={(e) => { if (e.key === 'Escape') setZoomed(false); }}
      role="button"
      tabIndex={0}
      style={{
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{
        aspectRatio: '4/3',
        background: 'var(--md-surface-container-low)',
        borderRadius: 'var(--md-radius-md)',
        overflow: 'hidden',
        position: 'relative',
      }}>
        <img
          src={src}
          alt={item.filename}
          style={{
            width: '100%',
            height: '100%',
            objectFit: zoomed ? 'contain' : 'cover',
            position: zoomed ? 'fixed' : 'static',
            top: zoomed ? 0 : undefined,
            left: zoomed ? 0 : undefined,
            right: zoomed ? 0 : undefined,
            bottom: zoomed ? 0 : undefined,
            zIndex: zoomed ? 9999 : undefined,
            background: zoomed ? 'var(--md-surface-container-highest)' : undefined,
          }}
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.opacity = '0.15'; }}
        />
      </div>
      <div style={{
        fontFamily: 'var(--md-font-code-inline)',
        fontSize: 10,
        color: 'var(--md-on-surface)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {item.filename}
      </div>
      <div style={{
        fontSize: 9,
        color: 'var(--md-on-surface-variant)',
        fontFamily: 'var(--md-font-body-md)',
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span>{item.size_bytes === 0 ? '—' : (item.size_bytes / 1024).toFixed(1) + ' KB'}</span>
        <span>{item.modified ?? '—'}</span>
      </div>
    </div>
  );
}

let activeProjectId: string | undefined;

export default function CastingPanel() {
  const { activeProject } = useAppStore();
  const [items, setItems] = useState<PanelCastItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  activeProjectId = activeProject?.id;

  const projectId = activeProject?.id;

  const fetchCast = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await fetch(withToken(`/api/projects/${projectId}/cast`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    const boot = setTimeout(() => void fetchCast(), 0);
    return () => clearTimeout(boot);
  }, [projectId, fetchCast]);

  const byCategory = (category: string) => items.filter((i) => i.category === category);
  const characters = byCategory('character');
  const wardrobe = byCategory('wardrobe');

  if (!projectId) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Select a project to view casting
      </div>
    );
  }

  const hasItems = characters.length > 0 || wardrobe.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 12, fontWeight: 700, color: 'var(--md-primary)' }}>Casting</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
          {loading ? 'loading…' : `${items.length} plate${items.length === 1 ? '' : 's'}`}
        </span>
        {error && <span style={{ fontSize: 11, color: '#f87171' }} role="alert">cast error: {error}</span>}
      </div>

      {hasItems ? (
        <div style={{ flex: 1, overflow: 'auto', padding: '12px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
          {characters.length > 0 && (
            <>
              <div style={{ gridColumn: '1 / -1', fontSize: 10, fontFamily: 'var(--md-font-display-lg)', color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                Characters
              </div>
              {characters.map((item) => (
                <CastCard key={`${item.category}/${item.filename}`} item={item} />
              ))}
            </>
          )}
          {wardrobe.length > 0 && (
            <>
              <div style={{ gridColumn: '1 / -1', fontSize: 10, fontFamily: 'var(--md-font-display-lg)', color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                Wardrobe
              </div>
              {wardrobe.map((item) => (
                <CastCard key={`${item.category}/${item.filename}`} item={item} />
              ))}
            </>
          )}
        </div>
      ) : (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          flex: 1, gap: 12, color: 'var(--md-on-surface-variant)', fontSize: 12,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.3 }}>theater_comedy</span>
          <div>No cast images yet — generate character sheets to populate casting.</div>
        </div>
      )}
    </div>
  );
}