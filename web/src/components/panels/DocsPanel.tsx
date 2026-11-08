import { useCallback, useEffect, useState } from 'react';
import { useAppStore, withToken } from '../../store';
import type { PanelDocItem } from '../../types';

interface DocRowProps {
  item: PanelDocItem;
  isActive: boolean;
  onSelect: (item: PanelDocItem) => void;
}

function DocRow({ item, isActive, onSelect }: DocRowProps) {
  return (
    <button
      onClick={() => onSelect(item)}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 8px',
        background: isActive ? 'var(--md-surface-container)' : 'transparent',
        border: 'none',
        borderLeft: isActive ? '2px solid var(--md-primary)' : '2px solid transparent',
        color: isActive ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
        cursor: 'pointer',
        fontSize: 11,
        fontFamily: 'var(--md-font-body-md)',
        textAlign: 'left',
        transition: 'background var(--md-transition-fast)',
      }}
    >
      <div style={{
        fontSize: 10,
        fontFamily: 'var(--md-font-code-inline)',
        color: isActive ? 'var(--md-primary)' : 'var(--md-on-surface)',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        flex: 1,
      }}>
        {item.filename}
      </div>
      <span style={{
        fontSize: 9,
        color: 'var(--md-outline)',
        fontFamily: 'var(--md-font-display-lg)',
        flexShrink: 0,
      }}>
        {item.size_bytes === 0 ? '—' : (item.size_bytes / 1024).toFixed(1) + ' KB'}
      </span>
    </button>
  );
}

const DOC_GROUPS: { key: string; label: string }[] = [
  { key: 'plan', label: 'Plan' },
  { key: 'bible', label: 'Bible' },
  { key: 'storyboard', label: 'Storyboard' },
  { key: 'screenplay', label: 'Screenplay' },
  { key: 'general', label: 'General' },
  { key: 'tmp', label: 'Working' },
];

export default function DocsPanel() {
  const { activeProject } = useAppStore();
  const [items, setItems] = useState<PanelDocItem[]>([]);
  const [selected, setSelected] = useState<PanelDocItem | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const projectId = activeProject?.id;

  const fetchDocs = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await fetch(withToken(`/api/projects/${projectId}/docs`));
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

  const fetchContent = useCallback(async (item: PanelDocItem) => {
    if (!projectId) return;
    try {
      const res = await fetch(
        withToken(`/api/projects/${projectId}/docs/content?path=${encodeURIComponent(item.path)}`)
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setContent(data.content ?? '');
      setSelected(item);
    } catch (e) {
      setError(String(e));
    }
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    const boot = setTimeout(() => void fetchDocs(), 0);
    return () => clearTimeout(boot);
  }, [projectId, fetchDocs]);

  if (!projectId) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--md-on-surface-variant)', fontSize: 12 }}>
        Select a project to view documents
      </div>
    );
  }

  if (items.length === 0 && !selected) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: '100%', gap: 12, color: 'var(--md-on-surface-variant)', fontSize: 12,
      }}>
        <span className="material-symbols-outlined" style={{ fontSize: 32, opacity: 0.3 }}>description</span>
        <div>No documents yet — run the plan/bible/storyboard phases to generate project documents.</div>
      </div>
    );
  }

  if (!selected) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden',
      }}>
        <div style={{
          padding: '8px 12px',
          borderBottom: '1px solid var(--md-surface-container-highest)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 12, fontWeight: 700, color: 'var(--md-primary)' }}>Project Docs</span>
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
            {loading ? 'loading…' : `${items.length} document${items.length === 1 ? '' : 's'}`}
          </span>
          {error && <span style={{ fontSize: 11, color: '#f87171' }} role="alert">docs error: {error}</span>}
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '12px', display: 'flex', flexDirection: 'column' }}>
          {DOC_GROUPS.map((g) => {
            const groupItems = items.filter((i) => i.category === g.key);
            if (groupItems.length === 0) return null;
            return (
              <div key={g.key} style={{ marginBottom: 10 }}>
                <div style={{
                  fontSize: 9,
                  fontFamily: 'var(--md-font-display-lg)',
                  color: 'var(--md-on-surface-variant)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  marginBottom: 4,
                }}>
                  {g.label}
                </div>
                {groupItems.map((item) => (
                  <DocRow
                    key={item.path}
                    item={item}
                    isActive={false}
                    onSelect={fetchContent}
                  />
                ))}
              </div>
            );
          })}
          {items.length > 0 && DOC_GROUPS.some((g) => items.some((i) => i.category === g.key)) === false && (
            <div style={{ padding: '20px', color: 'var(--md-on-surface-variant)', fontSize: 11 }}>
              No categorized documents found.
            </div>
          )}
        </div>
      </div>
    );
  }

  // Document viewer (right side) + rail (left side)
  const tmpItems = items.filter((i) => i.category === 'tmp');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--md-surface-container-highest)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ fontFamily: 'var(--md-font-display-lg)', fontSize: 12, fontWeight: 700, color: 'var(--md-primary)' }}>Project Docs</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
          {loading ? 'loading…' : `${items.length} document${items.length === 1 ? '' : 's'}`}
        </span>
        {error && <span style={{ fontSize: 11, color: '#f87171' }} role="alert">docs error: {error}</span>}
      </div>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left rail */}
        <div style={{
          width: 300,
          borderRight: '1px solid var(--md-surface-container-high)',
          background: 'var(--md-surface-container-lowest)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '8px 12px', fontSize: 9, fontFamily: 'var(--md-font-display-lg)', color: 'var(--md-on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
            Documents
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '0 4px' }}>
            {DOC_GROUPS.map((g) => {
              const groupItems = items.filter((i) => i.category === g.key);
              if (groupItems.length === 0) return null;
              return (
                <div key={g.key} style={{ marginBottom: 8 }}>
                  <div style={{
                    fontSize: 8,
                    fontFamily: 'var(--md-font-display-lg)',
                    color: 'var(--md-outline)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    marginBottom: 4,
                    paddingLeft: 6,
                  }}>
                    {g.label}
                  </div>
                  {groupItems.map((item) => (
                    <DocRow
                      key={item.path}
                      item={item}
                      isActive={selected?.path === item.path}
                      onSelect={fetchContent}
                    />
                  ))}
                </div>
              );
            })}
            {tmpItems.length > 0 && (
              <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--md-surface-container-highest)' }}>
                <div style={{
                  fontSize: 8,
                  fontFamily: 'var(--md-font-display-lg)',
                  color: 'var(--md-outline)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  marginBottom: 4,
                  paddingLeft: 6,
                }}>
                  Working
                </div>
                {tmpItems.map((item) => (
                  <DocRow
                    key={item.path}
                    item={item}
                    isActive={selected?.path === item.path}
                    onSelect={fetchContent}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
        {/* Right viewer */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--md-surface-container-lowest)' }}>
          <div style={{
            padding: '8px 12px',
            borderBottom: '1px solid var(--md-surface-container-high)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div style={{
              fontSize: 10,
              fontFamily: 'var(--md-font-code-inline)',
              color: 'var(--md-on-surface-variant)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}>
              {selected?.path ?? ''}
            </div>
            <div style={{
              fontSize: 9,
              color: 'var(--md-outline)',
              fontFamily: 'var(--md-font-display-lg)',
              flexShrink: 0,
            }}>
              {selected?.size_bytes === 0 ? '—' : (selected.size_bytes / 1024).toFixed(1) + ' KB'}
            </div>
          </div>
          <div style={{
            flex: 1,
            overflow: 'auto',
            padding: '12px',
            fontFamily: 'var(--md-font-code-inline)',
            fontSize: 12.5,
            color: 'var(--md-on-surface)',
            background: 'var(--md-surface-container-lowest)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {content ?? 'Select a document to view it.'}
          </div>
        </div>
      </div>
    </div>
  );
}