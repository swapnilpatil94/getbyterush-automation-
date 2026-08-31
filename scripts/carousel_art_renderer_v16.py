#!/usr/bin/env python3
"""GetByteRush V16 — renderer / executor.

Architecture: EDITORIAL -> GRAPHICS DIRECTOR -> V16 (this file) -> QA.

This file no longer decides what a slide should look like. It reads the
CarouselSpec produced once per story by graphics_director.direct(story) —
zero API calls, pure Python over the existing editorial JSON — and
executes each slide's spec by calling the matching primitive from
visual_primitives.py. What changed and why lives in graphics_director.py's
docstring and design/design-principles.md; this file is I/O, font/asset
routing, evidence capture, and wiring a spec to a primitive call.
"""
import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

import carousel_art_renderer_v9 as v9
import graphics_director as gd
import visual_primitives as vp
from playwright.async_api import async_playwright

W, H = v9.W, v9.H
ROOT = v9.ROOT
# GBR_INPUT lets renderer-only test fixtures be rendered without touching
# data/selected_story.json — the file the production editorial pipeline
# writes to. Never set in production workflows.
DATA = Path(os.environ['GBR_INPUT']) if os.environ.get('GBR_INPUT') else v9.DATA
OUT = Path(os.environ['GBR_OUT']) if os.environ.get('GBR_OUT') else v9.OUT
FONT_DIR = ROOT / 'assets/fonts'
FONT_ORIGIN = 'https://gbr-assets.internal'
ASSET_ORIGIN = 'https://gbr-local-asset.internal'
M = vp.M

clean, source_url, source_label, domain = v9.clean, v9.source_url, v9.source_label, v9.domain

# v9.capture()'s consent-banner CSS only matches selectors containing the
# literal substring "cookie" or "consent" — the major consent-management
# platforms (OneTrust, Cookiebot, Quantcast/TCF, TrustArc, Osano, Didomi,
# CookieYes) name their containers after the vendor instead, so none of
# them matched. Confirmed by direct capture: NVIDIA's OneTrust banner
# rendered directly on top of the "evidence" screenshot, covering roughly
# half the image, with none of the existing selectors touching it.
_CONSENT_HIDE_CSS = '''
[id*=cookie],[class*=cookie],[id*=consent],[class*=consent],
[aria-label*=cookie i],[aria-label*=consent i],
#onetrust-banner-sdk,#onetrust-consent-sdk,#onetrust-pc-sdk,.onetrust-pc-dark-filter,
#CybotCookiebotDialog,#CybotCookiebotDialogBodyUnderlay,
.qc-cmp2-container,#qc-cmp2-container,
#truste-consent-track,.truste_box_overlay,#trustarc-banner-overlay,
.osano-cm-window,.osano-cm-dialog,
#didomi-host,.didomi-popup-open,.didomi-popup-container,
#cookie-law-info-bar,.cli-modal-backdrop,
#termly-code-snippet-support,
.gdpr-banner,.cc-banner,.cc-window
{display:none!important}
'''


async def capture(page, url, target):
    if not url:
        return None
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(1000)
        await page.add_style_tag(content=_CONSENT_HIDE_CSS)
        await page.screenshot(path=str(target))
        return target.as_posix()
    except Exception as exc:
        print('Evidence capture skipped:', exc)
        return None


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


def asset_url(path):
    return f'{ASSET_ORIGIN}/{quote(str(Path(path).resolve()), safe="")}'


# ---------------------------------------------------------------------------
# Executor: spec -> primitive call. This is the only place that reads a
# SlideSpec dict; every primitive function itself takes plain typed values,
# not the spec, so visual_primitives.py stays free of any editorial-JSON
# or spec-schema coupling.
# ---------------------------------------------------------------------------

def assemble(spec, evidence):
    prim = spec['primitive']
    accent, bg, fg = spec['accent'], spec['bg'], spec['fg']
    kicker, headline, body = spec['kicker'], spec['headline'], spec['body']

    if prim == 'hook':
        hsize = round(gd.scale(headline, [(14, 128), (20, 106), (28, 90), (40, 74), (999, 60)]) * (1.08 if spec['psychology_intense'] else 1.0))
        html = vp.hook(kicker, headline, hsize, body, accent, fg, spec['metric_value'], spec['metric_size'], spec['source_label'])
        return bg, fg, html

    if prim == 'hook_myth':
        html = vp.hook_myth(kicker, spec['myth_text'], spec['fact_text'], body, accent, fg, spec['source_label'])
        return bg, fg, html

    if prim == 'payoff':
        hsize = gd.scale(headline, [(18, 92), (28, 78), (40, 64), (999, 52)])
        html = vp.payoff(kicker, headline, hsize, body, accent, fg, spec['cta'])
        return bg, fg, html

    if prim == 'statement':
        hsize = gd.scale(headline, [(18, 100), (28, 84), (40, 68), (999, 54)])
        html = vp.statement(kicker, headline, hsize, body, accent, fg)
        return bg, fg, html

    if prim == 'giant_metric':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(24, 56), (36, 46), (999, 38)]), accent, fg, body, top=800, max_w=760, body_max_w=620)
        hero = vp.giant_metric(spec['metric_value'], spec['metric_is_word'], accent, top=160 if not spec['metric_is_word'] else 300)
        return bg, fg, hero + header

    if prim == 'data_bars':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(24, 58), (36, 48), (999, 40)]), accent, fg, top=150, max_w=820)
        hero = vp.data_bars(spec['bars'], accent, fg, top=620)
        footer_line = f'<div style="position:absolute;left:{M}px;top:1080px;width:780px;border-top:1px solid {fg}33;padding-top:18px;color:{fg}"><div style="font:600 18px/1.32 \'Archivo\';opacity:.8">{vp.esc(body)}</div></div>'
        return bg, fg, header + hero + footer_line

    if prim == 'comparison_split':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 72), (30, 60), (999, 48)]), accent, fg, top=140, max_w=900)
        a_label, a_val, b_label, b_val = spec['sides']
        hero = vp.comparison_split(a_label, a_val, b_label, b_val, accent, fg, bg)
        verdict = f'<div style="position:absolute;left:{M}px;top:1030px;width:780px;color:{fg}"><div style="font:700 18px/1.32 \'Archivo\';opacity:.85">{vp.esc(body)}</div></div>'
        return bg, fg, header + hero + verdict

    if prim == 'before_after':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 72), (30, 60), (999, 48)]), accent, fg, top=140, max_w=900)
        a_label, a_val, b_label, b_val = spec['sides']
        hero = vp.before_after(a_label, a_val, b_label, b_val, accent, fg, bg)
        verdict = f'<div style="position:absolute;left:{M}px;top:1030px;width:780px;color:{fg}"><div style="font:700 18px/1.32 \'Archivo\';opacity:.85">{vp.esc(body)}</div></div>'
        return bg, fg, header + hero + verdict

    if prim == 'timeline':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 74), (30, 62), (999, 50)]), accent, fg, body, top=140, max_w=880, body_max_w=700)
        hero = vp.timeline(spec['timeline_points'], accent, fg, top=740)
        return bg, fg, header + hero

    if prim == 'process_flow':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 74), (30, 62), (999, 50)]), accent, fg, top=140, max_w=880)
        frm, to = spec['process']
        hero = vp.process_flow(frm, to, accent, fg, bg, top=460)
        footer_line = f'<div style="position:absolute;left:{M}px;top:1060px;width:780px;border-top:1px solid {fg}33;padding-top:18px;color:{fg}"><div style="font:600 18px/1.32 \'Archivo\';opacity:.82">{vp.esc(body)}</div></div>'
        return bg, fg, header + hero + footer_line

    if prim == 'annotated_screenshot':
        hsize = gd.scale(headline, [(20, 68), (30, 58), (999, 48)])
        header = vp.header_block(kicker, headline, hsize, accent, fg, top=140, max_w=900)
        if evidence:
            hero = vp.annotated_screenshot(asset_url(evidence), accent, spec['badge_text'], spec.get('annotation'), top=320)
            caption_top = 1010
        else:
            src = spec.get('_source_story') or {}
            title = src.get('title') or spec.get('_context') or 'Verified source metadata'
            hero = vp.citation_card(src.get('source') or 'Primary Source', title, src.get('url') or spec.get('_domain', ''), accent, top=320)
            caption_top = 1010
        dom = spec.get('_domain', '')
        caption = f'''<div style="position:absolute;left:{M}px;top:{caption_top}px;width:760px;color:{fg}">
          <div style="font:700 18px/1.3 'Archivo'">{vp.esc(body)}</div>
          <div class="mono" style="margin-top:14px;font:500 10px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.55">{vp.esc(dom)}</div>
        </div>'''
        return bg, fg, header + hero + caption

    if prim == 'visual_quote':
        html = vp.visual_quote(kicker, spec['quote_text'], spec['quote_source'], accent, fg)
        return bg, fg, html

    # Should be unreachable — every primitive name graphics_director can
    # emit is handled above — but fail into the calm reset rather than a
    # KeyError if a future primitive name isn't wired up here yet.
    hsize = gd.scale(headline, [(18, 100), (28, 84), (40, 68), (999, 54)])
    return bg, fg, vp.statement(kicker, headline, hsize, body, accent, fg)


async def _fulfill_font(route):
    name = route.request.url.rsplit('/', 1)[-1]
    path = FONT_DIR / name
    if path.exists():
        await route.fulfill(path=str(path))
    else:
        await route.abort()


async def _fulfill_asset(route):
    local_path = unquote(route.request.url[len(ASSET_ORIGIN) + 1:])
    p = Path(local_path)
    if p.exists():
        await route.fulfill(path=str(p))
    else:
        await route.abort()


async def main():
    story = json.loads(DATA.read_text())
    slides = story.get('slides') or []
    if not story.get('selected') or not slides:
        raise SystemExit('No selected editorial')

    carousel = gd.direct(story)
    specs = carousel['slides']

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
        await page.route(f'{ASSET_ORIGIN}/**', _fulfill_asset)
        for i, slide in enumerate(slides):
            spec = specs[i]
            evidence = None
            if spec.get('needs_evidence'):
                target = ed / f'{i+1:02d}.png'
                evidence = await capture(page, source_url(story, slide), target)
                src = story.get('source_story') or {}
                spec['_source_story'] = src
                spec['_context'] = slide.get('context')
                spec['_domain'] = domain(source_url(story, slide))
            bg, fg, inner_html = assemble(spec, evidence)
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
    (pkg / 'design_spec.json').write_text(json.dumps(
        {'slides': [{k: v for k, v in s.items() if not k.startswith('_')} for s in specs]},
        ensure_ascii=False, indent=2,
    ))
    for name, value in [('caption.txt', story.get('caption', '')), ('alt-text.txt', story.get('alt_text', '')),
                         ('hashtags.txt', ' '.join(story.get('hashtags', []) or [])),
                         ('pinned-comment.txt', story.get('pinned_comment', ''))]:
        (pkg / name).write_text(clean(value))
    print(f'RENDERED={pkg}')
    print('GEMINI_CALL=0')
    print('SLIDES=', len(slides))
    print('PRIMITIVES=', [s['primitive'] for s in specs])


if __name__ == '__main__':
    asyncio.run(main())
