import { useState, useRef, useCallback } from 'react';
import { useAppStore } from '../../store';
import type { Clip } from '../../types';

const LUTS = [
  'Teal_Orange_Commercial_v2.cube',
  'Nordic_Neutral_Product.cube',
  'Monochrome_HighContrast.cube',
];

interface WheelState {
  lift: { x: number; y: number };
  gamma: { x: number; y: number };
  gain: { x: number; y: number };
}

function ColorWheel({
  label,
  sublabel,
  offset,
  onChange,
}: {
  label: string;
  sublabel: string;
  offset: { x: number; y: number };
  onChange: (off: { x: number; y: number }) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    dragging.current = true;
    move(e.nativeEvent);
    const onMove = (ev: PointerEvent) => move(ev);
    const onUp = () => { dragging.current = false; document.removeEventListener('pointermove', onMove); document.removeEventListener('pointerup', onUp); };
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
  }, [onChange]);

  const move = useCallback((ev: PointerEvent) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    let x = (ev.clientX - cx) / (rect.width / 2);
    let y = (ev.clientY - cy) / (rect.height / 2);
    const dist = Math.sqrt(x * x + y * y);
    if (dist > 1) { x /= dist; y /= dist; }
    onChange({ x, y });
  }, [onChange]);

  const r = (offset.x * 80).toFixed(2);
  const g = (offset.y * 60).toFixed(2);
  const b = ((-offset.x - offset.y) * 40).toFixed(2);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8899a6' }}>{label}</span>
      <span style={{ fontSize: 8, color: '#556', fontFamily: 'var(--md-font-code-inline)' }}>{sublabel}</span>
      <svg ref={svgRef} width={80} height={80} onPointerDown={handlePointerDown} style={{ cursor: 'crosshair', touchAction: 'none' }}>
        <defs>
          <radialGradient id={`wg-${label}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#1a1a2e" />
            <stop offset="100%" stopColor="#0a0a10" />
          </radialGradient>
          <radialGradient id={`gl-${label}`} cx="35%" cy="35%" r="60%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.08)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
        </defs>
        <circle cx={40} cy={40} r={38} fill={`url(#wg-${label})`} stroke="var(--md-surface-container-highest)" strokeWidth={1} />
        <circle cx={40} cy={40} r={38} fill={`url(#gl-${label})`} />
        {/* Hue rings */}
        <circle cx={40} cy={40} r={30} fill="none" stroke="rgba(76,215,246,0.15)" strokeWidth={8} strokeDasharray="2 4" />
        <circle cx={40} cy={40} r={20} fill="none" stroke="rgba(255,184,115,0.12)" strokeWidth={6} strokeDasharray="1 5" />
        {/* Puck */}
        <circle
          cx={40 + offset.x * 34}
          cy={40 + offset.y * 34}
          r={5}
          fill="var(--md-primary)"
          stroke="#0e0e11"
          strokeWidth={1.5}
          style={{ pointerEvents: 'none' }}
        />
      </svg>
      <div style={{ fontSize: 9, fontFamily: 'var(--md-font-code-inline)', color: '#4cd7f6', display: 'flex', gap: 6 }}>
        <span>R{r}</span><span>G{g}</span><span>B{b}</span>
      </div>
    </div>
  );
}

export default function ColorGradingPanel() {
  const { selectedClipId, updateClip, timeline } = useAppStore();
  const clip = timeline?.clips.find((c: Clip) => c.id === selectedClipId) ?? null;
  const [wheels, setWheels] = useState<WheelState>({
    lift: { x: 0, y: 0 },
    gamma: { x: 0, y: 0 },
    gain: { x: 0, y: 0 },
  });
  const [lut, setLut] = useState(LUTS[0]);
  const [temp, setTemp] = useState(5600);

  const applyWheel = useCallback((key: keyof WheelState, off: { x: number; y: number }) => {
    setWheels((prev) => ({ ...prev, [key]: off }));
    if (clip) {
      updateClip(clip.id, {
        color_grade: JSON.stringify({
          ...wheels,
          [key]: off,
          lut,
          temperature: temp,
        }),
      });
    }
  }, [clip, updateClip, wheels, lut, temp]);

  const handleReset = () => {
    setWheels({ lift: { x: 0, y: 0 }, gamma: { x: 0, y: 0 }, gain: { x: 0, y: 0 } });
    setLut(LUTS[0]);
    setTemp(5600);
    if (clip) updateClip(clip.id, { color_grade: null });
  };

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
        <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)' }}>Color Grading & Wheels</span>
        <span style={{
          fontSize: 8, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
          background: 'rgba(76,215,246,0.15)', color: 'var(--md-primary)',
          fontFamily: 'var(--md-font-code-inline)', letterSpacing: '0.04em',
        }}>ACEScc Color Space</span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {/* Wheels */}
        <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 14 }}>
          <ColorWheel label="Lift" sublabel="Shadows" offset={wheels.lift} onChange={(o) => applyWheel('lift', o)} />
          <ColorWheel label="Gamma" sublabel="Mids" offset={wheels.gamma} onChange={(o) => applyWheel('gamma', o)} />
          <ColorWheel label="Gain" sublabel="Highlights" offset={wheels.gain} onChange={(o) => applyWheel('gain', o)} />
        </div>

        {/* LUT selector */}
        <div style={{ marginBottom: 12 }}>
          <FieldLabel>Active 3D LUT</FieldLabel>
          <select
            value={lut}
            onChange={(e) => { setLut(e.target.value); if (clip) updateClip(clip.id, { color_grade: JSON.stringify({ ...wheels, lut: e.target.value, temperature: temp }) }); }}
            style={{ width: '100%' }}
          >
            {LUTS.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>

        {/* Temperature */}
        <div style={{ marginBottom: 4 }}>
          <FieldLabel>Color Temperature</FieldLabel>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 9, color: '#666', fontFamily: 'var(--md-font-code-inline)', minWidth: 36 }}>3200K</span>
            <input
              type="range"
              min={3200}
              max={8000}
              step={100}
              value={temp}
              onChange={(e) => {
                const v = parseInt(e.target.value);
                setTemp(v);
                if (clip) updateClip(clip.id, { color_grade: JSON.stringify({ ...wheels, lut, temperature: v }) });
              }}
              style={{ flex: 1 }}
            />
            <span style={{ fontSize: 9, color: '#666', fontFamily: 'var(--md-font-code-inline)', minWidth: 36, textAlign: 'right' }}>8000K</span>
          </div>
          <div style={{ textAlign: 'center', fontSize: 10, fontFamily: 'var(--md-font-code-inline)', color: 'var(--md-primary)', marginTop: 4 }}>
            {temp}K
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '8px 14px',
        borderTop: '1px solid var(--md-surface-container-highest)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 9, color: '#556', fontFamily: 'var(--md-font-code-inline)' }}>GPU: Metal 3 / Vulkan</span>
        <button
          onClick={handleReset}
          style={{
            background: 'transparent',
            border: '1px solid var(--md-surface-container-highest)',
            borderRadius: 4,
            color: '#8899a6',
            fontSize: 10,
            cursor: 'pointer',
            padding: '3px 8px',
            fontFamily: 'var(--md-font-code-inline)',
          }}
        >
          Reset Grades
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
