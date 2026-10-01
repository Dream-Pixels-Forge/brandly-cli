import type { PanelKind } from './types';

/** Panel display names.
 *
 *  Single source of truth shared by the sidebar nav and the Toolbar
 *  breadcrumb, so the breadcrumb can never drift from the nav labels.
 *  Lives in its own module (not a component file) per the
 *  `react/only-export-components` lint rule.
 */
export const PANEL_LABELS: Record<PanelKind, string> = {
  preview: 'Preview Player',
  timeline: 'Timeline Sequencer',
  asset_manifest: 'Asset Manifest',
  props: 'Props Inspector',
  color: 'Color Grading',
  audio: 'Audio Mixer',
  render: 'Render Queue',
  monitor: 'Production Monitor',
  review: 'Review Queue',
  agnes_ai: 'Agnes AI Synthesizer',
};

/** Keyboard-shortcut hints shown on each sidebar nav row (design §6). */
export const PANEL_SHORTCUTS: Record<PanelKind, string> = {
  preview: 'P',
  timeline: 'T',
  asset_manifest: 'A',
  props: 'I',
  color: 'C',
  audio: 'S',
  render: 'R',
  monitor: 'M',
  review: 'Q',
  agnes_ai: 'G',
};
