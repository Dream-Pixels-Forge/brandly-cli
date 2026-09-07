# Video Styles Reference

Detailed breakdown of available video styles.

> **Important:** These are the ONLY valid values for `brandly video --style`. Image `--style-preset` values (`photorealistic`, `editorial`, `cinematic`, `commercial`, `documentary`) are a separate system.

---

## cinematic

**Credit cost:** 250  
**Use for:** Storytelling, narratives, brand films  
**Lighting:** Golden hour, natural  
**Camera:** Medium shots, tracking  
**Mood:** Emotional, engaging  
**Pace:** Moderate, deliberate

**Prompt tags:**
```
cinematic style, golden hour lighting,
storytelling, emotional narrative,
film quality, feature film aesthetic
```

**Best for:**
- Brand stories
- Product narratives
- Emotional connections
- Documentary-style content

---

## ugc

**Credit cost:** 150  
**Use for:** Social media, authentic content  
**Lighting:** Natural window light  
**Camera:** Medium, selfie-friendly  
**Mood:** Relatable, casual  
**Pace:** Quick, engaging

**Prompt tags:**
```
UGC style, authentic content,
social media aesthetic, smartphone feel,
casual, relatable, genuine
```

**Best for:**
- Social media ads
- Influencer content
- Testimonials
- Authentic reviews

---

## lifestyle

**Credit cost:** 170  
**Use for:** Aspirational, relatable living  
**Lighting:** Golden hour, natural  
**Camera:** Medium, lifestyle framing  
**Mood:** Warm, aspirational  
**Pace:** Relaxed, flowing

**Prompt tags:**
```
lifestyle style, aspirational,
warm atmosphere, everyday moments,
relatable, premium living
```

**Best for:**
- Home products
- Family-oriented campaigns
- Wellness content
- Everyday luxury

---

## montage

**Credit cost:** 200  
**Use for:** Fast-paced sequences, highlights reels  
**Lighting:** Variable, dramatic  
**Camera:** Quick cuts, dynamic angles  
**Mood:** Energetic, exciting  
**Pace:** Fast, rhythmic

**Prompt tags:**
```
montage style, quick cuts,
dynamic sequence, energetic pacing,
highlight reel, fast-paced
```

**Best for:**
- Event recaps
- Product feature highlights
- Behind-the-scenes compilations
- Multi-feature showcases

---

## continuous

**Credit cost:** 200  
**Use for:** Single-take storytelling  
**Lighting:** Natural, consistent  
**Camera:** Tracking, smooth movement  
**Mood:** Immersive, flowing  
**Pace:** Steady, continuous

**Prompt tags:**
```
continuous shot, single take,
uninterrupted flow, seamless movement,
cinéma vérité, long take
```

**Best for:**
- Immersive experiences
- Product in use demonstrations
- Walking tours
- Process videos

---

## unboxing

**Credit cost:** 180  
**Use for:** Product reveal experiences  
**Lighting:** Clean studio, bright  
**Camera:** Close-ups, macro details  
**Mood:** Exciting, discoverable  
**Pace:** Deliberate, revealing

**Prompt tags:**
```
unboxing style, product reveal,
opening experience, discovery moment,
first impression, premium packaging
```

**Best for:**
- New product launches
- Subscription boxes
- Tech gadgets
- Luxury packaging reveals

---

## collage_motion_graphic

**Credit cost:** 350  
**Use for:** Animated graphics, text overlays  
**Lighting:** N/A (graphic-based)  
**Camera:** N/A (motion design)  
**Mood:** Modern, dynamic  
**Pace:** Variable, rhythmic

**Prompt tags:**
```
motion graphic style, animated text,
kinetic typography, collage aesthetic,
modern graphic design, animated overlay
```

**Best for:**
- Social media explainers
- Data visualization
- Title sequences
- Animated advertisements

---

## brand_short_video

**Credit cost:** 280  
**Use for:** Short-form brand content  
**Lighting:** Studio quality  
**Camera:** Polished, professional  
**Mood:** Brand-aligned, consistent  
**Pace:** Tight, focused

**Prompt tags:**
```
brand short video, commercial quality,
brand identity, professional production,
advertising style, polished finish
```

**Best for:**
- Brand spot commercials
- Social ads
- Promotional content
- Product highlights

---

## explainer_video

**Credit cost:** 400  
**Use for:** How-to, educational content  
**Lighting:** Clear, informative  
**Camera:** Demonstrative, focused  
**Mood:** Educational, helpful  
**Pace:** Methodical, clear

**Prompt tags:**
```
explainer video, how-to style,
educational content, clear demonstration,
tutorial format, informative
```

**Best for:**
- Product tutorials
- Feature explanations
- How-to guides
- Educational content

---

## multi_shot

**Credit cost:** 300  
**Use for:** Multi-angle character/product campaigns  
**Lighting:** Consistent across shots  
**Camera:** Multiple angles, coverage  
**Mood:** Cohesive, comprehensive  
**Pace:** Varied by shot intent

**Prompt tags:**
```
multi-shot campaign, character consistency,
multiple angles, comprehensive coverage,
consistent lighting, same subject
```

**Best for:**
- Character-driven campaigns
- Product from multiple angles
- Consistency-focused shoots
- Multi-scene narratives

---

## Style Selection Guide

| Content Type | Best Style | Why |
|-------------|-----------|-----|
| Brand story | cinematic | Emotional connection |
| Social media ad | ugc | Relatable, shareable |
| Lifestyle product | lifestyle | Warm, aspirational |
| Product features | montage | Quick highlights |
| Immersive experience | continuous | Flowing, engaging |
| New product launch | unboxing | Discovery moment |
| Animated content | collage_motion_graphic | Modern, dynamic |
| Commercial spot | brand_short_video | Professional, polished |
| Tutorial/how-to | explainer_video | Clear, educational |
| Multi-angle campaign | multi_shot | Consistency focus |

---

## Invalid Video Styles

These are **image-only** `--style-preset` values and will fail with `brandly video --style`:

- ~~commercial~~ → Use `cinematic` or `brand_short_video` instead
- ~~documentary~~ → Use `cinematic` or `lifestyle` instead
- ~~luxury~~ → Use `cinematic` or `lifestyle` instead
- ~~action~~ → Use `montage` or `continuous` instead
