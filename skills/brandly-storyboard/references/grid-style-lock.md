# STORYBOARD STYLE LOCK — MANDATORY

Status: **MANDATORY / STRICT** for 4x4 grid storyboards generated via `brandly image`.
Applies to: any multi-frame contact-sheet storyboard. Single-frame workflows are unaffected.
Any change to this document requires explicit maintainer sign-off.

## Why this file exists

The first two attempts at a 4x4 storyboard grid came out wrong. Root cause was NOT grid
difficulty — it was that `brandly image` silently rewrote the prompt (see Issues filed).
The approved look must therefore be reproduced by *disciplined construction*, not by
re-rolling a single mega-prompt and hoping.

## The approved look (user-approved, do not reinterpret)

- Hand-drawn **graphite pencil** film storyboard, on **white paper**.
- Loose, confident linework; **light grey hatching**.
- Exactly **one** muted **gold-amber wash** accent per frame.
- Contact-sheet layout: **16 separate rectangular frames**, 4 columns x 4 rows.
- All frames identical in size and shape, thin white border, clean white gutter,
  grid filling the image edge to edge.
- Read order: left to right, top to bottom (F1..F16).
- **NO text, NO lettering, NO numbers, NO captions, NO labels** anywhere in the image.

## Character continuity rule (hard requirement)

The same gaunt male prospector — miner's headlamp harness, dark ragged clothing — appears
in every frame with **the same face and same silhouette throughout**. A grid that loses
character identity between panels is a FAILED grid, even if every panel is otherwise good.

## F1..F16 canonical content (do not reorder)

| Cell | Beat |
|---|---|
| F1 | wide scorched crater plain at dawn, tiny figure walking toward a mine mouth |
| F2 | close-up of a dirty thumb wiping grit from a bent iron sign on rock |
| F3 | black mine shaft, one hard headlamp beam cutting through thick dust |
| F4 | extreme close-up of a frozen circuit wafer inside clear mineral |
| F5 | wide, shaft opens into a vast chamber full of drifting glowing motes |
| F6 | close-up of a forearm, golden veins of light rising under the skin |
| F7 | wide, narrow corridor, liquid gold running along the ceiling |
| F8 | medium, man facing a black mirror wall, skeletal reflection with gold eyes |
| F9 | extreme wide, colossal cathedral cavern, tiny figure beside a black mirror pool |
| F10 | low angle, pool erupting into a vortex of molten gold forming a sphere |
| F11 | low dutch angle, towering deer-like molten gold beast lunging across black rock |
| F12 | wide, same beast with huge branching antlers, fragments feeding into it |
| F13 | low angle wide, man soaring in a high arc over the beast's antlers |
| F14 | frozen moment, golden droplets suspended in air around a man |
| F15 | wide, mine mouth breathing amber light across a plain at dawn |
| F16 | close-up of the bent iron sign at the entrance, face blank and rusted |

## Construction method (mandatory, learned the hard way)

Do NOT ask one model call to emit 16 frames. Instead:

1. Generate each frame as its **own single-frame image** (text-to-image, 16:9).
2. Style every frame prompt with the SAME style preamble from this document.
3. Tile the 16 single frames into the 4x4 contact sheet **locally in code** (PIL).

Reason: multi-frame generation drifts cell-to-cell and cannot guarantee a strict grid.
Local tiling is deterministic and guarantees the layout spec above.

## Style preamble (reusable verbatim)

```
A hand-drawn film storyboard panel in rough graphite pencil on white paper.
Loose confident linework, light grey hatching, a single muted gold-amber wash accent.
Clean white paper background. No text, no lettering, no numbers, no captions, no labels.
```
