# Casting Prompt Variants

Prompt templates for the casting pipeline. Every trait in these templates
comes from the production bible's Section 4 (Characters) — name, age, anchor
traits, wardrobe, consistency rule. Never invent traits.

## 1. Character image (hero shot) — ratio `3:2`

The character in context. Establishes presence and the world around them.

```text
Hero shot: [Name], [age], [anchor traits — 3-5 features that never change],
[signature outfit], [context from the bible: setting, time of day, mood].
[Style preset descriptor]. Professional photography, sharp focus on subject.
```

Example:

```text
Hero shot: Maya, 25, dark braids, olive skin, emerald eyes, wearing flowing
red dress, urban rooftop at golden hour. Cinematic, professional photography,
sharp focus on subject.
```

## 2. Portrait (headshot) — ratio `3:4`

The identity reference. Face detail only — this image locks the face for
identity checking, so it stays neutral and clean.

```text
Portrait headshot: [Name], [age], [face anchor traits: face shape, skin tone
with undertones, eye color and shape, hair color/texture/style],
[facial hair if any], neutral expression, soft studio light, plain neutral
backdrop. Photorealistic, professional headshot photography.
```

Rules:

- No props, no scene, no costume emphasis — the face is the subject.
- Plain neutral backdrop (never white, colored, or busy) so cutouts stay clean.
- Skin tone described with undertones, not vague terms.

## 3. Full-body portrait for wardrobe — ratio `2:3`

Head-to-toe, standing. This is the wardrobe reference — every wardrobe
variation starts from it.

```text
Full-body standing portrait, head to toe: [Name], [age], [anchor traits],
wearing [complete outfit from the bible: top, bottom, shoes, accessories],
neutral expression, neutral studio backdrop, even soft lighting.
Photorealistic, full figure visible in frame.
```

Rules:

- **Full figure visible** — cropped feet or head break the wardrobe reference.
- Outfit description is complete and concrete (colors, materials, styles).
- Neutral backdrop keeps variations comparable.

## 4. Wardrobe try (variation) — ratio `2:3`

One per outfit in the bible's wardrobe variants. Generated with the project
context so the cast set auto-injects as references — identity carries over.

```text
Same character, same pose, same lighting, now wearing [new outfit from the
bible's wardrobe variants]. Face, hair, and body stay identical to the
reference. Neutral studio backdrop.
```

Rules:

- The prompt describes **only the outfit change** — everything else stays fixed.
- Keep the `2:3` ratio and neutral backdrop so variations stay comparable.
- Name the output `char_<name>_wardrobe-<outfit>.png`.

## 5. Character sheet subject (from cast) — the GOLD plate

The subject text condenses the bible's Section 4 + the cast set. Every anchor
trait appears — the plate locks identity across all subsequent video calls.

```text
[Name], [age], [all anchor traits], [signature outfit]; wardrobe variants:
[variant 1], [variant 2].
```

Example:

```text
Maya, 25, dark braids, olive skin, emerald eyes; red dress, charcoal coat
variant.
```

Command:

```bash
brandly reference <id> --subject-type character \
  --subject "<condensed subject>" \
  --style-preset photorealistic --size 2K --ratio 16:9
```

The plate is saved with the `reference_character_*` prefix and auto-injected
as the strongest reference in every `brandly video` call. Pass
`--require-reference` to `brandly video` to fail-fast when it is missing.

## Pacing

Image RPM by size (run `brandly rate-limits` for the live table):
1K: 20 · 2K: 10 · 3K: 1 · 4K: 1. A cast of 3–6 characters at 2K (three cast
images + wardrobe tries + one plate) fits comfortably under the 10 RPM tier —
never bypass the rate limit, pace the casting sequence instead.
