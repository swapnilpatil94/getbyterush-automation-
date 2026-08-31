#!/usr/bin/env python3
"""GetByteRush V17 Graphics Director — art-directs each slide instead of
selecting a template family.

EDITORIAL JSON -> visual_grammars.select() (what IS this information,
structurally) -> this module (accent/bg/density/typography + payload
assembly) -> CarouselSpec -> carousel_art_renderer_v17.py executes it.

Reuses graphics_director.py's text utilities and psychology/accent system
unchanged — that layer was never the problem the V17 redesign is fixing,
so it isn't rewritten. Zero API calls, same as v16.
"""
import graphics_director as gd
import visual_grammars as vg

# ---------------------------------------------------------------------------
# Per-grammar defaults. dark_default mirrors design-principles.md's existing
# rule (loud grammars default to the near-black field); DEFAULT_ACCENT is
# only the fallback when no explicit/psychology accent resolves — accent_of()
# still checks slide/story/psychology signal first, same precedence as v16.
# ---------------------------------------------------------------------------
DARK_DEFAULT_GRAMMARS = {'confrontation', 'singular_object', 'accumulation_trail'}

DEFAULT_ACCENT = {
    'confrontation': gd.CANON_PALETTE['orange'], 'proportional_field': gd.BRAND_LIME,
    'accumulation_trail': gd.BRAND_GOLD, 'comparison': gd.BRAND_RED,
    'sequential_system': gd.BRAND_FOREST, 'chronological_sequence': gd.CANON_PALETTE['steel'],
    'evidence_board': gd.CANON_PALETTE['purple'], 'evidence_screenshot': gd.BRAND_FOREST,
    'quote': gd.BRAND_FOREST, 'singular_object': gd.BRAND_LIME,
}

# Static per (grammar, variant) design metadata — documentary fields for
# human/QA review, not consumed by renderer geometry (the geometry is
# already baked into each primitive). headline_optional records whether the
# grammar's own "remove the headline" self-check passed.
_GRAMMAR_META = {
    ('confrontation', 'strike_reveal'): (['struck myth', 'bold fact', 'evidence'], 'structured', True),
    ('evidence_screenshot', 'framed'): (['screenshot', 'annotation', 'caption'], 'structured', True),
    ('comparison', 'matrix'): (['row values', 'winning column', 'labels'], 'dense', True),
    ('comparison', 'two_panel'): (['dominant panel', 'neutral panel', 'verdict'], 'structured', True),
    ('proportional_field', 'dot_field'): (['filled cells', 'percentage numeral', 'remainder'], 'dense', True),
    ('proportional_field', 'bar_split'): (['fill numeral', 'seam', 'labels'], 'structured', True),
    ('accumulation_trail', 'shrinking_trail'): (['start block', 'thinning stages', 'hollow end'], 'structured', True),
    ('chronological_sequence', 'multi_point'): (['largest/last dot', 'track', 'earliest dot'], 'dense', True),
    ('chronological_sequence', 'two_point'): (['NOW marker', 'THEN marker', 'track'], 'sparse', True),
    ('sequential_system', 'chain_vertical'): (['widest node', 'chain', 'first node'], 'structured', True),
    ('sequential_system', 'layered_stack'): (['top layer', 'path line', 'bottom layer'], 'dense', True),
    ('quote', 'pull_quote'): (['quote text', 'source'], 'sparse', False),
    ('evidence_board', 'pinned_chips'): (['dominant chip', 'supporting chips'], 'dense', True),
    ('evidence_board', 'single_citation'): (['source name', 'quoted claim'], 'structured', True),
    ('singular_object', 'metric_texture'): (['numeral', 'unit texture'], 'sparse', True),
    ('singular_object', 'statement'): (['headline'], 'sparse', False),
}


def _ab_labels(headline):
    import re
    m = re.search(r'(.+?)\s+(?:vs\.?|versus)\s+(.+)', gd.clean(headline), re.I)
    if m:
        # Only the entity name after "vs", not the trailing qualifier
        # clause — "X vs Y, six months later" should label the column "Y",
        # not "Y, six months later" (confirmed truncated mid-clause by
        # direct render before this split was added).
        b_raw = re.split(r',', m.group(2), maxsplit=1)[0]
        return gd.punch(m.group(1), 4, 26), gd.punch(b_raw, 4, 26)
    return 'Before', 'After'


def _slide_spec(slide, story, i, total, evidence_url, avoid_grammars=None):
    is_first, is_last = i == 0, i == total - 1

    if is_last:
        accent = gd.accent_of(slide, story, gd.BRAND_GOLD)
        bg, fg = gd.bg_of(slide, dark_default=False)
        return {
            'number': i + 1, 'grammar': 'payoff', 'variant': 'payoff', 'primitive': 'payoff',
            'accent': accent, 'bg': bg, 'fg': fg,
            'kicker': gd.clean(slide.get('kicker')) or 'GetByteRush',
            'headline': gd.punch(slide.get('headline'), 9, 70), 'body': gd.support(slide.get('body'), 16, 130),
            'cta': gd.cta_line(story), 'psychology_intense': gd.psychology_intense(story),
            'needs_evidence': False, 'focal_sequence': ['signature', 'CTA'], 'density': 'sparse', 'headline_optional': False,
        }

    avoid = (avoid_grammars or {}).get(i, ())
    grammar, variant, payload = vg.select(slide, story, is_first, is_last, bool(evidence_url), avoid=avoid)

    dark_default = grammar in DARK_DEFAULT_GRAMMARS or is_first
    bg, fg = gd.bg_of(slide, dark_default)
    accent = gd.accent_of(slide, story, DEFAULT_ACCENT.get(grammar, gd.BRAND_LIME))

    headline = gd.punch(slide.get('headline'), 9, 70)
    body = gd.support(slide.get('body'), 16, 130)
    role = gd._canon_role(slide)
    kicker = gd.clean(slide.get('kicker')) or role.replace('_', ' ').title() or 'GetByteRush'
    focal_sequence, density, headline_optional = _GRAMMAR_META.get((grammar, variant), (['headline'], 'structured', False))

    spec = {
        'number': i + 1, 'grammar': grammar, 'variant': variant, 'primitive': f'{grammar}:{variant}',
        'accent': accent, 'bg': bg, 'fg': fg, 'kicker': kicker, 'headline': headline, 'body': body,
        'psychology_intense': gd.psychology_intense(story), 'needs_evidence': grammar == 'evidence_screenshot',
        'focal_sequence': focal_sequence, 'density': density, 'headline_optional': headline_optional,
    }

    if grammar == 'confrontation':
        myth, fact, remainder = payload['myth_split']
        spec['myth_text'], spec['fact_text'] = myth, fact
        spec['body'] = gd.support(remainder, 16, 130) if remainder else ''
        spec['source_label'] = gd.clean(slide.get('source_label')) or ''
    elif grammar == 'evidence_screenshot':
        spec['badge_text'] = 'Source — Verified'
        spec['annotation'] = gd._annotation_label(slide)
    elif grammar == 'comparison' and variant == 'matrix':
        a_label, b_label = _ab_labels(slide.get('headline'))
        spec['a_label'], spec['b_label'], spec['rows'] = a_label, b_label, payload['rows']
    elif grammar == 'comparison':
        spec['sides'] = payload['sides']
    elif grammar == 'proportional_field':
        spec['pct'] = payload['pct']
        spec['label_hi'] = gd.punch(slide.get('context'), 4, 30) or 'Share'
        spec['label_lo'] = gd.punch(slide.get('implication'), 4, 30) or 'Remaining'
    elif grammar == 'accumulation_trail':
        spec['start_value'], spec['stages'] = payload['start_value'], payload['stages']
        if payload.get('lead_in'):
            spec['body'] = gd.support(payload['lead_in'], 16, 130)
    elif grammar == 'chronological_sequence' and variant == 'multi_point':
        spec['years'] = payload['years']
    elif grammar == 'chronological_sequence':
        spec['timeline_points'] = payload['points']
    elif grammar == 'sequential_system':
        spec['steps'], spec['weights'] = payload['steps'], payload['weights']
    elif grammar == 'quote':
        spec['quote_text'] = gd.support(slide.get('body') or slide.get('context'), 22, 160)
        spec['quote_source'] = gd.clean(slide.get('source_label')) or 'GetByteRush'
    elif grammar == 'evidence_board' and variant == 'pinned_chips':
        spec['chips'] = payload['chips']
    elif grammar == 'evidence_board':
        spec['source_label_full'] = payload['source_label']
        spec['quote_text'] = gd.support(payload['quote_text'], 24, 170)
    elif grammar == 'singular_object' and variant == 'metric_texture':
        spec['metric_value'] = payload['metric_value']

    return spec


def direct(story, evidence_urls=None, avoid_grammars=None):
    """evidence_urls: optional {slide_index: url} so the director knows
    whether a real screenshot is actually capturable before choosing the
    evidence_screenshot grammar over evidence_board — zero network calls
    here, the renderer does the actual capture.

    avoid_grammars: optional {slide_index: [(grammar, variant), ...]} —
    used only when re-rendering after a VISUAL or DIFFERENT_APPROACH
    Telegram rejection, to force a materially different composition per
    slide. None/empty by default, so ordinary rendering is unaffected."""
    slides = story.get('slides') or []
    total = len(slides)
    evidence_urls = evidence_urls or {}
    specs = [_slide_spec(s, story, i, total, evidence_urls.get(i), avoid_grammars) for i, s in enumerate(slides)]

    # Whole-carousel rhythm pass: two consecutive slides landing on the
    # exact same (grammar, variant) reads as a repeated composition — but
    # two different variants of the same grammar family (chain_vertical
    # then layered_stack) are genuinely different compositions, which is
    # the whole point of grammars having internal variety, so only an
    # exact repeat gets swapped to the calm statement reset.
    for i in range(1, total - 1):
        prev, cur = specs[i - 1], specs[i]
        if (cur['grammar'], cur['variant']) == (prev['grammar'], prev['variant']) and cur['grammar'] not in ('payoff', 'singular_object'):
            bg, fg = gd.bg_of({}, dark_default=True)
            cur.update({
                'grammar': 'singular_object', 'variant': 'statement', 'primitive': 'singular_object:statement',
                'bg': bg, 'fg': fg, 'focal_sequence': ['headline'], 'density': 'sparse', 'headline_optional': False,
            })

    return {'slides': specs, 'story_title': story.get('story_title', '')}
