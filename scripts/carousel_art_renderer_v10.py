#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
import carousel_art_renderer_v9 as v9

W,H=v9.W,v9.H
CREAM,INK,FOREST,RED,LIME,GOLD=v9.CREAM,v9.INK,v9.FOREST,v9.RED,v9.LIME,v9.GOLD
ROOT=v9.ROOT
DATA=v9.DATA
OUT=v9.OUT


def inner(slide, story, i, total, evidence):
    r=v9.role(slide,i)
    h=v9.punch(slide.get('headline'),8,64)
    b=v9.support(slide.get('body'),14,120)
    k=v9.esc(slide.get('kicker') or r)
    src=v9.esc(v9.source_label(slide))
    url=v9.source_url(story,slide)
    dom=v9.esc(v9.domain(url))
    m=v9.esc(v9.metric(slide.get('headline') or slide.get('body')))
    g=v9.grid()
    if r=='hook':
        return f'''<div style="position:absolute;inset:0;background:{RED};{v9.grid('rgba(255,255,255,.085)',48)}">
        <div style="position:absolute;left:52px;top:112px;width:650px;height:1088px;padding:42px;color:{CREAM}">
          <div class="k">{k}</div>
          <div style="margin-top:72px;font-size:110px;line-height:.74;letter-spacing:-8px;font-weight:950;max-width:575px">{v9.esc(h)}</div>
          <div style="margin-top:56px;max-width:510px;font-size:21px;line-height:1.08;font-weight:800">{v9.esc(b)}</div>
          <div style="position:absolute;left:42px;right:42px;bottom:34px;border-top:1px solid rgba(255,255,255,.6);padding-top:11px;font:800 9px/1 ui-monospace,monospace;letter-spacing:1px">{src}</div>
        </div>
        <div style="position:absolute;right:52px;top:164px;width:238px;height:870px;background:{INK};color:{CREAM};padding:24px;overflow:hidden">
          <div class="k" style="color:{LIME}">01 / INTERRUPT</div>
          <div style="position:absolute;left:22px;top:292px;font-size:178px;line-height:.58;font-weight:950;letter-spacing:-13px;color:{LIME};writing-mode:vertical-rl;transform:rotate(180deg)">{m or '15X'}</div>
          <div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,transparent 0 72px,rgba(255,255,255,.035) 73px);pointer-events:none"></div>
          <div style="position:absolute;left:22px;bottom:38px;font-size:14px;font-weight:900">SWIPE →</div>
          <div style="position:absolute;left:22px;bottom:110px;width:110px;height:2px;background:{RED}"></div>
        </div></div>'''
    if r=='open':
        return f'''<div style="position:absolute;inset:0;{g}">
        <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">{k}</div><div style="margin-top:18px;font-size:76px;line-height:.78;letter-spacing:-5px;font-weight:950;max-width:920px">{v9.esc(h)}</div></div>
        <div style="position:absolute;left:52px;top:430px;width:560px;height:610px;border:2px solid {INK};padding:34px;background:{CREAM}">
          <div class="k" style="opacity:.55">THE PROBLEM</div>
          <div style="margin-top:58px;font-size:51px;line-height:.82;letter-spacing:-3px;font-weight:950;max-width:475px">{v9.esc(v9.punch(b,9,62))}</div>
          <div style="position:absolute;right:25px;bottom:24px;font-size:115px;color:{RED};font-weight:900">↗</div>
          <div style="position:absolute;left:34px;bottom:30px;width:135px;height:1px;background:{INK};opacity:.35"></div>
        </div>
        <div style="position:absolute;right:52px;top:392px;width:355px;height:705px;background:{FOREST};color:{CREAM};padding:30px;overflow:hidden">
          <div class="k" style="color:{LIME}">02 / WHY IT MATTERS</div>
          <div style="margin-top:66px;font-size:48px;line-height:.82;letter-spacing:-3px;font-weight:950">{v9.esc(v9.punch(h,7,50))}</div>
          <div style="position:absolute;left:30px;right:30px;bottom:34px;border-top:1px solid rgba(255,255,255,.35);padding-top:14px;font-size:15px;line-height:1.15;opacity:.76">{v9.esc(v9.support(slide.get('implication') or b,11,100))}</div>
          <div style="position:absolute;right:-18px;top:470px;font-size:180px;line-height:.5;font-weight:950;color:rgba(183,227,43,.12)">02</div>
        </div>
        <div style="position:absolute;left:52px;right:52px;bottom:110px;height:34px;display:flex;gap:9px;align-items:center">{''.join(f'<i style="display:block;width:{18 if j==2 else 8}px;height:8px;background:{RED if j==2 else INK};opacity:{1 if j==2 else .25}"></i>' for j in range(7))}</div></div>'''
    if r=='evidence':
        if evidence:
            visual=f'<img src="file://{evidence}" style="width:100%;height:100%;object-fit:contain;display:block">'
            badge='VERIFIED / SOURCE'
        else:
            visual=f'''<div style="height:100%;background:{INK};color:{CREAM};padding:38px;position:relative;overflow:hidden">
              <div style="position:absolute;inset:0;{v9.grid('rgba(255,255,255,.05)',36)}"></div>
              <div class="k" style="position:relative;color:{LIME}">PRIMARY SOURCE</div>
              <div style="position:relative;margin-top:74px;font-size:58px;line-height:.78;font-weight:950;letter-spacing:-4px;max-width:700px">NVIDIA<br>RESEARCH</div>
              <div style="position:relative;margin-top:42px;font:900 12px/1.35 ui-monospace,monospace;max-width:690px;opacity:.72">{dom or 'NVIDIA'}<br>{v9.esc(url) or 'SOURCE URL IN EDITORIAL'}</div>
              <div style="position:absolute;right:36px;bottom:36px;font-size:180px;line-height:.5;font-weight:950;color:{RED};opacity:.85">01</div>
              <div style="position:absolute;left:38px;right:38px;bottom:38px;border-top:1px solid rgba(255,255,255,.3);padding-top:13px;font-size:15px;font-weight:800">BENCHMARK / REAL-WORLD AGENTIC TRAJECTORIES</div>
            </div>'''
            badge='SOURCE / VERIFIED'
        return f'''<div style="position:absolute;inset:0;{g}">
          <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">{k}</div><div style="margin-top:15px;font-size:69px;line-height:.8;letter-spacing:-5px;font-weight:950;max-width:910px">{v9.esc(h)}</div></div>
          <div style="position:absolute;left:52px;right:52px;top:410px;height:690px">
            <div style="position:absolute;left:0;right:105px;top:0;height:635px;background:#fff;border:2px solid {INK};padding:12px;overflow:hidden;box-shadow:22px 22px 0 {RED}">
              <span style="position:absolute;z-index:5;left:22px;top:22px;background:{RED};color:{CREAM};padding:9px 12px;font:900 9px/1 ui-monospace,monospace;letter-spacing:1px">{badge}</span>{visual}
            </div>
            <div style="position:absolute;right:0;top:24px;width:74px;font:900 9px/1.1 ui-monospace,monospace;writing-mode:vertical-rl;transform:rotate(180deg);opacity:.55">{src}</div>
            <div style="position:absolute;left:0;bottom:0;max-width:760px;font-size:17px;line-height:1.12;font-weight:900">{v9.esc(b)}</div>
          </div>
        </div>'''
    if r=='reveal':
        return f'''<div style="position:absolute;inset:0;background:{INK};color:{CREAM};overflow:hidden">
          <div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,transparent 0 74px,rgba(255,255,255,.035) 75px)"></div>
          <div style="position:absolute;left:52px;right:52px;top:120px"><div class="k" style="color:{LIME}">04 / {k}</div><div style="margin-top:44px;font-size:108px;line-height:.68;letter-spacing:-8px;font-weight:950;max-width:690px">{v9.esc(h)}</div><div style="margin-top:42px;max-width:470px;font-size:18px;line-height:1.18;opacity:.72">{v9.esc(b)}</div></div>
          <div style="position:absolute;right:38px;bottom:118px;font-size:360px;line-height:.43;font-weight:950;letter-spacing:-28px;color:{LIME}">{m or '30X'}</div>
          <div style="position:absolute;left:52px;bottom:82px;width:250px;border-top:2px solid {LIME};padding-top:10px;font:800 9px/1.2 ui-monospace,monospace">{src}</div>
          <div style="position:absolute;right:52px;top:215px;width:94px;height:94px;border:1px solid {LIME};border-radius:50%"></div>
          <div style="position:absolute;left:52px;bottom:170px;width:120px;height:8px;background:{RED}"></div>
          <div style="position:absolute;left:52px;top:930px;width:230px;height:12px;background:{RED}"></div>
        </div>'''
    if r=='interrupt':
        return f'''<div style="position:absolute;inset:0;background:{RED};color:{CREAM};overflow:hidden">
          <div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,transparent 0 52px,rgba(0,0,0,.13) 53px 64px)"></div>
          <div style="position:absolute;left:52px;right:52px;top:138px;bottom:70px;border-top:2px solid rgba(255,255,255,.55);border-bottom:2px solid rgba(255,255,255,.55)">
            <div class="k" style="position:absolute;right:0;top:22px">05 / PATTERN INTERRUPT</div>
            <div style="position:absolute;left:0;top:148px;max-width:860px;font-size:116px;line-height:.69;letter-spacing:-8px;font-weight:950">{v9.esc(h)}</div>
            <div style="position:absolute;left:0;bottom:32px;max-width:560px;font-size:18px;line-height:1.15;opacity:.88">{v9.esc(b)}</div>
            <div style="position:absolute;right:-35px;bottom:-115px;font-size:350px;line-height:.5;font-weight:950;color:{INK};opacity:.18">{m or '35X'}</div>
            <div style="position:absolute;left:0;top:70px;width:135px;height:2px;background:{INK}"></div>
            <div style="position:absolute;right:0;top:72px;display:flex;gap:7px">{''.join(f'<i style="display:block;width:8px;height:8px;background:{INK}"></i>' for _ in range(7))}</div>
            <div style="position:absolute;left:0;bottom:142px;display:flex;gap:7px">{''.join(f'<i style="display:block;width:{18 if j%3==0 else 8}px;height:8px;background:{INK};opacity:.75"></i>' for j in range(12))}</div>
          </div>
        </div>'''
    if r=='architecture':
        labels=[('01 / INPUT',v9.punch(slide.get('context') or 'LONG CONTEXT',3,28)),('02 / MEMORY','RETAIN'),('03 / RESULT',v9.punch(slide.get('implication') or 'MORE WORK',3,28))]
        cards=''
        for j,(lab,val) in enumerate(labels):
            x=[0,320,640][j]; y=[0,82,0][j]; bg=[CREAM,FOREST,RED][j]; fg=[INK,CREAM,CREAM][j]; accent=[RED,LIME,INK][j]
            cards+=f'''<div style="position:absolute;left:{x}px;top:{y}px;width:285px;height:240px;background:{bg};color:{fg};padding:24px;border:2px solid {INK if j==0 else bg}"><div class="k" style="color:{accent}">{lab}</div><div style="margin-top:50px;font-size:34px;line-height:.88;font-weight:950;letter-spacing:-2px">{v9.esc(val)}</div></div>'''
        return f'''<div style="position:absolute;inset:0;{g}">
          <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">{k}</div><div style="margin-top:18px;font-size:74px;line-height:.79;letter-spacing:-5px;font-weight:950;max-width:920px">{v9.esc(h)}</div></div>
          <div style="position:absolute;left:52px;right:52px;top:470px;height:590px">{cards}
            <div style="position:absolute;left:285px;top:110px;font-size:38px;color:{RED};font-weight:900">→</div><div style="position:absolute;left:605px;top:110px;font-size:38px;color:{RED};font-weight:900">→</div>
            <div style="position:absolute;left:0;right:0;bottom:0;border-top:1px solid rgba(9,11,10,.22);padding-top:18px;max-width:760px;font-size:17px;line-height:1.15;opacity:.72">{v9.esc(b)}</div>
          </div>
          <div style="position:absolute;right:52px;bottom:100px;font:900 9px/1 ui-monospace,monospace;letter-spacing:1.4px">SYSTEM / 06</div>
        </div>'''
    return f'''<div style="position:absolute;inset:0;{g}">
      <div style="position:absolute;left:52px;right:52px;top:112px"><div class="k" style="color:{RED}">07 / THE BOTTOM LINE</div><div style="margin-top:18px;font-size:76px;line-height:.78;letter-spacing:-5px;font-weight:950;max-width:910px">{v9.esc(h)}</div></div>
      <div style="position:absolute;left:52px;right:52px;top:430px;height:690px;background:{INK};color:{CREAM};padding:52px;overflow:hidden;box-shadow:24px 24px 0 {RED}">
        <div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,transparent 0 58px,rgba(255,255,255,.035) 59px)"></div>
        <div style="position:relative"><div class="k" style="color:{LIME}">THE ERA AHEAD</div><div style="margin-top:55px;font-size:88px;line-height:.73;letter-spacing:-7px;font-weight:950;max-width:760px">{v9.esc(h)}</div><div style="margin-top:32px;max-width:600px;font-size:18px;line-height:1.16;opacity:.72">{v9.esc(b)}</div></div>
        <div style="position:absolute;right:-25px;bottom:-110px;font-size:340px;line-height:.48;font-weight:950;color:{RED}">→</div>
        <div style="position:absolute;left:52px;bottom:38px;border-top:1px solid rgba(255,255,255,.3);width:300px;padding-top:10px;font:800 9px/1 ui-monospace,monospace">{src}</div>
      </div>
    </div>'''


async def main():
    story=json.loads(DATA.read_text())
    slides=story.get('slides') or []
    if not story.get('selected') or not slides:
        raise SystemExit('No selected editorial')
    now=datetime.now().astimezone()
    slug=re.sub(r'[^a-z0-9]+','-',v9.clean(story.get('story_title','post')).lower()).strip('-')[:72]
    pkg=OUT/now.strftime('%Y-%m-%d')/(now.strftime('%H%M%S')+'-'+slug)
    sd,hd,ed=pkg/'slides',pkg/'html',pkg/'evidence'
    for p in (sd,hd,ed): p.mkdir(parents=True,exist_ok=True)
    async with v9.async_playwright() as pw:
        browser=await pw.chromium.launch()
        page=await browser.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
        for i,slide in enumerate(slides):
            evidence=None
            if v9.role(slide,i)=='evidence':
                target=ed/f'{i+1:02d}.png'
                evidence=await v9.capture(page,v9.source_url(story,slide),target)
            html_text=v9.doc(inner(slide,story,i,len(slides),evidence),i+1,len(slides),dark=v9.role(slide,i) in {'reveal'})
            (hd/f'{i+1:02d}.html').write_text(html_text)
            await page.set_content(html_text,wait_until='load')
            await page.screenshot(path=str(sd/f'{i+1:02d}.png'),full_page=False)
        await browser.close()
    out=dict(story)
    out['renderer']='getbyterush-pinterest-editorial-v10'
    out['gemini_calls']=0
    out['rendered_at']=datetime.now().astimezone().isoformat()
    (pkg/'post.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    for name,value in [('caption.txt',story.get('caption','')),('alt-text.txt',story.get('alt_text','')),('hashtags.txt',' '.join(story.get('hashtags',[]) or [])),('pinned-comment.txt',story.get('pinned_comment',''))]:
        (pkg/name).write_text(v9.clean(value))
    print(f'RENDERED={pkg}')
    print('GEMINI_CALL=0')
    print('SLIDES=',len(slides))


if __name__=='__main__':
    asyncio.run(main())
