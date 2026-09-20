---
name: brandly-storyboard
description: >
  Create production-ready multi-shot storyboards for AI video campaigns.
  Use when planning shot sequences, writing shot lists, or organizing
  narrative structure before generation. Triggers on "storyboard",
  "shot list", "shot sequence", "scene breakdown", "visual plan",
  "sequence of shots", "plan the video", "break down the script".
  NOT for single-image planning (use brandly-video-generation),
  NOT for frame-by-frame animation (use dpf-scene-splitter for film).
---

# Brandly Storyboard

Transform a campaign brief into a structured, shot-by-shot visual plan that AI video models can execute with consistency. A storyboard is the **blueprint** — it defines every shot before you generate anything.

## When to Use

- Pre-production planning before any generation
- Breaking a script or concept into numbered shots
- Planning continuity across multiple clips
- Coordinating assets (character, location, object sheets) per shot
- Communicating vision to a team or agent

---

## Routing Table

| Want to... | Read |
|------------|------|
| See shot format templates | `references/shot-formats.md` |
| Reference pacing and rhythm | `references/pacing-guide.md` |
| See example full storyboards | `references/examples.md` |

---

## Storyboard Anatomy

Every shot in the storyboard must specify:

```markdown
SHOT #N — [SHOT TYPE]
━━━━━━━━━━━━━━━━━━━━━━━━
Context:   [Where are we? What just happened?]
Subject:   [Who/what is in frame?]
Action:    [What is happening?]
Camera:    [Shot type + movement]
Duration:  [N seconds]
────────────────────────
Prompt:    "[Full generation prompt]"
Assets:    [--reference-images ...]
```

### Shot Types Quick Reference

| Type | Abbrev | Use Case |
|------|--------|----------|
| Establishing | EST | Open scene, set location |
| Wide | W | Show full environment + subject |
| Medium | MS | Waist-level, standard framing |
| Close-Up | CU | Face, product detail |
| Extreme CU | ECU | Macro, texture, eyes, logo |
| Over Shoulder | O/S | Dialogue, reaction context |
| Insert | INS | Detail insert, cutaway |
| POV | POV | Subject's point of view |
| Aerial | AER | Bird's eye, landscape sweep |
| Low Angle | LA | Heroic, powerful framing |
| High Angle | HA | Vulnerable, contextual framing |
| Tracking | TRACK | Follow subject movement |
| Orbital | ORB | 360° reveal around subject |
| Push In | PUSH | Approach subject slowly |
| Pull Out | PULL | Reveal environment from subject |

---

## Workflow

### Phase 1: Define the Beat Sheet

Before writing individual shots, map the **narrative beats**:

```
BEAT 1 — [Emotional beat name]
  Goal: [What must the viewer feel/understand here?]
  Visual: [One-line description of the moment]

BEAT 2 — [Beat name]
  ...
```

### Phase 2: Assign Shots to Beats

One beat may need 1–5 shots depending on complexity:

```
BEAT 1: Introduction (product reveal)
  SHOT 1 — EST, 4s — City at dawn, product on table
  SHOT 2 — TRACK, 3s — Camera follows hand reaching for product
  SHOT 3 — ECU, 2s — Condensation on bottle

BEAT 2: Product in use
  SHOT 4 — MS, 4s — Person using product naturally
  SHOT 5 — CU, 3s — Face reaction, satisfaction
```

### Phase 3: Write Full Prompts

Each shot becomes a complete, self-contained generation prompt:

```
MASTER PROMPT: [Campaign summary — repeated at top of every shot]

SHOT 1 — ESTABLISHING (4s):
[Dawn light]. [City skyline]. [Product] sits on a wooden table
in the foreground. Camera slowly pushes in.
[Style note]. Duration: 4s.
────────────────────────
brandly video <project_id> --prompt "..." --wait
```

### Phase 4: Asset Lock

For each shot, note which asset sheets are needed:

| Shot | Character Ref | Location Ref | Object Ref |
|------|---------------|--------------|------------|
| 1 | — | ✅ | ✅ |
| 2 | ✅ | ✅ | — |
| 3 | — | — | ✅ |
| 4 | ✅ | ✅ | ✅ |
| 5 | ✅ | — | — |

---

## Prompt Template: Multi-Shot Sequence

```markdown
# STORYBOARD: [Campaign Name]
# Style: [cinematic/commercial/documentary/etc.]
# Total Duration: [N]s

MASTER CONTEXT:
[One paragraph describing the entire sequence. Every shot will inherit this.]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHOT 1 — [TYPE] ([N]s)
Context:   [1 sentence setup]
Subject:   [who/what]
Action:    [verb + object]
Camera:    [movement + angle]
Prompt:    "[Full prompt text]"
Assets:    [--reference-images ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHOT 2 — [TYPE] ([N]s)
...
```

---

## Pacing Rules

| Campaign Type | Typical Shot Count | Shot Duration Range |
|---------------|--------------------|---------------------|
| 6s Social Ad | 3–5 shots | 1–2s |
| 15s Spot | 5–8 shots | 2–3s |
| 30s Commercial | 8–12 shots | 2–4s |
| 60s Commercial | 12–20 shots | 3–5s |
| Product Reveal | 4–6 shots | 2–4s |
| Narrative Scene | 6–15 shots | 3–6s |

**General rules:**
- Don't exceed 6s per shot (model coherence drops)
- End on a wide or hero shot for impact
- Minimum 2s per shot for model to render quality
- Match shot length to emotional beat (slow for drama, fast for energy)

---

## Continuity Checklist

Before generating, verify:

- [ ] Every shot references the same MASTER CONTEXT
- [ ] Character descriptions are identical across shots
- [ ] Lighting conditions match (same time of day, same quality)
- [ ] Background locations are consistent
- [ ] Color palette is defined and repeated
- [ ] Shot types progress logically (no jarring jump cuts unless intentional)
- [ ] All asset references are generated and URLs collected

---

## CLI Execution Pattern

**The production plan is the source of truth.** Write the storyboard as a
shot-list JSON file, then generate with `brandly produce` — it registers
every shot on `docs/plan/production_plan.md` first, then generates
**one shot at a time** with a 60s wait between requests (Agnes:
1 request/minute). Never call `brandly video` in a loop or batch —
that bypasses the production plan and violates the rate limit.

```bash
# shots.json — the storyboard in machine form (one entry per shot)
cat > shots.json <<'EOF'
[
  {"name": "shot-1", "prompt": "Establishing: city at dawn, product on table, slow push-in", "duration": 5, "style": "cinematic", "references": "loc_city.png,prop_bottle.png"},
  {"name": "shot-2", "prompt": "Tracking: hand reaches for the product", "duration": 4, "style": "cinematic", "references": "char_maya.png"},
  {"name": "shot-3", "prompt": "ECU: condensation on the bottle", "duration": 4, "style": "cinematic", "references": "prop_bottle.png"}
]
EOF

# Shot-by-shot production pulled from the production plan (resumable:
# COMPLETED shots are skipped on re-run)
brandly produce <project_id> --shots shots.json
```

---

## Quality Checklist

- [ ] Every shot has a clear type and duration
- [ ] Prompts are self-contained (no ambiguous references)
- [ ] Character/location/object consistency rules written
- [ ] Asset reference URLs collected before generation starts
- [ ] Master context paragraph included
- [ ] Total runtime calculated and within target
- [ ] Shot order supports narrative flow
