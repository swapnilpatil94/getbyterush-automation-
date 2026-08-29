#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
import carousel_art_renderer_v12 as v12
import carousel_art_renderer_v9 as v9

W,H=v12.W,v12.H
DATA,OUT=v12.DATA,v12.OUT

# Keep renderer-internal vocabulary out of visible production copy.
# This is a presentation-layer normalization only; editorial JSON remains unchanged.
FORBIDDEN_VISIBLE = {
    'INPUT': 'CONTEXT',
    'PROCESS': 'FLOW',
    'OUTCOME': 'PAYOFF',
}

def sanitize_visible(html):
    for src, dst in FORBIDDEN_VISIBLE.items():
        html = re.sub(rf'(?<![A-Za-z]){src}(?![A-Za-z])', dst, html, flags=re.I)
    return html

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
            inner=v12.inner(slide,story,i,len(slides),evidence)
            html_text=sanitize_visible(v9.doc(inner,i+1,len(slides),dark=v9.role(slide,i) in {'reveal'}))
            (hd/f'{i+1:02d}.html').write_text(html_text)
            await page.set_content(html_text,wait_until='load')
            await page.screenshot(path=str(sd/f'{i+1:02d}.png'),full_page=False)
        await browser.close()
    out=dict(story)
    out['renderer']='getbyterush-pinterest-editorial-v13'
    out['gemini_calls']=0
    out['rendered_at']=datetime.now().astimezone().isoformat()
    (pkg/'post.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(main())
