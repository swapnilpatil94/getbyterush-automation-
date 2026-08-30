#!/usr/bin/env python3
"""GetByteRush V16 — editorial visual system rewrite.

This is a full replacement of the V9-V15 render chain, not another layer on
top of it. V9-V15 applied one fixed pixel-template per pipeline stage and
stacked decorative overlays from file to file; this file instead selects one
of seven genuinely distinct composition families per slide, driven by the
editorial JSON's own `role` / `visual_type` / `background_mode` /
`accent_color` fields, with real typography (Fraunces / Archivo / IBM Plex
Mono) instead of Arial.

Only text utilities and the evidence-capture routine are reused from V9 —
everything visual is new.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import carousel_art_renderer_v9 as v9
from playwright.async_api import async_playwright

W, H = v9.W, v9.H
ROOT = v9.ROOT
DATA = v9.DATA
OUT = v9.OUT
FONT_DIR = ROOT / 'assets/fonts'
FONT_ORIGIN = 'https://gbr-assets.internal'

clean, esc, words, punch, support = v9.clean, v9.esc, v9.words, v9.punch, v9.support
metric, domain, source_url, source_label, capture = v9.metric, v9.domain, v9.source_url, v9.source_label, v9.capture

CREAM = '#F3EBDD'
INK = '#0B0D0C'
FOREST = '#12352B'
GOLD = '#C9A45C'
RED = '#B70C07'
BLUE = '#426A78'
LIME = '#B7E32B'

M = 64  # safe margin, per design system

ROLE_DEFAULT = ['hook', 'open', 'evidence', 'reveal', 'interrupt', 'architecture', 'payoff']


def canon_role(slide, i):
    r = clean(slide.get('role')).lower().replace(' ', '_')
    return {
        'interrupt': 'hook', 'open_loop': 'open', 'proof': 'evidence',
        'escalation': 'reveal', 'pattern_interrupt': 'interrupt',
        'implication': 'architecture', 'payoff': 'payoff',
    }.get(r, ROLE_DEFAULT[i % len(ROLE_DEFAULT)])


def accent_of(slide, fallback):
    c = clean(slide.get('accent_color'))
    return c if re.fullmatch(r'#[0-9a-fA-F]{6}', c) else fallback


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


FONT_CSS = f'''
@font-face{{font-family:'Fraunces';src:url('{FONT_ORIGIN}/Fraunces.ttf');font-weight:100 900;font-style:normal;font-display:block}}
@font-face{{font-family:'Archivo';src:url('{FONT_ORIGIN}/Archivo.ttf');font-weight:100 900;font-style:normal;font-display:block}}
@font-face{{font-family:'IBM Plex Mono';src:url('{FONT_ORIGIN}/IBMPlexMono-Medium.ttf');font-weight:500;font-style:normal;font-display:block}}
@font-face{{font-family:'IBM Plex Mono';src:url('{FONT_ORIGIN}/IBMPlexMono-Bold.ttf');font-weight:700;font-style:normal;font-display:block}}
'''

BASE = f'''
{FONT_CSS}
@page{{size:{W}px {H}px;margin:0}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:'Archivo',sans-serif}}
.s{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}
.mono{{font-family:'IBM Plex Mono',monospace;text-transform:uppercase}}
.serif{{font-family:'Fraunces',serif}}
'''


def masthead(i, total, fg):
    return f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:48px;display:flex;justify-content:space-between;align-items:baseline;color:{fg}">
      <span style="font:800 13px/1 'Archivo';letter-spacing:.02em">getByteRush</span>
      <span class="mono" style="font:500 11px/1 'IBM Plex Mono';letter-spacing:.16em;opacity:.7">{i:02d} — {total:02d}</span>
    </div>
    <div style="position:absolute;left:{M}px;right:{M}px;top:76px;height:1px;background:{fg};opacity:.2"></div>'''


def foot(fg):
    return f'''
    <div style="position:absolute;left:{M}px;right:{M}px;bottom:76px;height:1px;background:{fg};opacity:.2"></div>
    <div style="position:absolute;left:{M}px;right:{M}px;bottom:48px;display:flex;justify-content:space-between;color:{fg};opacity:.55">
      <span class="mono" style="font:500 9.5px/1 'IBM Plex Mono';letter-spacing:.14em">Tech · AI · Internet</span>
      <span class="mono" style="font:500 9.5px/1 'IBM Plex Mono';letter-spacing:.14em">Tested · Explained · Real</span>
    </div>'''


def doc(inner_html, bg, fg, i, total):
    return f'''<!doctype html><style>{BASE}.s{{background:{bg};color:{fg}}}</style><div class="s">{masthead(i,total,fg)}{inner_html}{foot(fg)}</div>'''


# ---------------------------------------------------------------------------
# Composition families
# ---------------------------------------------------------------------------

def comp_hook(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=True)
    accent = accent_of(slide, LIME)
    h = punch(slide.get('headline'), 9, 70)
    b = support(slide.get('body'), 16, 130)
    k = esc(slide.get('kicker') or 'getByteRush / Signal')
    m = esc(metric(slide.get('headline') or slide.get('body')))
    hsize = scale(h, [(14, 128), (20, 106), (28, 90), (40, 74), (999, 60)])
    mark = (f'<div class="serif" style="position:absolute;right:-70px;top:600px;font:900 {560 if len(m)<=3 else 440}px/.7 \'Fraunces\';letter-spacing:-.05em;color:{accent}">{m}</div>'
            if m else
            f'<div class="serif" style="position:absolute;right:-40px;top:640px;font:900 460px/.7 \'Fraunces\';color:{accent}">&rarr;</div>')
    body = f'''
    <div style="position:absolute;left:{M}px;right:340px;top:150px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{k}</div>
      <div class="serif" style="margin-top:26px;font:900 {hsize}px/.86 'Fraunces';letter-spacing:-.035em;text-wrap:balance">{esc(h)}</div>
      <div style="margin-top:34px;max-width:440px;font:600 19px/1.32 'Archivo';opacity:.86">{esc(b)}</div>
    </div>
    {mark}
    <div style="position:absolute;left:{M}px;bottom:118px;font:600 10px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.6" class="mono">{esc(source_label(slide))}</div>'''
    return bg, fg, body


def comp_context(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=False)
    accent = accent_of(slide, FOREST)
    h = punch(slide.get('headline'), 8, 60)
    b = support(slide.get('body'), 20, 160)
    k = esc(slide.get('kicker') or 'Context')
    imp = support(slide.get('implication') or '', 14, 105)
    hsize = scale(h, [(20, 82), (30, 68), (999, 56)])
    pts = [(40, 210), (280, 150), (520, 90), (760, 20)]
    path = ' '.join(f'{"M" if j == 0 else "L"}{x},{y}' for j, (x, y) in enumerate(pts))
    nodes = ''.join(
        f'<circle cx="{x}" cy="{y}" r="{10 if j == len(pts) - 1 else 6}" fill="{accent if j == len(pts) - 1 else "none"}" stroke="{accent}" stroke-width="2"/>'
        for j, (x, y) in enumerate(pts)
    )
    body = f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:140px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{k}</div>
      <div class="serif" style="margin-top:20px;font:900 {hsize}px/.9 'Fraunces';letter-spacing:-.03em;max-width:820px;text-wrap:balance">{esc(h)}</div>
      <div style="margin-top:30px;max-width:560px;font:600 19px/1.34 'Archivo';opacity:.82">{esc(b)}</div>
    </div>
    <svg viewBox="0 0 800 240" width="{W - 2*M}" height="264" style="position:absolute;left:{M}px;top:480px;overflow:visible">
      <path d="{path}" fill="none" stroke="{accent}" stroke-width="2" opacity=".55"/>
      {nodes}
    </svg>
    <div style="position:absolute;left:{M}px;top:800px;width:700px;border-top:2px solid {accent};padding-top:18px;color:{fg}">
      <div class="mono" style="font:600 9px/1 'IBM Plex Mono';letter-spacing:.14em;opacity:.6">Why it matters</div>
      <div style="margin-top:12px;font:700 24px/1.3 'Archivo'">{esc(imp)}</div>
    </div>'''
    return bg, fg, body


def comp_evidence(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=False)
    accent = accent_of(slide, FOREST)
    h = punch(slide.get('headline'), 8, 58)
    b = support(slide.get('body'), 18, 140)
    k = esc(slide.get('kicker') or 'Evidence')
    dom = esc(domain(source_url(story, slide)))
    hsize = scale(h, [(20, 68), (30, 58), (999, 48)])
    head = f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:140px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{k}</div>
      <div class="serif" style="margin-top:16px;font:900 {hsize}px/.92 'Fraunces';letter-spacing:-.03em;max-width:900px;text-wrap:balance">{esc(h)}</div>
    </div>'''
    if evidence:
        card = f'''
        <div style="position:absolute;left:{M}px;top:344px;width:820px;height:576px;background:#fff;border:1px solid rgba(11,13,12,.14);box-shadow:16px 20px 0 {accent}22;transform:rotate(-.5deg)">
          <img src="file://{evidence}" style="width:100%;height:100%;object-fit:contain;display:block">
        </div>
        <div class="mono" style="position:absolute;left:{M + 24}px;top:322px;background:{accent};color:{CREAM};padding:8px 12px;font:700 9px/1 'IBM Plex Mono';letter-spacing:.12em">Source — Verified</div>'''
    else:
        src = story.get('source_story') or {}
        title = esc(src.get('title') or slide.get('context') or 'Verified source metadata')
        card = f'''
        <div style="position:absolute;left:{M}px;top:344px;width:820px;height:576px;background:{INK};color:{CREAM};padding:44px">
          <div class="mono" style="font:600 10px/1 'IBM Plex Mono';letter-spacing:.16em;color:{accent}">{esc(src.get('source') or 'Primary Source')}</div>
          <div class="serif" style="margin-top:36px;font:600 34px/1.2 'Fraunces';font-style:italic;max-width:700px">&ldquo;{title}&rdquo;</div>
          <div class="mono" style="position:absolute;left:44px;right:44px;bottom:36px;border-top:1px solid rgba(243,235,221,.25);padding-top:14px;font:500 11px/1.3 'IBM Plex Mono';opacity:.7;word-break:break-all">{esc(src.get('url') or dom)}</div>
        </div>'''
    caption = f'''
    <div style="position:absolute;left:{M}px;top:944px;width:760px;color:{fg}">
      <div style="font:700 18px/1.3 'Archivo'">{esc(b)}</div>
      <div class="mono" style="margin-top:14px;font:500 10px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.55">{dom}</div>
    </div>'''
    return bg, fg, head + card + caption


def comp_metric(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=True)
    accent = accent_of(slide, LIME)
    h = punch(slide.get('headline'), 8, 58)
    b = support(slide.get('body'), 14, 110)
    k = esc(slide.get('kicker') or 'The Breakthrough')
    m = esc(metric(slide.get('headline') or slide.get('body')))
    big = m or esc(punch(slide.get('headline'), 2, 16))
    msize = (700 if len(big) <= 3 else 560) if m else scale(big, [(8, 220), (14, 160), (999, 120)])
    body = f'''
    <div style="position:absolute;left:0;right:0;top:{160 if m else 300}px;text-align:center;color:{accent};overflow:visible">
      <div class="serif" style="font:900 {msize}px/.74 'Fraunces';letter-spacing:-.06em;text-transform:uppercase">{big}</div>
    </div>
    <div style="position:absolute;left:{M}px;right:{M}px;top:800px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{k}</div>
      <div class="serif" style="margin-top:20px;font:900 {scale(h,[(24,56),(36,46),(999,38)])}px/1.02 'Fraunces';letter-spacing:-.02em;max-width:760px;text-wrap:balance">{esc(h)}</div>
      <div style="margin-top:20px;max-width:620px;font:600 17px/1.32 'Archivo';opacity:.78">{esc(b)}</div>
    </div>'''
    return bg, fg, body


def comp_statement(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=True)
    accent = accent_of(slide, GOLD)
    h = punch(slide.get('headline'), 10, 80)
    b = support(slide.get('body'), 16, 120)
    k = esc(slide.get('kicker') or 'Pattern Interrupt')
    hsize = scale(h, [(18, 100), (28, 84), (40, 68), (999, 54)])
    body = f'''
    <div style="position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:{fg};padding:0 {M}px">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.2em;color:{accent}">{k}</div>
      <div style="margin-top:30px;width:120px;height:2px;background:{accent}"></div>
      <div class="serif" style="margin-top:34px;font:900 {hsize}px/.94 'Fraunces';letter-spacing:-.03em;max-width:820px;text-wrap:balance">{esc(h)}</div>
      <div style="margin-top:30px;width:120px;height:2px;background:{accent}"></div>
      <div style="margin-top:34px;max-width:520px;font:600 18px/1.36 'Archivo';opacity:.75">{esc(b)}</div>
    </div>'''
    return bg, fg, body


def comp_process(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=False)
    accent = accent_of(slide, FOREST)
    h = punch(slide.get('headline'), 8, 58)
    b = support(slide.get('body'), 18, 140)
    k = esc(slide.get('kicker') or 'Mechanism')
    frm = punch(slide.get('context') or 'Before', 6, 46)
    to = punch(slide.get('implication') or 'After', 6, 46)
    hsize = scale(h, [(20, 74), (30, 62), (999, 50)])
    lane_w = (W - 2*M - 112) // 2
    body = f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:140px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{k}</div>
      <div class="serif" style="margin-top:20px;font:900 {hsize}px/.92 'Fraunces';letter-spacing:-.03em;max-width:880px;text-wrap:balance">{esc(h)}</div>
    </div>
    <div style="position:absolute;left:{M}px;top:600px;width:{lane_w}px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">01 / From</div>
      <div class="serif" style="margin-top:14px;font:700 32px/1.1 'Fraunces';text-wrap:balance">{esc(frm)}</div>
    </div>
    <div style="position:absolute;right:{M}px;top:600px;width:{lane_w}px;text-align:right;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">02 / To</div>
      <div class="serif" style="margin-top:14px;font:700 32px/1.1 'Fraunces';text-wrap:balance">{esc(to)}</div>
    </div>
    <svg viewBox="0 0 {W-2*M} 40" width="{W-2*M}" height="40" style="position:absolute;left:{M}px;top:820px">
      <line x1="0" y1="20" x2="{W-2*M-40}" y2="20" stroke="{accent}" stroke-width="2" opacity=".5"/>
      <polygon points="{W-2*M-40},10 {W-2*M},20 {W-2*M-40},30" fill="{accent}" opacity=".85"/>
      <circle cx="0" cy="20" r="7" fill="{bg}" stroke="{accent}" stroke-width="2"/>
    </svg>
    <div style="position:absolute;left:{M}px;top:900px;width:780px;border-top:1px solid {fg}33;padding-top:18px;color:{fg}">
      <div style="font:600 18px/1.32 'Archivo';opacity:.82">{esc(b)}</div>
    </div>'''
    return bg, fg, body


def comp_payoff(slide, story, i, total, evidence):
    bg, fg = bg_of(slide, dark_default=False)
    accent = accent_of(slide, GOLD)
    h = punch(slide.get('headline'), 9, 66)
    b = support(slide.get('body'), 18, 140)
    k = esc(slide.get('kicker') or 'The Bottom Line')
    hsize = scale(h, [(18, 92), (28, 78), (40, 64), (999, 52)])
    body = f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:190px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{k}</div>
      <div class="serif" style="margin-top:24px;font:900 {hsize}px/.94 'Fraunces';letter-spacing:-.03em;max-width:840px;text-wrap:balance">{esc(h)}</div>
      <div style="margin-top:28px;max-width:600px;font:600 18px/1.36 'Archivo';opacity:.8">{esc(b)}</div>
    </div>
    <div class="serif" style="position:absolute;right:-40px;top:560px;font:900 460px/.7 'Fraunces';color:{fg};opacity:.06">&rarr;</div>
    <div style="position:absolute;left:{M}px;top:900px;color:{fg}">
      <div class="serif" style="font:600 64px/1 'Fraunces';font-style:italic;color:{accent}">getByteRush<span style="color:{fg}">.</span></div>
    </div>'''
    return bg, fg, body


COMPOSERS = {
    'hook': comp_hook, 'open': comp_context, 'evidence': comp_evidence,
    'reveal': comp_metric, 'interrupt': comp_statement,
    'architecture': comp_process, 'payoff': comp_payoff,
}


def render(slide, story, i, total, evidence):
    r = canon_role(slide, i)
    fn = COMPOSERS.get(r, comp_statement)
    return fn(slide, story, i, total, evidence)


async def _fulfill_font(route):
    name = route.request.url.rsplit('/', 1)[-1]
    path = FONT_DIR / name
    if path.exists():
        await route.fulfill(path=str(path))
    else:
        await route.abort()


async def main():
    story = json.loads(DATA.read_text())
    slides = story.get('slides') or []
    if not story.get('selected') or not slides:
        raise SystemExit('No selected editorial')
    now = datetime.now().astimezone()
    slug = re.sub(r'[^a-z0-9]+', '-', clean(story.get('story_title', 'post')).lower()).strip('-')[:72]
    pkg = OUT / now.strftime('%Y-%m-%d') / (now.strftime('%H%M%S') + '-' + slug)
    sd, hd, ed = pkg / 'slides', pkg / 'html', pkg / 'evidence'
    for p in (sd, hd, ed):
        p.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        await page.route(f'{FONT_ORIGIN}/**', _fulfill_font)
        for i, slide in enumerate(slides):
            evidence = None
            r = canon_role(slide, i)
            if r == 'evidence':
                target = ed / f'{i+1:02d}.png'
                evidence = await capture(page, source_url(story, slide), target)
            bg, fg, inner_html = render(slide, story, i, len(slides), evidence)
            html_text = doc(inner_html, bg, fg, i + 1, len(slides))
            (hd / f'{i+1:02d}.html').write_text(html_text)
            await page.set_content(html_text, wait_until='load')
            await page.evaluate('document.fonts.ready')
            await page.screenshot(path=str(sd / f'{i+1:02d}.png'), full_page=False)
        await browser.close()
    out = dict(story)
    out['renderer'] = 'getbyterush-pinterest-editorial-v16'
    out['gemini_calls'] = 0
    out['rendered_at'] = datetime.now().astimezone().isoformat()
    (pkg / 'post.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
    for name, value in [('caption.txt', story.get('caption', '')), ('alt-text.txt', story.get('alt_text', '')),
                         ('hashtags.txt', ' '.join(story.get('hashtags', []) or [])),
                         ('pinned-comment.txt', story.get('pinned_comment', ''))]:
        (pkg / name).write_text(clean(value))
    print(f'RENDERED={pkg}')
    print('GEMINI_CALL=0')
    print('SLIDES=', len(slides))


if __name__ == '__main__':
    asyncio.run(main())
