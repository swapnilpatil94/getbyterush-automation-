#!/usr/bin/env python3
"""GetByteRush V17 — renderer / executor.

Architecture: EDITORIAL -> GRAPHICS DIRECTOR (graphics_director_v17.py,
via visual_grammars.py) -> V17 (this file) -> QA.

Same split as v16: this file makes no design decisions. It reads the
CarouselSpec from graphics_director_v17.direct(story) and calls the
matching grammar-variant primitive from visual_primitives_v17.py (falling
back to visual_primitives.py for the variants that were already correct —
real-screenshot evidence, the two-panel comparison, the pull quote, the
2-point timeline, the calm payoff bookend). I/O, font/asset routing, and
evidence capture are reused unchanged from carousel_art_renderer_v16.py —
none of that plumbing was the problem V17 is fixing.
"""
import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

import carousel_art_renderer_v16 as v16
import carousel_families
import graphics_director as gd
import graphics_director_v17 as gd17
import visual_primitives as vp
import visual_primitives_v17 as vp17
from playwright.async_api import async_playwright

W, H, M = v16.W, v16.H, v16.M
DATA = Path(os.environ['GBR_INPUT']) if os.environ.get('GBR_INPUT') else v16.DATA
OUT = Path(os.environ['GBR_OUT']) if os.environ.get('GBR_OUT') else v16.OUT
clean, source_url, source_label, domain = v16.clean, v16.source_url, v16.source_label, v16.domain
doc, masthead, foot, asset_url = v16.doc, v16.masthead, v16.foot, v16.asset_url
capture = v16.capture


def assemble(spec, evidence):
    grammar, variant = spec['grammar'], spec['variant']
    accent, bg, fg = spec['accent'], spec['bg'], spec['fg']
    kicker, headline, body = spec['kicker'], spec['headline'], spec['body']
    is_first = spec['number'] == 1

    if grammar == 'payoff':
        hsize = gd.scale(headline, [(18, 92), (28, 78), (40, 64), (999, 52)])
        return bg, fg, vp.payoff(kicker, headline, hsize, body, accent, fg, spec['cta'])

    if grammar == 'confrontation':
        top = 170 if is_first else 460
        scale = 1.0 if is_first else 0.8
        html = vp17.confrontation(kicker, spec['myth_text'], spec['fact_text'], body, accent, fg, spec.get('source_label', ''), top=top, scale=scale)
        return bg, fg, html

    if grammar == 'evidence_screenshot':
        hsize = gd.scale(headline, [(20, 68), (30, 58), (999, 48)])
        header = vp.header_block(kicker, headline, hsize, accent, fg, top=140, max_w=900)
        if evidence:
            hero = vp.annotated_screenshot(asset_url(evidence), accent, spec['badge_text'], spec.get('annotation'), top=320)
        else:
            src = spec.get('_source_story') or {}
            title = src.get('title') or spec.get('_context') or 'Verified source metadata'
            hero = vp.citation_card(src.get('source') or 'Primary Source', title, src.get('url') or spec.get('_domain', ''), accent, top=320)
        dom = spec.get('_domain', '')
        caption = f'''<div style="position:absolute;left:{M}px;top:1010px;width:760px;color:{fg}">
          <div style="font:700 18px/1.3 'Archivo'">{vp.esc(body)}</div>
          <div class="mono" style="margin-top:14px;font:500 10px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.55">{vp.esc(dom)}</div>
        </div>'''
        return bg, fg, header + hero + caption

    if grammar == 'comparison' and variant == 'matrix':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 68), (30, 58), (999, 46)]), accent, fg, top=140, max_w=900)
        hero = vp17.comparison_matrix(spec['a_label'], spec['b_label'], spec['rows'], accent, fg, top=420)
        return bg, fg, header + hero

    if grammar == 'comparison':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 72), (30, 60), (999, 48)]), accent, fg, top=140, max_w=900)
        a_label, a_val, b_label, b_val = spec['sides']
        hero = vp.comparison_split(a_label, a_val, b_label, b_val, accent, fg, bg)
        verdict = f'<div style="position:absolute;left:{M}px;top:1030px;width:780px;color:{fg}"><div style="font:700 18px/1.32 \'Archivo\';opacity:.85">{vp.esc(body)}</div></div>'
        return bg, fg, header + hero + verdict

    if grammar == 'proportional_field':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 72), (30, 60), (999, 48)]), accent, fg, top=140, max_w=880)
        if variant == 'dot_field':
            hero = vp17.proportional_field(spec['pct'], spec['label_hi'], spec['label_lo'], accent, fg)
        else:
            hero = vp17.bar_split(spec['pct'], spec['label_hi'], spec['label_lo'], accent, fg)
        return bg, fg, header + hero

    if grammar == 'accumulation_trail':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 68), (30, 58), (999, 46)]), accent, fg, body, top=140, max_w=880, body_max_w=760)
        hero = vp17.accumulation_trail(spec['start_value'], spec['stages'], accent, fg)
        return bg, fg, header + hero

    if grammar == 'chronological_sequence':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 74), (30, 62), (999, 50)]), accent, fg, top=140, max_w=880)
        if variant == 'multi_point':
            hero = vp17.chronological_multi(spec['years'], accent, fg, top=680)
        else:
            hero = vp.timeline(spec['timeline_points'], accent, fg, top=740)
        return bg, fg, header + hero

    if grammar == 'sequential_system':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 68), (30, 58), (999, 46)]), accent, fg, top=140, max_w=880)
        if variant == 'chain_vertical':
            hero = vp17.chain_vertical(spec['steps'], spec['weights'], accent, fg)
        else:
            hero = vp17.layered_stack(spec['steps'], accent, fg)
        return bg, fg, header + hero

    if grammar == 'quote':
        return bg, fg, vp.visual_quote(kicker, spec['quote_text'], spec['quote_source'], accent, fg)

    if grammar == 'evidence_board' and variant == 'pinned_chips':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(20, 68), (30, 58), (999, 46)]), accent, fg, top=140, max_w=880)
        hero = vp17.evidence_board(spec['chips'], accent, fg, bg, top=380)
        return bg, fg, header + hero

    if grammar == 'evidence_board':
        hero = vp.citation_card(spec['source_label_full'], spec['quote_text'], '', accent, top=320)
        caption = f'<div style="position:absolute;left:{M}px;top:1010px;width:760px;color:{fg}"><div style="font:700 18px/1.3 \'Archivo\'">{vp.esc(headline)}</div></div>'
        return bg, fg, hero + caption

    if grammar == 'singular_object' and variant == 'metric_texture':
        header = vp.header_block(kicker, headline, gd.scale(headline, [(24, 56), (36, 46), (999, 38)]), accent, fg, body, top=840, max_w=760, body_max_w=620)
        hero = vp17.metric_texture(spec['metric_value'], accent, fg, top=160)
        return bg, fg, hero + header

    hsize = gd.scale(headline, [(18, 100), (28, 84), (40, 68), (999, 54)])
    return bg, fg, vp.statement(kicker, headline, hsize, body, accent, fg)


async def main():
    story = json.loads(DATA.read_text())
    slides = story.get('slides') or []
    if not story.get('selected') or not slides:
        raise SystemExit('No selected editorial')

    # Visual families (Bulletin/Headline Block/Ledger/Signal/Dossier/Pulse)
    # replaced the old per-slide grammar system as the default render path
    # after the design review — see carousel_families.py. GBR_LEGACY_GRAMMAR=1
    # is a rollback escape hatch to the old graphics_director_v17 system
    # without a code revert, kept only for that purpose.
    use_legacy = os.environ.get('GBR_LEGACY_GRAMMAR') == '1'
    evidence_urls = {i: source_url(story, s) for i, s in enumerate(slides) if source_url(story, s)}
    specs = None
    family_specs = None
    if use_legacy:
        carousel = gd17.direct(story, evidence_urls)
        specs = carousel['slides']
    else:
        family = carousel_families.resolve_family(story)
        accent = ((story.get('design') or {}).get('accent_color')) or '#12352B'
        family_specs = []

    now = datetime.now().astimezone()
    slug = re.sub(r'[^a-z0-9]+', '-', clean(story.get('story_title', 'post')).lower()).strip('-')[:72]
    pkg = OUT / now.strftime('%Y-%m-%d') / (now.strftime('%H%M%S') + '-' + slug)
    sd, hd, ed = pkg / 'slides', pkg / 'html', pkg / 'evidence'
    for p in (sd, hd, ed):
        p.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        await page.route(f'{v16.FONT_ORIGIN}/**', v16._fulfill_font)
        await page.route(f'{v16.ASSET_ORIGIN}/**', v16._fulfill_asset)
        for i, slide in enumerate(slides):
            if use_legacy:
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
            else:
                is_hook, is_payoff = (i == 0), (i == len(slides) - 1)
                bg, fg, inner_html = carousel_families.render_slide(
                    family,
                    kicker=slide.get('kicker', ''),
                    headline=slide.get('headline', ''),
                    body=slide.get('body', ''),
                    accent=accent,
                    number=i + 1,
                    total=len(slides),
                    is_hook=is_hook,
                    is_payoff=is_payoff,
                )
                family_specs.append({
                    'number': i + 1,
                    'grammar': 'headline_block' if (is_hook or is_payoff) else family,
                    'variant': 'bookend' if (is_hook or is_payoff) else family,
                    'accent': accent, 'bg': bg, 'fg': fg,
                })
            html_text = doc(inner_html, bg, fg, i + 1, len(slides))
            (hd / f'{i+1:02d}.html').write_text(html_text)
            await page.set_content(html_text, wait_until='load')
            await page.evaluate('document.fonts.ready')
            # JPEG, not PNG: Instagram's Content Publishing API only
            # accepts JPEG images (confirmed live — a Make.com carousel
            # post failed Instagram-side validation on the image files
            # specifically once caption/URL issues were ruled out). Pure
            # output-format change — the design system (visual_grammars,
            # graphics_director, primitives) is untouched; every slide is
            # still an opaque full-bleed background with no transparency,
            # so JPEG loses nothing.
            await page.screenshot(path=str(sd / f'{i+1:02d}.jpg'), type='jpeg', quality=92, full_page=False)
        await browser.close()

    out = dict(story)
    out['renderer'] = 'getbyterush-pinterest-editorial-v17'
    out['gemini_calls'] = 0
    out['rendered_at'] = datetime.now().astimezone().isoformat()
    out['visual_family'] = 'legacy_grammar' if use_legacy else family
    final_specs = specs if use_legacy else family_specs
    (pkg / 'post.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
    (pkg / 'design_spec.json').write_text(json.dumps(
        {'slides': [{k: v for k, v in s.items() if not k.startswith('_')} for s in final_specs]},
        ensure_ascii=False, indent=2,
    ))
    for name, value in [('caption.txt', story.get('caption', '')), ('alt-text.txt', story.get('alt_text', '')),
                         ('hashtags.txt', ' '.join(story.get('hashtags', []) or [])),
                         ('pinned-comment.txt', story.get('pinned_comment', ''))]:
        (pkg / name).write_text(clean(value))
    print(f'RENDERED={pkg}')
    print('GEMINI_CALL=0')
    print('SLIDES=', len(slides))
    print('GRAMMARS=', [f"{s['grammar']}:{s['variant']}" for s in final_specs])


if __name__ == '__main__':
    asyncio.run(main())
