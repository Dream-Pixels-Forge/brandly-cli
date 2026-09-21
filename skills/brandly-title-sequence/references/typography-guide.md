# Title Sequence Typography Reference

Deep reference for selecting, pairing, and animating type in premium title sequences.

---

## Typography Anatomy for Titles

### Key Terms
- **x-height** — Height of lowercase letters; affects readability at distance
- **Cap height** — Height of uppercase letters; defines title presence
- **Tracking** — Overall letter spacing; wide = epic, tight = urgent
- **Kerning** — Space between specific letter pairs; critical for logo/title treatment
- **Leading** — Line spacing; generous = luxurious, tight = intense
- **Counter** — Enclosed space within letters (o, e, a); affects visual weight
- **Stem** — Main vertical stroke; thick = bold presence, thin = elegant

### Screen-Specific Considerations
- **TV/Streaming:** Minimum 48pt equivalent for primary title at 1920×1080
- **Cinema:** Can go larger; 72pt+ equivalent at 4K
- **Mobile preview:** Title must be readable at 320px width (thumbnail test)
- **Overscan:** Keep critical type within 90% safe area

---

## Font Selection by Genre

### Sci-Fi / Futuristic
| Font | Weight | Why |
|------|--------|-----|
| **Space Grotesk** | Medium-ExtraBold | Geometric with quirky details |
| **Orbitron** | Bold-Black | Angular, digital feel |
| **Exo 2** | Semibold-Black | Modern tech aesthetic |
| **Rajdhani** | Medium-Bold | Squared, technical |
| **Saira** | ExtraBold-Black | Compressed, urgent |

**Pairing:** Space Grotesk (title) + JetBrains Mono (supporting)

### Thriller / Crime
| Font | Weight | Why |
|------|--------|-----|
| **Bebas Neue** | Regular | Condensed, commanding |
| **Oswald** | Bold | Authoritative, newspaper-headline energy |
| **DIN Alternate** | Bold | Industrial, cold precision |
| **Futura** | Bold-ExtraBold | Geometric menace (Kubrick used it) |
| **Anton** | Regular | Heavy, imposing |

**Pairing:** Bebas Neue (title) + Lato Light (supporting)

### Period Drama / Prestige
| Font | Weight | Why |
|------|--------|-----|
| **Playfair Display** | Bold-Black | High-contrast elegance |
| **Cormorant Garamond** | Semibold-Bold | Refined, literary |
| **Libre Baskerville** | Bold | Traditional authority |
| **Cinzel** | Regular-Bold | Classical, inscription feel |
| **IM Fell English** | Regular | Antique, hand-pressed character |

**Pairing:** Playfair Display (title) + Source Sans Pro Light (supporting)

### Horror / Gothic
| Font | Weight | Why |
|------|--------|-----|
| **Unifraktur Maguntia** | Regular | Blackletter dread |
| **Cinzel Decorative** | Regular | Ornate, unsettling beauty |
| **MedievalSharp** | Regular | Ancient, cursed text |
| **IM Fell Double Pica** | Regular | Decay and age |
| **Custom distressed** | — | Damage tells the story |

**Pairing:** Cormorant Garamond (title, distressed) + Inter (supporting, clean contrast)

### Comedy / Light
| Font | Weight | Why |
|------|--------|-----|
| **Nunito** | ExtraBold-Black | Rounded warmth |
| **Quicksand** | Bold | Friendly geometry |
| **Baloo 2** | ExtraBold-Black | Playful bounce |
| **Fredoka** | Medium-Bold | Cheerful roundness |
| **Righteous** | Regular | Retro fun without being kitsch |

**Pairing:** Quicksand Bold (title) + Nunito Sans Regular (supporting)

### Documentary / Non-Fiction
| Font | Weight | Why |
|------|--------|-----|
| **Merriweather** | Bold | Trustworthy serif |
| **Lora** | Bold | Journalistic authority |
| **IBM Plex Sans** | Semibold-Bold | Modern institutional |
| **Source Serif Pro** | Semibold-Bold | Academic credibility |
| **PT Serif** | Bold | International, serious |

**Pairing:** Merriweather Bold (title) + IBM Plex Sans Regular (supporting)

---

## Title Animation Patterns

### 1. Letter-by-Letter Reveal (The Alien)
**How:** Each character appears sequentially, not in reading order
**Timing:** 80-120ms per letter with variable gaps
**Easing:** Smooth cubic-bezier (0.4, 0, 0.2, 1)
**Best for:** Mystery, tension, atmosphere
**AE technique:** Text animator > Range Selector > Randomize Order

### 2. Mask Wipe (The Bond)
**How:** Text revealed by animated mask following a shape or path
**Timing:** 1.5-3s for full title
**Easing:** Punch ease for energy (0.34, 1.56, 0.64, 1)
**Best for:** Action, confidence, forward momentum
**AE technique:** Track matte > Shape layer animated with Trim Paths

### 3. Blur-to-Focus (The Dream)
**How:** Text starts heavily blurred, sharpens into clarity
**Timing:** 1-2s blur reduction
**Easing:** Exponential (starts fast, slows dramatically)
**Best for:** Memory, revelation, awakening
**AE technique:** Camera Lens Blur > Animate blur from 50 to 0

### 4. Scale + Settling (The Impact)
**How:** Text scales from oversized, overshoots, settles into position
**Timing:** 0.8-1.2s total
**Easing:** Elastic bounce (0.68, -0.55, 0.265, 1.55)
**Best for:** Bold statements, energy, confidence
**AE technique:** Scale keyframes with overshoot, or use Motion 4 preset

### 5. Assembly from Fragments (The Puzzle)
**How:** Letterforms assemble from scattered pieces
**Timing:** 2-4s assembly
**Easing:** Variable — fragments move slowly, then snap fast
**Best for:** Mystery solving, construction, complexity
**AE technique:** Split text into segments, animate position/rotation

### 6. Environmental Emergence (The World)
**How:** Text emerges from or integrates with environment/scene
**Timing:** 3-6s (longer, more cinematic)
**Easing:** Smooth, cinematic — barely perceptible motion
**Best for:** World-building, immersion, atmosphere
**AE technique:** 3D camera, text in scene space, parallax layers

---

## Typography Mistakes to Avoid

| Mistake | Why It Fails | Fix |
|---------|-------------|-----|
| **Using default system fonts** | Feels cheap, unconsidered | Pick a distinctive display font |
| **Too many typefaces** | Visual chaos, no hierarchy | Max 2 fonts: 1 display + 1 neutral |
| **Poor kerning on title** | Looks amateurish immediately | Manual kern every letter pair |
| **Ignoring screen size** | Beautiful on desktop, unreadable on TV | Test at target resolution |
| **Trendy over timeless** | Dates the production quickly | Classic proportions > current fads |
| **No weight contrast** | Hierarchy unclear | 2-3 weight steps between primary/supporting |
| **Centering everything** | Static, boring | Try asymmetrical composition |

---

## Font Licensing for Title Sequences

### Free (OFL/Apache)
- Google Fonts library — 1500+ families, commercial use allowed
- Font Squirrel — Curated free fonts, all commercially licensed
- Fontshare (Indian Type Foundry) — Premium quality, free

### Paid (Per-Project)
- MyFonts — Per-project licenses, massive library
- Fontspring — Perpetual licenses, no subscriptions
- Adobe Fonts — Included with Creative Cloud (check license terms)

### Custom Lettering
- Commission type designer for unique title treatment
- Own the letterforms — no licensing issues
- Becomes part of the production's IP
- Cost: $2,000-$15,000+ depending on complexity

---

## Quick Selection Flowchart

```
What's the genre/mood?
├── Epic/Iconic → Geometric Sans (Futura, Bebas Neue) at heavy weight
├── Elegant/Prestige → Didone Serif (Playfair Display, Bodoni)
├── Mysterious/Dark → Display Serif with distressing (Cormorant Garamond)
├── Tech/Sci-Fi → Geometric怪诞 (Space Grotesk, Orbitron)
├── Urgent/Thriller → Condensed Sans (Bebas Neue, DIN Condensed)
├── Warm/Human → Humanist Sans (Gill Sans, Optima)
└── Personal/Intimate → Handwritten/Script (custom lettering preferred)

Then pair with:
├── If primary is distinctive → Supporting should be neutral (Inter, Source Sans)
├── If primary is heavy → Supporting should be light (2-3 weight steps)
└── If primary is ornate → Supporting should be simple (no competing character)
```
