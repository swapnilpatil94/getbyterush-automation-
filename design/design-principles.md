# GetByteRush Information-Design Principles

Reference for the Graphics Director. V17 (`scripts/graphics_director_v17.py`
+ `scripts/visual_grammars.py`) is the current system; V16
(`scripts/graphics_director.py`) remains in the repo and still runs, but the
sections below describe what V17 actually does. Every rule here maps to a
concrete decision in code, not aspirational writing.

## V17: information → form, not text → type → decoration

The V16 system asked "which composition family fits this content?" and
picked from a fixed menu — which produced correct typography sitting on top
of a lot of empty canvas, not designed graphics. V17 asks a different
question per slide, in this order:

1. What is the ONE idea a viewer should get in under 2 seconds?
2. What is the information *relationship* here — progression, proportion,
   accumulation, comparison, contradiction, chronology, evidence, or a
   single isolated fact?
3. What concrete object or diagram IS that relationship, before any
   typography gets involved?
4. Only then: headline, body, kicker, accent.

**The mandatory self-check, for every non-cover, non-quote, non-reset
slide: remove the headline and body. Does the remaining graphic still
communicate something?** A dot-grid with 92 of 100 cells filled still says
"92%" with no caption. A numeral alone with an arrow says nothing — that
gap is exactly what V17 replaces. `headline_optional` in each slide's spec
records whether a given grammar/variant passes this test by construction;
`quote` and the plain `statement` reset are the two intentional exceptions
(design-principles for typographic beats, below, still apply to them).

## The 8 visual grammars

Selected deterministically in `visual_grammars.select()` from the same
free-text editorial fields V16 used (headline/body/context/implication/
kicker/source_label/visual_type/role) plus the story's psychology signal —
zero additional Gemini calls, same as V16. Each grammar has 1-2 composition
variants chosen by the actual shape of the extracted data (step count,
percentage magnitude, row count), not by which grammar looks nice.

| Grammar | Fires on | Variants | Primitive(s) |
|---|---|---|---|
| **Confrontation** | an explicit "everyone thinks X... actually Y" pattern in headline+body | `strike_reveal` (slide 1, full scale) / same, scaled down for interior slides | `hook_myth` / `confrontation` |
| **Proportional Field** | a clean 0-100% found in the slide's text | `dot_field` (extreme %, ≥85 or ≤15 — a striking sparse/dense grid) / `bar_split` (mid-range %, a single filled/unfilled bar) | `proportional_field` / `bar_split` |
| **Accumulation Trail** | a money/resource figure + loss language ("spent", "wasted", "never shipped"...) + extractable stages | `shrinking_trail` — blocks shrink stage to stage, the last one hollow | `accumulation_trail` |
| **Asymmetric Comparison** | `vs`/`versus` in the headline, an explicit comparison visual_type, or (weakest signal, checked last) both context and implication present | `matrix` (2-3 independently comma-split rows on each side — a real multi-metric table) / `two_panel` (single prose pair) | `comparison_matrix` / `comparison_split` |
| **Chronological Sequence** | 3+ distinct years found in the text | `multi_point` — marker size grows toward the most recent point (recency emphasis, not a fabricated magnitude claim) / `two_point` (THEN/NOW fallback) | `chronological_multi` / `timeline` |
| **Sequential System** | body splits into 2-6 parts on an explicit structural marker (→, em-dash, semicolon — never on words like "then"/"which", see below) | `chain_vertical` (vertical, node weight can ascend when the text itself signals growth) / `layered_stack` (when headline/concept says "layers"/"architecture"/"stack") | `chain_vertical` / `layered_stack` |
| **Evidence Board** | investigative psychology or an evidence-flavored visual_type, no real screenshot URL | `pinned_chips` (3-4 real facts — a stat, a date, a source tag; requires ≥3, see below) / `single_citation` (1-2 facts, reuses the citation-card frame) | `evidence_board` / `citation_card` |
| **Singular Object** | a real number exists (gd.metric's x/%-suffix match, or a bare large integer) | `metric_texture` — the numeral plus a literal tick-count field sized to its own value (15X → 15 marks), not decoration | `metric_texture` |
| *(reset, not one of the 8)* | nothing else matched, or content is genuinely a single typographic idea | `statement` / `quote` — legitimate typography-led beats, per the original design-principles below | `statement` / `visual_quote` |

`evidence_screenshot` (a real capturable URL) and `payoff` (last slide,
always calm) are structural, not grammar-selected — same as V16.

## Selection-order lessons (why the priority list looks like this)

Found by rendering real content and inspecting the PNGs, not by reasoning
in the abstract:

- **A real metric outranks the generic comparison fallback.** Almost every
  real editorial slide has non-empty context AND implication, so a rule
  as broad as "ctx and impl both present → comparison" swallows nearly
  everything, including slides whose whole point is a number ("15X MORE
  TOKENS." rendered as a generic two-panel comparison instead of the 15X
  that mattered). The generic ctx/impl comparison fallback is checked
  *after* percentage/money/dates/steps/quote/evidence *and* after a
  metric check — it only fires when nothing more specific exists.
- **Word-based sentence splitting garbles prose.** An early version split
  step/stage candidates on "then"/"which"/"so" — words that occur
  constantly in ordinary sentences — and produced fragments like "No one
  runs the" / "AI to build on" from one torn-in-half sentence. Step and
  stage extraction now only splits on unambiguous structural markers (→,
  em/en-dash, semicolon); content without one of those falls through to a
  simpler grammar instead of being garbled.
- **A weak role hint isn't enough to pick a rich grammar.** `role ==
  'open_loop'` used to be sufient on its own to trigger Sequential System,
  which routed a genuine two-way contrast ("chain-of-thought" vs "tree
  search") into a 2-node process chain — wrong grammar for a comparison.
  Sequential System now requires either 3+ real extracted steps or an
  explicit process-flavored visual_type.
- **Splitting on every comma corrupts thousand-separated numbers.**
  Comparison-matrix row extraction originally split on any comma, which
  cut "$40,000" into "$40" and "000" — silently changing the actual
  figure. The split regex now uses a negative lookahead so a comma
  immediately followed by a digit is left alone.
- **Density should scale with what's actually there.** A dot-field at a
  fixed small cell size, a 2-stage money trail, a 2-chip evidence board,
  and a matrix with only 2 rows all left large stretches of dead canvas
  below them even after the content was correct. Cell size, row height,
  chip size, and trail block width are now computed from the actual
  item count instead of being fixed constants, so a thinner slide's
  content still reads as deliberately composed rather than unfinished.
  Below a real content floor (e.g. 2 evidence chips), the fix is not
  "make the 2 chips bigger" — it's degrading to a simpler, honest grammar
  (`single_citation` instead of `pinned_chips`) rather than padding a
  thin composition to look fuller than it is.
- **Two different variants of one grammar back-to-back is real variety,
  not a repeat.** The whole-carousel rhythm pass only swaps a slide to
  the calm `statement` reset when the *exact* (grammar, variant) repeats
  consecutively — `chain_vertical` followed by `layered_stack` are
  different enough compositions to stand next to each other.

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
