---
name: "brandly-continuous-action-film"
description: "61-category action prompt engineering for AI video. Transforms shotlists, scripts, scenes, keyframes into model-tuned prompts — the grammar transfers across models, and brandly-cli executes them on Agnes via `brandly video` / `brandly produce` (production plan, 1 request/minute, Scene-XX-Shot-X-Y clip names). Covers core action, combat, documentary, commercial, sports, genre/art. Each category has camera signature, beat structure, model grammar, continuity. Includes 3-clip chain for continuous-take ads, Director's Mindset (mise-en-scene, camera, choreography), Claude Prompting Skill Framework, Asset Compatibility Testing. Use when user provides shotlist/script/scene needing action prompts, model-optimized direction, or sequence continuation. Trigger on: action film, fight scene, combat, documentary, commercial, sport, car chase, heist, surreal, FPV. DO NOT USE FOR: dialogue-only, static products, title sequences (use brandly-title-sequence)."
---

# DPF Continue Action Film — 61-Category Action Prompt Engineering

Transform shotlists, scripts, scenes, and keyframes into **model-optimized action prompts** with cinematic-grade precision. This skill is the **action director's lens** — spanning combat, documentary, commercial, sport, genre, and experimental action.

> "Every frame is directed. Every category has its own physics, its own camera, its own grammar. This skill maps 61 action categories to every AI video model."

### What's New

- **Category 31B: Beverage Ingredient Explosion** — 3-clip chain for continuous-take product ads (Mboka Elengi case study)
- **Director's Mindset** — Mise-en-scène, motivated camera, shooting script format, temporal choreography (from "Directing for the Latent Space")
- **Claude Prompting Skill Framework** — Dual-output workflow: save human-readable version for team/reference, generate model-optimized version for pasting into tools
- **Asset Compatibility Testing** — Test clip workflow + decision matrix to validate assets before locking
- **Vault References** — Cross-linked to Obsidian vault filmmaking knowledge

## Executing with brandly-cli

This skill writes the prompts; brandly-cli produces the film:

1. Write the shot list as JSON (flat array, or structured
   `{"character": ..., "acts": {...}}` with per-act `prefix`/`style`/`folder`
   and plate-stem `refs`) — see `brandly produce --help`.
2. Generate **one shot at a time** with
   `brandly produce <project_id> --shots shots.json` — shots register on the
   production plan, honour the 1 request/minute rate limit, and are resumable.
3. Clips land in `videos/scenes/` named `Scene-<scene:02d>-Shot-<scene>-<n>.mp4`;
   transition shots (`"folder": "transition"`) move to `videos/transition/`.
4. Gate questionable takes with `brandly gate <project_id> <clip>` and redo
   single shots with `--only <shot-id>`.
5. Assemble with `brandly stitch`.

The per-category **model grammar** (Hailuo/Kling/Veo phrasing) is prompt
craft — brandly's Agnes backend takes the plain cinematic prompt, so drop the
vendor-specific bracket syntax when generating through the CLI.

---

## Quick Start

| User Provides            | What You Get                                          |
| ------------------------ | ----------------------------------------------------- |
| **Shotlist**             | Shot-by-shot action prompts, model-optimized          |
| **Script**               | Beat-by-beat action breakdown with prompt chains      |
| **Scene description**    | Single prompt matched to the closest of 60 categories |
| **Shot-keyframes**       | Image-to-video action prompts with continuity         |
| **"Continue this shot"** | Continuation prompt matching existing style/momentum  |

### The Flow

```
User input → 1. IDENTIFY (match to 1 of 60 categories) → 2. SELECT MODEL → 3. BUILD PROMPT → 4. CONTINUITY CHAIN → Output
```

---

## Categories 1–20: Core Action (Full Detail)

### Category 1: Continue FPV Oner — Macro Bullet-Time

**Signature:** Single continuous unbroken shot, FPV drone flight, macro detail, bullet-time interrupt, no cuts

**Reference DNA (Fae Battlefield / Serpent / Butterfly Chase):**

> single continuous shot, one take no cuts, cinematic FPV oner, photorealistic macro detail, anamorphic film look, cinematic lighting, professional color grading, sharp focus, hyper-detailed texture, film grain, depth of field mastery, fluid drone flight

**Camera DNA:** FPV presence flying nonstop and low through environment, weaving approach → bursting into clash → spiraling assault → macro bullet-time orbit → weaving back without pulling up.

| Model                | Tuning                                                                                             |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3**       | `[Tracking shot]` + `[Push in]` chained. "Fluid drone flight, no cuts." `--motion 7-8`             |
| **Kling 3.0**        | "Single continuous unbroken shot — absolutely no cuts, no transitions" as opening constraint.      |
| **Seedance 1.5 Pro** | First-frame of environment. "Continuous fluid camera motion, no cuts, no edits."                   |
| **Veo 3.1**          | Natural paragraph: "One continuous unbroken take. The camera flies..." Emphasize "unbroken" twice. |
| **Sora 2**           | Timecode the arc: "0-3s approach, 3-8s clash, 8-12s orbit, 12-15s weave out."                      |

**Continuity Chain:**

```
Carry over: flight speed, camera height, macro detail level, lighting direction
Prompt suffix: "Continuing the unbroken FPV flight. Same environment, altitude, macro detail — camera never stops moving."
```

---

### Category 2: Continue Combat — Slow Motion + Dynamic Camera

**Signature:** Multi-attacker combat, acrobatic precision, freeze-frame beats, dynamic camera orbiting, slow-motion impacts

**Reference DNA (Ronin Blizzard Ambush):**

> 35mm anamorphic survival action cinema, glacial blue shadows, snow white, iron gray, pine black, weathered dark brown samurai armor, torn crimson scarf as sole color anchor. Lone armored ronin survives multi-attacker ambush through impossible acrobatic precision — never struck, every counterattack immediate and final.

**Beat Structure:**

```
1. STANCE — Wide, coiled. Low-angle.
2. ERUPTION — Attackers from 4 vectors simultaneously.
3. LAUNCH — Hero explodes upward. Weapons cross beneath.
4. COUNTER 1 — Airborne sweep.
5. TRANSITION — Land, wall-run.
6. COUNTER 2 — Corkscrew cut.
7. RESET — Handspring. Land in guard.
8. FINISH — Final strike, freeze on impact.
```

| Model          | Tuning                                                                                    |
| -------------- | ----------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Pan left]`, `[Tilt up]`, `[Push in]` for vectors. `[Shake]` on impact. `--motion 6`     |
| **Kling 3.0**  | Best realistic human motion. "Tight vertical flip", "corkscrews upside down through air." |
| **Veo 3.1**    | Full choreography prose. Audio: impact SFX, snow crunch, blade ring.                      |

**Continuity Chain:**

```
Carry over: combatant positions, wound states, weapon trajectories, blood/snow marks, lighting
Prompt suffix: "Continuing combat. Same fighters, wounds, environment, color palette. Blood marks and body positions match."
```

---

### Category 3: Continue Action Handheld

**Signature:** Raw handheld camera, urgent shake, documentary-style kinetics, crowd/chaos, fast snap pans

**Reference DNA (Harbor Evacuation):**

> Sweeping wide shot of vast crowd flooding across harbor dock toward ships, cranes looming. Handheld camera through the crush with urgent shake, snapping from people hauling bags to ropes snapping to gulls scattering. Cold steel grays and weathered timber, dense large-scale momentum.

**Camera DNA:** Handheld + shake, wide lens, snap pans, documentary urgency, dense momentum.

| Model          | Tuning                                                                     |
| -------------- | -------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Shake]` critical. `[Pan left/right]` abrupt. `--motion 7-8`              |
| **Kling 3.0**  | "Handheld with natural micro-jitter, documentary style, urgent snap pans." |
| **Veo 3.1**    | "Handheld documentary camera, urgent shake, snapping between subjects."    |

---

### Category 4: Continue Epic Scale Action

**Signature:** Sweeping aerial → ground chase → massive threat → low-angle hero → crane/orbit climax

**Reference DNA (Desert Worm Chase):** Aerial drift over dunes → warrior crests ridge → ground heaves → close-up reaction → sprint down dune → colossal worm breach → hero plants device, draws blade, camera orbits low as worm arcs overhead.

**Phasing:** 0-5s AERIAL CONTEXT → 5-10s THREAT EMERGENCE → 10-15s CLOSE ACTION

| Model          | Tuning                                                                                                  |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` aerial, `[Push in]` face, `[Pedestal up]` breach, `[Pan right]` orbit. `--motion 6-8` |
| **Kling 3.0**  | Strong physics for creature emergence. Anamorphic lens, hard golden low-sun key.                        |
| **Veo 3.1**    | Full audio: "Subterranean rumble → thunderous eruption → ragged breath → swelling score."               |

---

### Category 5: Continue Space/Aerial Battle

**Signature:** Vast scale, organic/asymmetric ships, handheld drift, plasma/energy weapons, debris fields

**Reference DNA (Organic Starfleet):** Colossal starfleets clash above ringed gas giant. Warships organic and asymmetrical — curved hulls like whale ribs, barnacled coral, bioluminescent seams pulsing as they fire. Ring-shaped fighters spin and bank through debris field.

| Model          | Tuning                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Shake]` + `[Tracking shot]`. "Organic biomechanical ships, bioluminescent seams, plasma arcs." |
| **Veo 3.1**    | Audio: "Low rumbling hum, crackling plasma, silence of void, muffled explosions."                |
| **Sora 2**     | Best for complex multi-element space scenes. Detail debris field physics.                        |

---

### Category 6: Continue Macro Body Horror / Tension

**Signature:** Extreme macro, single continuous take, fixed distance, handheld micro-jitter, transformation, escalating dread

**Reference DNA (Pupil Multiplication):** Single continuous shot, raw hand-held kinetic camera, extreme macro, ARRI ALEXA aesthetic. Eye fills frame entire unbroken take, fixed macro distance, no push-in. Single pupil tears into second, third, fourth — pulsing cluster of dark holes.

**Camera DNA:** Locked macro distance (no push-in/zoom), raw handheld micro-drift + jitter, subject transforms within frame, clinical contrast lighting.

| Model          | Tuning                                                                                 |
| -------------- | -------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Shake]` jitter. "Extreme macro, fixed distance, no zoom, no push-in." `--motion 3-4` |
| **Veo 3.1**    | Audio: "Low drone, shrill stabs, ragged breath, wet organic clicks as pupils split."   |

---

### Category 7: Continue Atmospheric Dark Fantasy

**Signature:** Slow deliberate movement, mood preservation, subtle animation, cinematic push-in, dark fantasy

**Reference DNA (Demon Warrior Temple):** Giant demon warrior slowly walks forward — heavy footsteps, subtle breathing, long hair moving in wind, eyes flickering softly, cloth and armor swaying, dust particles rising, torches flickering, mist drifting, clouds moving across moon, subtle camera push-in.

**Motion Settings:** Low–Medium (20–35%), 24fps, 5–8s. Avoid: rubber motion, exaggerated faces, fast walking, excessive particles.

| Model          | Tuning                                                                                         |
| -------------- | ---------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` slowly. `--motion 3-4`. "Subtle, slow, atmospheric, no sudden movement."           |
| **Kling 3.0**  | "Slow deliberate movement, heavy footsteps, subtle breathing, gentle hair/cloth motion."       |
| **Veo 3.1**    | Audio: "Distant wind, heavy slow footsteps on stone, crackling torch fire, low ambient drone." |

**MUST AVOID:** Rubber motion, exaggerated faces, fast walking, excessive particles, sudden shake, CGI eye glow.

---

### Category 8: Continue Crowd Mass Action

**Signature:** Vast crowd scale, urgent mass movement, environmental dread, wide → close detail → environmental reveal

**Reference DNA (Harbor Evacuation):** Shared with Category 3, emphasizing crowd scale over handheld technique.

```
[Wide/establishing] shot. [Crowd scale] flooding across [environment].
[Environmental elements]. Camera [handheld sweeping / static wide / orbit].
[Color palette]. Dense large-scale momentum. 16:9, [duration]s.
```

---

### Category 9: Continue Survival Chase

**Signature:** Hero vs colossal creature/environment, terrain traversal, point-of-no-return, weapon draw climax

**Beat Structure:**

```
1. REVEAL — Aerial terrain scale
2. CREST — Hero on ridge
3. HEAVE — Threat announces
4. REACT — Face close-up
5. SPRINT — Hero commits
6. BREACH — Threat erupts
7. PLANT — Hero stops, makes stand
8. DRAW — Weapon drawn, camera orbits
```

---

### Category 10: Continue Body Hardcore Combat

**Signature:** Brutal hand-to-hand, bone-breaking, grappling, blood spray, close-quarters visceral — no weapons, no acrobatics

**Reference DNA (Brutalist CQC):** 35mm anamorphic, raw handheld kinetic, shallow depth of field, muted earth/concrete palette. Two bodies locked in primal close-quarters — grappling, elbows, knees, headbutts. Every impact lands with real weight: skin splits, blood sprays in fine mist, sweat arcs, ribs compress. Ugly and desperate. Tight handheld orbits, shaking on impact, rack-focusing faces and impact points, never wider than medium.

**Beat Structure:** 1. CLINCH → 2. STRIKE EXCHANGE → 3. THROW → 4. GROUND FIGHT → 5. FINISH

| Model          | Tuning                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Shake]` every impact. `[Push in]` pre-strike. `[Pan left/right]` whip on throws. `--motion 7-8` |
| **Kling 3.0**  | "Ribs compress visibly on impact, sweat arcs off hair, skin splits, blood sprays."                |
| **Veo 3.1**    | Audio: "Heavy wet impacts, bone cracks, ragged breathing, flesh slaps, guttural grunts."          |

**Key Constraints:** NEVER wider than medium. NO acrobatics. Every impact lingers. Blood is restrained mist. Sound is half the violence. Environment is a weapon.

**Continuity Chain:**

```
Carry over: blood on faces/floor, torn clothing, swelling/bruising, sweat, exact positions
Prompt suffix: "Continuing same fight. Same combatants, injuries, blood marks. Sweat/swelling/torn clothing match. Never wider than medium."
```

---

### Category 11: Continue Mystical Combat

**Signature:** Magic duels, elemental attacks, rune casting, energy projection, spell circles, light-vs-dark energy

**Reference DNA (Wizard Duel):** Two sorcerers face across ancient stone chamber — shadow sorcerer with violet-black smoke, light sorcerer with golden mandalas spinning behind. Arcane symbols bloom in mid-air. Dark tendrils laced with violet lightning vs golden hexagonal shields. Shockwave of white fire. Both levitate, gather energy, release simultaneously — impact point erupts into swirling vortex, chamber trembling, glyphs peeling off walls.

**Camera DNA:** Slow majestic orbit (steady, not handheld), wide to medium, slow push-ins on casting gestures, crane up as energy rises, static wide on collision.

**Spell Visual Vocabulary:**
| Element | Visual | Palette | Motion |
|---------|--------|---------|--------|
| Fire | Flowing streams, expanding rings | Orange-crimson-gold | Fast, expanding |
| Ice | Crystalline shards, freezing mist | Cyan-white-blue | Sharp, geometric |
| Lightning | Crackling arcs, chain lightning | Electric violet-white | Erratic, jagged |
| Shadow | Tendrils, void spheres | Black-violet | Slow, coiling |
| Light/Holy | Radiant beams, golden shields | Gold-white-amber | Expanding, geometric |
| Nature | Vines, roots breaking stone | Emerald-lime | Organic, wrapping |
| Arcane | Floating symbols, rotating circles | Cyan-magenta | Geometric, rotating |

| Model          | Tuning                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Static shot]` spell charge, `[Push in]` gesture, `[Pedestal up]` energy rise. `--motion 5-6`         |
| **Kling 3.0**  | "Runes rotate in concentric circles. Energy tendrils coil and snap with real weight."                  |
| **Sora 2**     | "Runes ignite in sequence like dominoes of radiance. Glyphs peel off walls and spiral into maelstrom." |

**Key Constraints:** Camera is steady (not handheld). Lighting comes FROM spells. Runes must be specific (shape, rotation, color, glow). Energy has physics. Impact on environment. Color contrast between opposing forces.

**Continuity Chain:**

```
Carry over: spell residue, active runes, environmental damage, caster positions, energy auras
Prompt suffix: "Continuing mystical combat. Same casters, chamber, active spells, environmental damage. Energy residue and runes match. Lighting from spells consistent."
```

---

### Category 12: Continue Underwater Action

**Signature:** Submerged fight/chase, aquatic creatures, light caustics, suspended motion, drifting bubbles, weightlessness physics

**Camera DNA:** Fluid gliding motion, never static, orbits like a swimmer, gentle drift with currents, god rays passing through frame, caustic light patterns on subjects.

**Beat Structure:** 1. DESCENT → 2. ENGAGE → 3. STRUGGLE → 4. ESCAPE → 5. SURFACE/BREACH

**Underwater Physics:** "Hair floats in halo", "blood blooms in crimson clouds", "bubble trails follow strikes", "movements slowed by water resistance", "caustics dancing on skin", "god rays piercing from surface."

| Model          | Tuning                                                                                        |
| -------------- | --------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` fluid drift, `[Pan right]` slow orbit, `[Tilt up]` to surface. `--motion 5` |
| **Kling 3.0**  | "Underwater combat — water resistance slows every motion. Blood blooms, bubbles trail."       |
| **Veo 3.1**    | Audio: "Muffled underwater — whale calls, muffled impacts, rushing water, heartbeat."         |

**Key Constraints:** Water resistance slows everything. Blood blooms don't spray. Bubbles essential. Light from above only. Camera always in gentle motion. Sound is muffled.

**Continuity Chain:**

```
Carry over: blood clouds, bubble trails, floating debris, god ray angle, water clarity
Prompt suffix: "Continuing underwater. Same depth, god ray angle, water clarity. Blood clouds and bubble trails from prior movements persist."
```

---

### Category 13: Continue Vertical Combat

**Signature:** Cliff-side fighting, falling combat, aerial grappling, wall-running, gravity-defying acrobatics on vertical surfaces

**Camera DNA:** Hovering at combatant level, vertigo tilts (down to show abyss, up to show distance), orbit with void backdrop, slight wind shake, never cuts away from the height.

**Beat Structure:** 1. VERTIGO ESTABLISH → 2. LEDGE FIGHT → 3. FALL → 4. CATCH & RETURN → 5. WALL-RUN → 6. CLIMB EXCHANGE

| Model          | Tuning                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tilt down]` reveal abyss, `[Tilt up]` show cliff top, `[Tracking shot]` on wall-run. `--motion 6-7` |
| **Kling 3.0**  | "Sheer cliff face into mist. Wind whips hair. Rocks tumble into void. Camera hovers at ledge level."  |
| **Veo 3.1**    | Audio: "Wind howling past cliff, rocks echoing into void, strained breathing, fabric whipping."       |

**Key Constraints:** Show the void (tilt down twice minimum). Wind is a character. Rocks disappear into mist. Gravity pulls everything. Camera never leaves the height.

---

### Category 14: Continue Vehicle Chase

**Signature:** Car/bike/speeder pursuit, mounted creature chase, drifting, ramming, POV wheels, environmental weaving at high speed

**Camera DNA:** Multi-angle — low POV wheels, interior handheld shake, over-shoulder forward, external chase cam, wide drone, orbiting drift shots. Fast snap cuts within continuous action.

**Beat Structure:** 1. ESTABLISH → 2. CLOSE THE GAP → 3. RAM → 4. EVADE → 5. DRIFT → 6. OVERTAKE → 7. FINISH

| Vehicle Type     | Visual Cues                                             |
| ---------------- | ------------------------------------------------------- |
| Muscle Car       | Chrome, smoking tires, dust clouds, buckled metal       |
| Motorcycle       | Lean angles, knee-down, speed wobble, close wheel shots |
| Sci-Fi Speeder   | Neon trails, energy wake, holo-HUD, anti-grav sparks    |
| Mounted Creature | Galloping hooves, streaming mane, dust kicking          |
| Boat             | Wake trails, water spray, banking turns, wave jumping   |

| Model          | Tuning                                                                                          |
| -------------- | ----------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` alongside, `[Shake]` interior, `[Pan right]` drift orbit. `--motion 8-9`      |
| **Kling 3.0**  | "Low camera racing alongside spinning wheels. Metal buckles, sparks shower. Dust/smoke trails." |
| **Veo 3.1**    | Audio: "Engine roar, screeching tires, metal crunching, wind roar, gear shifts, bass rumble."   |

**Key Constraints:** Speed must be felt (motion blur, wind roar, vibration). Impacts have weight (metal buckles, sparks). Environment is obstacle course. Driver reactions essential. Never static camera.

---

### Category 15: Continue Sniper/Precision Action

**Signature:** Long-range targeting, scope view, stealth approach, tension buildup, single lethal shot, bullet trajectory in slow motion

**Camera DNA:** Wide establishing → interior shadow hide → POV scope → extreme CU eye → slow-mo bullet flight → impact → real-time aftermath. Camera IS the bullet for flight sequence.

**Beat Structure:** 1. ENVIRONMENT → 2. HIDE → 3. SCOPE POV → 4. SQUEEZE → 5. FLIGHT (slow-mo) → 6. IMPACT → 7. AFTERMATH

| Model          | Tuning                                                                                                                  |
| -------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` slow on eye, `[Static shot]` scope, `[Zoom in]` impact. `--motion 2-3` stillness, 7 draw                    |
| **Kling 3.0**  | "Crosshairs drifting with heartbeat. Bullet leaves barrel — shockwave ring. Visible distortion trail."                  |
| **Veo 3.1**    | Audio: "Slow breathing, heartbeat, trigger mechanism, deafening blast, supersonic whip, distant echo, ringing silence." |

**Key Constraints:** Patience is tension. Scope POV essential. Bullet flight is payoff. Sound travels slower than bullet (impact first, gunshot arrives later). Sniper's body tells story.

---

### Category 16: Continue Parkour/Free-Run

**Signature:** Urban traversal, rooftop vaulting, environmental fluidity, wall-running, cat-leap precision, momentum never breaking

**Camera DNA:** Running alongside traceur (steadicam fluidity), drops with them, tilts up on wall-runs, follows through rolls, vertigo tilt on gap jumps showing street below, never cuts, never stops.

**Beat Structure:** 1. SPRINT → 2. GAP JUMP → 3. WALL-RUN → 4. CAT-LEAP → 5. VAULT → 6. DROP → 7. ROLL → 8. CONTINUE

| Model          | Tuning                                                                                                  |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` alongside, `[Tilt down]` gap jump, `[Tilt up]` wall-run. `--motion 8-9`               |
| **Kling 3.0**  | "Fluid urban traversal. Landing roll converts impact into forward momentum. Camera moves with traceur." |
| **Veo 3.1**    | Audio: "Rhythmic footfalls, heavy breathing, wind rush on jumps, impact grunts, city ambience."         |

**Key Constraints:** Momentum never breaks. Show stakes (vertigo tilt every gap). Environment is the playground. Camera IS parkour. Sound is rhythm.

---

### Category 17: Continue War/Battlefield

**Signature:** Mass military combat, trench warfare, formations, artillery, explosions, tactical movement, epic destruction

**Camera DNA:** Handheld running alongside soldiers, concussion shake on explosions, tilt-up on incoming shells, snap to individual moments, wide drone for scale, never clean/smooth.

**Beat Structure:** 1. ESTABLISH → 2. WHISTLE → 3. CROSSING → 4. CONTACT → 5. BREACH → 6. AFTERMATH

| Model          | Tuning                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Shake]` every explosion, `[Tracking shot]` running, `[Tilt up]` shells. `--motion 7-8`         |
| **Kling 3.0**  | "Geysers of mud and shrapnel. Camera jolts with concussions. Men fall — the line keeps moving."  |
| **Sora 2**     | "Wave of soldiers climbing out of trenches across mile-wide front. Shells detonate in sequence." |

**Key Constraints:** Never glorify. Sound is overwhelming and constant. Camera in the fight. Scale through individuals. Color desaturated — fire and blood only warm tones.

---

### Category 18: Continue Kaiju/Creature Battle

**Signature:** Giant monster vs monster, city destruction, scale contrast with tiny humans, primal savagery, debris rain, massive impacts

**Camera DNA:** Human-scale perspective emphasizing size — low-angle tilting up, ground-level chaos with debris rain, aerial for geography, shockwave rings from above, never aestheticizing.

**Beat Structure:** 1. REVEAL → 2. ADVANCE → 3. CHALLENGER → 4. CLASH → 5. EXCHANGE → 6. FALLOUT

**Scale Techniques:** Low-angle tilt up, debris rain at human scale, fleeing crowd between footsteps, slow-motion building collapse, shockwave rings from above, water displacement on emergence.

| Model          | Tuning                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Tilt up]` slowly up creature, `[Pedestal up]` emergence, `[Static shot]` debris rain. `--motion 6-8` |
| **Kling 3.0**  | "Each footstep craters street. Shockwave blows out windows. Debris falls at human scale."              |
| **Sora 2**     | "Top half of skyscraper slides diagonally, collapsing in slow motion. Ship swung like bat."            |

**Key Constraints:** Always show human scale. Movements slow and heavy (mass has inertia). Debris is second weapon. Sound is sub-bass. Weather changes with creature presence.

---

### Category 19: Continue Escape/Breakout

**Signature:** Prison/structure escape, infiltration in reverse, collapsing environment, tight corridors, time pressure, improvised solutions

**Camera DNA:** Tight over-the-shoulder/POV, handheld shake, never wider than medium, every corner is suspense, environment degrades behind, red emergency lighting, smoke, chaos.

**Beat Structure:** 1. CELL BREACH → 2. CORRIDOR GAUNTLET → 3. RESISTANCE → 4. VERTICAL MOVEMENT → 5. OPEN GROUND → 6. TUNNEL/DUCT → 7. BREACH SURFACE

| Model          | Tuning                                                                                                               |
| -------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Shake]` running, `[Push in]` door breach, `[Pan left/right]` corners, `[Tracking shot]` tight behind. `--motion 8` |
| **Kling 3.0**  | "Tight handheld behind escapee. Red strobes. Smoke. Environment collapsing behind. Never wider than medium."         |
| **Veo 3.1**    | Audio: "Alarms, footsteps, explosions, shouting guards, gunfire, heavy breathing, collapsing concrete, steam."       |

**Key Constraints:** Claustrophobia is tone (never wider than medium until freedom). Environment is enemy. Every corner suspense. Exhaustion tells story. Sound overwhelming. Final exit earns wide pull-back.

---

### Category 20: Continue Duel/Showdown

**Signature:** One-on-one standoff, Western gunfight, samurai duel, eye-contact tension, stillness before explosion, single decisive moment

**Camera DNA:** Extreme wide (arena) → ECU eyes → ECU hands → wide (tension) → extreme slow-mo draw → bullet flight → impact → wide aftermath. Ceremonial precision.

**Duel Types:**
| Type | Weapons | Arena | Light | Tone |
|------|---------|-------|-------|------|
| Western | Revolvers | Dusty street, noon | Harsh overhead, no shadows | Stoic, fatalistic |
| Samurai | Katana | Bamboo grove / courtyard | Overcast / low sun | Honor, single cut |
| Sci-Fi | Energy pistols | Neon alley / station | Neon + fog + shadows | Tense, technological |
| Medieval | Longswords | Tournament ground | Golden hour, dust motes | Chivalric, brutal |
| Noir | Pistols | Rain-slicked rooftop | Single streetlamp | Desperate, intimate |

**Beat Structure:** 1. ARENA → 2. EYES → 3. HANDS → 4. RETURN → 5. THE MOMENT → 6. DRAW → 7. FLIGHT → 8. IMPACT → 9. AFTERMATH

| Model          | Tuning                                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Static shot]` wide, `[Push in]` slow on eyes, `[Push in]` ultra-fast on draw. `--motion 2` stillness, 7 draw     |
| **Kling 3.0**  | "Two figures motionless at opposite ends. ECU eyes — unblinking, sweat beading. Slow motion on the draw."          |
| **Veo 3.1**    | Audio: "Absolute silence. Wind. Tumbleweed. Heartbeat. Rustle of clothing. Deafening shot. Echo. Silence returns." |

**Key Constraints:** Stillness IS action. Eyes tell story. One decisive moment. Extreme slow-mo on critical beat. Sound: silence → violence → silence. Arena is a character.

---

## Categories 21–28: Documentary & Nature

### Category 21: Continue Wildlife Documentary

**Signature:** BBC/Attenborough-style animal behavior, patient observation, telephoto intimacy, natural habitat, predator-prey dynamics

**Camera DNA:** Long telephoto (300mm+) at animal eye-level, shallow DOF isolating subject from habitat, slow pans following movement, locked-off observation for behavior, no human presence visible.

**Quick Prompt Pattern:**

```
[Telephoto medium/close-up]. [Animal species] in [natural habitat: savannah/jungle/arctic].
[Behavior: hunting/grazing/nurturing/migrating]. [Time of day + weather].
Camera [static locked-off / slow pan following subject].
Natural light only — [golden hour/overcast/harsh midday].
Ultra-shallow depth of field — subject sharp, background melting into bokeh.
Photorealistic, National Geographic aesthetic. 24fps, natural color grade.
No human presence. No music. Natural ambient sound only. [Duration]s.
```

| Model          | Tuning                                                                                                     |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Static shot]` locked-off observation. `[Pan left/right]` slow animal tracking. `--motion 2-3`            |
| **Kling 3.0**  | Best for realistic animal motion. "Natural gait, real muscle movement under fur/skin, authentic behavior." |
| **Veo 3.1**    | Audio: "Natural ambient — wind, birds, insects, rustling grass. No music. No human sound."                 |

**Key Constraints:** No anthropomorphism. No human presence or structures. Natural light only. Telephoto compression. Behavior must be species-accurate. Patience — no rushed cuts.

---

### Category 22: Continue Underwater Documentary

**Signature:** Coral reef exploration, marine megafauna, deep-sea mystery, light rays, bioluminescence, drifting cinematography

**Camera DNA:** Fluid drifting camera (not diver POV), god rays from surface, slow majestic orbits around subjects, descent into blue, macro on reef detail, bioluminescent deep-sea glow.

**Quick Prompt Pattern:**

```
[Underwater wide/medium]. [Marine subject: coral reef / whale / shark / jellyfish / deep-sea creature].
[Environment: sunlit shallows / twilight zone / deep abyss].
Camera [slowly drifts / orbits / descends] with [current-like fluidity].
God rays piercing from surface. Light caustics dancing on [subject].
[Bioluminescent glow / natural reef colors / deep blue palette].
Natural underwater acoustics. No human divers in frame. 16:9, [duration]s.
```

| Model          | Tuning                                                                                         |
| -------------- | ---------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` fluid drift, `[Pan right]` orbits, `[Tilt down]` descent. `--motion 4-5`     |
| **Kling 3.0**  | "Weightless drift through water column. Marine life moves with natural grace. Caustics dance." |
| **Veo 3.1**    | Audio: "Muffled whale song, clicking dolphins, reef crackle, distant current, no music."       |

**Key Constraints:** Camera is invisible observer, not diver POV. No bubbles (rebreather aesthetic). Natural marine behavior only. Colors true to depth (reds fade at depth). Bioluminescence subtle, not neon.

---

### Category 23: Continue Macro Nature Documentary

**Signature:** Extreme close-up insects, flowers, fungi, time-lapse bloom, dewdrops, pollen, microscopic wonder

**Camera DNA:** Macro lens (100mm+), extreme shallow DOF, slow rack focus between planes, time-lapse for blooming/growth, static locked-off for tiny subjects, no wider than medium macro.

**Quick Prompt Pattern:**

```
Extreme macro close-up. [Subject: insect / flower / fungi / dewdrop / pollen].
[Environment: forest floor / meadow / jungle understory].
[Action: pollinating / blooming / crawling / unfolding].
Camera [locked-off macro / slow rack focus / subtle push-in].
Dewdrops glinting like glass. Pollen drifting as luminous motes.
Every [texture: petal vein / chitin ridge / spore / wing scale] razor-sharp.
Natural light — [dappled canopy / soft overcast / backlit golden].
Photorealistic macro, BBC Planet Earth aesthetic. Shallow DOF. [Duration]s.
```

| Model          | Tuning                                                                                                     |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Static shot]` macro locked-off. `[Push in]` slowly for growth. `--motion 2-3`                            |
| **Kling 3.0**  | "Hyper-detailed macro — every hair on insect leg, every vein in petal, dewdrops magnifying cells beneath." |
| **Veo 3.1**    | Audio: "Amplified micro-sounds — wing beats, mandible clicks, dripping dew, rustling. No music."           |

**Key Constraints:** No wider than macro. Natural subjects only (no CGI creatures). Time-lapse must feel organic. Sound is amplified micro-world. Scale is revealed through detail, not pull-back.

---

### Category 24: Continue Aerial Landscape Documentary

**Signature:** Drone cinematography over epic terrain, mountains, glaciers, forests, coastlines, revealing scale through movement

**Camera DNA:** High-altitude drone, slow majestic flight, reveals (flying over ridge to reveal valley), top-down patterns, low skimming over water/forest canopy, golden hour long shadows.

**Quick Prompt Pattern:**

```
Aerial drone shot. [Landscape: mountain range / glacier / forest / coastline / desert].
[Time of day: golden hour / blue hour / midday].
Camera [slowly flies forward / orbits / rises over ridge to reveal] [subject].
[Atmospheric elements: mist in valleys / cloud shadows / sun glitter on water / fog banks].
Epic scale emphasizing the grandeur of [landscape type].
Natural light. No human structures visible. Slow majestic movement. 16:9, [duration]s.
```

| Model          | Tuning                                                                                                     |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` forward flight, `[Pedestal up]` reveal, `[Pan right]` orbit. `--motion 4-5`              |
| **Kling 3.0**  | "Vast landscape revealed through slow drone flight. Mist in valleys. Cloud shadows moving across terrain." |
| **Veo 3.1**    | Audio: "Wind, distant eagle cry, silence of altitude, subtle ambient drone. No music."                     |

**Key Constraints:** Slow and majestic — no fast drone moves. Natural light only. No human structures visible (pure wilderness). Reveal through movement (fly over ridge → valley appears). Scale is the subject.

---

### Category 25: Continue Volcanic/Geological Documentary

**Signature:** Active volcanoes, lava flows, geothermal features, cave formations, tectonic drama, planet-scale forces

**Camera DNA:** Aerial over caldera (respecting heat), ground-level near lava flow (heat haze, glow), interior cave pans (headlamp/ambient), time-lapse of eruption cycle, extreme wide establishing volcanic landscape.

**Quick Prompt Pattern:**

```
[Wide/aerial/ground-level] shot. [Subject: erupting volcano / lava flow / geyser / ice cave / canyon].
[Geological action: eruption / flowing / steaming / crystallizing / eroding].
Camera [slowly orbits at safe distance / tracks alongside flow / static on vent].
[Lighting: lava glow under smoke / natural cave light / geothermal steam backlit].
[Colors: incandescent orange-red / obsidian black / sulfur yellow / ice blue].
Photorealistic. Raw power of planetary forces. [Duration]s.
```

| Model          | Tuning                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Pedestal up]` eruption rise, `[Tracking shot]` lava flow, `[Static shot]` vent. `--motion 4-5`            |
| **Kling 3.0**  | "Lava flows with real viscosity — cooling crust cracking, incandescent veins beneath. Ash plume billowing." |
| **Veo 3.1**    | Audio: "Deep earth rumble, lava crackle and hiss, explosive venting, falling rock, geothermal steam."       |

**Key Constraints:** Scale is geological — show human insignificance. Light should come from lava/geothermal. Smoke/ash/steam are atmospheric elements. Motion is slow and heavy (lava viscosity).

---

### Category 26: Continue Weather/Storm Documentary

**Signature:** Hurricanes, tornadoes, lightning storms, blizzards, monsoon, extreme weather as protagonist

**Camera DNA:** Wide establishing of storm structure, time-lapse cloud formation, handheld struggle against wind, lightning strike capture, aerial penetrating storm eye, ground-level chaos.

**Quick Prompt Pattern:**

```
[Wide/extreme/aerial] shot. [Storm type: hurricane / tornado / lightning / blizzard / monsoon].
[Environment responding: trees bending / ocean raging / structures straining / snow accumulating].
Camera [static witnessing / handheld struggling / aerial penetrating].
[Lighting: lightning flash / green sky / whiteout / dark threatening clouds / silver lining].
[Motion: wind-blown debris / rain horizontal / snow driving / waves crashing].
Raw power of nature. No human drama — the storm is the subject. [Duration]s.
```

| Model          | Tuning                                                                                                          |
| -------------- | --------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Shake]` wind struggle, `[Static shot]` lightning capture, `[Tracking shot]` storm movement. `--motion 6-8`    |
| **Kling 3.0**  | "Tornado funnel touching down — debris field rotating. Lightning branching across cloud base. Rain horizontal." |
| **Sora 2**     | Best for complex weather physics. "Hurricane eye wall — cloud structure, rain bands, ocean surface chaos."      |

**Key Constraints:** The storm is the protagonist — no human drama. Show scale (trees, structures for reference). Lightning timing must feel natural. Sound is overwhelming weather. No music — nature's own score.

---

### Category 27: Continue Arctic/Polar Documentary

**Signature:** Ice fields, glaciers calving, polar wildlife, aurora borealis, extreme cold atmosphere, pristine white-blue palette

**Camera DNA:** Wide establishing on ice expanse, slow pan across glacier face, underwater beneath ice, time-lapse aurora, ground-level with wildlife, everything in blue-white-cyan palette.

**Quick Prompt Pattern:**

```
[Wide/aerial/underwater] shot. [Subject: glacier / ice sheet / polar bear / penguin colony / aurora].
[Environment: arctic ice field / Antarctic coast / frozen tundra].
Camera [slowly pans across / tracks alongside / tilts up to] [subject].
[Lighting: midnight sun / aurora borealis / blue hour / ice-reflected light].
Palette: cyan, white, ice-blue, with [aurora green / penguin orange-beak] as accent.
Extreme cold atmosphere. Pristine and untouched. [Duration]s.
```

| Model          | Tuning                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Pan right]` across glacier, `[Tilt up]` to aurora, `[Tracking shot]` wildlife. `--motion 3-4`             |
| **Kling 3.0**  | "Glacier calving — massive ice sheet cracking, splintering, crashing into sea. Aurora rippling across sky." |
| **Veo 3.1**    | Audio: "Howling wind, ice cracking like thunder, distant animal calls, absolute silence between."           |

**Key Constraints:** Palette is ice — white, cyan, blue. Warmth only from wildlife. Show scale of ice. Aurora must feel alive (rippling, not static). Extreme cold is felt through atmosphere (breath fog, ice crystals in air).

---

### Category 28: Continue Time-Lapse Documentary

**Signature:** Day-to-night transitions, seasons changing, city life hyperlapse, natural growth, star trails, clouds racing

**Camera DNA:** Static locked-off, extreme patience, frame accumulates change, motion blur on moving elements, exposure ramping for day-to-night, hyperlapse movement through space.

**Quick Prompt Pattern:**

```
Time-lapse shot. Static locked-off camera. [Subject: city skyline / landscape / flower / night sky].
[Transformation: day-to-night / season change / growth / crowd flow / cloud formation].
[Duration compressed]: [hours/days/weeks] into [seconds].
[Lighting ramp]: [warm golden → cool blue → neon night / winter → spring bloom].
[Motion: clouds racing / stars trailing / shadows crawling / people flowing / plant unfurling].
Smooth exposure transition throughout. [Duration]s.
```

| Model          | Tuning                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Static shot]` locked-off. Describe the time compression: "hours compressed into seconds." `--motion 2`            |
| **Kling 3.0**  | "Day-to-night transition — shadows crawl across landscape, sky cycles through golden → blue → black → stars."       |
| **Veo 3.1**    | Audio: "Time-compressed ambience. Fading light. Rising then fading city noise. Returning birdsong. Natural rhythm." |

**Key Constraints:** Camera is static (locked-off). Transition must feel natural and gradual. Lighting ramp is crucial. Motion blur on moving elements. No sudden jumps.

---

## Categories 29–39: Creative Ads & Commercial

### Category 29: Continue Product Hero Commercial

**Signature:** Premium product reveal, rotating showcase on pedestal, macro detail of materials, dramatic lighting, satisfying motion

**Camera DNA:** Slow majestic orbit around product, macro push-in on textures/materials, crane reveal, dramatic rim light, clean dark or gradient background, satisfying mechanical motion (opening, clicking, unfolding).

**Quick Prompt Pattern:**

```
[Macro/medium/wide] shot. [Product] on [pedestal / clean surface / floating in space].
Camera [slowly orbits / pushes in / cranes up] revealing [key feature: texture / mechanism / finish].
[Lighting: dramatic rim light / soft product photography / gradient backdrop / specular highlights].
[Product details: brushed titanium / genuine leather / precision machining / sapphire crystal].
[Motion: rotating / opening / clicking into place / water beading on surface].
Premium commercial aesthetic, shallow DOF. Clean, aspirational. [Duration]s, 16:9.
```

| Model          | Tuning                                                                                                          |
| -------------- | --------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Pan right]` slow orbit, `[Push in]` macro detail, `[Pedestal up]` reveal. `--motion 3-4`                      |
| **Kling 3.0**  | "Product rotates on pedestal. Macro detail on brushed metal texture. Specular highlights glide across surface." |
| **Veo 3.1**    | Audio: "Satisfying click, soft whoosh, premium sound design, subtle ambient score, no dialogue."                |

**Key Constraints:** Product is the hero. Clean background only. Lighting must highlight materials. Motion is slow and deliberate. Sound design is premium (clicks, whooshes). No clutter.

---

### Category 30: Continue Fashion & Beauty Commercial

**Signature:** Runway walk, editorial portrait, fabric in motion, cosmetics application, model presence, aspirational aesthetic

**Camera DNA:** Tracking alongside runway walk, slow push-in on face (beauty), macro on fabric texture/flow, dynamic editorial angles, high-contrast fashion lighting, strong color grading.

**Quick Prompt Pattern:**

```
[Medium/close-up/tracking] shot. [Model description: age, look, expression] wearing [garment description].
[Environment: runway / studio / urban / natural].
Camera [tracks alongside / slowly pushes in / orbits].
[Fabric in motion: silk flowing / leather creasing / sequins catching light / chiffon billowing].
[Beauty detail: skin texture, makeup precision, catch-lights in eyes, hair movement].
[Lighting: high-contrast editorial / soft beauty dish / golden hour / neon accent].
Fashion editorial aesthetic. 35mm film look. Aspirational. [Duration]s.
```

| Model          | Tuning                                                                                                         |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` alongside model, `[Push in]` on face, `[Pan right]` fabric motion. `--motion 5-6`            |
| **Kling 3.0**  | Best for fabric physics. "Silk ripples with every step. Chiffon billows in breeze. Leather creases naturally." |
| **Veo 3.1**    | Audio: "Heels on runway, fabric rustle, camera shutter, ambient runway music, no dialogue."                    |

**Key Constraints:** Model is aspirational but human (real skin texture, not plastic). Fabric movement is the secondary subject. Lighting must flatter. Color grade is editorial, not natural. Movement is confident, not rushed.

---

### Category 31: Continue Food & Beverage Commercial

**Signature:** Cooking action, pouring shots, slow-mo splashes, steaming, sizzling, ingredient beauty, appetite appeal

**Camera DNA:** Macro on food surface/texture, slow-mo liquid pours, top-down plating, steam/smoke trails, sizzle close-ups, hero shot on final dish, warm appetizing lighting.

**Quick Prompt Pattern:**

```
[Macro/medium/top-down] shot. [Food/drink subject].
[Action: pouring / sizzling / steaming / being plated / being sliced / splashing].
Camera [slowly pushes in / top-down static / orbits the dish].
[Lighting: warm golden / soft diffused / dramatic backlight through steam].
[Appetite details: glistening surface / caramelized edge / condensation on glass / rising steam / dripping sauce].
Slow motion on [pour/splash/slice]. Warm inviting colors. Food photography aesthetic.
Shallow DOF on hero element. [Duration]s.
```

| Model          | Tuning                                                                                                                |
| -------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` on dish, `[Static shot]` top-down, `[Tilt down]` pour. Slow motion on splash. `--motion 3-4`              |
| **Kling 3.0**  | "Steam rises from hot dish. Sauce drips slowly. Liquid splashes in slow motion — droplets suspended. Sizzle visible." |
| **Veo 3.1**    | Audio: "Sizzle, pour, knife through crust, satisfying crunch, subtle appetite music. No dialogue."                    |

**Key Constraints:** Food must look appetizing (glistening, steaming, fresh). Colors warm and inviting. Slow motion on action moments. Steam and motion = life. Clean presentation. No cold/clinical lighting.

---

### Category 31B: Continue Product Burst — Beverage Ingredient Explosion

**Signature:** Frozen packshot comes alive — ingredients orbit, liquid splashes, bullet-time macro on product surface, continuous chain edited from 3 clips, no first-frame lock

**Reference DNA (Mboka Elengi Tropical Soda):**

> green metallic can with vibrant illustrated label, whole mangoes, halved passion fruit with visible seeds, gnarled ginger root knobs, red hibiscus flowers, water droplets and ice crystals suspended mid-air, dark emerald backdrop, rich tropical premium feel, deep green golden yellow mango orange passion fruit purple hibiscus red color palette

**Camera DNA:** Tracking chase behind tumbling ingredients → fast push-in on convergence collision → orbital bullet-time macro around frozen instant. Three distinct phases chained in post.

**Why T2V over I2V:** Locking the packshot as a first frame constrains Hailuo's motion generation — the model prioritizes preserving pixels over creating dynamic movement. Pure text-to-video lets the model hallucinate freely, producing richer physics, better liquid dynamics, and more natural ingredient orbits.

**Beat Structure (3-Clip Chain):**

```
CLIP 1 — THE CHASE (~5s)
Tracking shot from behind tumbling ingredients (mango, passion fruit,
ginger, hibiscus) as they spin and weave through a lush environment.
Erratic, kinetic, water trailing in crystalline arcs. Strong motion
blur, shallow DOF, bright natural light.

CLIP 2 — THE CATCH (~4s)
The product can bursts up on a geyser of sparkling water, intercepting
the tumbling ingredients mid-flight. Massive splash collision — water
exploding, ingredients slamming into can from all directions. Camera
pushes in fast on impact. Violent, satisfying, precise.

CLIP 3 — BULLET-TIME MACRO (~6s)
Extreme macro on can surface. Water frozen mid-explosion. Ingredients
suspended motionless at convergence point. Camera orbits slowly around
the frozen instant. Every droplet razor-sharp. Iridescent condensation,
powder particles frozen mid-flight. Hyper-detailed textures.

ALTERNATE CLIP 3 — HERO SETTLE (~6s)
Time gradually resumes — droplets fall, ingredients descend, splash
settles. Camera pushes out to wide hero composition. Product centered,
ingredients in balanced still-life. Clean finish.
```

| Model                | Tuning                                                                                                                                                                                       |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3**       | Clip 1: `[Tracking shot]` behind, `--motion 7-8`. Clip 2: `[Push in]` fast on impact, `--motion 8`. Clip 3: `[Orbital]` slow macro, `--motion 2-3`. No first-frame lock — pure T2V per clip. |
| **Kling 3.0**        | "Ingredients tumble with real weight and collision physics. Liquid splashes with viscosity. Macro detail on frozen droplets." Best for realistic ingredient physics and water simulation.    |
| **Seedance 1.5 Pro** | First-frame of environment only (not product). "Continuous fluid camera motion. Ingredients orbit with gravitational physics."                                                               |
| **Veo 3.1**          | Audio per clip: Clip 1 wind rush + tumbling. Clip 2 massive splash + impact. Clip 3 silence + subtle chime. Full audio design sells the chain.                                               |
| **Sora 2**           | Timecode: "0-5s chase, 5-9s collision, 9-15s bullet-time orbit." Best for complex multi-element physics (many ingredients + liquid simultaneously).                                          |

**Continuity Chain:**

```
Carry over across all 3 clips: exact product label/branding, ingredient
types and colors, lighting direction (golden key + cool green fill),
environment color palette, water droplet density, backdrop tone.

Clip 1→2 transition: Match motion direction — ingredients converging
toward camera at end of Clip 1, already colliding at start of Clip 2.

Clip 2→3 transition: Match the freeze moment — splash at peak in Clip 2,
frozen at peak in Clip 3.

Prompt suffix (Clip 2): "Same green metallic can, same tropical label,
same ingredients (mango, passion fruit, ginger, hibiscus), same emerald
backdrop, same golden key light. Continuity from previous chase shot."
Prompt suffix (Clip 3): "Same can, same ingredients frozen at convergence
point, same water splash frozen at peak, same lighting, same backdrop.
Bullet-time continuation of the collision."
```

**Key Constraints:**

- NEVER lock first frame to packshot reference — use pure T2V for all clips
- Each clip has ONE dominant camera move (tracking → push-in → orbital)
- Product label must be readable in at least one clip (Clip 3 macro)
- Ingredients must have real weight and collision physics — not floating
- Water/liquid must have viscosity and surface tension — not CG-smooth
- Color palette is locked: emerald green, golden yellow, mango orange, passion fruit purple, hibiscus red
- Clip transitions hidden by matching motion momentum — not hard cuts
- Bullet-time clip is the payoff — spend resolution budget here
- 3-clip chain edited in post reads as one continuous shot to viewer

**Single Prompt Fallback (if 3-clip not possible):**

```
One single continuous unbroken shot, no cuts, one fluid camera move,
16:9. [Product description]. [Ingredients] tumble and orbit through
[environment]. Camera [Tracking shot] from behind chasing ingredients,
then [Push in] fast as they converge on the can in a splash collision,
then slows into [Orbital] bullet-time macro around the frozen instant
— water droplets suspended, ingredients motionless, every texture
razor-sharp. [Lighting]. [Style]. ~10s.
```

> WARNING: Single-prompt version is hit-or-miss on Hailuo — model may not honor the 3-phase choreography. 3-clip chain is recommended.

---

### Category 32: Continue Automotive Commercial

**Signature:** Car on epic road, studio turntable, detail craftsmanship, driving dynamics, aspirational lifestyle

**Camera DNA:** Low tracking alongside on winding road, studio turntable orbit, macro on badge/stitching/materials, POV driver hands on wheel, drone following through landscape, golden hour hero.

**Quick Prompt Pattern:**

```
[Wide/tracking/macro/POV] shot. [Vehicle make/model] on [winding coastal road / mountain pass / studio].
Camera [tracks low alongside / orbits on turntable / pushes into detail / POV through windshield].
[Vehicle details: body lines catching light / wheel design / exhaust note visible / interior craftsmanship].
[Environment: golden hour coastal / autumn forest road / rain-slicked urban / clean studio].
[Driving dynamics: cornering / acceleration / braking / drifting].
Automotive commercial aesthetic. Anamorphic lens. Premium. [Duration]s.
```

| Model          | Tuning                                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Tracking shot]` low alongside, `[Pan right]` turntable orbit, `[Push in]` detail. `--motion 5-7`                 |
| **Kling 3.0**  | "Car carving through corner — body roll, suspension compressing, tires gripping. Reflections gliding across body." |
| **Veo 3.1**    | Audio: "Engine note, exhaust growl, tires on asphalt, gear shift, wind, subtle score."                             |

**Key Constraints:** Car is the hero — always sharp and prominent. Reflections and body lines must catch light. Driving must feel dynamic. Golden hour or dramatic sky. Studio shots: clean, rotating, premium.

---

### Category 33: Continue Travel & Tourism Commercial

**Signature:** Paradise beaches, city landmarks, cultural experiences, wanderlust, drone reveals, golden hour everywhere

**Camera DNA:** Drone reveal over destination, walking POV through market/street, wide establishing of landmark, intimate cultural moments, golden hour and blue hour predominance, people experiencing joy.

**Quick Prompt Pattern:**

```
[Wide/aerial/POV/medium] shot. [Destination: beach / city / mountain / cultural site].
[Experience: exploring / dining / swimming / hiking / cultural ceremony].
Camera [drones over / walks through / reveals / pans across].
[Atmosphere: golden hour warmth / tropical clarity / misty mountains / vibrant market].
[People: experiencing joy, authentic moments, not posed].
Travel and wanderlust aesthetic. Vibrant yet natural colors. Aspirational. [Duration]s.
```

| Model          | Tuning                                                                                             |
| -------------- | -------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` drone reveal, `[Pan right]` vista, `[Push in]` cultural detail. `--motion 4-5`   |
| **Kling 3.0**  | "Turquoise water lapping white sand. Palm fronds swaying. People walking shoreline. Golden light." |
| **Veo 3.1**    | Audio: "Waves, distant music, market chatter, birds, wind through palms, subtle wanderlust score." |

**Key Constraints:** Authentic not staged. Golden hour/blue hour predominance. People experiencing (not posing). Destination is hero. Colors vibrant but natural. Sound is sense of place.

---

### Category 34: Continue Tech & Gadget Commercial

**Signature:** Device unboxing, UI interactions, sleek product demo, precision engineering, satisfying clicks and animations

**Camera DNA:** Macro on materials (aluminum, glass, ceramic), slow pull-apart of components, UI screen interactions glowing, satisfying mechanical actions, dark studio with rim light, futuristic but warm.

**Quick Prompt Pattern:**

```
[Macro/medium/close-up] shot. [Device: phone / laptop / wearable / gadget].
[Action: unboxing / screen activating / being used / component revealed].
Camera [slowly pushes in / orbits / macro scans surface].
[Details: precision-machined edges / glass reflection / haptic feedback / UI glowing on face].
[Lighting: dark studio + rim light / clean white infinity / ambient screen glow].
Sleek, premium, futuristic. Satisfying mechanical precision. [Duration]s.
```

| Model          | Tuning                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Push in]` macro detail, `[Pan right]` surface scan, `[Static shot]` UI interaction. `--motion 3-4`   |
| **Kling 3.0**  | "Device unboxes — lid lifts, light catches machined edge. Screen activates, UI glows on user's face."  |
| **Veo 3.1**    | Audio: "Satisfying mechanical click, haptic buzz, UI sound design, premium whoosh, subtle tech score." |

**Key Constraints:** Precision is the aesthetic. Materials must look real (aluminum, glass, ceramic). UI interactions feel magical. Sound design is premium clicks and haptics. Clean, minimal backgrounds.

---

### Category 35: Continue Jewelry & Luxury Commercial

**Signature:** Gold, diamonds, gemstones, watches, extreme macro sparkle, light play on precious surfaces, vault aesthetic

**Camera DNA:** Extreme macro on gems (fire, brilliance, scintillation), slow rotation catching light, macro on precious metal texture, dramatic single-source lighting creating sparkle, dark luxurious backdrop.

**Quick Prompt Pattern:**

```
Extreme macro shot. [Jewelry piece: diamond ring / gold necklace / luxury watch].
[Detail: diamond facets catching light / gold brushing texture / sapphire crystal / pearl luster].
Camera [slowly rotates / orbits / pushes into macro detail].
[Lighting: dramatic single source creating fire and sparkle / soft gradient on metal / rim light on edges].
Diamonds catching light — fire (colored flashes), brilliance (white return), scintillation (sparkle).
Luxury aesthetic. Dark elegant backdrop. Premium materials. [Duration]s.
```

| Model          | Tuning                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Pan right]` slow rotation, `[Push in]` macro gem detail. `--motion 2-3`                                    |
| **Kling 3.0**  | "Diamond facets catch light — fire flashes in prismatic colors. Gold catches rim light along polished edge." |
| **Veo 3.1**    | Audio: "Elegant silence, subtle chime, soft premium score, the sound of precious metal against velvet."      |

**Key Constraints:** Light IS the subject — it must play on precious surfaces. Extreme macro on gems (see the facets). Dark backdrop makes sparkle pop. Slow, deliberate motion. Nothing looks cheap or plastic.

---

### Category 36: Continue Real Estate & Architecture Commercial

**Signature:** Drone flythrough, interior walkthrough, golden hour exterior, architectural details, lifestyle aspiration

**Camera DNA:** Drone approaching/revealing property, smooth interior walkthrough (gimbal), tilt-up on facade, detail shots of materials/finishes, golden hour exterior hero, lifestyle vignettes (pool, kitchen, view).

**Quick Prompt Pattern:**

```
[Drone/gimbal/wide/detail] shot. [Property: modern home / penthouse / resort / commercial].
Camera [approaches through drone flythrough / walks through interior / tilts up facade / pans view].
[Details: floor-to-ceiling windows / marble countertops / infinity pool / landscaped garden / city view].
[Lighting: golden hour exterior / natural daylight interior / twilight with interior lights glowing].
[Lifestyle: sunlight streaming through windows / breeze moving curtains / pool water sparkling].
Architectural photography aesthetic. Aspirational living. [Duration]s.
```

| Model          | Tuning                                                                                                          |
| -------------- | --------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` drone approach, `[Push in]` interior, `[Tilt up]` facade, `[Pan right]` view. `--motion 4-5`  |
| **Kling 3.0**  | "Sunlight streams through floor-to-ceiling windows. Curtains billow gently. Pool water sparkles in background." |
| **Veo 3.1**    | Audio: "Ambient luxury — birds, distant water, soft breeze, subtle lifestyle music. No voiceover."              |

**Key Constraints:** Property is the hero. Natural light preferred (golden hour exterior, daylight interior). Movement is smooth and cinematic (gimbal/drone). Lifestyle elements are subtle. No clutter.

---

### Category 37: Continue Perfume & Fragrance Commercial

**Signature:** Abstract sensuality, fluid dynamics, flower blooming, glass bottle beauty, ethereal movement, mood over product

**Camera DNA:** Abstract macro — liquid dynamics, smoke tendrils, flower petals unfurling, glass bottle catching light, fabric flowing, skin-close intimacy, dreamlike slow motion, sensual lighting.

**Quick Prompt Pattern:**

```
[Abstract/macro/dreamlike] shot. [Element: perfume bottle / flower blooming / liquid swirling / fabric flowing / skin].
[Action: glass catching light / petals unfurling / golden liquid pouring / silk rippling].
Camera [slowly drifts / macro pushes in / orbits dreamily].
[Lighting: soft golden glow / moody chiaroscuro / ethereal backlight / warm skin tones].
[Mood: sensuality, mystery, elegance, desire]. No literal product demo — mood first.
Slow motion throughout. Dreamlike atmosphere. [Duration]s.
```

| Model          | Tuning                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` slow on bottle, `[Tracking shot]` dreamy drift, `[Static shot]` flower blooming. `--motion 3-4`   |
| **Kling 3.0**  | "Golden liquid swirls in slow motion. Flower petals unfurl. Glass catches rim light. Silk ripples sensually." |
| **Veo 3.1**    | Audio: "Ethereal score. Soft breath. Liquid pour. Glass chime. Intimate whisper. No dialogue."                |

**Key Constraints:** Abstract and sensual over literal product demo. Slow motion throughout. Lighting is soft and moody. Fragrance is invisible — sell the feeling, not the liquid. Bottle is iconic detail, not the whole shot.

---

### Category 38: Continue Sports Brand Commercial

**Signature:** Athlete in peak action, sweat and determination, slow-mo muscle tension, motivational energy, product integration

**Camera DNA:** Dynamic action angles (low, tracking, POV), slow-mo on peak exertion, macro on sweat/texture/equipment, stadium/arena atmosphere, athlete portrait moments between action, high-contrast motivational lighting.

**Quick Prompt Pattern:**

```
[Action/portrait/detail] shot. [Athlete] performing [sport] at peak intensity.
Camera [tracks low alongside / pushes into face / POV action / orbits mid-move].
[Details: sweat flying / muscles tensing / shoe gripping surface / ball spinning / breath visible].
[Lighting: dramatic stadium / high-contrast training / golden hour outdoor / gritty gym].
[Emotion: determination, focus, triumph]. Slow motion on peak exertion.
Motivational sports aesthetic. Powerful. [Duration]s.
```

| Model          | Tuning                                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Tracking shot]` alongside, `[Push in]` on face, `[Shake]` impact. Slow motion on exertion. `--motion 6-8`        |
| **Kling 3.0**  | "Athlete at peak exertion — muscles tense, sweat flies in slow motion. Shoe grips surface. Determination in eyes." |
| **Veo 3.1**    | Audio: "Crowd roar, impact sounds, heavy breathing, motivational beat, swelling score."                            |

**Key Constraints:** Athlete is hero. Peak exertion in slow motion. Sweat, muscle, determination. Product is visible but secondary. Lighting is dramatic. Sound is motivational.

---

### Category 39: Continue Pharmaceutical & Healthcare Ad

**Signature:** Clean, hopeful, scientific but human, soft lighting, diverse patients, active lifestyle, medical credibility

**Camera DNA:** Warm natural light, slow intimate camera, diverse people in active life moments, scientific imagery (cells, molecules) as abstract b-roll, doctor-patient warmth, hopeful tone throughout.

**Quick Prompt Pattern:**

```
[Medium/wide/abstract] shot. [Subject: patient / family / doctor / active person / scientific visualization].
[Action: walking in nature / playing with children / consulting with doctor / abstract cellular animation].
Camera [slowly tracks / pushes in warmly / reveals lifestyle].
[Lighting: soft natural / warm golden / clean medical / abstract scientific glow].
[Emotion: hope, relief, vitality, trust]. Diverse, authentic people.
Clean healthcare aesthetic. Warm and human. [Duration]s.
```

| Model          | Tuning                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` warm on faces, `[Tracking shot]` lifestyle, `[Static shot]` medical moment. `--motion 3-4`      |
| **Kling 3.0**  | "Warm natural light. Diverse people in active, happy moments. Scientific visualization abstract and clean." |
| **Veo 3.1**    | Audio: "Warm score, natural ambience, gentle voiceover space, hopeful tone, no clinical coldness."          |

**Key Constraints:** Hopeful, not clinical. Diverse, authentic casting. Warm natural light. Scientific elements are abstract and beautiful. Active lifestyle over illness. Trust and humanity over technology.

---

## Categories 40–49: Sports & Athletics

### Category 40: Continue Extreme Sports

**Signature:** Wingsuit, base jump, big wave surfing, cliff diving, vertigo-inducing scale, adrenaline, GoPro POV

**Camera DNA:** POV helmet/chest mount, drone tracking from distance, ground-level scale shot (tiny human vs massive wave/cliff), slow-mo on apex of trick, vertigo tilts down showing height.

**Quick Prompt Pattern:**

```
[POV/aerial/wide] shot. [Extreme sport: wingsuit / base jump / big wave / cliff dive / free solo].
[Athlete] performing [specific action: flying through canyon / dropping into barrel / launching off cliff].
Camera [POV helmet mount / drone tracking / vertigo tilt down from cliff edge].
[Scale: tiny human against massive wave / canyon wall / mountain face].
Adrenaline, speed, vertigo. Natural light. [Duration]s.
```

| Model          | Tuning                                                                                                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` POV or drone follow, `[Tilt down]` vertigo. `--motion 8-9`                                      |
| **Kling 3.0**  | "Wingsuit flies through canyon — walls blurring past. Surfer drops into massive barrel — water curling overhead." |
| **Veo 3.1**    | Audio: "Wind roar, heart pounding, wave crash, breath, distant echo of canyon."                                   |

**Key Constraints:** Show scale (tiny human, massive environment). POV is immersive. Speed must be felt. Vertigo is intentional. No safety gear visible in POV (adds to thrill).

---

### Category 41: Continue Martial Arts Training

**Signature:** Dojo atmosphere, kata/forms, sparring, discipline, sweat and focus, tradition, respect between practitioners

**Camera DNA:** Wide establishing dojo, slow orbit during kata, handheld during sparring, macro on hands/feet/weapon, low-angle showing power, dust motes in light, traditional atmosphere.

**Quick Prompt Pattern:**

```
[Wide/medium/macro] shot. [Martial art: karate / kung fu / taekwondo / BJJ / Muay Thai].
[Practitioner] performing [kata / sparring / technique / training].
Camera [slowly orbits during form / handheld during sparring / macro on striking surface].
[Environment: wooden dojo / outdoor temple / modern gym].
[Atmosphere: dust motes in sunbeams / sweat on skin / focused expressions / gi fabric movement].
Discipline, tradition, focus. Not aggression — mastery. [Duration]s.
```

| Model          | Tuning                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Pan right]` slow orbit, `[Shake]` sparring impact, `[Push in]` focused face. `--motion 5-6`                 |
| **Kling 3.0**  | "Kata performed with precision — gi snapping on sharp movements. Sweat on focused face. Dust motes in light." |
| **Veo 3.1**    | Audio: "Kiai, breathing, feet on wooden floor, gi rustling, distant instruction, meditative silence."         |

**Key Constraints:** Discipline over violence. Technique over spectacle. Dojo atmosphere is sacred. Light through windows. Sweat and focus. Traditional not Hollywood.

---

### Category 42: Continue Football/Soccer Action

**Signature:** Stadium scale, goal moments, crowd energy, slow-mo kick, ball trajectory, celebration, dramatic lighting

**Camera DNA:** Wide stadium establishing, tracking alongside play, slow-mo on kick/strike, ball trajectory flight, goal line tech angle, crowd eruption, player celebration close-up.

**Quick Prompt Pattern:**

```
[Wide/tracking/slow-mo] shot. [Player/team] in [stadium/arena].
[Action: strike / save / tackle / header / celebration].
Camera [tracks alongside play / slow-mo on ball strike / orbits celebration].
[Ball physics: spinning / curving / net rippling].
[Atmosphere: floodlit pitch / rain / golden sunset / crowd color].
Crowd as living entity. Dramatic sports cinematography. [Duration]s.
```

| Model          | Tuning                                                                                                   |
| -------------- | -------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` play, `[Push in]` strike, slow-mo on goal. `--motion 7-8`                              |
| **Kling 3.0**  | "Ball curves through air — visible spin. Net ripples on impact. Player slides on knees — turf spraying." |
| **Veo 3.1**    | Audio: "Crowd roar, ball strike, net ripple, whistle, chant, swelling emotion."                          |

**Key Constraints:** Ball physics must be real (spin, curve, trajectory). Crowd is a character. Goal moments in slow-mo. Stadium light is dramatic. Emotion of the game.

---

### Category 43: Continue Basketball Action

**Signature:** Court intensity, dunk flight, dribble rhythm, sneaker squeak, buzzer beater, sweat and athleticism

**Camera DNA:** Low court-level tracking, rim-level for dunks, POV dribble, slow-mo on release, crowd reaction, locker room intimacy.

**Quick Prompt Pattern:**

```
[Low/rim-level/POV] shot. [Player] on [court: NBA arena / street court / training facility].
[Action: dunk / crossover / three-pointer / block / buzzer beater].
Camera [low tracking / rim-level for dunk / slow-mo on release / orbits celebration].
[Details: sweat / sneaker grip / ball rotation / net snap].
Dramatic sports cinematography. Court as stage. [Duration]s.
```

| Model          | Tuning                                                                                                           |
| -------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` low, `[Tilt up]` dunk, slow-mo on shot release. `--motion 7-8`                                 |
| **Kling 3.0**  | "Player launches for dunk — float time, ball cocked back, rim-level perspective. Ball rotation visible on shot." |
| **Veo 3.1**    | Audio: "Sneaker squeak, ball bounce rhythm, buzzer, crowd explosion, rim rattle, player shout."                  |

**Key Constraints:** Verticality is basketball's signature (dunks, jumps). Speed of the game. Court as stage with dramatic lighting. Sneaker squeak is the soundtrack of the sport.

---

### Category 44: Continue Combat Sports (Boxing/MMA)

**Signature:** Ring/cage atmosphere, corner intensity, knockdown moment, sweat spray on impact, stare-down, raw combat theater

**Camera DNA:** Low-angle ring-side, overhead for cage, handheld during exchange, slow-mo on impact (sweat spray, face distortion), corner between rounds (cut man, coach, exhaustion), wide stare-down.

**Quick Prompt Pattern:**

```
[Low/overhead/handheld] shot. [Fighter] in [boxing ring / MMA cage].
[Action: exchange / knockdown / submission / corner moment / stare-down].
Camera [low ringside / overhead cage / handheld during flurry / push-in on corner].
[Impact details: sweat spraying / glove compressing face / blood mist / mouthguard ejecting].
[Atmosphere: arena lights / smoke / corner bucket / cut man working].
Raw combat theater. Gritty, real, brutal. [Duration]s.
```

| Model          | Tuning                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Shake]` impact, `[Push in]` corner, `[Static shot]` stare-down. Slow-mo on knockdown. `--motion 6-7`        |
| **Kling 3.0**  | "Glove compresses face on impact. Sweat sprays in halo. Mouthguard ejects. Body hits canvas."                 |
| **Veo 3.1**    | Audio: "Glove impact, corner shouting, crowd roar, bell, heavy breathing, cut man instruction, stool scrape." |

**Key Constraints:** Impact is real (face distortion, sweat spray). Corner is drama. Ring/cage is a stage. Fighter exhaustion is the story. Not glorifying — respecting the sport's brutality.

---

### Category 45: Continue Motorsport Racing

**Signature:** F1/MotoGP speed, pit stop precision, cockpit POV, cornering forces, speed blur, rain spray, checkered flag

**Camera DNA:** Low track-level speed pan, helicopter tracking, cockpit POV, pit stop choreography, slow-mo drift, finish line, start grid tension.

**Quick Prompt Pattern:**

```
[Track-level/cockpit/aerial] shot. [Race type: F1 / MotoGP / rally / endurance].
[Vehicle] at [moment: cornering / overtaking / pit stop / start / finish].
Camera [low speed pan / cockpit POV / helicopter tracking / pit crew choreography].
[Speed visual: motion blur / heat haze / rain spray / tire smoke / sparks].
[Atmosphere: rain-soaked track / golden hour / night race under lights].
Pure speed. Precision engineering. [Duration]s.
```

| Model          | Tuning                                                                                             |
| -------------- | -------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` speed pan, `[Shake]` cockpit, `[Static shot]` pit stop. `--motion 8-9`           |
| **Kling 3.0**  | "F1 car corners at极限 — suspension compressing, sparks from skid plate, heat haze from exhaust."  |
| **Veo 3.1**    | Audio: "Engine scream, gear shift, tire screech, pit gun rattle, crowd roar, Doppler effect pass." |

**Key Constraints:** Speed is everything (motion blur essential). Vehicle physics (body roll, suspension). Pit stop is ballet of precision. Sound is the engine note — visceral and loud.

---

### Category 46: Continue Winter Sports

**Signature:** Skiing powder, snowboarding halfpipe, ice skating grace, bobsled speed, snow spray, mountain scale

**Camera DNA:** Tracking alongside skier/boarder, drone following through terrain, low angle spray shot, POV run, slow-mo on aerial trick, wide mountain establishing, ice spray on hockey stop.

**Quick Prompt Pattern:**

```
[Tracking/aerial/POV] shot. [Athlete] [skiing / snowboarding / skating / bobsledding].
[Action: powder turn / aerial trick / spin / speed run].
Camera [tracks alongside / drone follows / POV downhill / slow-mo on trick apex].
[Snow details: powder spray / ice crystals in air / tracks in fresh snow / breath fog].
[Atmosphere: bluebird day / storm / night under lights / alpine glow].
Mountain scale. Cold crisp atmosphere. [Duration]s.
```

| Model          | Tuning                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` alongside, `[Tilt up]` on jump, slow-mo on trick. `--motion 7-8`                          |
| **Kling 3.0**  | "Snowboarder carves through powder — spray blooms behind. Skier launches off cornice — snow plume follows." |
| **Veo 3.1**    | Audio: "Edge carving snow, wind rush, landing impact, distant avalanche control, cold silence."             |

**Key Constraints:** Snow must feel deep/powdery. Cold is visible (breath fog, crisp air). Mountain scale dwarfs the athlete. Spray is the signature visual. Bluebird or storm atmosphere.

---

### Category 47: Continue Water Sports

**Signature:** Surfing barrel, diving form, swimming race, kayaking rapids, water interaction, spray and foam

**Camera DNA:** Inside barrel POV, underwater tracking, overhead drone of lineup, pool-level for swimming, low-angle spray, GoPro on board.

**Quick Prompt Pattern:**

```
[Water-level/underwater/aerial] shot. [Athlete] [surfing / diving / swimming / kayaking].
[Action: barrel ride / dive entry / sprint finish / rapid navigation].
Camera [inside barrel / underwater track / drone overhead / pool-level].
[Water details: spray / foam / bubbles / surface tension breaking / wake trail].
[Atmosphere: sunrise session / storm surf / pool competition / river mist].
Human vs water. Elemental power. [Duration]s.
```

| Model          | Tuning                                                                                                         |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` barrel POV, `[Tilt up]` from underwater, slow-mo on dive. `--motion 6-8`                     |
| **Kling 3.0**  | "Surfer inside barrel — water curling overhead, light through wave lip, spray backlit. Diver pierces surface." |
| **Veo 3.1**    | Audio: "Wave crash, underwater muffled rush, breathing, starting gun, paddling, crowd distant."                |

**Key Constraints:** Water is the co-star. Show water interaction (spray, foam, bubbles). Inside barrel is the holy grail shot. Underwater + surface transition. Elemental respect for water's power.

---

### Category 48: Continue Track & Field

**Signature:** Sprint finish, long jump flight, pole vault arc, javelin release, stadium atmosphere, explosive power

**Camera DNA:** Finish line slow-mo, low-angle sprint tracking, overhead for jumps, side-on for vault/javelin, stadium wide for scale, athlete face pre-competition focus.

**Quick Prompt Pattern:**

```
[Tracking/slow-mo/overhead] shot. [Athlete] in [event: sprint / long jump / pole vault / javelin / hurdles].
[Action: explosive start / mid-air flight / release / crossing line].
Camera [low tracking / overhead arc / side-on pan / finish line slow-mo].
[Details: muscle definition / track surface grip / sand spray on landing / bar trembling].
Stadium atmosphere. Olympic spirit. [Duration]s.
```

| Model          | Tuning                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` sprint, `[Tilt up]` pole vault, `[Static shot]` finish slow-mo. `--motion 7-8`              |
| **Kling 3.0**  | "Sprinter explodes from blocks — muscles firing. Pole vaulter arcs over bar — body contorted, bar trembling." |
| **Veo 3.1**    | Audio: "Starting gun, spike grip on track, crowd cheer, landing in sand, bar clatter, heavy breathing."       |

**Key Constraints:** Explosive power at start. Mid-air grace during flight. Track surface and stadium are essential context. Athlete focus pre-event. Olympic/elite competition aesthetic.

---

### Category 49: Continue Gymnastics & Dance

**Signature:** Balance beam precision, floor routine artistry, ballet grace, contemporary expression, body as art, fluid motion

**Camera DNA:** Slow orbit during routine, low-angle showing height/elevation, macro on pointed feet/hands, wide for full choreography, slow-mo on leaps/spins, spotlight for performance.

**Quick Prompt Pattern:**

```
[Wide/orbit/macro] shot. [Dancer/gymnast] performing [routine / leap / spin / balance].
[Discipline: ballet / contemporary / gymnastics / rhythmic].
Camera [slowly orbits / static wide / macro on feet/hands / low-angle on elevation].
[Details: pointed toes / extended fingers / fabric flowing / chalk dust / sweat].
[Lighting: spotlight / natural studio / stage performance / soft diffused].
Body as art. Grace, strength, expression. [Duration]s.
```

| Model          | Tuning                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Pan right]` slow orbit, `[Push in]` on expression, slow-mo on leap. `--motion 5-6`                          |
| **Kling 3.0**  | "Gymnast on beam — perfect balance, arms extended. Dancer in grand jeté — suspended mid-air. Fabric flowing." |
| **Veo 3.1**    | Audio: "Music swelling, breath, feet landing, fabric rustle, distant coach, performance silence."             |

**Key Constraints:** Body is the art. Grace over power (though power is present). Slow-mo on leaps/spins. Fabric and hair movement are secondary choreography. Performance atmosphere (spotlight or natural studio).

---

## Categories 50–57: Genre & Cinematic Action

### Category 50: Continue Horror/Stalker POV

**Signature:** POV stalker camera, victim unaware, creeping dread, silhouette in doorway, flickering lights, jump scare setup

**Camera DNA:** POV from predator's perspective (low, creeping, predatory), slow push-ins on unaware victim, snap zooms, flickering light (darkness as threat), Dutch angles for unease, never showing the monster — only its POV.

**Quick Prompt Pattern:**

```
[POV/creeping/slow-push] shot. Predator POV — camera IS the threat.
[Victim: unaware, alone, in vulnerable moment].
[Environment: dark house / empty parking garage / forest at night / abandoned hospital].
Camera [slowly creeps forward / watches from doorway / tilts around corner / snap-zooms on victim].
[Lighting: single flickering bulb / moonlight through blinds / flashlight / TV static glow].
[Sound is dread]: floorboard creak, distant thump, victim's breathing, rising tension drone.
Never show the threat — only its POV. [Duration]s.
```

| Model          | Tuning                                                                                                                     |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` slow creeping, `[Zoom in]` snap on victim, `[Shake]` jump scare. `--motion 2-3` creeping, 8 jump               |
| **Kling 3.0**  | "Camera IS the predator — creeping low, watching from shadows. Victim unaware. Flickering light. Dread builds."            |
| **Veo 3.1**    | Audio critical: "Floorboard creak from BEHIND. Victim breathing. Distant thump. Rising drone. Sudden silence. LOUD STING." |

**Key Constraints:** Camera IS the threat (POV only). Never show monster/killer. Dread over gore. Sound is the primary scare tool. Flickering light = darkness cycles (threat in the dark). Victim vulnerability.

---

### Category 51: Continue Heist & Infiltration

**Signature:** Laser grids, safe cracking, silent movement, team coordination, pressure plates, time ticking, close calls

**Camera DNA:** Tight close-ups on hands/tools, wide establishing the security system, slow dolly through laser grid, POV through night vision goggles, clock counting down, split-second freezes on near-misses.

**Quick Prompt Pattern:**

```
[Tight/wide/POV] shot. [Team member: safecracker / infiltrator / hacker / lookout].
[Action: cracking safe / navigating lasers / bypassing security / grabbing target].
Camera [tight on hands / dolly through laser grid / POV night vision / wide security room].
[Details: sweating brow / steady hands / laser beam grazing skin / pressure plate depressing].
[Lighting: laser grid red / night vision green / single flashlight / security monitor glow].
Tension. Precision. Every second counts. [Duration]s.
```

| Model          | Tuning                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Push in]` slow on safe, `[Tracking shot]` through lasers, `[Static shot]` pressure plate. `--motion 3-4`                         |
| **Kling 3.0**  | "Laser grid — beams visible in smoke. Hand passes between beams. Safe lock — tumblers clicking. Pressure plate — weight shifting." |
| **Veo 3.1**    | Audio: "Heartbeat. Pin dropping in silence. Laser hum. Safe tumbler click. Distant guard footsteps. Alarm threat."                 |

**Key Constraints:** Tension through precision. Hands are the focus. Laser grids are visual signature. Clock/time pressure visible. Near-misses (laser grazing, plate almost triggering). Silence is suspense.

---

### Category 52: Continue Post-Apocalyptic Wasteland

**Signature:** Ruined cities, scavenger survival, desolate landscapes, weathered costume, makeshift tech, hope against desolation

**Camera DNA:** Wide establishing wasteland scale, handheld following scavenger, macro on weathered details (rusted metal, torn fabric), low-angle on ruined skyscrapers, drone over desolation, muted desaturated palette.

**Quick Prompt Pattern:**

```
[Wide/handheld/macro] shot. [Survivor/scavenger] in [ruined city / desert wasteland / flooded world].
[Action: scavenging / traveling / evading threat / discovering].
Camera [wide drone over ruins / handheld following survivor / macro on weathered detail].
[Environment: collapsed skyscrapers / overgrown highway / sand-buried suburbs / rusted vehicles].
[Palette: muted earth tones, rust, faded concrete, the only bright color is [survival element: fire / green plant / clean water]].
Desolation. Survival. Faint hope. [Duration]s.
```

| Model          | Tuning                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` drone over ruins, `[Shake]` handheld survival, `[Push in]` discovery. `--motion 4-6`                    |
| **Kling 3.0**  | "Ruined city — skyscrapers collapsed, nature reclaiming. Survivor in weathered gear. Dust in the air. Faint hope."        |
| **Sora 2**     | Best for massive environmental destruction. "Mile-wide ruined cityscape. Overgrown highways. Nature reclaiming concrete." |

**Key Constraints:** World is the character (show the scale of ruin). One pop of hope color. Weathered everything. Sound is wind and silence. Survival, not action-hero.

---

### Category 53: Continue Cyberpunk Action

**Signature:** Neon-drenched city, rain-slicked streets, augmentations, hacking, flying vehicles, high-tech low-life, synthwave energy

**Camera DNA:** Low-angle looking up at neon towers, rain on lens, reflections in puddles, handheld chase through neon market, macro on cybernetic augmentations, drone between skyscrapers, holographic overlays.

**Quick Prompt Pattern:**

```
[Low/wide/macro] shot. [Subject: hacker / augmented mercenary / street samurai / drone].
[Action: running / hacking / fighting / flying through city].
Camera [low-angle neon tower / rain on lens / handheld chase / drone between buildings].
[Environment: neon-drenched megacity / rain-slicked street / hologram-filled market / dark alley with neon reflection].
[Palette: cyan and magenta neon / deep blacks / rain reflection / holographic blue].
[Details: cybernetic limb glowing / data streams in air / flying vehicle passing / steam from street vents].
Blade Runner meets Ghost in the Shell. 16:9, [duration]s.
```

| Model          | Tuning                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tilt up]` neon towers, `[Tracking shot]` chase, `[Shake]` handheld, `[Push in]` cybernetics. `--motion 7-8`       |
| **Kling 3.0**  | "Rain-slicked streets reflecting neon. Holographic advertisements in the air. Flying vehicles between skyscrapers." |
| **Veo 3.1**    | Audio: "Synthwave score, rain, distant sirens, neon hum, flying vehicle pass, augmented reality data sounds."       |

**Key Constraints:** Neon is the lighting source. Rain/wet surfaces essential for reflection. High-tech + low-life contrast. Augmentations must feel integrated, not costume. Holograms and data streams are part of the world.

---

### Category 54: Continue Superhero Action

**Signature:** Flight, super strength, energy powers, city saving, iconic poses, cape dynamics, civilian rescue

**Camera DNA:** Dynamic flight tracking (alongside/behind), low-angle hero shot, slow-mo on impact (catching falling object, punching through wall), wide destruction as context, civilian POV looking up.

**Quick Prompt Pattern:**

```
[Tracking/low/wide] shot. [Hero] using [power: flight / super strength / energy / speed].
[Action: flying through city / catching falling structure / energy blast / rescuing civilians].
Camera [tracks alongside flight / low-angle hero landing / slow-mo on superhuman feat / POV from civilian looking up].
[Details: cape billowing / energy crackling / shockwave ring / civilians reacting / rubble falling].
[Lighting: heroic backlight / energy glow as light source / dramatic sky].
Superhero cinema. Iconic, hopeful, powerful. [Duration]s.
```

| Model          | Tuning                                                                                                                       |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` flight alongside, `[Tilt up]` hero landing, `[Pedestal up]` taking off. `--motion 7-8`                     |
| **Kling 3.0**  | "Hero flies between skyscrapers — cape billowing. Catches falling debris — shockwave from impact. Civilian looks up in awe." |
| **Veo 3.1**    | Audio: "Wind rush, sonic boom, debris crashing, civilians screaming then cheering, heroic score swell."                      |

**Key Constraints:** Hero must look iconic (lighting, pose, cape). Powers must have physics (shockwaves, wind, energy arcs). Show civilian perspective (scale of heroism). Hopeful, not grimdark.

---

### Category 55: Continue Stealth & Assassination

**Signature:** Silent takedown, shadows as cover, silenced weapon, body hiding, infiltration, precision kill, no witnesses

**Camera DNA:** Shadows with figure barely visible, POV through scope/sights, slow deliberate movement, tight on hands/weapon, wide showing isolation of target, Dutch angles for unease, sudden violence then silence.

**Quick Prompt Pattern:**

```
[Shadow/POV/tight] shot. [Assassin] in [environment: mansion / embassy / warehouse / city rooftop].
[Action: moving through shadows / silent takedown / setting up shot / hiding body].
Camera [in shadow watching / POV scope / tight on hands / slow deliberate move].
[Lighting: single shaft of light / moonlight / security monitor glow / laser sight dot].
[Details: silenced weapon / garrote wire / gloved hands / body being dragged into shadow].
Silence. Precision. No witnesses. [Duration]s.
```

| Model          | Tuning                                                                                                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Static shot]` shadow observation, `[Push in]` slow on target, `[Pan right]` silent move. `--motion 2-3`         |
| **Kling 3.0**  | "Figure in shadow — barely visible. Silent takedown — hand over mouth, quick knife. Body dragged into darkness."  |
| **Veo 3.1**    | Audio: "Silence. Distant footsteps of target. Suppressed shot — a whisper. Body thud. Dragging. Silence returns." |

**Key Constraints:** Silence is the weapon. Violence is sudden then over. Shadows hide the assassin. Show the consequence (body hidden). Target vulnerability. Professional, not emotional.

---

### Category 56: Continue Swashbuckling & Pirate Action

**Signature:** Ship boarding, sword fight on deck, cannon fire, swinging from rigging, treasure, sea spray, wooden ship romance

**Camera DNA:** Wide ship-to-ship establishing, handheld on deck during sword fight, crane up rigging, low on deck for cannon recoil, underwater for cannonball impact, POV swinging from rope.

**Quick Prompt Pattern:**

```
[Wide/handheld/crane] shot. [Pirate/swashbuckler] on [ship: galleon / frigate / sloop].
[Action: boarding enemy ship / sword duel on deck / swinging from rigging / cannon barrage].
Camera [wide ships closing / handheld deck fight / crane up rigging / POV rope swing].
[Details: cutlasses clashing / sails billowing / cannon smoke / splintering wood / spray from hull].
[Atmosphere: storm / sunset / dawn mist / tropical clear].
Romantic adventure. Pirates. The sea. [Duration]s.
```

| Model          | Tuning                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` deck, `[Shake]` cannon recoil, `[Tilt up]` rigging, `[Pan right]` sword fight. `--motion 6-7`                       |
| **Kling 3.0**  | "Cutlasses clashing on deck. Sails billowing in wind. Cannon fire — recoil, smoke, splintering enemy hull. Rope swing between ships." |
| **Veo 3.1**    | Audio: "Creaking wood, crashing waves, cannon roar, sword clash, sail wind, pirate shouts, sea shanty distant."                       |

**Key Constraints:** Romantic, not gritty. Wooden ship authenticity (creaking, billowing, splintering). Sword fights are swashbuckling (fun, not brutal). Sea is always present. Treasure/gold visual pop.

---

### Category 57: Continue Musical & Dance Number

**Signature:** Choreographed group dance, Bollywood spectacle, Broadway stage, street dance battle, music video energy, synchronized movement

**Camera DNA:** Wide for full choreography, tracking through dancers, crane sweeping over stage, low-angle for power moves, Steadicam fluidity during number, audience reaction, spotlights.

**Quick Prompt Pattern:**

```
[Wide/tracking/crane] shot. [Performers: dancers / musical cast / street crew].
[Number: Bollywood spectacle / Broadway showstopper / street dance battle / flash mob].
Camera [wide choreography / Steadicam through dancers / crane over stage / low on power move].
[Details: synchronized movement / costume color / fabric spinning / sweat / joy on faces].
[Lighting: stage spotlights / natural street / golden hour flash mob / theatrical color wash].
[Color palette: vibrant / theatrical / coordinated costumes].
Joy through movement. Music made visible. [Duration]s.
```

| Model          | Tuning                                                                                                               |
| -------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` through dancers, `[Pedestal up]` reveal, `[Pan right]` orbit group. `--motion 7-8`                 |
| **Kling 3.0**  | Best for group choreography. "Synchronized dance number — fabric spinning, coordinated movement, joy on faces."      |
| **Veo 3.1**    | Audio: "Music track, synchronized footfalls, fabric rustle, crowd cheer, breaths in unison, swelling orchestration." |

**Key Constraints:** Joy is the emotion. Choreography is the subject. Camera moves WITH the dance. Costumes are visual spectacle. Lighting is theatrical. Music is inseparable from movement.

---

## Categories 58–60: Experimental & Art

### Category 58: Continue Abstract Kinetic Art

**Signature:** Paint in water, ink drops, fluid dynamics, particle systems, color blending, organic abstraction, no literal subject

**Camera DNA:** Macro on fluid surface, top-down on paint/ink, slow-mo on droplet impact, abstract camera moves following color trails, no human presence, pure visual music.

**Quick Prompt Pattern:**

```
Abstract macro shot. [Medium: ink in water / paint mixing / oil on water / pigment explosion / molten color].
[Action: droplet falling / colors swirling / tendrils forming / pigment blooming / fluid merging].
Camera [macro on surface / top-down / slow tracking through color trails].
[Colors: [specific palette — e.g., gold and indigo / neon pink and cyan / earth tones swirling]].
[Lighting: backlit fluid / soft diffused / dramatic single source].
No literal subject. Pure color and motion. Visual meditation. [Duration]s.
```

| Model          | Tuning                                                                                                           |
| -------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Static shot]` macro, `[Push in]` slow into color. Slow motion on bloom. `--motion 3-4`                         |
| **Kling 3.0**  | "Ink drops hit water — tendrils unfurl like smoke. Gold pigment swirls into indigo. Colors bloom, merge, dance." |
| **Veo 3.1**    | Audio: "Ambient drone, subtle chimes, the sound of liquid, meditative score, no rhythm — pure atmosphere."       |

**Key Constraints:** No literal subject. Color is the protagonist. Fluid physics must look real (viscosity, mixing, blooming). Slow motion throughout. Meditative, not chaotic. Pure visual music.

---

### Category 59: Continue Slow-Mo Destruction

**Signature:** Objects shattering, glass breaking, fruit exploding, bullet impacts, water balloons bursting, controlled demolition

**Camera DNA:** High-speed camera aesthetic, extreme slow-mo (1000fps+ feel), macro on point of impact, fragments suspended mid-air, shockwave visible, pristine before → chaos after.

**Quick Prompt Pattern:**

```
Extreme slow motion. [Object] being destroyed by [force: bullet / hammer / fall / explosion].
[Impact moment]: [glass crystallizing and exploding / fruit rupturing / ceramic shattering / water balloon bursting].
Camera [macro on impact point / wide slow-mo / tracking fragment trajectory].
[Details: every shard suspended / juice droplets hanging mid-air / glass cracks spider-webbing / dust cloud blooming].
Pristine white/black background. The beauty of destruction. [Duration]s.
```

| Model          | Tuning                                                                                                                               |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Hailuo 2.3** | `[Static shot]` macro, slow motion throughout. `--motion 2-3`                                                                        |
| **Kling 3.0**  | "Glass shatters — every shard suspended mid-air. Bullet passes through apple — exit wound blooming in slow motion. Fragments hang."  |
| **Sora 2**     | Best for complex destruction physics. "Ceramic vase shattering — spider-web cracks propagating in slow motion before fragmentation." |

**Key Constraints:** Slow motion is the point (not real-time). Show the PROCESS of destruction (cracks spreading before break). Fragments suspended mid-air. Clean background for contrast. Beauty in destruction.

---

### Category 60: Continue Dream & Surreal Sequence

**Signature:** Impossible physics, scale shifts, morphing reality, dream logic, floating, melting, time distortion, subconscious imagery

**Camera DNA:** Fluid impossible camera moves (passing through solid objects), slow dreamlike drift, morphing between scenes, scale shifts (tiny in giant world / giant in tiny world), time distortion (slow then fast), no spatial logic.

**Quick Prompt Pattern:**

```
Surreal dream sequence. [Subject] in [impossible environment: floating city / upside-down world / infinite corridor / underwater sky].
[Action defying physics]: [walking on air / falling upward / objects morphing / time flowing backward / scale shifting].
Camera [passes through solid objects / drifts impossibly / morphs between scenes].
[Colors: oversaturated / desaturated / inverted / shifting hue].
[Logic: none — dream rules. One thing becomes another. Space is fluid. Time is elastic.]
Surreal. Hypnotic. Impossible. [Duration]s.
```

| Model          | Tuning                                                                                                                              |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Hailuo 2.3** | `[Tracking shot]` dreamy drift, `[Push in]` morph transition. `--motion 4-5`                                                        |
| **Kling 3.0**  | "Figure walks on air — ground is sky. Corridor stretches infinitely. Object morphs into bird. Scale shifts — tiny in giant teacup." |
| **Veo 3.1**    | Audio: "Reversed sounds, underwater voices, time-stretched music, heartbeat in reverse, whispers, distant bells."                   |

**Key Constraints:** No physics rules. Dream logic (one thing becomes another). Scale is fluid. Color can shift mid-shot. Camera can pass through solids. Sound is disorienting. Not horror — wonder and strangeness.

---

## Model-Specific Action Grammar

### Hailuo 2.3 — Camera Command Action System

| Action Type              | Command Chain                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| **FPV flight**           | `[Tracking shot], [Push in], then [Pan left]`                                               |
| **Combat impact**        | `[Push in] to impact, [Shake] on hit, [Pull out] to reveal aftermath`                       |
| **Bullet-time orbit**    | `[Static shot] hold on impact, then [Pan right] slow orbit around frozen action`            |
| **Chase handheld**       | `[Tracking shot] behind subject, [Shake] with footstep rhythm, [Pan left] to reveal threat` |
| **Epic breach**          | `[Pedestal up] as creature rises, [Tilt up] following it, [Push in] on hero reaction`       |
| **Macro tension**        | `[Static shot] at macro distance, [Shake] with micro-jitter, no push/pull`                  |
| **Atmospheric slow**     | `[Push in] slowly, [Static shot] on details, motion 3-4`                                    |
| **Hand-to-hand**         | `[Shake] every hit, [Push in] faces pre-strike, [Pan left/right] whip on throws`            |
| **Magic casting**        | `[Push in] slow on gesture, [Pedestal up] as energy rises, [Zoom in] on collision`          |
| **Underwater glide**     | `[Tracking shot] fluid drift, [Pan right] slow orbit, [Tilt up] toward surface`             |
| **Vertical wall-run**    | `[Tilt up/down] following vertical movement, [Tracking shot] sideways on wall-run`          |
| **Vehicle pursuit**      | `[Tracking shot] alongside, [Shake] interior, [Pan right] orbit on drift`                   |
| **Sniper scope**         | `[Static shot] scope POV, [Push in] on eye, [Zoom in] on impact`                            |
| **Parkour flow**         | `[Tracking shot] alongside, [Tilt up] wall-run, [Tilt down] gap jump`                       |
| **War charge**           | `[Shake] explosion concussions, [Tracking shot] running, [Tilt up] incoming shells`         |
| **Kaiju scale**          | `[Tilt up] slowly up creature, [Pedestal up] emergence, [Static shot] debris rain`          |
| **Escape corridor**      | `[Tracking shot] tight behind, [Shake] running, [Pan left/right] corner turns`              |
| **Duel standoff**        | `[Static shot] wide arena, [Push in] sloooow on eyes, [Push in] ultra-fast on draw`         |
| **Documentary wildlife** | `[Static shot] locked-off observation, [Pan left/right] slow animal tracking, motion 2-3`   |
| **Product hero**         | `[Pan right] slow orbit, [Push in] macro detail, [Pedestal up] reveal, motion 3-4`          |
| **Food commercial**      | `[Push in] on dish, [Static shot] top-down, [Tilt down] pour, slow motion on splash`        |
| **Fashion runway**       | `[Tracking shot] alongside model, [Push in] on face, [Pan right] fabric motion, motion 5-6` |
| **Horror POV**           | `[Push in] slow creeping, [Zoom in] snap on victim, [Shake] jump scare, motion 2-3 then 8`  |
| **Abstract art**         | `[Static shot] macro, [Push in] slow into color, slow motion throughout, motion 3-4`        |
| **Dream surreal**        | `[Tracking shot] dreamy drift, [Push in] morph transition, motion 4-5`                      |
| **Sport tracking**       | `[Tracking shot] alongside athlete, slow-mo on peak moment, [Tilt up] on jump`              |

### Hailuo Motion Intensity Reference (All 60 Categories)

| Cat | Category            | Motion | Cat | Category              | Motion |
| --- | ------------------- | ------ | --- | --------------------- | ------ |
| 1   | FPV Oner            | 7–8    | 31  | Food & Beverage       | 3–4    |
| 2   | Combat Slow-Mo      | 6–7    | 32  | Automotive            | 5–7    |
| 3   | Action Handheld     | 7–8    | 33  | Travel Tourism        | 4–5    |
| 4   | Epic Scale          | 6–8    | 34  | Tech Gadget           | 3–4    |
| 5   | Space Battle        | 7–8    | 35  | Jewelry Luxury        | 2–3    |
| 6   | Macro Tension       | 3–4    | 36  | Real Estate           | 4–5    |
| 7   | Atmospheric Fantasy | 3–4    | 37  | Perfume Fragrance     | 3–4    |
| 8   | Crowd Mass          | 6–7    | 38  | Sports Brand          | 6–8    |
| 9   | Survival Chase      | 7–8    | 39  | Pharma Healthcare     | 3–4    |
| 10  | Body Hardcore       | 7–8    | 40  | Extreme Sports        | 8–9    |
| 11  | Mystical Combat     | 5–6    | 41  | Martial Arts Training | 5–6    |
| 12  | Underwater Action   | 5      | 42  | Football/Soccer       | 7–8    |
| 13  | Vertical Combat     | 6–7    | 43  | Basketball            | 7–8    |
| 14  | Vehicle Chase       | 8–9    | 44  | Combat Sports         | 6–7    |
| 15  | Sniper Precision    | 2–3/7  | 45  | Motorsport            | 8–9    |
| 16  | Parkour Free-Run    | 8–9    | 46  | Winter Sports         | 7–8    |
| 17  | War Battlefield     | 7–8    | 47  | Water Sports          | 6–8    |
| 18  | Kaiju Creature      | 6–8    | 48  | Track & Field         | 7–8    |
| 19  | Escape Breakout     | 8      | 49  | Gymnastics Dance      | 5–6    |
| 20  | Duel Showdown       | 2/7    | 50  | Horror Stalker        | 2–3/8  |
| 21  | Wildlife Doc        | 2–3    | 51  | Heist Infiltration    | 3–4    |
| 22  | Underwater Doc      | 4–5    | 52  | Post-Apocalyptic      | 4–6    |
| 23  | Macro Nature        | 2–3    | 53  | Cyberpunk             | 7–8    |
| 24  | Aerial Landscape    | 4–5    | 54  | Superhero             | 7–8    |
| 25  | Volcanic Geo        | 4–5    | 55  | Stealth Assassin      | 2–3    |
| 26  | Weather Storm       | 6–8    | 56  | Swashbuckling         | 6–7    |
| 27  | Arctic Polar        | 3–4    | 57  | Musical Dance         | 7–8    |
| 28  | Time-Lapse          | 2      | 58  | Abstract Kinetic      | 3–4    |
| 29  | Product Hero        | 3–4    | 59  | Slow-Mo Destruction   | 2–3    |
| 30  | Fashion Beauty      | 5–6    | 60  | Dream Surreal         | 4–5    |

### Kling 3.0 — Realistic Motion & Physics

Kling excels at natural human motion and physics. For action:

- **Combat:** Specify body mechanics precisely. "Tight vertical flip" not "jumps."
- **Multi-character:** List each person and their vector independently.
- **Physics keywords:** "Real weight", "contact shadows", "blood disperses in blooming cloud", "shockwave ring."
- **Slow motion:** "Slow motion on [beat], snap back to real-time on [beat]."
- **Body hardcore:** "Ribs compress visibly", "sweat arcs off hair", "skin splits."
- **Documentary:** "Natural animal gait, real muscle movement, authentic behavior."
- **Food:** "Steam rises, sauce drips slowly, liquid splashes in slow motion."
- **Sports:** "Athlete at peak exertion — muscles tense, sweat flies."

### Seedance 1.5 Pro — First-Frame Control

- Upload exact start frame — model animates FROM that image.
- Visual + audio separated. Action in visual prompt, sounds in audio prompt.
- Multi-shot cuts: "then" or "cut to" for beat changes.
- 10 seconds per generation, chain for longer.

### Veo 3.1 — Natural Language + Native Audio

- Write action as prose paragraphs. Veo understands narrative flow.
- Audio inline: "The blade rings out. Snow crunches underfoot."
- Emotional arc: "He holds until the last moment — then explodes."
- Up to 60 seconds. Plan longer sequences.

### Sora 2 — Physics & World Simulation

- Complex multi-element scenes handled well. Be detailed.
- "Sand cascades in sheets", "shockwave ripples outward", "glyphs peel off walls."
- Environmental storytelling for scale before action.

### Runway Gen-4.5 — Camera-First

- Camera direction opens every prompt.
- "Shot on ARRI Alexa, anamorphic lens flares, 35mm film grain."
- Up to 10 seconds. Chain for longer.

---

## Shotlist / Script / Scene / Continue-Shot Modes

### Shotlist-to-Prompt

1. Identify action category (1–60)
2. Apply model grammar → 3. Build from category pattern → 4. Add continuity chain → 5. Output code-fenced prompt

### Script-to-Breakdown

1. Extract all action beats → 2. Map each to category → 3. Continuous beats use Cat 1 or 6 → 4. Discrete beats get individual prompts → 5. Chain all → 6. Output

### Scene-to-Prompt

1. Extract category DNA → 2. Match to closest of 60 → 3. Build prompt → 4. Split into Na/Nb/Nc if needed → 5. Output

### Continue-Shot Mode

1. Analyze existing: category, camera trajectory, subject state, lighting, palette, motion, damage/wounds
2. Build continuation: picks up exact state, maintains all elements, flows naturally
3. Tag: "Seamless continuation. Same [all elements]. Camera picks up at same [speed/height/distance]."

---

## The Action Prompt Skeleton

```
1. CAMERA DNA — How the camera moves (opens the prompt)
2. SUBJECT + ACTION — Who and what they do
3. ENVIRONMENT — Where and atmosphere
4. CHOREOGRAPHY / BEAT-BY-BEAT — Action sequence
5. LIGHTING + COLOR — Visual mood
6. STYLE + FORMAT — Film aesthetic
7. CONSTRAINTS — Hard rules
8. CONTINUITY — If part of a sequence
```

---

## Output Rules

1. **Always output copy-ready plain-text blocks inside code fences.**
2. **Never output HTML, tables, artifacts, or interactive files as the deliverable.**
3. **Multiple shots: separate code-fenced prompts back-to-back.**
4. **Include model name and category in a comment above each prompt block.**
5. **One short follow-up question allowed. The prompt is the deliverable.**

---

## Cross-Skill Integration

| When Using                  | Role                                          |
| --------------------------- | --------------------------------------------- |
| `dpf-film-director`         | General film direction, 8-layer framework     |
| `hailuo-prompting`          | Hailuo 2.3 camera commands, subject-reference |
| `kling-prompting`           | Kling 3.0 multi-shot, character reference     |
| `seedance-prompt-structure` | Seedance skeleton, element tags, style prefix |

### Vault References

| Note                                           | Key Insight                                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `Directing for the Latent Space`               | Three-act structure for micro-clips, mise-en-scène, motivated camera, shooting script format |
| `Anatomy of Production-Grade AI Video Prompts` | Technical deep-dive on prompt structure                                                      |
| `How to use HAILUO 2.3`                        | Dance, fight, stylized, facial realism, product ads — practical testing results              |
| `Soul Cinema Preview`                          | Cinematic-grade AI images as video keyframes                                                 |
| `Art Direction roadmap`                        | Concept development, insight-driven ideas, visual storytelling                               |

---

## Quick Reference: All 61 Categories

| #   | Category                      | Key Technique                                | Camera Signature                               |
| --- | ----------------------------- | -------------------------------------------- | ---------------------------------------------- |
| 1   | FPV Oner Macro                | Unbroken flight, bullet-time                 | FPV low flight, macro orbit                    |
| 2   | Combat Slow-Mo                | Multi-attacker, freeze beats                 | Low-angle, orbit, dynamic                      |
| 3   | Action Handheld               | Urgent shake, snap pans                      | Wide handheld, documentary                     |
| 4   | Epic Scale                    | Aerial → chase → orbit                       | Drift → push → crane → orbit                   |
| 5   | Space Battle                  | Organic ships, plasma                        | Handheld drift in void                         |
| 6   | Macro Body Horror             | Fixed macro, transformation                  | Locked distance, micro-jitter                  |
| 7   | Atmospheric Fantasy           | Slow push-in, mood                           | Slow dolly, 24fps, subtle                      |
| 8   | Crowd Mass                    | Vast scale, mass urgency                     | Sweeping wide, handheld                        |
| 9   | Survival Chase                | Creature threat, hero stand                  | Aerial → chase → low orbit                     |
| 10  | Body Hardcore                 | Brutal CQC, bone-breaking                    | Tight handheld, impact shake                   |
| 11  | Mystical Combat               | Magic duels, elemental                       | Steady orbit, cinematic                        |
| 12  | Underwater Action             | Submerged fight, weightless                  | Fluid drift, god rays                          |
| 13  | Vertical Combat               | Cliff fight, wall-run                        | Vertigo tilt, hovering                         |
| 14  | Vehicle Chase                 | Pursuit, drift, ram                          | Multi-angle, speed blur                        |
| 15  | Sniper Precision              | Scope, bullet trajectory                     | Stillness → slow-mo flight                     |
| 16  | Parkour Free-Run              | Urban fluidity, vault                        | Running alongside, never cuts                  |
| 17  | War Battlefield               | Mass military, explosions                    | Handheld charge, concussions                   |
| 18  | Kaiju Creature                | Giant monster, destruction                   | Human scale, tilt-up                           |
| 19  | Escape Breakout               | Prison break, collapsing                     | Tight over-shoulder, claustrophobic            |
| 20  | Duel Showdown                 | 1v1, stillness→explosion                     | Wide → ECU eyes → draw                         |
| 21  | Wildlife Documentary          | Animal behavior, telephoto                   | Locked-off observation, natural                |
| 22  | Underwater Documentary        | Reef, megafauna, bioluminescence             | Fluid drift, god rays                          |
| 23  | Macro Nature Doc              | Insects, flowers, dewdrops                   | Macro locked-off, rack focus                   |
| 24  | Aerial Landscape Doc          | Drone over epic terrain                      | Slow drone flight, reveals                     |
| 25  | Volcanic Geological           | Lava, eruption, caves                        | Safe distance orbit, heat haze                 |
| 26  | Weather Storm Doc             | Hurricane, tornado, lightning                | Wide witness, handheld struggle                |
| 27  | Arctic Polar Doc              | Ice, aurora, polar wildlife                  | Blue-white palette, slow pan                   |
| 28  | Time-Lapse Doc                | Day-to-night, growth, stars                  | Static locked-off, time compression            |
| 29  | Product Hero Ad               | Rotating showcase, macro                     | Slow orbit, rim light, clean bg                |
| 30  | Fashion Beauty Ad             | Runway, fabric, cosmetics                    | Tracking model, editorial light                |
| 31  | Food Beverage Ad              | Pour, sizzle, splash                         | Macro, top-down, slow-mo                       |
| 31B | Beverage Ingredient Explosion | Can/bottle burst, fruit orbit, liquid spiral | 3-clip chain: push-in → tracking → bullet-time |
| 32  | Automotive Ad                 | Winding road, detail, turntable              | Low tracking, golden hour                      |
| 33  | Travel Tourism Ad             | Destination reveals, wanderlust              | Drone reveal, golden hour                      |
| 34  | Tech Gadget Ad                | Unboxing, UI glow, precision                 | Macro materials, dark studio                   |
| 35  | Jewelry Luxury Ad             | Gems, sparkle, precious metal                | Extreme macro, light play                      |
| 36  | Real Estate Arch Ad           | Drone flythrough, interior                   | Smooth gimbal, golden hour                     |
| 37  | Perfume Fragrance Ad          | Abstract, fluid, sensuality                  | Dreamy drift, soft light                       |
| 38  | Sports Brand Ad               | Athlete peak, sweat, slow-mo                 | Dynamic action, motivational                   |
| 39  | Pharma Healthcare Ad          | Hopeful, diverse, clean                      | Warm natural, soft light                       |
| 40  | Extreme Sports                | Wingsuit, big wave, vertigo                  | POV, drone tracking, scale                     |
| 41  | Martial Arts Training         | Dojo, kata, discipline                       | Slow orbit, dust motes                         |
| 42  | Football/Soccer               | Goal, stadium, ball flight                   | Tracking play, crowd roar                      |
| 43  | Basketball                    | Dunk, dribble, buzzer beater                 | Low court, rim-level                           |
| 44  | Combat Sports                 | Boxing/MMA, knockdown                        | Ringside, sweat spray impact                   |
| 45  | Motorsport                    | F1/MotoGP, speed, pit stop                   | Track-level speed pan                          |
| 46  | Winter Sports                 | Ski, snowboard, powder                       | Tracking alongside, spray                      |
| 47  | Water Sports                  | Surf barrel, swim, kayak                     | Inside barrel, underwater                      |
| 48  | Track & Field                 | Sprint, jump, vault                          | Finish line slow-mo                            |
| 49  | Gymnastics Dance              | Beam, ballet, contemporary                   | Slow orbit, spotlight                          |
| 50  | Horror Stalker                | POV predator, dread                          | Creeping POV, flicker light                    |
| 51  | Heist Infiltration            | Lasers, safe, silent                         | Tight hands, laser grid dolly                  |
| 52  | Post-Apocalyptic              | Ruins, scavenger, desolation                 | Wide wasteland, muted palette                  |
| 53  | Cyberpunk                     | Neon city, augmentations                     | Low-angle neon, rain on lens                   |
| 54  | Superhero                     | Flight, powers, rescue                       | Flight tracking, hero low-angle                |
| 55  | Stealth Assassin              | Silenced takedown, shadows                   | Shadow POV, sudden violence                    |
| 56  | Swashbuckling Pirate          | Ship boarding, sword fight                   | Deck handheld, crane rigging                   |
| 57  | Musical Dance Number          | Choreography, spectacle                      | Steadicam through dancers                      |
| 58  | Abstract Kinetic Art          | Ink, fluid, color                            | Macro fluid, slow-mo bloom                     |
| 59  | Slow-Mo Destruction           | Shatter, explode, impact                     | High-speed macro, fragments                    |
| 60  | Dream Surreal                 | Impossible physics, morph                    | Fluid impossible camera                        |

---

## The Director's Mindset: From Prompt to Treatment

> "The prompt is not a request. It's a rehearsal." — Directing for the Latent Space

### Think Like a Director, Not an Engineer

Most AI video prompts fail because they describe what they want. Directors create conditions for magic to occur. Your prompt is a **shooting script** — a document that establishes mise-en-scène, motivates every camera move, and ensures emotional coherence.

### The Three-Act Structure of a 6-Second Clip

Even micro-content needs narrative architecture:

| Act                            | Time | Purpose                                                    |
| ------------------------------ | ---- | ---------------------------------------------------------- |
| **I: Establishment**           | 0-2s | Dramatic question, visual strategy, character introduction |
| **II: Expansion & Tension**    | 2-4s | Narrative reveal, escalation, rising stakes                |
| **III: The Event & Aftermath** | 4-6s | Catharsis, character beat, audience payoff                 |

**Example — Beverage Ingredient Explosion (3-clip chain):**

- Clip 1 (5s): Can at rest → tension builds → explosive burst (Act I → II)
- Clip 2 (4s): Fruit spiral + camera dive → momentum peak (Act II → III)
- Clip 3 (6s): Bullet-time hero settle → liquid settle → brand logo (Act III → denouement)

### Mise-en-Scène: Directing the Frame

Every element must answer to dramatic necessity, not decoration:

- **Casting your props** — A soda can isn't "a prop." It's your lead actor. Give it a character bible (backstory, physicality, relationship to space)
- **Blocking the scene** — Specify exact timing: "Frame 0-30 (0:00-0:02): Can position centered, 1/3 from bottom..."
- **The psychology of color** — Color is cinematography, not graphic design. Warm amber = tropical; deep red = passion; electric cyan = energy

### Motivated Camera Movement

Amateur prompts treat camera moves as effects. Directors treat them as narrators:

| Camera Move          | Narrative Function              | When to Use                             |
| -------------------- | ------------------------------- | --------------------------------------- |
| Static macro         | Intimacy, conspiracy, detail    | Opening beats, product close-ups        |
| Dolly zoom (Vertigo) | Psychological reveal, isolation | Mid-shot transitions, tension peaks     |
| Tracking shot        | Pursuit, momentum, journey      | Chase sequences, product journey        |
| Orbital              | 360° inspection, awe            | Hero product moments, character reveals |
| Crane up/down        | Scale reveal, power shift       | Epic reveals, aftermath                 |

**Example shooting script format:**

```
SHOT 1 - ECU CAN (0:00-0:02)
[Camera]: 100mm macro, f/2.8, static, low angle (hero shot)
[Action]: Can rests on dark stone. Condensation beads. Single fruit shadow falls across label.
[Lighting]: Hard key, soft fill, warm rim. Specular highlights on aluminum.
[Subtext]: This can has main character energy. It believes in itself.
```

### Lens Language

- **100mm macro (f/2.8)** — Paper-thin depth of field, background blurs into abstraction
- **50mm (f/4)** — Natural perspective, product in context
- **24mm (f/8)** — Wide reveal, environment expansion, scale contrast
- **8mm fisheye** — Distortion for impact moments, kinetic energy

### Lighting Design: Mood as Material

Your lighting isn't illumination — it's emotional weather:

- **Key Light** — "Bright studio" isn't enough. Think: "10am Mediterranean sun through a skylight"
- **Practical Motivation** — Water droplets catch light specularly. Each droplet is a mirror reflecting the key light
- **Rim Light** — Warm edge glow = nostalgia, separation, premium feel
- **The 70/20 Rule** — 70% intensity from above (product photography cleanliness), 20% warm rim (prevents sterility)

### Temporal Choreography: Directing Time

AI video isn't animation — it's temporal photography. Think like an editor with a stopwatch:

```
Beat 1 (0:00-0:02): THE POSE — Holding still is comic timing. The audience completes the joke.
Beat 2 (0:02-0:04): THE REVEAL — Camera movement reveals context. No handheld shake = formal comedy.
Beat 3 (0:04-0:06): THE BREATHING — Oscillation frequency matches human breath. Tension builds.
Beat 4 (0:06-0:06.2): THE VIOLATION — Impact. Physics must be ruthless. Gravity wins.
Beat 5 (0:06.2-0:08): THE HANG — Aftermath holds. Audience needs time to register.
```

### Director's Note to AI Cast & Crew

When directing Hailuo, Kling, Veo, or Seedance, you're working with actors who:

- Have seen every film ever made (training data)
- Have no intuition (need explicit motivation)
- Will improvise physics if not constrained

**Example director's note:**

> "Treat this not as 'a soda can exploding' but as 'a transformation from stillness to kinetic poetry.' The fruit is the orchestra. The liquid is the conductor. The 6 seconds are a complete narrative arc from potential to celebration. Maintain the dignity of the product even as you destroy it — commercial requires empathy."

---

## Claude Prompting Skill Framework

When writing prompts for Claude-based AI video tools (or any tool that processes natural language prompts), follow a dual-output format: **save the human-readable version** AND **generate the model-optimized version** separately.

### Human-Readable Version

This is what you save for your team, your future self, or your client. It reads like a creative brief:

```
Mboka Elengi — Continue Product Burst

Beat 1 (0:00-0:05): THE CHASE
Wide FPV oner chasing the product through a tropical jungle at dawn.
Camera weaves between palm trunks, vines whipping past.
Speed: fast, urgent. Motion: 7/10.

Beat 2 (0:05-0:09): THE IMPACT
Camera slams into the product as it lands on a volcanic rock.
Liquid erupts outward in a crown splash. Fruit pieces scatter.
Speed: fast deceleration. Motion: 8/10.

Beat 3 (0:09-0:15): THE CELEBRATION
Bullet-time orbit around the splash. Individual droplets frozen.
Camera pulls back to reveal the full scene.
Speed: bullet-time. Motion: 2/10.
```

### Model-Optimized Version

This is what you paste into the model. It follows the model's specific syntax:

```
[FPV oner] chasing soda can through tropical jungle at dawn. Camera weaves between palm trunks. Fast, urgent motion. [Push in] as can lands on volcanic rock. Liquid erupts. Fruit scatter. [Orbital] bullet-time around splash. Droplets frozen. Pull back to wide. --motion 7 --ar 16:9
```

### Why Two Versions?

1. **Human-readable** = documentation, collaboration, revision history
2. **Model-optimized** = what actually gets pasted into the tool
3. **Never paste the model-optimized version into your notes** — you'll lose the creative context
4. **Never paste the human-readable version into the model** — it wastes tokens on conversational language

### Workflow

1. Write the human-readable version first (creative intent)
2. Translate to model-optimized version (technical execution)
3. Save both in your prompt library
4. Reference the human-readable version when iterating

---

## Asset Compatibility Testing

Before locking assets and generating full sequences, test that your assets work together in the same frame.

### The Test Clip

Generate a **single 6-second test clip** combining:

- Character + Location
- Product + Environment
- Multiple characters together

**What to check:**

- Lighting consistency (does the character's lighting match the environment?)
- Scale (is the character the right size relative to the environment?)
- Style coherence (do they look like they belong in the same world?)
- Color palette harmony (do the colors complement or clash?)

### Decision Matrix

| Test Result                                        | Action                             |
| -------------------------------------------------- | ---------------------------------- |
| ✅ Lighting matches, scale correct, style coherent | Lock assets, proceed to production |
| ⚠️ Minor mismatch (slight color shift)             | Adjust one asset, re-test          |
| ❌ Major mismatch (wrong scale, clashing styles)   | Regenerate the weaker asset        |
| ❌ Fundamental incompatibility                     | Choose different assets entirely   |

### Batch Testing Strategy

- Generate 4 test clips with slight prompt variations
- Pick the best combination
- Lock assets before generating the full sequence
- Cost: 4 test clips = ~0.5 credits (Soul Cinema) — worth it to avoid wasting credits on bad final outputs

### Key Insight

**Location is the most important asset.** Video grabs textures, lighting mood, and color temperature from the reference image. A bad location will make even a perfect character prompt look wrong. Always lock the location first, then test character + location compatibility.

---

## Golden Rules for Action Prompts

- **Camera opens every prompt** — never let the model decide how to move
- **Speed belongs to the scene** — FPV 7-8, atmospheric 3-4, duel stillness 2, time-lapse 2
- **Physics is non-negotiable** — real weight, contact shadows, no floating
- **Continuity is everything** — carry over lighting, wounds, positions, palette, blood, debris
- **Bullet-time is a beat, not the whole shot** — freeze, orbit, then snap back
- **Handheld is intentional** — "urgent shake" not random noise; "impact shake" on hits
- **Blood behaves differently per environment** — fine mist in air, blooming cloud in water, smear on concrete
- **One category per prompt** — don't mix FPV oner with food commercial
- **Scale needs contrast** — kaiju need humans, epic needs close-ups, macro needs the void
- **Silence is the loudest sound** — duels, sniper beats, horror POV, before explosions
- **The environment is a weapon** — walls, water, gravity, debris, weather all participate
- **Every action has a cost** — exhaustion, wounds, blood, sweat, aftermath
- **Documentary observes, commercial sells, action drives** — know which mode you're in
- **Nature speaks for itself** — no human drama in wildlife, weather, or landscape categories
- **Color palette defines the world** — neon for cyberpunk, ice-blue for arctic, muted for post-apocalyptic
- **Order of information determines emotional interpretation** — AI models process tokens sequentially; use this as your edit timeline
- **Direct boldly** — the latent space is your soundstage
