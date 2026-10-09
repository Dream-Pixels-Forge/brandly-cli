---
name: brandly-casting
description: >
  Cast characters from the production bible — generate each character's
  image, portrait, and full-body wardrobe portrait, try wardrobe variations,
  then generate the character sheet from the cast set. Use when a campaign
  needs casting, character casting, "cast from the bible", character image,
  character portrait, headshot, full-body portrait, wardrobe tries, outfit
  variations, or a character sheet built from a cast. NOT for the production
  bible document itself (use brandly-production-bible), NOT for shot
  planning (use brandly-storyboard), NOT for generic product/prop sheets
  (use brandly-object-sheet).
---

# Brandly Casting

Cast characters from the production bible and turn the cast into a consistent
character sheet. The bible's Characters section (Section 4) is the source;
the cast set it produces is the reference material for everything downstream.

## Quick start

```bash
# 1. CAST — three images per character, from the bible
brandly image --project-id <id> -p "Hero shot: Maya, 25, dark braids, olive skin, emerald eyes, flowing red dress, urban rooftop at golden hour" --style-preset cinematic --ratio 3:2 --output pre-production/<id>/character/char_maya_cast-hero.png

brandly image --project-id <id> -p "Portrait headshot: Maya, 25, dark braids, olive skin, emerald eyes, neutral expression, soft studio light" --style-preset photorealistic --ratio 3:4 --output pre-production/<id>/character/char_maya_cast-portrait.png

brandly image --project-id <id> -p "Full-body standing portrait, head to toe: Maya, 25, wearing flowing red dress, neutral studio backdrop" --style-preset photorealistic --ratio 2:3 --output pre-production/<id>/character/char_maya_cast-fullbody.png

# 2. TRY WARDROBE — one variation per outfit (i2i via project auto-refs)
brandly image --project-id <id> -p "Same character, same pose, now wearing a charcoal wool coat over the red dress" --style-preset photorealistic --ratio 2:3 --output pre-production/<id>/character/char_maya_wardrobe-coat.png

# 3. CHARACTER SHEET FROM CAST — the GOLD reference plate
brandly reference <id> --subject-type character \
  --subject "Maya, 25, dark braids, olive skin, emerald eyes; red dress, charcoal coat variant" \
  --style-preset photorealistic --size 2K --ratio 16:9
```

## The casting pipeline

```text
production bible (Section 4: Characters)
      │
      ▼
1. CAST          per character: character image + portrait +
                 full-body portrait for wardrobe
      │
      ▼
2. TRY WARDROBE  wardrobe variations, image-to-image from the
                 full-body portrait (one per outfit)
      │
      ▼
3. SHEET         character sheet from the cast: the GOLD plate
                 that locks identity across every video
```

### Step 1 — Cast from the production bible

Read Section 4 (Characters) of the production bible: name, key anchor traits,
wardrobe variants, consistency rule. For each character generate the cast set
(three images):

| Cast image | Shows | Ratio | Prompt opens with |
|------------|-------|-------|-------------------|
| Character image | The character in context (hero shot) | `3:2` | `Hero shot:` |
| Portrait | The face only — identity detail | `3:4` | `Portrait headshot:` |
| Full-body portrait for wardrobe | Head-to-toe, standing, the wardrobe visible | `2:3` | `Full-body standing portrait, head to toe:` |

Rules:

- **Source every trait from the bible** — name, anchor traits, wardrobe, and
  the consistency rule come from Section 4 verbatim. Never invent traits.
- **Use `--project-id`** so the cast lands in the real media root
  (`pre-production/<id>/character/`) with the `char_` prefix, and every later
  `brandly video` call auto-injects it.
- **Use `--output`** for the exact path (issue #73: atomic download, format
  validated, written to exactly this path).
- **Portrait prompts stay neutral** — plain backdrop, soft light, no props.
  The portrait is the identity reference, not a scene.
- **Pace multi-character casting** — image RPM by size is 1K: 20, 2K: 10,
  3K: 1, 4K: 1 (`brandly rate-limits`); 2K keeps both quality and pace for a
  cast of 3–6 characters.

### Step 2 — Try wardrobe

The full-body portrait is the wardrobe reference. Generate one variation per
outfit listed in the bible's wardrobe variants:

- Run `brandly image` with the same `--project-id` — the cast set (already in
  the project) auto-injects as references, so identity carries over.
- The prompt describes **only the outfit change** — "same character, same
  pose, now wearing …". Face, hair, and body stay fixed.
- Keep the `2:3` full-body ratio and the neutral backdrop so variations stay
  comparable.
- Name variations `char_<name>_wardrobe-<outfit>.png`.

### Step 3 — Character sheet from cast

The cast set is the reference material for the sheet. Generate the GOLD
character reference plate — the 16:9 multi-view grid that locks identity
across all subsequent `brandly video` generations:

```bash
brandly reference <id> --subject-type character \
  --subject "<condensed: name, age, anchor traits, signature outfit + variants>" \
  --style-preset photorealistic --size 2K --ratio 16:9
```

- The subject text condenses the bible's Section 4 + the cast set — every
  anchor trait appears in the plate prompt.
- The plate is saved with the `reference_character_*` prefix and
  auto-injected as the **strongest** reference in every `brandly video` call.
- Pass `--require-reference` to `brandly video` to fail-fast when the
  reference is missing.

## Which brandly commands this skill drives

- `brandly image` — the cast set (character image, portrait, full-body
  wardrobe portrait) and wardrobe variations
- `brandly reference` — the character sheet / GOLD plate from the cast
- `brandly gate` — verify the generated cast and plates before use
- `brandly rate-limits` — pacing for multi-image casting

## Quality gate

- [ ] Every cast trait sourced from the bible's Section 4 (verbatim)
- [ ] Three cast images per character (hero `3:2`, portrait `3:4`, full-body `2:3`)
- [ ] Portrait on a neutral backdrop with soft light (identity reference, not a scene)
- [ ] One wardrobe variation per bible-listed outfit, full-body `2:3`
- [ ] GOLD reference plate generated from the cast (16:9, `2K`)
- [ ] `brandly gate` run on the cast set before video generation

## References

For the full prompt templates (cast, portrait, full-body wardrobe, wardrobe
try, and the sheet subject condensation), see
[references/prompt-variants.md](references/prompt-variants.md). For the bible
format, see [../brandly-production-bible/SKILL.md](../brandly-production-bible/SKILL.md).
For identity locking rules, see
[../brandly-consistency/SKILL.md](../brandly-consistency/SKILL.md).
