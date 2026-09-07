# Character Consistency Checklist

Ensure consistent character appearance across all generated content.

## Pre-Generation Checklist

- [ ] Full physical description documented
- [ ] Wardrobe details specified (colors, materials)
- [ ] Distinctive features identified
- [ ] Posture and movement defined
- [ ] Reference images generated

## Consistency Rules Template

```
CHARACTER ANCHOR:
- Name: [Name]
- Key traits: [3-5 most important visual features]
- Clothing: [Signature outfit]
- Distinguishers: [What makes them unique]

CONSISTENCY RULES:
- Never change: [features that must stay the same]
- Can vary: [features that can change between scenes]
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Face drifts between shots | Add more specific facial features to prompt |
| Hair color changes | Include "identical hair" in consistency anchors |
| Wardrobe mismatches | Specify exact outfit in every prompt |
| Body type varies | Include build description consistently |
| Age appears different | Include age range in character anchor |

## Best Practices

1. **Anchor First**: Define character completely before generating
2. **Use References**: Pass reference images to maintain identity
3. **Be Specific**: Use exact terms (not "blue eyes" but "steel blue eyes")
4. **Document Everything**: Save prompts and settings
5. **Test Small**: Generate 1 shot first, verify consistency

## Prompt Anchoring Techniques

### Technique 1: Full Description in Every Shot
```
[Character name], [age], [ethnicity], with [body type] build,
[facial features], wearing [outfit].
```

### Technique 2: Consistency Anchors
```
IMPORTANT: Maintain identical appearance across all shots:
- Same face structure
- Same hair color and style
- Same clothing colors and fit
- Same body type
No identity drift allowed.
```

### Technique 3: Reference Image + Description
```
Reference: [URL]
Description: [detailed appearance]
Action: [what happens in scene]
```
