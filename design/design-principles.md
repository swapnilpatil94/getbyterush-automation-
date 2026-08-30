# GetByteRush Information-Design Principles

Reference for the Graphics Director (`scripts/graphics_director.py`). These
are the actual rules it applies, not aspirational writing — every rule here
maps to a concrete decision in code. Extracted from the supplied Pinterest
references as *principles*, not layouts to copy: none of these prescribe a
specific composition, all of them prescribe how to choose one.

## What visual treatment fits which content

| Content shape | Treatment | Why |
|---|---|---|
| One standout number, nothing else comparable | `giant_metric` | A single number's whole job is scale-shock. Making it huge and isolated *is* the encoding — a chart around one data point adds structure without adding information. |
| Two or more numbers meant to be compared to each other | `data_bars` | The moment a second comparable number exists, relative magnitude becomes the story, and magnitude is what a bar encodes and a bare numeral doesn't. Three same-size numerals side by side asks the reader to do the comparison in their head; bars do it for them. |
| Two competing options, positions, or products | `comparison_split` | Spatial contrast (two zones, one canvas) reads faster than "X vs Y" prose, and asymmetric color weight between the panels can signal which side the piece favors without saying so in text. |
| The same subject in two states over time | `before_after` | Not the same as comparison — comparison is *either/or*, before/after is *the same thing, transformed*. Sharing one frame (not two independent panels) is what signals "one subject changed" rather than "two options exist." |
| A sequence of dated or ordered events | `timeline` | Chronology is itself the information. A paragraph listing dates makes the reader reconstruct the sequence; a line with ordered markers shows it. |
| A mechanism or transformation with a clear start and end state | `process_flow` | "How something works" is a direction, not a list. An arrow from A to B carries the causality a sentence has to spell out. |
| A real screenshot, product shot, or webpage exists | `annotated_screenshot` | Evidence is proof, not decoration — show the real thing captured, don't describe it in prose. Add a leader-line annotation only when there's something specific worth pointing at (a UI element, a number on the page); a plain framed citation is still correct when there isn't. |
| A quotable line — from a source, an expert, or the story's own insight | `visual_quote` | Attribution matters for credibility; a quote wants a citation-styled frame (source name, not just italic text) to read as sourced rather than invented. |
| No hero visual has a genuine content match | `statement` | A calm, centered, full-bleed typographic slide is a real design choice for a "reset" beat — not a fallback to hide behind when nothing else fits. If most slides in a carousel end up here, that's a sign the underlying content is thin, not that the renderer needs more templates. |

## Visual hierarchy

Every slide has exactly one dominant element — the thing a one-second glance
lands on. Everything else is subordinate by size, weight, or position, never
by equal competing size. Three type roles, used consistently:

- **Display** (Fraunces, 900 weight) — the dominant element: headline or hero
  numeral. Only one per slide.
- **Support** (Archivo, 600 weight) — body copy, comparison values, process
  labels. Legible, never competing with display for attention.
- **Annotation** (IBM Plex Mono, tracked caps) — kickers, source lines,
  technical labels. Small and quiet by design; it's the register that makes
  the display type feel loud by contrast, not decoration in its own right.

A slide with two same-size, same-weight headline-scale elements has no
hierarchy — it has two slides fighting for the one slot.

## How to create curiosity

Withhold, don't obscure. The hook slide states the number or the claim
plainly and *omits the explanation* — the reader already has real
information (a number, a stated fact), just not the "why," which is a
different thing from being confusing. An incomplete number ("some agents use
more tokens") creates confusion; a complete number with no mechanism ("15X
more tokens.") creates curiosity. Cropping a hero numeral off the canvas
edge is the visual equivalent — the reader sees enough to know it's big, not
enough to see the whole shape, which is itself a small, deliberate
incompleteness.

## How to alternate visual intensity

A carousel of seven "loud" slides in a row exhausts attention before slide
four; seven "quiet" slides never earns it. The rhythm that works:

- Slide 1 (hook) is always loud — dark field, maximum type scale. It has one
  job (make someone stop) and no competing objective.
- The interior slides should not repeat the same background-intensity
  choice more than twice in a row when the content doesn't force it — this
  is a rhythm decision the Graphics Director makes at the whole-carousel
  level, not something any single slide can decide for itself.
- At least one interior slide should be a deliberate "reset": full negative
  space, centered, calm — this is what a `statement` slide is *for*. It
  isn't a quieter version of a hook, it's the release after tension the
  louder slides built.
- The payoff slide is calm, not loud — confidence reads differently from
  shock, and a carousel that ends on maximum intensity has nowhere left to
  land.

## How to avoid generic card/template aesthetics

- No uniform bordered box repeated across every slide. A citation gets a
  frame because it's citing something; a comparison gets two panels because
  there are two things to weigh. A slide with nothing to frame gets no
  frame — full-bleed color and type instead.
- No decorative corner brackets, no pill-shaped labels used purely as
  ornament, no drop shadows applied for their own sake. Every graphic
  element earns its place: an offset shadow on the evidence frame signals
  "this is a physical clipping," not "boxes look nicer with shadows."
- Vary panel treatment deliberately across a carousel: full-bleed color
  field, inset framed card, split two-panel, bare typography with no
  container at all. A carousel where every slide is "a box with a headline
  and a body paragraph inside it" is a template regardless of how many
  different colors it uses.
- Color is a decision, not a default. An accent color exists because the
  story's psychology or the editorial engine's own art direction called for
  it — never applied because a slide needs "some" color.

## Topic-specific art direction, brand DNA preserved

GetByteRush's recognizability comes from typography (Fraunces + Archivo +
IBM Plex Mono, used consistently), the masthead/footer thread (present,
identically positioned, on every slide regardless of composition), editorial
restraint, and composition quality — not from a fixed four-color palette.
Cream and near-black remain the two structural background modes (the
brand's actual "canvas," the thing that stays constant), but the accent
color is free to range across the full canonical palette the editorial
engine already validates against, driven by the story's own psychology
signal rather than clamped to a narrow default set. A security story earning
a red accent and a business story earning a gold one is the brand
*working*, not drifting.
