# GetByteRush Carousel Design System V2 — Editorial Poster

## Reference direction

Use the supplied editorial carousel reference as the primary composition benchmark: bold typographic blocks, near-black/cream fields, one strong signal accent, numbered editorial rhythm, asymmetry, micro-details, and minimal copy.

## Core principle

**One slide = one idea = one visual action.**

Do not render dense paragraphs, generic UI cards, or internal visual-direction instructions.

## Canvas

- 1080 × 1350 px
- Safe horizontal margin: 64 px
- Strong negative space
- Oversized typography
- Asymmetric magazine/editorial composition

## Brand palette

- Near Black: `#0B0D0C`
- Warm Cream: `#F3EBDD`
- Deep Forest: `#12352B`
- Restrained Gold: `#C9A45C`
- Signal Red: `#B70C07`
- Technical Blue: `#426A78`
- Pattern Interrupt Lime: `#B7E32B`

Use one dominant background and one signal accent per slide. Never use every accent simultaneously.

## Composition families

1. **Statement / Hook** — oversized headline, sparse field, tiny metadata.
2. **Technical Diagram** — two meaningful nodes, clear directional relationship.
3. **Evidence** — real source screenshot contained in a deliberate frame, `object-fit: contain`.
4. **Metrics** — three numbers with one featured metric.
5. **Pattern Interrupt** — strong signal field, minimal copy, swipe reset.
6. **Quote / Statement** — typographic quote treatment with editorial rule.
7. **Payoff** — large final statement, brand signature.

## Content budgets

- Hero: 3–8 words preferred; never compensate by shrinking type.
- Supporting line: ≤ 12 words preferred.
- Body: ≤ 25 words.
- Labels: 1–4 words.
- Numbers: oversized and isolated.
- Paragraphs on canvas: prohibited.

## Content safety

Never visibly render:

- `visual_concept`
- `visual_direction`
- `visual_strategy`
- `design_direction`
- `layout_instruction`
- generation notes
- template placeholders such as `INPUT`, `PROCESS`, `OUTCOME`
- phrases such as `callout graphic`, `data graphic showing`, `highlight that`

These fields may influence composition logic but are not visible editorial copy.

## Neuromarketing rhythm

For a typical 6–8 slide story:

`Interrupt → Curiosity → Explain → Proof → Pattern Interrupt → Reveal → Implication → Payoff`

Use a strong contrast slide around the middle of the carousel to reset attention.

## Evidence

Evidence is proof, not decoration. Capture only when the slide explicitly uses an evidence composition. Preserve source aspect ratio with `object-fit: contain`; never stretch screenshots.

## Quality gate

Every generated package must pass:

- 1080 × 1350 PNG dimensions
- expected slide count
- no internal design-text leaks
- no generic placeholders
- evidence PNG validity
- one isolated package committed per render
- Gemini calls = 0 for renderer-only runs
