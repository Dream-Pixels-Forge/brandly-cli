---
name: brandly-fight-choreography
description: >
  JKD-derived fight choreography for AI video generation via brandly-cli.
  Breaks fights into beats (1-2 seconds each) with position, action,
  reaction, and new position. Prompts are Seedance-proof: pure body
  geometry, zero martial-arts terminology, zero prohibitions, physics of
  consequences. Every fight prompt ends with the identical FIGHT STYLE LOCK.
  Use when building fight scenes, combat exchanges, interception sequences,
  kick-to-punch entries, trap combos, straight blast finishes, or any
  cinematic action for brandly video generation.
  Triggers on "fight choreography", "combat scene", "action beat",
  "interception", "straight blast", "trap combo", "kick-to-punch",
  "fight style lock", "seedance-proof prompt", "body geometry".
  NOT for general shot direction (use brandly-camera), NOT for project
  init or phase ordering (use brandly-init), NOT for CLI execution
  (use brandly-video-generation).
---

# Brandly Fight Choreography

## Concern separation (read first)

| Skill | Concern | Responsibility |
|-------|---------|----------------|
| **brandly-fight-choreography** (this skill) | **WHAT** happens in a fight | Beat patterns, body geometry, strike reactions, FIGHT STYLE LOCK, prompt packaging for combat sequences |
| **brandly-camera** | **HOW** shots are directed | Camera language, framing, angles, movement, lighting rules for shot direction briefs |
| **brandly-init** | **WHERE** things land | Layout contract, directory structure, artifact paths, phase order, gate approvals, project init cwd enforcement |
| **brandly-video-generation** | **HOW** execution | CLI execution via `brandly video` / `brandly produce` using the choreographed prompts |

This skill does NOT teach project init, phase ordering, artifact placement, or gate management. For where each artifact lands and the mandatory phase order, see brandly-init. For CLI execution via `brandly video` / `brandly produce`, see brandly-video-generation. For camera and lighting, see brandly-camera. This skill only covers HOW to write fight choreography — the body geometry and physics of combat.

## Routing Table

| Want to... | Read |
|------------|------|
| Core principles and beat-prompt rules | Section 1 |
| The FIGHT STYLE LOCK appended to every prompt | Section 2 |
| Ready-to-use beat patterns P1–P4 | Section 3 |
| Opening stance body geometry | Section 4 |
| Camera rules for action | Section 5 |
| Per-strike reaction physics | Section 6 |
| Packaging a fight prompt | Section 7 |
| Anti-patterns (positive phrasing only) | Section 8 |
| Tool contract for `fight_choreography` | Section 9 |

---

## 1. Core principle

AI video models generate "movie kung fu" by default: wide windups, high kicks, endless combinations. To get authentic, cinematic combat, the prompt must actively override these defaults:

1. **Specific limbs and targets.** Not "he punches" → "his lead right fist snaps into the jaw". Every strike: which limb, from where, along which path, to where, and what happens to the target.
2. **Remove the windup with a POSITIVE lock.** The prohibition "no windup" itself conjures a windup. Use: "the first visible motion of a limb IS the strike already travelling, launched from where the hands rest at guard." Remove high kicks with: "every kick stays below belt height."
3. **Stance in the first frame.** Full body geometry before the exchange begins; in later frames, reprise "the narrow side-on stance" with identical wording.
4. **Reaction physics.** Every impact must include a described reaction from the opponent's body. Without it, the model "misses" the contact.
5. **Beat timing.** 1 beat ≈ 1-2 seconds of screen time. An 8-second shot holds 4-6 beats maximum, including 1-2 beats of stance/pause. Do not cram in 10 strikes.
6. **The pause is part of the fight.** Broken rhythm requires written stop-stills: "he settles back into stance, motionless" — that is the style.
7. **Camera favors profile.** A sideways stance and straight punches read best in profile or three-quarter view; low kicks require a frame that shows the legs (not a chest-up close-up).
8. **One exchange = one shot.** For multi-shot sequences, cut at the broken-rhythm pauses — natural edit points.

---

## 2. The FIGHT STYLE LOCK

Appended verbatim to every fight prompt. Identical wording across all scenes so the model learns the style by repetition:

```
FIGHT STYLE LOCK: every kick stays below belt height; every punch travels
a short straight line launched from where the hands already rest at guard
— the first visible motion of a limb IS the strike itself; between
exchanges the fighter is completely still in his narrow side-on stance;
the fight is short straight lines and long stillness.
```

---

## 3. Beat patterns

Ready-to-use structures translated from choreography theory into prompt language. Each beat: `(position, action, reaction, new_position, start_seconds, end_seconds)`.

### P1 — Intercepting a Single Attack (4-6 sec)
1. Side-on stance, weight on balls of feet, lead hand half-extended → Opponent throws a sweeping haymaker → Straight lead lands on the jaw at the moment of the windup, opponent's strike dies halfway → Opponent staggers back, hero returns to stance
2. Opponent reeling backward → Hero settles back into the narrow side-on stance and goes completely still → Stillness holds a full second → Hero motionless
3. Hero still in stance → Opponent lunges again with a wide right swing → Stop-hit straight lead mid-motion, opponent's own punch dying halfway → Opponent's head whips back, staggers two steps
4. Opponent falling backward → Hero remains still in stance → Stillness holds → Hero motionless

### P2 — Kick-to-Punch Entry (Long → Medium Range, 6-8 sec)
1. Side-on stance, circling in an arc on small fencing steps → Opponent steps forward → Low side kick from the lead leg spears into the knee; leg buckles, opponent pitches forward → Opponent pitching forward
2. Opponent pitching forward → Straight lead or lead hook to the jaw → Head snaps back hard, two steps backward → Opponent falls past the hero
3. Opponent falling past → Hero settles back into stance and goes completely still → Stillness holds a full second → Hero motionless

### P3 — Trap-Combo (Medium → Close Range, 6-8 sec)
1. Side-on stance → Opponent throws a straight punch → Left palm slaps the guard down while the right fist fires through the opening in the same beat → Opponent sways
2. Opponent sways, attempts a second strike → Wrist pull jerks the man forward into a short punch — pull and hit landing as one motion → Opponent jerked forward and down
3. Opponent falling past → Hero releases the hand, stillness → Stillness holds → Hero motionless

### P4 — Straight Blast Finish (Pressure, 4-6 sec)
1. Opponent stunned, losing structure → Chain of vertical-fist punches piston down the centerline, hero surging forward → Opponent retreats without time to recover structure → Opponent stumbling backward
2. Opponent retreating → Side kick slams into the sternum → Entire body flies backward 2-3 meters into an obstacle → Opponent against obstacle
3. Opponent against obstacle → Hero remains still in stance → Stillness holds → Hero motionless

---

## 4. Opening stance (full body geometry)

Packaged as the first line of every fight prompt:

```
<hero> stands almost side-on, <lead_hand> shoulder and <lead_hand> foot leading, feet just past shoulder width, rear heel floating off the ground, knees softly bent, weight riding the balls of both feet with a light constant spring. His lead hand floats half-extended at shoulder height, rear fist rests at his chin, elbows close to the ribs, chin tucked, eyes steady over the lead shoulder, face calm and unreadable.
```

Replace `<hero>` and `<lead_hand>` with the actual fighter.

---

## 5. Camera rules for action

| Strike type | Camera |
|-------------|--------|
| Punch | Profile or three-quarter view, chest-up close-up, long fixed shot |
| Kick | Wide shot showing the legs, profile view, long fixed shot |
| Exchange | Three-quarter view, long fixed shot, no montage cuts |

---

## 6. Per-strike reaction physics

Mandatory in prompts so the model registers contact:

| Strike | Reaction |
|--------|----------|
| Straight lead to jaw | Head snaps backward, one or two steps back, sinking down |
| Side kick to body | Entire body flies backward, 2-3 meters, into an obstacle |
| Finger jab to eyes | Flinches back, both hands flying to his face, eyes screwed shut |
| Low kick to knee | Leg buckles, he pitches forward |
| Backfist to temple | Head snaps sideways |
| Hook to jaw | Head jerks to the side, stumbling |

---

## 7. Packaging a fight prompt

1. Choose a beat pattern (P1-P4) matching the scene duration.
2. Compute number of beats: `min(len(pattern), max(2, round(duration / 1.5)))`.
3. Write each beat as: `BEAT N (start-end sec): <position>. <action>. <reaction>. <new_position>. <camera>.`
4. Prepend the opening stance geometry.
5. Append the FIGHT STYLE LOCK.
6. Persist to `docs/general/fight_choreography_<scene_id>.json`.

Example packaged prompt:

```
<hero> stands almost side-on, right shoulder and right foot leading...
BEAT 1 (0.0-1.5s): side-on stance... opponent throws a sweeping haymaker. straight lead lands on the jaw at the moment of the windup... profile.
BEAT 2 (1.5-3.0s): opponent reeling backward. hero settles back into the narrow side-on stance... profile.
FIGHT STYLE LOCK: every kick stays below belt height; every punch travels...
```

---

## 8. Anti-patterns (do NOT transfer as prompt prohibitions)

Everything excluded through **positive phrasing**:

- High kicks to the head → "every kick stays below belt height" (NOT "no high kicks")
- Blocking → interception snippets instead (NOT "no blocking")
- Long combinations without pauses → broken rhythm stop-stills (NOT "no combos over 4")
- Square boxing stance → side-on stance geometry (NOT "no square stance")
- Retreating backward → angles/pendulum step geometry (NOT "no retreating")
- Windups / loaded punches → "first visible motion IS the strike" (NOT "no windup")

Naming a prohibited action summons it. Use positive constraints only.

---

## 9. Tool contract

The `fight_choreography` tool maps to this skill. Inputs:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | Yes | Project ID |
| `scene_id` | string | Yes | Scene ID |
| `fighters` | array | Yes | `[{name, role, lead_hand, style, description}]` |
| `pattern` | string | No | `P1` (intercept), `P2` (kick-to-punch), `P3` (trap-combo), `P4` (straight blast) |
| `duration` | integer | No | Shot duration in seconds (default 6) |
| `location` | string | No | Where the fight takes place |
| `emotion` | string | No | Emotional tone of the exchange |
| `winner` | string | No | Who wins the fight |

Outputs: `prompt` (Seedance-proof fight prompt), `beats` (list of beat dicts), `style_lock` (the FIGHT STYLE LOCK), `path` (persisted JSON path).

The cascade pipeline consumes the output: each stage with `fight_choreography` writes the prompt into `input.fight_prompt` so `brandly produce` can generate the shot.
