# GetByteRush Carousel Design System V3 — V16 Renderer

Supersedes v2 for anything touching composition selection or the family
roster; the brand palette and content-safety rules in v2 still hold.
Written against `scripts/carousel_art_renderer_v16.py`.

## What changed from v2 / why this file exists

V2 described the palette and named 7 "composition families," but the
renderer that shipped against it (V9–V15) actually assigned exactly one
fixed pixel template per story-arc *position* — slide 3 always got the
same layout regardless of what slide 3 was about. V16 fixes that: the
family a slide renders as is chosen from the editorial JSON's own
`visual_type` field first, so two different stories with different
content shapes produce different carousels, not the same carousel with
different words in it.

## The composition roster (9 families)

| Family | Function | Reads for content | Typical `visual_type` |
|---|---|---|---|
| `comp_hook` | 1-second opener, oversized headline + optional bled numeral or arrow mark | first slide, always | — (structural) |
| `comp_context` | staircase escalation diagram, "why this is building" | open/setup beats | `open_loop` role |
| `comp_evidence` | framed screenshot or citation card, source-attributed | proof, product shots, breaking-news announcements | `evidence`, `screenshot`, `product` |
| `comp_metric` | one oversized numeral (or oversized word if no clean number) dominates the canvas | single hero statistic | `metric`, `stat`, `number`, `reveal` |
| `comp_datablock` | 2–3 numbers side by side with mono labels | multiple related statistics | `data`, `stats`, `statistics` |
| `comp_comparison` | two colored panels split by a "VS" badge | A-vs-B, before/after, trade-offs | `comparison`, `versus`, `vs` |
| `comp_statement` | centered, full-bleed typographic statement, calm pacing | quotes, insight, the carousel's "reset" beat | `typography`, `quote`, `insight` |
| `comp_process` | two-node FROM→TO flow with a connecting arrow | mechanism, transformation | `diagram`, `flow`, `process`, `mechanism` |
| `comp_payoff` | quiet close, brand signature lockup | last slide, always | — (structural) |

## Selection algorithm (`select_role`, in the renderer)

1. **Slide 1 is always `comp_hook`, the last slide is always `comp_payoff`.**
   This is positional, not content-driven — every carousel needs a
   1-second opener and a memorable, on-brand close regardless of what
   the story is about. Everything else below applies only to interior
   slides.
2. **`visual_type` (content type) decides first**, via `VISUAL_TYPE_MAP`.
   A slide tagged `comparison` renders as a comparison no matter which
   story beat it happens to land on.
3. **Story-arc `role` is the fallback** (`canon_role` — maps
   `interrupt`/`open_loop`/`proof`/`escalation`/`pattern_interrupt`/
   `implication`/`payoff` to a family) for content whose `visual_type`
   isn't recognized.
4. **A positional cycle is the last resort** (`POSITION_CYCLE`), so
   content that matches neither still varies slide-to-slide instead of
   collapsing onto one family.

This ordering is what makes two different topics produce two different
visual *structures*, not just different text in the same boxes — verify
by reading `select_role`'s output for a story before assuming its shape.

## Design primitives

Reusable elements composed differently inside each family, not
duplicated per family:

- **Editorial grid** — 64px safe margin (`M`), masthead (wordmark +
  page count) at 48px, footer (tagline pair) at 48px from bottom, both
  with a 1px hairline rule. Identical on every slide — this is the
  "one publication" thread that holds the carousel together while
  compositions vary.
- **Display typography** — Fraunces (variable serif) for anything that
  needs to *feel* like an editorial headline: `.serif` class, weight
  900 for display, negative letter-spacing scaled to size via `scale()`.
- **Body/label typography** — Archivo (grotesk sans) for supporting
  text and body copy; IBM Plex Mono for kickers, source lines, and
  technical annotations — the tension between serif display and mono
  technical labels is the "editorial magazine + tech publication" fusion.
- **Content-length tiering** (`scale()`) — headline/numeral font sizes
  step down as character count grows, instead of a fixed size that
  either overflows or wastes space. Never the sole defense against long
  copy — see below.
- **Screenshot/evidence frame** — white card, subtle single-offset
  shadow tinted with the slide's accent, slight rotation, pinned source
  tag. Reused for product shots (`comp_evidence` with `visual_type:
  product`) without a separate family — a product photo and a proof
  screenshot are the same visual grammar.
- **Citation fallback card** — when no screenshot was captured (or none
  applies), a dark card quoting `source_story.title`/`source`/`url`
  from the real editorial JSON. Never fabricated placeholder text.
- **Oversized numeral / oversized word** — `comp_metric`'s core move;
  falls back to the first 1–2 words of the headline, sized up, when no
  clean numeric metric exists in the text — never a bare fallback
  symbol bled off-canvas (a prior bug: an unmatched metric rendered as
  a nearly-invisible cropped "×" fragment; fixed by giving both
  `comp_hook` and `comp_metric` real content-shaped fallbacks).
- **Multi-metric extraction** (`metrics_all()`) — pulls up to 3 distinct
  `\d+(?:\.\d+)?[x%]` values from a slide's combined text for
  `comp_datablock`; degrades to `comp_metric` if fewer than 2 are found,
  rather than rendering an empty or lopsided block.
- **Comparison split** — two panels (dark neutral vs. accent-colored,
  not two equal neutrals) with a straddling "VS" badge; the color
  asymmetry does real work — it visually weights one side, which is a
  legitimate editorial technique, not decoration.
- **Flow diagram** — SVG line + arrowhead + circles only; all text
  labels are separate HTML blocks with `max-width` and normal wrapping,
  never SVG `<text>` (SVG text doesn't wrap — an earlier version put
  FROM/TO labels directly in the SVG and they collided when content ran
  long; the fix was moving labels out of the SVG entirely, not
  shortening the text harder).
- **Editorial rule** — thin horizontal rules bracket pull-quotes/stats
  and separate a callout from its supporting line; used sparingly, one
  or two per slide, never as a grid.
- **Brand signature** — large italic Fraunces "getByteRush." wordmark,
  `comp_payoff` only. The one place the brand asserts itself at scale
  instead of staying in the masthead/footer thread.

## Content-length handling

Two independent mechanisms, not one:

1. `punch()`/`support()` (from V9, reused unchanged) truncate at a
   word/char budget with an ellipsis, word-boundary safe.
2. `scale()` steps the *display size* down as the truncated text gets
   longer, so a short punchy headline gets to be huge and a longer one
   doesn't overflow — verified under a synthetic stress test with
   headlines/bodies deliberately 2–3x the length of real editorial
   output, across every family, with no overflow or overlap.

Composition choice itself is also part of the length response:
`comp_datablock` degrades to `comp_metric` when it can't find enough
data points rather than rendering broken content — selecting a
*different family* is the last line of defense, not just shrinking type.

## Known limits / what to check before trusting a new story shape

- `metric()`'s regex requires the matched number to be followed by a
  non-letter — verified against `%`, `x`/`X`, decimals, and end-of-string,
  but a genuinely novel numeric format (e.g. `1:4` ratios, currency) will
  fall through to the word-fallback path, not crash — check the render
  if a story leans on an unusual stat format.
- `VISUAL_TYPE_MAP` is a fixed vocabulary. If the editorial engine ever
  emits a `visual_type` value not listed here, the slide falls back to
  `role`/position rather than failing — expected, but worth checking
  `select_role`'s output (see `scripts/fixtures/render_all.py`) for any
  new story shape rather than assuming it landed on the intended family.
- Evidence capture depends on live network access to the source URL at
  render time; it fails closed to the citation-card fallback (confirmed
  in both local and CI environments) rather than crashing the render.

## Regression fixtures

`scripts/fixtures/` holds 6 renderer-only test stories (never touched
by Gemini/the editorial pipeline) spanning consumer product, security,
social platforms, AI model comparison, business impact, and human
psychology, at slide counts from 5 to 9. `scripts/fixtures/render_all.py`
renders all of them via `GBR_INPUT`/`GBR_OUT` env overrides (production
`data/selected_story.json` is never touched) and prints which family
each slide selected, so a future renderer change can be checked for
generalization regressions in seconds instead of by rendering one story
and eyeballing it.
