#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
import carousel_art_renderer_v11 as v11
import carousel_art_renderer_v9 as v9

W,H=v11.W,v11.H
DATA,OUT=v11.DATA,v11.OUT

# Renderer-internal labels must never leak into published artwork.
RENDERER_LABELS = {
    'INPUT': 'CONTEXT',
    'PROCESS': 'FLOW',
    'OUTCOME': 'PAYOFF',
}

def sanitize_renderer_labels(html):
    for src, dst in RENDERER_LABELS.items():
        html = re.sub(rf'\\b{src}\\b', dst, html, flags=re.I)
    return html

def inner(slide, story, i, total, evidence):
    html=v11.inner(slide,story,i,total,evidence)
    if v9.role(slide,i)=='evidence' and not evidence:
        html=html.replace('PRIMARY SOURCE','SOURCE STATUS')
        html=html.replace('NVIDIA<br>RESEARCH','SOURCE CAPTURE<br>UNAVAILABLE')
        html=html.replace('SOURCE URL IN EDITORIAL','SOURCE URL / SEE POST METADATA')
    return sanitize_renderer_labels(html)

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
    out['renderer']='getbyterush-pinterest-editorial-v12'
    out['gemini_calls']=0
    out['rendered_at']=datetime.now().astimezone().isoformat()
    (pkg/'post.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(main())
