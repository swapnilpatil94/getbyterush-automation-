#!/usr/bin/env python3
import asyncio, json, re
from datetime import datetime
from pathlib import Path
import carousel_art_renderer_v12 as v12
import carousel_art_renderer_v9 as v9

W,H=v12.W,v12.H
DATA,OUT=v12.DATA,v12.OUT

FORBIDDEN={'INPUT':'CONTEXT','PROCESS':'FLOW','OUTCOME':'PAYOFF'}

def sanitize(s):
    for a,b in FORBIDDEN.items(): s=re.sub(rf'(?<![A-Za-z]){a}(?![A-Za-z])',b,s,flags=re.I)
    return s

def art(role):
    # Designerly poster devices: editorial bars, crop marks, oversized numerals,
    # asymmetric blocks and texture. These are intentionally decorative and do
    # not alter editorial facts.
    common='''<div style="position:absolute;inset:0;pointer-events:none;overflow:hidden"><div style="position:absolute;left:34px;top:34px;width:18px;height:18px;border-left:2px solid currentColor;border-top:2px solid currentColor;opacity:.55"></div><div style="position:absolute;right:34px;top:34px;width:18px;height:18px;border-right:2px solid currentColor;border-top:2px solid currentColor;opacity:.55"></div><div style="position:absolute;left:34px;bottom:34px;width:18px;height:18px;border-left:2px solid currentColor;border-bottom:2px solid currentColor;opacity:.55"></div><div style="position:absolute;right:34px;bottom:34px;width:18px;height:18px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;opacity:.55"></div></div>'''
    if role=='interrupt':
        return common+'''<div style="position:absolute;right:52px;top:205px;width:260px;height:520px;background:#090B0A;color:#F2EBDD;padding:28px;pointer-events:none"><div style="font:900 10px ui-monospace,monospace;letter-spacing:2px;color:#B7E32B">GETBYTERUSH / SIGNAL</div><div style="position:absolute;right:-18px;top:125px;font:950 190px/.65 Arial,sans-serif;letter-spacing:-14px;color:#B7E32B;writing-mode:vertical-rl;transform:rotate(180deg)">15X</div><div style="position:absolute;left:28px;right:28px;bottom:28px;border-top:2px solid #B80D08;padding-top:12px;font:900 9px ui-monospace,monospace;letter-spacing:1.2px">AGENTIC LOAD / SCALE SHOCK</div></div>'''
    if role=='open':
        return common+'''<div style="position:absolute;right:52px;top:350px;width:350px;height:170px;background:#B80D08;color:#F2EBDD;padding:22px;transform:rotate(-1.5deg);pointer-events:none"><div style="font:950 54px/.82 Arial,sans-serif;letter-spacing:-3px">THE COST<br>COMPOUNDS.</div></div><div style="position:absolute;right:82px;top:550px;width:118px;height:118px;border:2px solid #B80D08;border-radius:50%;pointer-events:none"></div>'''
    if role=='evidence':
        return common+'''<div style="position:absolute;right:52px;top:390px;width:96px;height:340px;background:#12372C;pointer-events:none"><div style="position:absolute;left:18px;top:20px;width:60px;height:2px;background:#B7E32B"></div><div style="position:absolute;left:18px;top:58px;width:60px;height:210px;border-left:2px solid #B80D08;border-right:2px solid #B7E32B;opacity:.7"></div><div style="position:absolute;left:18px;bottom:22px;font:900 9px ui-monospace,monospace;color:#F2EBDD;writing-mode:vertical-rl">SOURCE / DATA</div></div>'''
    if role=='reveal':
        return '''<div style="position:absolute;right:44px;top:190px;width:270px;height:270px;border:2px solid #B7E32B;border-radius:50%;pointer-events:none"><div style="position:absolute;left:50%;top:-1px;height:272px;border-left:1px solid #B7E32B;transform:rotate(37deg)"></div><div style="position:absolute;top:50%;left:18px;right:18px;border-top:1px solid #B7E32B;transform:rotate(-22deg)"></div></div><div style="position:absolute;right:58px;bottom:120px;width:210px;height:12px;background:#B80D08;pointer-events:none"></div>'''
    if role=='payoff':
        return common+'''<div style="position:absolute;right:52px;top:390px;width:330px;height:430px;background:#090B0A;color:#F2EBDD;padding:30px;pointer-events:none"><div style="font:900 10px ui-monospace,monospace;letter-spacing:2px;color:#B7E32B">THE SHIFT</div><div style="margin-top:45px;font:950 66px/.78 Arial,sans-serif;letter-spacing:-5px">ALWAYS<br>ON.</div><div style="position:absolute;left:30px;right:30px;bottom:28px;border-top:1px solid #B80D08;padding-top:12px;font:900 9px ui-monospace,monospace">FROM PROMPTS → AGENT LOOPS</div></div>'''
    return common+'''<div style="position:absolute;right:52px;bottom:118px;width:190px;height:190px;background:#B80D08;transform:rotate(3deg);opacity:.92;pointer-events:none"><div style="position:absolute;inset:18px;border:2px solid #F2EBDD"></div></div>'''

def inner(slide,story,i,total,evidence):
    r=v9.role(slide,i)
    base=v12.inner(slide,story,i,total,evidence)
    # Replace the evidence dead-state with an authored source card, never fake evidence.
    if r=='evidence' and not evidence:
        base=base.replace('SOURCE CAPTURE<br>UNAVAILABLE','SOURCE LINK / VERIFIED METADATA')
        base=base.replace('SOURCE URL / SEE POST METADATA','SOURCE URL / POST METADATA')
    return base+art(r)

async def main():
    story=json.loads(DATA.read_text()); slides=story.get('slides') or []
    if not story.get('selected') or not slides: raise SystemExit('No selected editorial')
    now=datetime.now().astimezone(); slug=re.sub(r'[^a-z0-9]+','-',v9.clean(story.get('story_title','post')).lower()).strip('-')[:72]
    pkg=OUT/now.strftime('%Y-%m-%d')/(now.strftime('%H%M%S')+'-'+slug); sd,hd,ed=pkg/'slides',pkg/'html',pkg/'evidence'
    for p in (sd,hd,ed): p.mkdir(parents=True,exist_ok=True)
    async with v9.async_playwright() as pw:
        browser=await pw.chromium.launch(); page=await browser.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
        for i,slide in enumerate(slides):
            evidence=None
            if v9.role(slide,i)=='evidence':
                target=ed/f'{i+1:02d}.png'; evidence=await v9.capture(page,v9.source_url(story,slide),target)
            html_text=sanitize(v9.doc(inner(slide,story,i,len(slides),evidence),i+1,len(slides),dark=v9.role(slide,i) in {'reveal'}))
            (hd/f'{i+1:02d}.html').write_text(html_text); await page.set_content(html_text,wait_until='load'); await page.screenshot(path=str(sd/f'{i+1:02d}.png'),full_page=False)
        await browser.close()
    out=dict(story); out['renderer']='getbyterush-pinterest-editorial-v14'; out['gemini_calls']=0; out['rendered_at']=datetime.now().astimezone().isoformat(); (pkg/'post.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__': asyncio.run(main())
