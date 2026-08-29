#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
import carousel_art_renderer_v10 as v10
import carousel_art_renderer_v9 as v9

W,H=v10.W,v10.H
DATA,OUT=v10.DATA,v10.OUT

def deco(role, i):
    # Restrained art-direction layer: make the canvas feel authored, not UI-generated.
    common='''<div style="position:absolute;inset:0;pointer-events:none;overflow:hidden">
      <div style="position:absolute;left:34px;top:34px;width:16px;height:16px;border-left:2px solid rgba(9,11,10,.55);border-top:2px solid rgba(9,11,10,.55)"></div>
      <div style="position:absolute;right:34px;top:34px;width:16px;height:16px;border-right:2px solid rgba(9,11,10,.55);border-top:2px solid rgba(9,11,10,.55)"></div>
      <div style="position:absolute;left:34px;bottom:34px;width:16px;height:16px;border-left:2px solid rgba(9,11,10,.55);border-bottom:2px solid rgba(9,11,10,.55)"></div>
      <div style="position:absolute;right:34px;bottom:34px;width:16px;height:16px;border-right:2px solid rgba(9,11,10,.55);border-bottom:2px solid rgba(9,11,10,.55)"></div>
    </div>'''
    if role=='open':
        return common+'''<div style="position:absolute;right:82px;top:315px;width:86px;height:86px;border:1px solid rgba(198,24,24,.55);border-radius:50%;pointer-events:none"></div>
        <div style="position:absolute;right:105px;top:348px;width:40px;height:1px;background:#c61818;transform:rotate(-45deg);pointer-events:none"></div>'''
    if role=='evidence':
        return common+'''<div style="position:absolute;left:38px;top:384px;width:9px;height:58px;background:#c61818;pointer-events:none"></div>
        <div style="position:absolute;right:52px;top:382px;width:9px;height:58px;background:#0b4a3d;pointer-events:none"></div>'''
    if role=='reveal':
        return '''<div style="position:absolute;right:42px;top:52px;font:900 9px/1 ui-monospace,monospace;letter-spacing:2px;color:rgba(245,239,224,.52);pointer-events:none">FIELD NOTE / %02d</div>'''%(i+1)
    if role=='interrupt':
        return '''<div style="position:absolute;right:52px;bottom:48px;display:flex;gap:8px;pointer-events:none">%s</div>'''%(''.join('<i style="display:block;width:8px;height:8px;background:#0b0d0c;opacity:.75"></i>' for _ in range(9)))
    if role=='architecture':
        return common+'''<div style="position:absolute;right:52px;top:445px;font:900 9px/1 ui-monospace,monospace;letter-spacing:1.5px;writing-mode:vertical-rl;transform:rotate(180deg);opacity:.45">FLOW / CONTEXT → MEMORY → ACTION</div>'''
    return common+'''<div style="position:absolute;right:76px;top:350px;width:112px;height:1px;background:rgba(245,239,224,.32);pointer-events:none"></div>
    <div style="position:absolute;right:76px;top:343px;width:8px;height:8px;background:#c61818;pointer-events:none"></div>'''

def inner(slide, story, i, total, evidence):
    base=v10.inner(slide,story,i,total,evidence)
    return base+deco(v9.role(slide,i),i)

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
    out['renderer']='getbyterush-pinterest-editorial-v11'
    out['gemini_calls']=0
    out['rendered_at']=datetime.now().astimezone().isoformat()
    (pkg/'post.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(main())
