#!/usr/bin/env python3
"""GetByteRush carousel visual families — the production version of the
6 templates pitched and approved in the design review (Bulletin, Headline
Block, Ledger, Signal, Dossier, Pulse).

Zero Gemini calls: family selection is a deterministic lookup from the
post's own already-computed content-mix category (quality_scoring.py's 7
buckets, carried through as story['selection_meta']['category']), with a
fallback derived from the editorial `format` field for posts that didn't
go through the slotted selection engine (manual/test renders).

Font substitution from the pitch: the design review used Unbounded +
Manrope (Google Fonts, fine for a one-off review artifact) but V17's
Playwright render runs against a fixed self-hosted font set with no
network access (FONT_ORIGIN routing in carousel_art_renderer_v16.py) —
so production uses 'Archivo' (already self-hosted, full 100-900 weight
range) for both headline and body, and 'IBM Plex Mono' for labels/kickers,
matching every other primitive in this codebase. Same bold, geometric
feel; no new font infrastructure required.

Each render_* function returns (bg, fg, inner_html) — inner_html is the
CONTENT layer only. The masthead ("getByteRush" / "NN — TT") and footer
("Tech · AI · Internet" / "Tested · Explained · Real") are drawn by
carousel_art_renderer_v16.doc() around every slide regardless of family,
so content here stays within the safe zone (roughly y:100 to y:1250) to
avoid colliding with them.
"""
import graphics_director as gd
import visual_primitives as vp

W, H, M = vp.W, vp.H, vp.M
CREAM, INK = vp.CREAM, vp.INK
esc = vp.esc

FONT_HEAD = "'Archivo'"
FONT_BODY = "'Archivo'"
FONT_MONO = "'IBM Plex Mono'"

PULSE_ACCENT = '#F26A21'  # deliberate hot-end override — Pulse always signals urgency, regardless of the post's own accent

# ---------------------------------------------------------------------------
# Family selection — deterministic, reuses the pool's own category
# ---------------------------------------------------------------------------

FAMILY_BY_CATEGORY = {
    'EVERGREEN_VALUE': 'bulletin',
    'DATA_RESEARCH': 'ledger',
    'EXPERIMENT': 'signal',
    'PRODUCT_TOOL': 'signal',
    'INTERNET_HUMAN_TECH_BEHAVIOR': 'dossier',
    'CURIOSITY': 'dossier',
    'LAST_24H': 'pulse',
}

# Fallback for posts with no selection_meta (manual/test renders, or the
# old full-batch path) — approximated from editorial_engine.py's own
# `format` enum, which the two never share a source of truth with, so
# this is intentionally coarse rather than exact.
FORMAT_TO_CATEGORY = {
    'breaking_news': 'LAST_24H', 'daily_24_hours': 'LAST_24H',
    'model_drop': 'LAST_24H', 'failure_story': 'LAST_24H',
    'data_story': 'DATA_RESEARCH', 'model_comparison': 'DATA_RESEARCH',
    'experiment': 'EXPERIMENT', 'what_happens_next': 'EXPERIMENT',
    'tool_discovery': 'PRODUCT_TOOL', 'product_story': 'PRODUCT_TOOL',
    'internet_mystery': 'INTERNET_HUMAN_TECH_BEHAVIOR',
    'business_story': 'EVERGREEN_VALUE', 'ai_agent_story': 'EVERGREEN_VALUE',
    'deep_dive': 'EVERGREEN_VALUE', 'explainer': 'EVERGREEN_VALUE', 'timeline': 'EVERGREEN_VALUE',
}

DEFAULT_FAMILY = 'bulletin'


def resolve_family(story):
    category = ((story.get('selection_meta') or {}).get('category') or '').upper()
    if category in FAMILY_BY_CATEGORY:
        return FAMILY_BY_CATEGORY[category]
    fallback_category = FORMAT_TO_CATEGORY.get(story.get('format', ''))
    return FAMILY_BY_CATEGORY.get(fallback_category, DEFAULT_FAMILY)


# ---------------------------------------------------------------------------
# 01 — Bulletin: offset circle, numbered badge. EVERGREEN_VALUE body slides.
# ---------------------------------------------------------------------------

def bulletin(kicker, headline, body, accent, number, total, side='right'):
    hsize = gd.scale(headline, [(20, 72), (30, 60), (45, 48), (999, 40)])
    is_right = side != 'left'
    blob_style = (f'right:-360px;bottom:-200px;' if is_right else f'left:-360px;bottom:-200px;')
    text_align = 'left'
    body_left = M
    swipe_style = f'left:{M}px' if is_right else f'right:{M}px'

    return f'''
    <div style="position:absolute;width:1220px;height:920px;border-radius:50%;background:{accent};{blob_style}"></div>
    <div style="position:absolute;left:{M}px;top:150px;width:92px;height:92px;border-radius:50%;background:{INK};
                display:flex;align-items:center;justify-content:center;font:600 30px/1 {FONT_MONO};color:{CREAM}">{number:02d}</div>
    <div class="mono" style="position:absolute;left:{M}px;top:270px;right:{M}px;font:600 15px/1 {FONT_MONO};
                letter-spacing:.1em;opacity:.62;color:{INK}">{esc(kicker)}</div>
    <div style="position:absolute;left:{M}px;top:310px;width:660px;font:800 {hsize}px/1.12 {FONT_HEAD};
                letter-spacing:-0.01em;color:{INK};text-align:{text_align}">{esc(headline)}</div>
    <div style="position:absolute;left:{body_left}px;bottom:190px;width:420px;font:600 21px/1.5 {FONT_BODY};
                color:{INK};opacity:.72">{esc(body)}</div>
    <div class="mono" style="position:absolute;bottom:130px;{swipe_style};font:500 14px/1 {FONT_MONO};
                letter-spacing:.12em;opacity:.55;color:{INK}">SWIPE →</div>
    '''


# ---------------------------------------------------------------------------
# 02 — Headline Block: torn color block. Always used for the hook (slide 1)
# and payoff (last slide) regardless of family, per the approved routing.
# ---------------------------------------------------------------------------

_TORN_CLIP = (
    'polygon(0% 9%, 4% 4%, 9% 8%, 14% 3%, 19% 7%, 25% 2%, 31% 6%, 37% 1%, 43% 5%, '
    '49% 0%, 55% 5%, 61% 1%, 67% 6%, 73% 2%, 79% 7%, 85% 3%, 91% 8%, 96% 3%, 100% 7%, 100% 100%, 0% 100%)'
)


def headline_block(kicker, headline, body, accent):
    hsize = gd.scale(headline, [(20, 80), (30, 66), (45, 52), (999, 42)])
    # Cream zone is a flex column centered within its own band (roughly
    # y:96 to y:770) so a short 1-line headline doesn't leave a large dead
    # gap above the torn edge — caught live on the first real render.
    return f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:96px;bottom:580px;display:flex;
                flex-direction:column;justify-content:center;gap:20px">
      <div class="mono" style="font:600 15px/1 {FONT_MONO};letter-spacing:.12em;opacity:.85;color:{accent}">{esc(kicker)}</div>
      <div style="font:900 {hsize}px/1.08 {FONT_HEAD};letter-spacing:-0.015em;color:{INK};max-width:900px">{esc(headline)}</div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:46%;background:{accent};color:{CREAM};
                clip-path:{_TORN_CLIP};padding:110px {M}px 0">
      <div style="font:700 21px/1.55 {FONT_BODY};opacity:.94;max-width:720px">{esc(body)}</div>
      <div class="mono" style="position:absolute;bottom:130px;left:{M}px;font:500 14px/1 {FONT_MONO};
                  letter-spacing:.12em;opacity:.85">SWIPE →</div>
    </div>
    '''


# ---------------------------------------------------------------------------
# 03 — Ledger: terminal-black, ruled lines, huge tabular numerals. DATA_RESEARCH.
# ---------------------------------------------------------------------------

def ledger(kicker, headline, body, accent, number, total):
    hsize = gd.scale(headline, [(14, 108), (22, 88), (32, 68), (45, 54), (999, 44)])
    rules = ''.join(f'<div style="position:absolute;left:0;right:0;top:{y}px;height:1px;background:{CREAM};opacity:.08"></div>' for y in range(100, 1260, 68))
    return f'''
    {rules}
    <div class="mono" style="position:absolute;left:{M}px;top:200px;font:600 15px/1 {FONT_MONO};letter-spacing:.1em;
                color:{accent};border:1px solid {accent}66;padding:8px 16px;border-radius:2px">{esc(kicker)}</div>
    <div style="position:absolute;left:{M}px;right:{M}px;top:340px;font:800 {hsize}px/1.02 {FONT_HEAD};
                letter-spacing:-0.02em;color:{accent};font-variant-numeric:tabular-nums">{esc(headline)}</div>
    <div style="position:absolute;left:{M}px;right:{M}px;bottom:190px;font:600 21px/1.55 {FONT_BODY};color:{CREAM};opacity:.7">{esc(body)}</div>
    <div class="mono" style="position:absolute;bottom:130px;right:{M}px;font:500 14px/1 {FONT_MONO};
                letter-spacing:.12em;opacity:.75;color:{accent}">SWIPE →</div>
    '''


# ---------------------------------------------------------------------------
# 04 — Signal: diagonal split, status pill. EXPERIMENT / PRODUCT_TOOL.
# ---------------------------------------------------------------------------

def signal(kicker, headline, body, accent, status_label):
    hsize = gd.scale(headline, [(20, 76), (30, 62), (45, 50), (999, 40)])
    return f'''
    <div style="position:absolute;top:0;left:0;right:0;height:100%;background:{INK};color:{CREAM};
                clip-path:polygon(0 0, 100% 0, 100% 60%, 0 76%);padding:220px {M}px 0">
      <div class="mono" style="font:600 15px/1 {FONT_MONO};letter-spacing:.1em;color:{accent};opacity:.95">{esc(kicker)}</div>
      <div style="margin-top:16px;font:800 {hsize}px/1.15 {FONT_HEAD};letter-spacing:-0.01em;max-width:820px">{esc(headline)}</div>
    </div>
    <div class="mono" style="position:absolute;left:{M}px;bottom:290px;display:inline-flex;align-items:center;gap:10px;
                font:600 14px/1 {FONT_MONO};letter-spacing:.08em;background:{CREAM};padding:10px 16px;border-radius:20px;color:{INK}">
      <span style="width:9px;height:9px;border-radius:50%;background:{accent};display:inline-block"></span>{esc(status_label)}</div>
    <div style="position:absolute;left:{M}px;right:{M}px;bottom:190px;font:700 20px/1.5 {FONT_BODY};color:{INK}">{esc(body)}</div>
    '''


# ---------------------------------------------------------------------------
# 05 — Dossier: pinned, rotated case-file card. INTERNET_HUMAN / CURIOSITY.
# ---------------------------------------------------------------------------

def dossier(kicker, headline, body, accent):
    hsize = gd.scale(headline, [(20, 60), (32, 50), (48, 42), (999, 36)])
    return f'''
    <div style="position:absolute;top:120px;left:50%;width:16px;height:16px;border-radius:50%;
                background:{accent};transform:translateX(-50%);box-shadow:0 4px 8px -1px #0000005a;z-index:3"></div>
    <div style="position:absolute;left:{M}px;right:{M}px;top:170px;bottom:150px;background:{CREAM};
                transform:rotate(-1.2deg);box-shadow:0 20px 40px -18px #0000004d;padding:70px 60px">
      <div class="mono" style="display:inline-block;font:600 14px/1 {FONT_MONO};letter-spacing:.1em;color:{accent};
                  border:1.6px solid {accent};padding:8px 14px;border-radius:3px;transform:rotate(-1.3deg)">{esc(kicker)}</div>
      <div style="margin-top:26px;font:800 {hsize}px/1.18 {FONT_HEAD};letter-spacing:-0.005em;color:{INK}">{esc(headline)}</div>
      <div style="margin-top:26px;font-style:italic;font:600 italic 19px/1.55 {FONT_BODY};color:{INK}cc">{esc(body)}</div>
    </div>
    <div class="mono" style="position:absolute;bottom:130px;left:{M}px;font:500 14px/1 {FONT_MONO};
                letter-spacing:.12em;opacity:.55;color:{INK}">SWIPE →</div>
    '''


# ---------------------------------------------------------------------------
# 06 — Pulse: radiating rings, hot urgency. LAST_24H.
# ---------------------------------------------------------------------------

def pulse(kicker, headline, body, number, total):
    hsize = gd.scale(headline, [(20, 76), (30, 62), (45, 50), (999, 40)])
    rings = ''.join(
        f'<div style="position:absolute;left:50%;top:34%;width:{w}%;aspect-ratio:1;border-radius:50%;'
        f'border:1px solid {PULSE_ACCENT}{op};transform:translate(-50%,-50%)"></div>'
        for w, op in [(150, '22'), (108, '38'), (68, '55')]
    )
    return f'''
    {rings}
    <div class="mono" style="position:absolute;left:{M}px;top:200px;display:inline-flex;align-items:center;gap:10px;
                font:600 15px/1 {FONT_MONO};letter-spacing:.1em;color:{PULSE_ACCENT}">
      <span style="width:9px;height:9px;border-radius:50%;background:{PULSE_ACCENT};display:inline-block"></span>{esc(kicker)}</div>
    <div style="position:absolute;left:{M}px;right:{M}px;top:490px;font:800 {hsize}px/1.12 {FONT_HEAD};
                letter-spacing:-0.01em;color:{CREAM}">{esc(headline)}</div>
    <div style="position:absolute;left:{M}px;right:{M}px;bottom:190px;font:600 21px/1.55 {FONT_BODY};color:{CREAM};opacity:.7">{esc(body)}</div>
    <div class="mono" style="position:absolute;bottom:130px;right:{M}px;font:500 14px/1 {FONT_MONO};
                letter-spacing:.12em;opacity:.85;color:{PULSE_ACCENT}">SWIPE →</div>
    '''


# ---------------------------------------------------------------------------
# Dispatch: one slide -> (bg, fg, inner_html)
# ---------------------------------------------------------------------------

def render_slide(family, kicker, headline, body, accent, number, total, is_hook, is_payoff):
    """is_hook (slide 1) and is_payoff (last slide) always render as
    Headline Block regardless of the resolved family — the approved
    routing: bold bookends, family-specific body in between."""
    if is_hook or is_payoff:
        return CREAM, INK, headline_block(kicker, headline, body, accent)

    if family == 'ledger':
        return INK, CREAM, ledger(kicker, headline, body, accent, number, total)

    if family == 'signal':
        status = 'IN PROGRESS' if number < total else 'KEY TAKEAWAY'
        return accent, CREAM, signal(kicker, headline, body, accent, status)

    if family == 'dossier':
        return '#E8DDC4', INK, dossier(kicker, headline, body, accent)

    if family == 'pulse':
        return INK, CREAM, pulse(kicker, headline, body, number, total)

    # bulletin (default)
    side = 'right' if number % 2 else 'left'
    return CREAM, INK, bulletin(kicker, headline, body, accent, number, total, side=side)
