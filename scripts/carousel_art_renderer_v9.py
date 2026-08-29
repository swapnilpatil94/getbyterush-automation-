#!/usr/bin/env python3
import asyncio
import html
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

W, H = 1080, 1350
CREAM = '#F2EBDD'
INK = '#090B0A'
FOREST = '#12372C'
RED = '#B80D08'
LIME = '#B7E32B'
GOLD = '#C4A05B'
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/selected_story.json'
OUT = ROOT / 'output/posts'


def clean(v):
    s = html.unescape(str(v or ''))
    s = re.sub(r'https?://\S+', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def esc(v):
    return html.escape(clean(v), quote=True)


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


def metric(v):
    m = re.search(r'\b\d+(?:\.\d+)?\s*[xX%]\b', clean(v))
    return m.group(0).replace(' ', '') if m else ''


def domain(url):
    m = re.search(r'https?://([^/]+)', clean(url))
    return m.group(1).replace('www.', '') if m else 'source'


def role(slide, i):
    r = clean(slide.get('role')).lower().replace(' ', '_')
    return {
        'interrupt': 'hook', 'open_loop': 'open', 'proof': 'evidence',
        'escalation': 'reveal', 'pattern_interrupt': 'interrupt',
        'implication': 'architecture', 'payoff': 'payoff'
    }.get(r, ['hook', 'open', 'evidence', 'reveal', 'interrupt', 'architecture', 'payoff'][i])


def source_url(story, slide):
    u = clean(slide.get('asset_url') or slide.get('source_url'))
    return u if u.startswith('http') else clean((story.get('source_story') or {}).get('url'))


def source_label(slide):
    return clean(slide.get('source_label') or 'SOURCE')

BASE = f'''
@page{{size:{W}px {H}px;margin:0}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:Arial,Helvetica,sans-serif}}
.s{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}
.meta{{position:absolute;z-index:50;top:28px;left:52px;right:52px;display:flex;justify-content:space-between;align-items:center;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.7px;text-transform:uppercase}}
.page{{border:1px solid currentColor;padding:7px 9px}}
.foot{{position:absolute;z-index:50;bottom:27px;left:52px;right:52px;display:flex;justify-content:space-between;font:900 9px/1 ui-monospace,monospace;letter-spacing:1.2px;opacity:.55}}
.k{{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.8px;text-transform:uppercase}}
'''


def doc(inner, i, total, dark=False):
    bg, fg = (INK, CREAM) if dark else (CREAM, INK)
    return f'''<!doctype html><style>{BASE}.s{{background:{bg};color:{fg}}}</style><div class="s">{inner}<div class="meta"><span>getByteRush</span><span class="page">{i:02d} / {total:02d}</span></div><div class="foot"><span>TECH • AI • INTERNET</span><span>TESTED • EXPLAINED • REAL</span></div></div>'''


def grid(color='rgba(9,11,10,.07)', size=42):
    return f'background-image:linear-gradient({color} 1px,transparent 1px),linear-gradient(90deg,{color} 1px,transparent 1px);background-size:{size}px {size}px;'


def inner(slide, story, i, total, evidence):
    r = role(slide, i)
    h = punch(slide.get('headline'))
    b = support(slide.get('body'))
    k = esc(slide.get('kicker') or r)
    src = esc(source_label(slide))
    url = source_url(story, slide)
    dom = esc(domain(url))
    m = esc(metric(slide.get('headline') or slide.get('body')))

    if r == 'hook':
        return f'''<div style="position:absolute;inset:0;{grid('rgba(255,255,255,.09)',48)};background-color:{RED}">
          <div style="position:absolute;left:52px;top:112px;width:650px;height:1088px;padding:42px;color:{CREAM}">
            <div class="k">{k}</div>
            <div style="margin-top:72px;font-size:110px;line-height:.74;letter-spacing:-8px;font-weight:950;max-width:575px">{esc(h)}</div>
            <div style="margin-top:56px;max-width:510px;font-size:21px;line-height:1.08;font-weight:800">{esc(b)}</div>
            <div style="position:absolute;left:42px;right:42px;bottom:34px;border-top:1px solid rgba(255,255,255,.6);padding-top:11px;font:800 9px/1 ui-monospace,monospace;letter-spacing:1px">{src}</div>
          </div>
          <div style="position:absolute;right:52px;top:164px;width:238px;height:870px;background:{INK};color:{CREAM};padding:24px">
            <div class="k" style="color:{LIME}">01 / INTERRUPT</div>
            <div style="position:absolute;left:22px;top:300px;font-size:178px;line-height:.58;font-weight:950;letter-spacing:-13px;color:{LIME};writing-mode:vertical-rl;transform:rotate(180deg)">{m or '×'}</div>
            <div style="position:absolute;left:22px;bottom:38px;font-size:14px;font-weight:900">SWIPE →</div>
            <div style="position:absolute;left:22px;bottom:110px;width:110px;height:2px;background:{RED}"></div>
          </div>
        </div>'''

    if r == 'open':
        return f'''<div style="position:absolute;inset:0;{grid()}">
          <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">{k}</div><div style="margin-top:18px;font-size:76px;line-height:.78;letter-spacing:-5px;font-weight:950;max-width:920px">{esc(h)}</div></div>
          <div style="position:absolute;left:52px;top:430px;width:560px;height:610px;border:2px solid {INK};padding:34px;background:{CREAM}">
            <div class="k" style="opacity:.55">THE PROBLEM</div>
            <div style="margin-top:58px;font-size:51px;line-height:.82;letter-spacing:-3px;font-weight:950;max-width:475px">{esc(punch(b,10,68))}</div>
            <div style="position:absolute;right:25px;bottom:24px;font-size:115px;color:{RED};font-weight:900">↗</div>
            <div style="position:absolute;left:34px;bottom:30px;width:135px;height:1px;background:{INK};opacity:.35"></div>
          </div>
          <div style="position:absolute;right:52px;top:392px;width:355px;height:705px;background:{FOREST};color:{CREAM};padding:30px">
            <div class="k" style="color:{LIME}">02 / WHY IT MATTERS</div>
            <div style="margin-top:66px;font-size:48px;line-height:.82;letter-spacing:-3px;font-weight:950">{esc(punch(h,7,50))}</div>
            <div style="position:absolute;left:30px;right:30px;bottom:34px;border-top:1px solid rgba(255,255,255,.35);padding-top:14px;font-size:15px;line-height:1.15;opacity:.76">{esc(support(slide.get('implication') or b,13,105))}</div>
          </div>
          <div style="position:absolute;left:52px;right:52px;bottom:110px;height:34px;display:flex;gap:9px;align-items:center">{''.join(f'<i style="display:block;width:{18 if j==2 else 8}px;height:8px;background:{RED if j==2 else INK};opacity:{1 if j==2 else .25}"></i>' for j in range(7))}</div>
        </div>'''

    if r == 'evidence':
        if evidence:
            visual = f'<img src="file://{evidence}" style="width:100%;height:100%;object-fit:contain;display:block">'
            badge = 'VERIFIED / SOURCE'
        else:
            visual = f'''<div style="height:100%;padding:34px;display:flex;flex-direction:column;justify-content:space-between;background:{INK};color:{CREAM}">
              <div class="k" style="color:{LIME}">WEB SOURCE</div>
              <div><div style="font-size:38px;line-height:.9;font-weight:950;letter-spacing:-2px">{dom}</div><div style="margin-top:20px;font:800 10px/1.3 ui-monospace,monospace;opacity:.65;word-break:break-all">{esc(url)}</div></div>
              <div style="border-top:1px solid rgba(255,255,255,.25);padding-top:16px;font-size:18px;line-height:1.08;font-weight:800">{esc(punch(b,14,120))}</div>
            </div>'''
            badge = 'SOURCE / CHECKED'
        return f'''<div style="position:absolute;inset:0;{grid()}">
          <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">{k}</div><div style="margin-top:15px;font-size:69px;line-height:.8;letter-spacing:-5px;font-weight:950;max-width:910px">{esc(h)}</div></div>
          <div style="position:absolute;left:52px;right:52px;top:420px;height:670px">
            <div style="position:absolute;left:0;right:125px;top:0;height:620px;background:#fff;border:2px solid {INK};padding:12px;overflow:hidden;box-shadow:24px 24px 0 {RED}">
              <span style="position:absolute;z-index:5;left:22px;top:22px;background:{RED};color:{CREAM};padding:9px 12px;font:900 9px/1 ui-monospace,monospace;letter-spacing:1px">{badge}</span>{visual}
            </div>
            <div style="position:absolute;right:0;top:35px;width:86px;font:900 9px/1.1 ui-monospace,monospace;writing-mode:vertical-rl;transform:rotate(180deg);opacity:.55">{src}</div>
            <div style="position:absolute;left:0;bottom:0;max-width:740px;font-size:18px;line-height:1.12;font-weight:900">{esc(b)}</div>
          </div>
        </div>'''

    if r == 'reveal':
        return f'''<div style="position:absolute;inset:0;background:{INK};color:{CREAM}">
          <div style="position:absolute;left:52px;right:52px;top:120px"><div class="k" style="color:{LIME}">04 / {k}</div><div style="margin-top:44px;font-size:108px;line-height:.68;letter-spacing:-8px;font-weight:950;max-width:690px">{esc(h)}</div><div style="margin-top:42px;max-width:510px;font-size:18px;line-height:1.18;opacity:.72">{esc(b)}</div></div>
          <div style="position:absolute;right:-25px;bottom:80px;font-size:340px;line-height:.5;font-weight:950;letter-spacing:-24px;color:{LIME}">{m or '→'}</div>
          <div style="position:absolute;left:52px;bottom:82px;width:250px;border-top:2px solid {LIME};padding-top:10px;font:800 9px/1.2 ui-monospace,monospace">{src}</div>
          <div style="position:absolute;right:52px;top:215px;width:94px;height:94px;border:1px solid {LIME};border-radius:50%"></div>
          <div style="position:absolute;left:52px;bottom:170px;width:120px;height:8px;background:{RED}"></div>
        </div>'''

    if r == 'interrupt':
        return f'''<div style="position:absolute;inset:0;background:{RED};color:{CREAM}">
          <div style="position:absolute;left:52px;right:52px;top:138px;bottom:70px;border-top:2px solid rgba(255,255,255,.55);border-bottom:2px solid rgba(255,255,255,.55)">
            <div class="k" style="position:absolute;right:0;top:22px">05 / PATTERN INTERRUPT</div>
            <div style="position:absolute;left:0;top:148px;max-width:860px;font-size:116px;line-height:.69;letter-spacing:-8px;font-weight:950">{esc(h)}</div>
            <div style="position:absolute;left:0;bottom:20px;max-width:560px;font-size:18px;line-height:1.15;opacity:.82">{esc(b)}</div>
            <div style="position:absolute;right:-25px;bottom:-90px;font-size:310px;line-height:.5;font-weight:950;color:{INK};opacity:.18">{m or '×'}</div>
            <div style="position:absolute;left:0;top:70px;width:135px;height:2px;background:{INK}"></div>
            <div style="position:absolute;right:0;top:72px;display:flex;gap:7px">{''.join('<i style="display:block;width:8px;height:8px;background:'+INK+'"></i>' for _ in range(5))}</div>
          </div>
        </div>'''

    if r == 'architecture':
        labels = [
            ('01 / INPUT', punch(slide.get('context') or 'LONG CONTEXT', 3, 28)),
            ('02 / MEMORY', 'RETAIN'),
            ('03 / RESULT', punch(slide.get('implication') or 'MORE WORK', 3, 28)),
        ]
        cards = ''
        for j, (lab, val) in enumerate(labels):
            x = [0, 320, 640][j]
            bg = [CREAM, FOREST, RED][j]
            fg = [INK, CREAM, CREAM][j]
            accent = [RED, LIME, INK][j]
            cards += f'''<div style="position:absolute;left:{x}px;top:{[0,82,0][j]}px;width:285px;height:240px;background:{bg};color:{fg};padding:24px;border:2px solid {INK if j==0 else bg}"><div class="k" style="color:{accent}">{lab}</div><div style="margin-top:50px;font-size:34px;line-height:.88;font-weight:950;letter-spacing:-2px">{esc(val)}</div></div>'''
        return f'''<div style="position:absolute;inset:0;{grid()}">
          <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">{k}</div><div style="margin-top:15px;font-size:74px;line-height:.79;letter-spacing:-5px;font-weight:950;max-width:920px">{esc(h)}</div></div>
          <div style="position:absolute;left:52px;right:52px;top:470px;height:590px">
            {cards}
            <div style="position:absolute;left:285px;top:110px;font-size:38px;color:{RED};font-weight:900">→</div><div style="position:absolute;left:605px;top:110px;font-size:38px;color:{RED};font-weight:900">→</div>
            <div style="position:absolute;left:0;right:0;bottom:0;border-top:1px solid rgba(9,11,10,.22);padding-top:18px;max-width:760px;font-size:18px;line-height:1.15;opacity:.72">{esc(b)}</div>
          </div>
          <div style="position:absolute;right:52px;bottom:100px;font:900 9px/1 ui-monospace,monospace;letter-spacing:1.4px">SYSTEM / 06</div>
        </div>'''

    return f'''<div style="position:absolute;inset:0;{grid()}">
      <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">07 / THE BOTTOM LINE</div><div style="margin-top:18px;font-size:76px;line-height:.78;letter-spacing:-5px;font-weight:950;max-width:910px">{esc(h)}</div></div>
      <div style="position:absolute;left:52px;right:52px;top:430px;height:690px;background:{INK};color:{CREAM};padding:52px;overflow:hidden">
        <div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,transparent 0 58px,rgba(255,255,255,.035) 59px)"></div>
        <div style="position:relative"><div class="k" style="color:{LIME}">THE ERA AHEAD</div><div style="margin-top:55px;font-size:88px;line-height:.73;letter-spacing:-7px;font-weight:950;max-width:760px">{esc(h)}</div><div style="margin-top:32px;max-width:600px;font-size:18px;line-height:1.16;opacity:.72">{esc(b)}</div></div>
        <div style="position:absolute;right:-25px;bottom:-110px;font-size:340px;line-height:.48;font-weight:950;color:{RED}">→</div>
        <div style="position:absolute;left:52px;bottom:38px;border-top:1px solid rgba(255,255,255,.3);width:300px;padding-top:10px;font:800 9px/1 ui-monospace,monospace">{src}</div>
      </div>
    </div>'''


async def capture(page, url, target):
    if not url:
        return None
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(1000)
        await page.add_style_tag(content='''[id*=cookie],[class*=cookie],[id*=consent],[class*=consent],[aria-label*=cookie i],[aria-label*=consent i]{display:none!important}''')
        await page.screenshot(path=str(target))
        return target.as_posix()
    except Exception as exc:
        print('Evidence capture skipped:', exc)
        return None


async def main():
    story = json.loads(DATA.read_text())
    slides = story.get('slides') or []
    if not story.get('selected') or not slides:
        raise SystemExit('No selected editorial')
    now = datetime.now().astimezone()
    slug = re.sub(r'[^a-z0-9]+', '-', clean(story.get('story_title', 'post')).lower()).strip('-')[:72]
    pkg = OUT / now.strftime('%Y-%m-%d') / (now.strftime('%H%M%S') + '-' + slug)
    sd, hd, ed = pkg/'slides', pkg/'html', pkg/'evidence'
    for p in (sd, hd, ed):
        p.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        for i, slide in enumerate(slides):
            evidence = None
            if role(slide, i) == 'evidence':
                target = ed / f'{i+1:02d}.png'
                evidence = await capture(page, source_url(story, slide), target)
            html_text = doc(inner(slide, story, i, len(slides), evidence), i+1, len(slides), dark=role(slide, i) in {'reveal'})
            hf = hd / f'{i+1:02d}.html'
            pf = sd / f'{i+1:02d}.png'
            hf.write_text(html_text)
            await page.set_content(html_text, wait_until='load')
            await page.screenshot(path=str(pf), full_page=False)
        await browser.close()
    out = dict(story)
    out['renderer'] = 'getbyterush-pinterest-editorial-v9'
    out['gemini_calls'] = 0
    out['rendered_at'] = datetime.now().astimezone().isoformat()
    (pkg/'post.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
    for name, value in [('caption.txt', story.get('caption','')), ('alt-text.txt', story.get('alt_text','')), ('hashtags.txt', ' '.join(story.get('hashtags',[]) or [])), ('pinned-comment.txt', story.get('pinned_comment',''))]:
        (pkg/name).write_text(clean(value))
    print(f'RENDERED={pkg}')
    print('GEMINI_CALL=0')
    print('SLIDES=', len(slides))


if __name__ == '__main__':
    asyncio.run(main())
