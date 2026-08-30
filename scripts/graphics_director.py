#!/usr/bin/env python3
"""GetByteRush Graphics Director.

Sits between the editorial JSON and the renderer. Produces a structured
design specification per slide — hero primitive, typography sizing,
accent/bg, psychology-driven intensity, rhythm across the carousel — that
`carousel_art_renderer_v16.py` executes. Never generates HTML/CSS itself
and never calls Gemini or any other model: every decision here is a
deterministic rule over the editorial JSON's own fields, informed by
design/design-principles.md.

This is deliberately not a new creative brain — see the architecture
report that preceded this file: editorial_engine.py's single Gemini call
already emits `visual_concept`, `psychological_goal`, `design.
visual_strategy`, `design.primary_psychology`, `design.emotional_mode`
per topic, none of which the renderer previously read. Most of what this
module does is finally use signal that was already being generated and
discarded; the rest is deterministic derivation, exactly as before, just
formalized into its own layer instead of scattered across composition
functions.
"""
import re

# ---------------------------------------------------------------------------
# Text utilities (duplicated minimally rather than imported from the
# renderer, so this module has no dependency on carousel_art_renderer_v16 —
# the director must be importable and testable standing alone).
# ---------------------------------------------------------------------------

def clean(v):
    import html
    s = html.unescape(str(v or ''))
    s = re.sub(r'https?://\S+', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def words(v):
    return clean(v).split()


def punch(v, limit=8, chars=68):
    s = clean(v).strip(' .,:;!?—–-')
    if len(words(s)) <= limit and len(s) <= chars:
        return s
    x = ' '.join(words(s)[:limit]).rstrip(' .,:;!?—–-')
    return x if len(x) <= chars else x[:chars].rsplit(' ', 1)[0]


def support(v, limit=18, chars=150):
    s = clean(v)
    if len(words(s)) > limit:
        s = ' '.join(words(s)[:limit]).rstrip(' .,;:') + '…'
    return s if len(s) <= chars else s[:chars].rsplit(' ', 1)[0] + '…'


_METRIC_RE = re.compile(r'\b\d+(?:\.\d+)?\s*(?:[xX](?![a-zA-Z])|%)')


def metric(text):
    m = _METRIC_RE.search(clean(text))
    return m.group(0).replace(' ', '') if m else ''


def metrics_all(text, limit=4):
    seen, out = [], []
    for mo in _METRIC_RE.finditer(clean(text)):
        v = mo.group(0).replace(' ', '')
        if v.upper() not in seen:
            seen.append(v.upper())
            out.append(v)
        if len(out) >= limit:
            break
    return out


def _magnitude(v):
    """Numeric magnitude of a "15X" / "80%" style token, for bar sizing."""
    m = re.match(r'([\d.]+)', v)
    return float(m.group(1)) if m else 0.0


def _hex(v):
    c = clean(v)
    return c if re.fullmatch(r'#[0-9a-fA-F]{6}', c) else None


# ---------------------------------------------------------------------------
# Brand palette. Cream/near-black are the two structural background modes —
# the actual constant, per design-principles.md — while the accent is free
# to range across the full canonical palette editorial_engine.py's own
# prompt already validates every slide's accent_color against, rather than
# a narrow default set. See BRAND_ACCENT vs PSYCH_ACCENT below.
# ---------------------------------------------------------------------------
CREAM = '#F3EBDD'
INK = '#0B0D0C'

BRAND_RED = '#B70C07'
BRAND_FOREST = '#12352B'
BRAND_GOLD = '#C9A45C'
BRAND_LIME = '#B7E32B'

# Canonical palette from editorial_engine.py's prompt (the same 15 colors
# Gemini is already constrained to per-slide) — the pool topic-specific
# psychology-derived accents draw from, so a security story and a business
# story can land on genuinely different colors instead of the same four.
CANON_PALETTE = {
    'forest': '#12352B', 'red_alt': '#E53935', 'teal': '#2D8C7A', 'lime': '#B7E32B',
    'steel': '#527A91', 'orange': '#F26A21', 'blue_grey': '#426A78', 'blue': '#3159C9',
    'chartreuse': '#C7F000', 'tan_gold': '#C9A75D', 'tan': '#B99A5B', 'purple': '#7457FF',
    'blue2': '#4B78A8', 'sage': '#BFDCCF', 'grey': '#D7D9D5',
}

# Exact match against editorial_engine.py's own enums first (this is the
# real vocabulary Gemini is constrained to, not a guess), substring
# fallback second for resilience if the schema drifts slightly.
_PSYCH_TO_ACCENT = {
    'urgency': BRAND_RED, 'tension': BRAND_RED, 'scale': BRAND_RED, 'contradiction': BRAND_RED,
    'money': BRAND_GOLD,
    'explainer': CANON_PALETTE['blue_grey'], 'understanding': CANON_PALETTE['blue_grey'], 'utility': CANON_PALETTE['blue_grey'],
    'investigation': CANON_PALETTE['purple'], 'mystery': CANON_PALETTE['purple'], 'discovery': CANON_PALETTE['purple'],
    'competition': CANON_PALETTE['orange'], 'comparison': CANON_PALETTE['orange'],
    'curiosity': BRAND_LIME, 'surprise': BRAND_LIME,
    'story': CANON_PALETTE['teal'], 'experiment': CANON_PALETTE['teal'],
    'timeline': CANON_PALETTE['steel'],
    'data': CANON_PALETTE['chartreuse'],
}
_INTENSITY_WORDS = {'urgency', 'tension', 'scale', 'surprise', 'contradiction', 'shock', 'crisis'}


def _psych_words(story):
    d = story.get('design') or {}
    text = f"{d.get('primary_psychology', '')} {d.get('emotional_mode', '')}".lower()
    return set(re.findall(r'[a-z]+', text))


def psychology_accent(story):
    for w in _psych_words(story):
        if w in _PSYCH_TO_ACCENT:
            return _PSYCH_TO_ACCENT[w]
    return None


def psychology_intense(story):
    return bool(_psych_words(story) & _INTENSITY_WORDS)


def accent_of(slide, story, fallback):
    return (_hex(slide.get('accent_color'))
            or _hex((story.get('design') or {}).get('accent_color'))
            or psychology_accent(story)
            or fallback)


def bg_of(slide, dark_default):
    mode = clean(slide.get('background_mode')).lower()
    if mode == 'black':
        return INK, CREAM
    if mode == 'cream':
        return CREAM, INK
    return (INK, CREAM) if dark_default else (CREAM, INK)


def scale(text, table):
    n = len(clean(text))
    for limit, size in table:
        if n <= limit:
            return size
    return table[-1][1]


# ---------------------------------------------------------------------------
# CTA — renderer/director-owned copy, never touching Gemini.
# ---------------------------------------------------------------------------
_CTA_LINES = [
    'Save this before you need it again.',
    'Send this to the person who needs to see it.',
    'We test the stuff everyone else just explains.',
    'Follow along — we go deeper than the headline.',
    'This is the version worth remembering.',
]


def cta_line(story):
    import zlib
    key = clean(story.get('story_title') or story.get('story_sentence') or '')
    return _CTA_LINES[zlib.crc32(key.encode('utf-8')) % len(_CTA_LINES)] if key else _CTA_LINES[0]


# ---------------------------------------------------------------------------
# Content-type -> primitive. visual_type first (including visual_concept
# keyword scan, since that field is real per-slide creative direction
# Gemini already writes and the renderer previously never read), role
# second, position last — same priority discipline as before, extended
# with three primitives (data_bars, timeline, before_after) the old
# VISUAL_TYPE_MAP had no equivalent for at all.
# ---------------------------------------------------------------------------
_VISUAL_TYPE_TO_PRIMITIVE = {
    'comparison': 'comparison_split', 'versus': 'comparison_split', 'vs': 'comparison_split',
    'metric': 'metric_or_bars', 'stat': 'metric_or_bars', 'number': 'metric_or_bars',
    'shock-number': 'metric_or_bars', 'reveal': 'metric_or_bars',
    'data': 'data_bars', 'stats': 'data_bars', 'statistics': 'data_bars', 'datapoints': 'data_bars',
    'timeline': 'timeline', 'chronology': 'timeline', 'history': 'timeline',
    'evidence': 'annotated_screenshot', 'screenshot': 'annotated_screenshot', 'product': 'annotated_screenshot',
    'photo': 'annotated_screenshot', 'photographic': 'annotated_screenshot',
    'diagram': 'process_flow', 'flow': 'process_flow', 'process': 'process_flow', 'mechanism': 'process_flow',
    'before_after': 'before_after', 'before/after': 'before_after', 'transformation': 'before_after',
    'typography': 'statement', 'insight': 'statement', 'statement': 'statement',
    'quote': 'visual_quote',
    'final': 'payoff',
}

# Keyword scan of visual_concept — Gemini's own free-text creative
# direction for the slide — as a secondary signal when visual_type alone
# is ambiguous or generic. Not exact-match; substring, same graceful-
# degradation discipline as the psychology buckets.
_CONCEPT_KEYWORDS = [
    (('screenshot', 'interface', 'ui ', 'product shot'), 'annotated_screenshot'),
    (('comparison', ' vs ', 'versus', 'side by side'), 'comparison_split'),
    (('timeline', 'chronolog', 'over time', 'history of'), 'timeline'),
    (('flow diagram', 'flowchart', 'architecture', 'mechanism', 'pipeline'), 'process_flow'),
    (('quote', 'said', 'according to'), 'visual_quote'),
    (('typography', 'statement', 'bold text'), 'statement'),
]

# Positional variety net, primitive-named now instead of family-named.
# before_after included here (not just via explicit visual_type) since
# nothing in today's schema reliably distinguishes "these are two
# competing options" from "this is the same thing before and after" —
# an honest limitation, noted in the accompanying report, not hidden.
POSITION_CYCLE = ['process_flow', 'annotated_screenshot', 'metric_or_bars', 'statement', 'comparison_split', 'before_after']

_ROLE_TO_PRIMITIVE_HINT = {
    'open_loop': 'process_flow', 'proof': 'annotated_screenshot', 'escalation': 'metric_or_bars',
    'pattern_interrupt': 'statement', 'implication': 'process_flow',
}


def _canon_role(slide):
    return clean(slide.get('role')).lower().replace(' ', '_')


def _pick_primitive(slide, i, total, taken_by_visual_type):
    vt = clean(slide.get('visual_type')).lower()
    if vt in _VISUAL_TYPE_TO_PRIMITIVE:
        return _VISUAL_TYPE_TO_PRIMITIVE[vt], True
    concept = clean(slide.get('visual_concept')).lower()
    for kws, prim in _CONCEPT_KEYWORDS:
        if any(k in concept for k in kws):
            return prim, True
    role = _canon_role(slide)
    if role in _ROLE_TO_PRIMITIVE_HINT:
        return _ROLE_TO_PRIMITIVE_HINT[role], False
    return POSITION_CYCLE[i % len(POSITION_CYCLE)], False


def _metric_or_bars(slide):
    """The "should this become a chart" decision design-principles.md
    describes: one comparable number stays a giant numeral (the isolation
    is the encoding); two or more become proportional bars."""
    pool = ' '.join(clean(slide.get(f) or '') for f in ('headline', 'body', 'context', 'implication'))
    nums = metrics_all(pool, limit=4)
    return 'data_bars' if len(nums) >= 2 else 'giant_metric'


def _comparison_sides(slide):
    h = clean(slide.get('headline'))
    m = re.search(r'(.+?)\s+(?:vs\.?|versus)\s+(.+)', h, re.I)
    if m:
        a_label, b_label = punch(m.group(1), 3, 22), punch(m.group(2), 3, 22)
    else:
        a_label, b_label = 'Before', 'After'
    a_val = support(slide.get('context') or slide.get('body'), 14, 105)
    b_val = support(slide.get('implication') or slide.get('body'), 14, 105)
    return (a_label, a_val), (b_label, b_val)


def _timeline_points(slide):
    """Two points — start and end, from context/implication. A 3-point
    version was tried first and rejected: the schema has no third field
    distinct from what's already on screen, since the slide's own headline
    and body are always shown in the header above the timeline, so a
    middle marker could only ever duplicate one of them verbatim (verified
    by direct render — "SHIFT" literally repeated the slide's headline).
    Two honest points beat three where one is padding."""
    ctx = punch(slide.get('context') or '', 5, 34) or 'Then'
    imp = punch(slide.get('implication') or '', 5, 34) or 'Now'
    return [('THEN', ctx), ('NOW', imp)]


def _annotation_label(slide):
    """A leader-line annotation only when there's something specific and
    short enough to point at — context/implication under ~46 chars reads
    as a callable-out detail; longer text is a sentence, not a label, and
    the primitive degrades to a plain framed citation instead."""
    for field in ('implication', 'context'):
        v = clean(slide.get(field))
        if v and len(v) <= 46:
            return v
    return None


def _slide_spec(slide, story, i, total):
    is_first, is_last = i == 0, i == total - 1
    role = _canon_role(slide)
    vt = clean(slide.get('visual_type')).lower()

    if is_first:
        primitive, explicit = 'hook', True
    elif is_last or vt == 'final' or role == 'payoff':
        primitive, explicit = 'payoff', True
    else:
        primitive, explicit = _pick_primitive(slide, i, total, None)
        if primitive == 'metric_or_bars':
            primitive = _metric_or_bars(slide)

    dark_default = primitive in ('hook', 'giant_metric', 'data_bars', 'statement')
    bg, fg = bg_of(slide, dark_default)
    default_accent = {
        'hook': BRAND_LIME, 'payoff': BRAND_GOLD, 'giant_metric': BRAND_LIME, 'data_bars': BRAND_LIME,
        'comparison_split': BRAND_RED, 'before_after': BRAND_RED, 'process_flow': BRAND_FOREST,
        'annotated_screenshot': BRAND_FOREST, 'timeline': BRAND_FOREST, 'statement': BRAND_GOLD,
        'visual_quote': BRAND_FOREST,
    }.get(primitive, BRAND_LIME)
    accent = accent_of(slide, story, default_accent)

    headline = punch(slide.get('headline'), 9, 70)
    body = support(slide.get('body'), 16, 130)
    kicker = clean(slide.get('kicker')) or role.replace('_', ' ').title() or 'GetByteRush'

    spec = {
        'number': i + 1, 'primitive': primitive, 'explicit_signal': explicit,
        'accent': accent, 'bg': bg, 'fg': fg, 'kicker': kicker, 'headline': headline, 'body': body,
        'psychology_intense': psychology_intense(story),
        'needs_evidence': primitive == 'annotated_screenshot',
    }

    if primitive == 'giant_metric':
        m = metric(slide.get('headline') or slide.get('body'))
        spec['metric_value'] = m or punch(slide.get('headline'), 2, 16)
        spec['metric_is_word'] = not m
    elif primitive == 'data_bars':
        pool = ' '.join(clean(slide.get(f) or '') for f in ('headline', 'body', 'context', 'implication'))
        nums = metrics_all(pool, limit=3)
        mags = [_magnitude(n) for n in nums]
        labels = ['PRIMARY', 'SECONDARY', 'TERTIARY']
        # A bar's width is a magnitude claim — valid only when every number
        # shares a unit. "80%" vs "3x" vs "15%" are not on the same scale;
        # sizing bars off their raw digits regardless of unit is a real
        # data-visualization error (confirmed by looking at the actual
        # render: an "80%" bar dwarfing a "3x" bar implies 80 is bigger
        # than 3 in some comparable sense, which it isn't). Proportional
        # only when the units genuinely match; otherwise every bar gets an
        # equal, non-comparative mark — still a graphic grouping the
        # numbers, just not asserting a false comparison between them.
        units = {n[-1] for n in nums}
        proportional = len(units) == 1
        if proportional:
            peak = max(mags) or 1.0
            spec['bars'] = [(labels[j], n, mags[j] / peak) for j, n in enumerate(nums)]
        else:
            spec['bars'] = [(labels[j], n, None) for j, n in enumerate(nums)]
    elif primitive in ('comparison_split', 'before_after'):
        (a_label, a_val), (b_label, b_val) = _comparison_sides(slide)
        spec['sides'] = (a_label, a_val, b_label, b_val)
    elif primitive == 'timeline':
        spec['timeline_points'] = _timeline_points(slide)
    elif primitive == 'process_flow':
        spec['process'] = (
            punch(slide.get('context') or 'Before', 6, 46),
            punch(slide.get('implication') or 'After', 6, 46),
        )
    elif primitive == 'annotated_screenshot':
        spec['annotation'] = _annotation_label(slide)
        spec['badge_text'] = 'Source — Verified'
    elif primitive == 'visual_quote':
        spec['quote_text'] = support(slide.get('body') or slide.get('context'), 22, 160)
        spec['quote_source'] = clean(slide.get('source_label')) or 'GetByteRush'
    elif primitive == 'hook':
        m = metric(slide.get('headline') or slide.get('body'))
        spec['metric_value'] = m
        spec['metric_size'] = round((560 if len(m) <= 3 else 440) * (1.08 if spec['psychology_intense'] else 1.0)) if m else round(460 * (1.08 if spec['psychology_intense'] else 1.0))
        spec['source_label'] = clean(slide.get('source_label')) or 'Source'
    elif primitive == 'payoff':
        spec['cta'] = cta_line(story)

    return spec


def direct(story):
    """The single entry point: reads the unmodified editorial JSON, returns
    a CarouselSpec dict. Zero API calls."""
    slides = story.get('slides') or []
    total = len(slides)
    specs = [_slide_spec(s, story, i, total) for i, s in enumerate(slides)]

    # Whole-carousel rhythm pass — the one thing per-slide-independent
    # selection structurally can't do. Only touches slides whose primitive
    # was picked by fallback (position cycle / role hint), never a slide
    # with an explicit visual_type/visual_concept signal, so real editorial
    # intent is never overridden for the sake of variety. Swaps only to
    # 'statement', the one primitive needing no extra payload beyond the
    # kicker/headline/body every spec already carries — swapping to e.g.
    # data_bars/comparison_split would need their payload recomputed, which
    # the fallback branch never ran; 'statement' is also thematically the
    # right rhythm-break per design-principles.md, not an arbitrary choice.
    for i in range(1, total - 1):
        prev, cur = specs[i - 1], specs[i]
        if cur['explicit_signal']:
            continue
        if cur['primitive'] == prev['primitive'] and cur['primitive'] != 'statement':
            cur['primitive'] = 'statement'
            cur['bg'], cur['fg'] = bg_of({}, dark_default=True)

    return {'slides': specs, 'story_title': story.get('story_title', '')}
