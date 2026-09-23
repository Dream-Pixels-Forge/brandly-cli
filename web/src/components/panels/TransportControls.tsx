import { useAppStore } from '../../store';

export default function TransportControls() {
  const { isPlaying, currentFrame, totalFrames, playbackRate, loop, volume, togglePlay, stepFrame, setPlayhead, setPlaybackRate, setLoop, setVolume } = useAppStore();

  const fmtFrame = (f: number) => {
    const fps = 24;
    const h = Math.floor(f / (fps * 3600));
    const m = Math.floor((f % (fps * 3600)) / (fps * 60));
    const s = Math.floor((f % (fps * 60)) / fps);
    const frames = f % fps;
    const parts = [];
    if (h > 0) parts.push(`${h}:`);
    parts.push(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`);
    return parts.join('');
  };

  return (
    <div style={{
      height: 44,
      padding: '0 12px',
      borderBottom: '1px solid var(--md-surface-container-highest)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'var(--md-surface-container)',
      flexShrink: 0,
      gap: 8,
    }}>
      {/* Left: Step controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {[
          { icon: 'skip_previous', action: () => setPlayhead(0), title: 'Jump to start' },
          { icon: 'navigate_before', action: () => stepFrame(-1), title: 'Previous frame' },
          { icon: isPlaying ? 'pause' : 'play_arrow', action: togglePlay, title: 'Play/Pause' },
          { icon: 'navigate_next', action: () => stepFrame(1), title: 'Next frame' },
          { icon: 'skip_next', action: () => setPlayhead(totalFrames), title: 'Jump to end' },
        ].map(({ icon, action, title }) => (
          <button key={icon} onClick={action} title={title}
            style={{
              width: 28, height: 28,
              background: icon === (isPlaying ? 'pause' : 'play_arrow') ? 'var(--md-primary-container)' : 'transparent',
              color: icon === (isPlaying ? 'pause' : 'play_arrow') ? 'var(--md-on-primary-container)' : 'var(--md-on-surface-variant)',
              border: icon === (isPlaying ? 'pause' : 'play_arrow') ? '1px solid var(--md-primary)' : '1px solid transparent',
              borderRadius: 4,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all var(--md-transition-fast)',
            }}
            onMouseEnter={(e) => { if (icon !== (isPlaying ? 'pause' : 'play_arrow')) (e.currentTarget as HTMLButtonElement).style.color = 'var(--md-on-surface)'; }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{icon}</span>
          </button>
        ))}
        {/* Loop */}
        <button onClick={() => setLoop(!loop)} title="Toggle loop"
          style={{
            width: 28, height: 28, marginLeft: 4,
            background: loop ? 'rgba(76,215,246,0.15)' : 'transparent',
            color: loop ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
            border: loop ? '1px solid rgba(76,215,246,0.4)' : '1px solid transparent',
            borderRadius: 4, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>repeat</span>
        </button>
      </div>

      {/* Center: Frame counter */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontFamily: 'var(--md-font-code-inline)',
        fontSize: 11,
        color: 'var(--md-on-surface-variant)',
        background: 'var(--md-surface-container-lowest)',
        padding: '4px 10px',
        borderRadius: 4,
        border: '1px solid var(--md-surface-container-highest)',
        minWidth: 200,
        justifyContent: 'center',
      }}>
        <span style={{ fontSize: 9, color: 'var(--md-outline)', textTransform: 'uppercase' }}>FR</span>
        <input
          type="number"
          min={0}
          max={totalFrames}
          value={currentFrame}
          onChange={(e) => setPlayhead(parseInt(e.target.value) || 0)}
          style={{
            width: 60,
            background: 'transparent',
            border: 'none',
            borderBottom: '1px solid var(--md-primary)',
            color: 'var(--md-primary)',
            fontFamily: 'var(--md-font-code-inline)',
            fontSize: 12,
            fontWeight: 700,
            textAlign: 'center',
            outline: 'none',
            padding: '0 4px',
          }}
        />
        <span style={{ color: 'var(--md-outline)' }}>/</span>
        <span style={{ color: 'var(--md-on-surface-variant)' }}>{totalFrames}</span>
        <span style={{ color: 'var(--md-outline)', margin: '0 4px' }}>|</span>
        <span style={{ color: 'var(--md-on-surface)', fontWeight: 600 }}>{fmtFrame(currentFrame)}</span>
      </div>

      {/* Right: Volume + Rate */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--md-outline)' }}>volume_up</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={volume}
          onChange={(e) => setVolume(parseFloat(e.target.value))}
          style={{ width: 80 }}
        />
        <div style={{ display: 'flex', background: 'var(--md-surface-container-lowest)', border: '1px solid var(--md-surface-container-highest)', borderRadius: 4, overflow: 'hidden' }}>
          {([0.5, 1, 2] as const).map((r) => (
            <button key={r} onClick={() => setPlaybackRate(r)}
              style={{
                padding: '2px 8px',
                background: playbackRate === r ? 'var(--md-surface-container-high)' : 'transparent',
                color: playbackRate === r ? 'var(--md-primary)' : 'var(--md-on-surface-variant)',
                border: 'none',
                fontSize: 10,
                fontFamily: 'var(--md-font-code-inline)',
                cursor: 'pointer',
              }}>
              {r}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
