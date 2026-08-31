#!/usr/bin/env python3
"""GetByteRush V17 — visual grammar selection.

This module is the "art direction" brain: it looks at what a slide's
editorial content actually contains — a percentage, a money figure with
loss language, a sequence of connected steps, a set of dated events, a
myth/fact contradiction, a real comparison with multiple measurable rows —
and decides which of eight visual GRAMMARS (not templates) the information
itself calls for, plus which composition VARIANT within that grammar fits
the data shape (2 steps vs 5, extreme percentage vs mid-range, etc).

Hard rule carried over from graphics_director.py: never fabricate. Every
detector here either finds real structure in the text and returns a payload
built from it, or returns None so selection falls through to a simpler
grammar. Nothing here invents a comparison row, a date, or a step that
isn't actually in the editorial JSON.

Zero API calls — pure Python over the same 6 free-text fields
(headline/body/context/implication/kicker/source_label) editorial_engine.py
already writes. No new schema is required from Gemini.
"""
import re

import graphics_director as gd

# ---------------------------------------------------------------------------
# Structural signal extraction — the "does this content contain X" layer.
# Each function returns real extracted content or None; nothing here writes
# placeholder text.
# ---------------------------------------------------------------------------

# Structural markers only — arrows, em/en-dashes, semicolons. Word-based
# connectors ("then", "which", "so") were tried first and rejected: they
# match constantly inside ordinary prose ("before choosing which AI to
# build on") and split a real sentence into two nonsense fragments, not
# two real steps (confirmed by direct render — "No one runs the" / "AI to
# build on" is not a sequence, it's one sentence torn in half). A step
# extraction that garbles real content is worse than one that fires less
# often; sequences without an explicit marker fall through to the honest
# 2-point context/implication version instead.
_CONNECTOR_RE = re.compile(r'\s*(?:→|->|—|–|;)\s*')


def _connector_split(text, max_parts=5):
    parts = [p.strip(' .,:;') for p in _CONNECTOR_RE.split(gd.clean(text)) if p.strip(' .,:;')]
    return parts[:max_parts]


_GROWTH_WORDS = {'more', 'grow', 'grows', 'growing', 'expand', 'compound', 'cascade',
                  'stack', 'accumulate', 'multiply', 'spawn', 'burn', 'burns'}


def _sequence_steps(slide):
    """2-5 ordered step labels extracted from body's own structural markers,
    or None. Deliberately does NOT fall back to a bare context/implication
    pair: that pair is usually two ALTERNATIVES ("chain-of-thought" vs
    "tree search"), not two steps of one process — confirmed by direct
    render, where routing that fallback through here produced a two-node
    "chain" for what was actually a contrast, with the real payoff words
    truncated off each label. Content shaped like that now reaches the
    comparison grammar instead (see select()), which is what it actually is."""
    body_parts = _connector_split(slide.get('body'), 6)
    if len(body_parts) < 2:
        return None
    steps = [gd.punch(p, 6, 40) for p in body_parts]
    return [s for s in steps if s] or None


def _sequence_weights(slide, n):
    """Ascending weights only when the text itself signals growth/scale —
    otherwise every step gets equal visual weight rather than implying a
    magnitude claim the content never made."""
    pool = ' '.join(gd.clean(slide.get(f) or '') for f in ('headline', 'body')).lower()
    growing = any(w in pool for w in _GROWTH_WORDS)
    if not growing or n < 2:
        return [0.62] * n
    step = 0.85 / (n - 1)
    return [round(0.15 + step * i, 2) for i in range(n)]


_PCT_RE = re.compile(r'\b(\d{1,3})\s?%')


def _percentage(text):
    m = _PCT_RE.search(gd.clean(text))
    if not m:
        return None
    v = int(m.group(1))
    return v if 0 <= v <= 100 else None


_MONEY_RE = re.compile(r'\$\s?[\d,]+(?:\.\d+)?\s?[KkMmBb]?\b')
_LOSS_WORDS = {'spent', 'wasted', 'burned', 'burnt', 'lost', 'never shipped', 'disappeared',
               'dropped', 'abandoned', 'gone', 'vanished', 'write-off', 'wrote off', 'nothing to show'}


def _money_value(text):
    m = _MONEY_RE.search(gd.clean(text))
    return m.group(0).replace(' ', '') if m else None


def _has_loss_language(text):
    t = gd.clean(text).lower()
    return any(w in t for w in _LOSS_WORDS)


def _trail_stages(slide):
    """Returns (stages, lead_in) or None. `stages` are 2-4 short items
    pulled from body/context/implication via the same structural-marker
    split as sequence_steps. The fragment BEFORE the first marker is
    usually a full lead-in sentence, not a short stage label — truncating
    it to a 3-word stage name produced a garbled fragment (confirmed by
    direct render: "They spent every"), so a long first fragment is
    dropped from the stage list and returned as `lead_in` instead, to use
    as the slide's caption where it actually reads as a sentence."""
    pool = ' '.join(gd.clean(slide.get(f) or '') for f in ('body', 'context', 'implication'))
    parts = [p for p in _connector_split(pool, 5) if p]
    lead_in = None
    if parts and len(parts[0]) > 46:
        lead_in, parts = parts[0], parts[1:]
    stages = [gd.punch(p, 5, 34) for p in parts]
    return (stages[:4], lead_in) if len(stages) >= 2 else None


# Negative lookahead on the comma keeps "$40,000" intact — splitting on
# every comma cut thousand-separated numbers in half (confirmed by direct
# render: "average cost $40,000" became the row values "$40" and "000",
# silently changing the actual figure, not just the layout).
_COMPARE_SPLIT_RE = re.compile(r',(?!\d)\s*| and ', re.I)


def _comparison_rows(slide):
    """2-3 (row_label, a_val, b_val) rows when context and implication each
    independently break into that many comma/and-separated clauses — a
    real multi-metric comparison, not a single prose pair. Falls through
    to the plain two-panel treatment (via graphics_director._comparison_sides)
    when the content doesn't support a matrix."""
    ctx_parts = [p.strip() for p in _COMPARE_SPLIT_RE.split(gd.clean(slide.get('context') or '')) if p.strip()]
    impl_parts = [p.strip() for p in _COMPARE_SPLIT_RE.split(gd.clean(slide.get('implication') or '')) if p.strip()]
    n = min(len(ctx_parts), len(impl_parts), 3)
    if n < 2:
        return None
    return [(f'{i+1:02d}', gd.punch(ctx_parts[i], 7, 42), gd.punch(impl_parts[i], 7, 42)) for i in range(n)]


_BARE_NUM_RE = re.compile(r'\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?(?:million|billion|thousand)\b|\b\d{2,}\b', re.I)


def _bare_number(text):
    """A standalone large integer ("700", "22 million") with no x/%
    suffix — gd.metric() intentionally only matches ratio/percent tokens,
    but a bare large number is exactly the "huge statistic" a STOP slide
    needs, so the singular_object grammar gets its own, wider detector
    rather than showing a plain typographic headline for a slide whose
    whole point is one big number (confirmed missing by direct render —
    "700 JOBS." rendered as prose, not as the number it actually is)."""
    m = _BARE_NUM_RE.search(gd.clean(text))
    return m.group(0) if m else None


_YEAR_RE = re.compile(r'\b(?:19|20)\d{2}\b')


def _chrono_years(slide):
    pool = ' '.join(gd.clean(slide.get(f) or '') for f in ('headline', 'body', 'context', 'implication'))
    years = sorted(set(_YEAR_RE.findall(pool)))
    return years if len(years) >= 3 else None


def _evidence_chips(slide):
    """2-4 small real facts (a stat, a date, a source tag, a short note) —
    used when the story has investigative texture but no capturable
    screenshot, so the "evidence" is represented as real pinned facts
    rather than a placeholder frame."""
    chips = []
    m = gd.metric(slide.get('headline') or slide.get('body'))
    if m:
        chips.append(('stat', m))
    pool = ' '.join(gd.clean(slide.get(f) or '') for f in ('body', 'context', 'implication'))
    years = _YEAR_RE.findall(pool)
    if years:
        chips.append(('date', years[0]))
    sl = gd.clean(slide.get('source_label'))
    if sl:
        chips.append(('tag', sl.upper()))
    ctx = gd.clean(slide.get('context'))
    if ctx and len(chips) < 3:
        chips.append(('note', gd.punch(ctx, 6, 40)))
    return chips[:4] if len(chips) >= 2 else None


_LAYER_WORDS = {'layer', 'layers', 'architecture', 'stack', 'pipeline', 'infrastructure'}


def _mentions_layers(slide):
    pool = f"{slide.get('visual_concept', '')} {slide.get('headline', '')}".lower()
    return any(w in pool for w in _LAYER_WORDS)


_SCREENSHOT_VT = {'evidence', 'screenshot', 'product', 'photo', 'photographic'}
_INVESTIGATION_WORDS = {'investigation', 'mystery', 'discovery'}
_QUOTE_VT = {'quote'}


def _psych_words(story):
    return gd._psych_words(story)


# ---------------------------------------------------------------------------
# Grammar + variant selection. Priority order matches "most specific,
# most-information-preserving signal first" — the same discipline
# graphics_director.py already uses for primitive selection, one level up.
# ---------------------------------------------------------------------------

STOP_GRAMMARS = {'confrontation', 'proportional_field', 'accumulation_trail', 'comparison', 'singular_object'}


def select(slide, story, is_first, is_last, has_evidence_url):
    vt = gd.clean(slide.get('visual_type')).lower()
    role = gd._canon_role(slide)
    pool = ' '.join(gd.clean(slide.get(f) or '') for f in ('headline', 'body', 'context', 'implication'))

    candidates = []

    myth = gd._myth_fact_split(slide.get('headline'), slide.get('body'))
    if myth:
        candidates.append(('confrontation', 'strike_reveal', {'myth_split': myth}))

    if vt in _SCREENSHOT_VT and has_evidence_url:
        candidates.append(('evidence_screenshot', 'framed', {}))

    has_vs = bool(re.search(r'\bvs\.?\b|\bversus\b', slide.get('headline') or '', re.I))
    ctx, impl = gd.clean(slide.get('context')), gd.clean(slide.get('implication'))
    explicit_comparison = has_vs or vt in ('comparison', 'versus', 'vs')
    if explicit_comparison:
        rows = _comparison_rows(slide)
        if rows:
            candidates.append(('comparison', 'matrix', {'rows': rows}))
        else:
            (a_label, a_val), (b_label, b_val) = gd._comparison_sides(slide)
            candidates.append(('comparison', 'two_panel', {'sides': (a_label, a_val, b_label, b_val)}))

    pct = _percentage(pool)
    if pct is not None:
        variant = 'dot_field' if (pct >= 85 or pct <= 15) else 'bar_split'
        candidates.append(('proportional_field', variant, {'pct': pct}))

    money = _money_value(pool)
    if money and _has_loss_language(pool):
        trail = _trail_stages(slide)
        if trail:
            stages, lead_in = trail
            candidates.append(('accumulation_trail', 'shrinking_trail', {'start_value': money, 'stages': stages, 'lead_in': lead_in}))

    years = _chrono_years(slide)
    if years:
        candidates.append(('chronological_sequence', 'multi_point', {'years': years}))
    elif vt in ('timeline', 'chronology', 'history') or role == 'timeline':
        ctx, impl = gd.clean(slide.get('context')), gd.clean(slide.get('implication'))
        if ctx and impl:
            candidates.append(('chronological_sequence', 'two_point', {'points': [('THEN', gd.punch(ctx, 5, 34)), ('NOW', gd.punch(impl, 5, 34))]}))

    steps = _sequence_steps(slide)
    if steps and (len(steps) >= 3 or vt in ('flow', 'process', 'mechanism')):
        variant = 'layered_stack' if _mentions_layers(slide) else 'chain_vertical'
        candidates.append(('sequential_system', variant, {'steps': steps, 'weights': _sequence_weights(slide, len(steps))}))

    if vt in _QUOTE_VT or role == 'quote' or 'quote' in (slide.get('visual_concept') or '').lower():
        candidates.append(('quote', 'pull_quote', {}))

    if not has_evidence_url:
        chips = _evidence_chips(slide)
        # 3+ real facts earns the pinned-board treatment; 2 is too thin to
        # fill that composition without visibly padding it (confirmed by
        # direct render: 2 chips left most of the canvas empty even after
        # scaling them up) — degrades to the single-citation card instead.
        if chips and len(chips) >= 3 and (bool(_psych_words(story) & _INVESTIGATION_WORDS) or vt in _SCREENSHOT_VT):
            candidates.append(('evidence_board', 'pinned_chips', {'chips': chips}))
        elif (vt in _SCREENSHOT_VT or role == 'proof') and gd.clean(slide.get('source_label')):
            candidates.append(('evidence_board', 'single_citation', {
                'source_label': gd.clean(slide.get('source_label')),
                'quote_text': gd.clean(slide.get('body')) or gd.clean(slide.get('headline')),
            }))

    # A real extracted number (ratio/percent-style via gd.metric, or a bare
    # large integer) outranks the generic ctx-vs-impl fallback below — most
    # real editorial slides have SOME context/implication text, so without
    # this ordering the generic fallback swallowed genuinely strong metric
    # slides almost every time (confirmed on the real production story:
    # "15X MORE TOKENS." and "30X THROUGHPUT PER MEGAWATT." both rendered
    # as a generic two-panel comparison instead of the number that's
    # actually the whole point of the slide).
    m = gd.metric(slide.get('headline') or slide.get('body')) or _bare_number(slide.get('headline'))
    if m:
        candidates.append(('singular_object', 'metric_texture', {'metric_value': m}))

    # Generic two-state fallback: context/implication both present but no
    # stronger signal (percentage/money/dates/steps/quote/evidence/metric)
    # claimed the slide.
    if not explicit_comparison and ctx and impl:
        (a_label, a_val), (b_label, b_val) = gd._comparison_sides(slide)
        candidates.append(('comparison', 'two_panel', {'sides': (a_label, a_val, b_label, b_val)}))

    candidates.append(('singular_object', 'statement', {'metric_value': None}))

    if is_first:
        stop_candidates = [c for c in candidates if c[0] in STOP_GRAMMARS]
        return (stop_candidates or candidates)[0]

    return candidates[0]
