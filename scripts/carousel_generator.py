#!/usr/bin/env python3
"""GetByteRush production carousel renderer.

Deterministic renderer for saved editorial JSON.
- 1080x1350 / 4:5
- story-specific theme selection
- slide-level visual routing
- no invented source claims
- preserved evidence aspect ratio
- safe-zone layout
- dated output package
"""

import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")
WIDTH, HEIGHT, SAFE = 1080, 1350, 78
RETENTION_DAYS = 7

THEMES = {
    "story": {"bg":"#F4EFE4","fg":"#111311","accent":"#12352B","signal":"#B99A5B","surface":"#EAE3D5"},
    "urgency": {"bg":"#111311","fg":"#F4EFE4","accent":"#E53935","signal":"#E53935","surface":"#1D1F1D"},
    "experiment": {"bg":"#F4EFE4","fg":"#12352B","accent":"#2D8C7A","signal":"#BFDCCF","surface":"#E4EEE9"},
    "money": {"bg":"#111311","fg":"#F4EFE4","accent":"#B7E32B","signal":"#B99A5B","surface":"#20231D"},
    "explainer": {"bg":"#F4EFE4","fg":"#12352B","accent":"#527A91","signal":"#D7D9D5","surface":"#E5E9E8"},
    "contradiction": {"bg":"#F4EFE4","fg":"#111311","accent":"#F26A21","signal":"#111311","surface":"#EFE1D7"},
    "investigation": {"bg":"#EFE8D8","fg":"#12352B","accent":"#426A78","signal":"#C83C3C","surface":"#E2DBCC"},
    "timeline": {"bg":"#F4EFE4","fg":"#12352B","accent":"#3159C9","signal":"#B99A5B","surface":"#E5E8EF"},
    "comparison": {"bg":"#F4EFE4","fg":"#111311","accent":"#12352B","signal":"#4B78A8","surface":"#E5E8E6"},
    "mystery": {"bg":"#0D0F0E","fg":"#F4EFE4","accent":"#C7F000","signal":"#7457FF","surface":"#1A1D1A"},
    "data": {"bg":"#F4EFE4","fg":"#12352B","accent":"#C9A75D","signal":"#4B78A8","surface":"#E6E9E8"},
}

TEMPLATE_THEME = {"story":"story","experiment":"experiment","shock-number":"money","breakdown":"explainer","contradiction":"contradiction","receipts":"investigation","timeline":"timeline","comparison":"comparison","wtf":"mystery","data-story":"data"}
CATEGORY_TEMPLATE = {"breaking_news":"story","daily_24_hours":"story","model_drop":"story","model_comparison":"comparison","experiment":"experiment","product_story":"breakdown","business_story":"story","ai_agent_story":"breakdown","internet_mystery":"wtf","deep_dive":"story","explainer":"breakdown","tool_discovery":"breakdown","data_story":"data-story","timeline":"timeline","what_happens_next":"story","failure_story":"contradiction","TECH_NEWS":"story","MODEL_UPDATE":"story","AI_AGENTS":"breakdown","BUSINESS":"story"}

BASE_CSS = r'''
@page{size:1080px 1350px;margin:0}*{box-sizing:border-box}html,body{width:1080px;height:1350px;margin:0;padding:0;overflow:hidden}body{font-family:"Inter Tight",Inter,Arial,Helvetica,sans-serif}.slide{position:relative;width:1080px;height:1350px;padding:78px;overflow:hidden;background:var(--bg);color:var(--fg)}.meta{position:absolute;top:40px;left:78px;right:78px;display:flex;justify-content:space-between;align-items:center;font:800 16px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.25px;text-transform:uppercase}.meta .right{color:var(--accent)}.rule{width:92px;height:4px;background:var(--accent);margin:44px 0 24px}.kicker{display:inline-block;max-width:760px;padding:9px 12px 8px;border:1.5px solid var(--accent);color:var(--accent);font:900 16px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.35px;text-transform:uppercase}.headline{max-width:900px;margin:18px 0 0;font-size:78px;line-height:.94;letter-spacing:-3.1px;font-weight:900;overflow-wrap:anywhere}.headline.tight{font-size:64px;letter-spacing:-2.3px;line-height:.97}.headline.long{font-size:54px;letter-spacing:-1.7px;line-height:1.02}.body{max-width:820px;margin-top:26px;font-size:29px;line-height:1.14;font-weight:550;overflow-wrap:anywhere}.footer{position:absolute;left:78px;right:78px;bottom:44px;display:flex;justify-content:space-between;align-items:flex-end;gap:24px}.source{max-width:620px;font:700 13px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;opacity:.68;overflow-wrap:anywhere}.brand{font-size:14px;font-weight:900;letter-spacing:1.6px;white-space:nowrap;text-transform:uppercase}.eyebrow{margin-top:36px;font:900 15px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);letter-spacing:1.1px;text-transform:uppercase}.pair{margin-top:48px;display:grid;grid-template-columns:1fr 58px 1fr;gap:14px;align-items:stretch}.pair-card{min-height:205px;padding:26px;background:var(--surface);border:2px solid var(--accent)}.pair-card.primary{border-top-width:8px}.pair-label{font:900 15px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px;text-transform:uppercase;opacity:.68}.pair-title{margin-top:20px;font-size:34px;line-height:.95;font-weight:900;letter-spacing:-1.2px;overflow-wrap:anywhere}.pair-copy{margin-top:15px;font-size:20px;line-height:1.04;font-weight:700;overflow-wrap:anywhere}.vs{display:flex;justify-content:center;align-items:center;color:var(--accent);font:950 28px/1 ui-monospace,SFMono-Regular,Menlo,monospace}.metric-grid{margin-top:52px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.metric-card{min-height:315px;padding:26px;background:var(--surface);border-top:7px solid var(--accent);display:flex;flex-direction:column;justify-content:space-between}.metric-value{color:var(--accent);font-size:82px;line-height:.82;letter-spacing:-5px;font-weight:950;overflow-wrap:anywhere}.metric-label{font-size:23px;line-height:1.0;font-weight:900}.metric-note{font:700 12px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;opacity:.62;text-transform:uppercase}.evidence-frame{position:absolute;left:78px;right:78px;top:300px;bottom:150px;padding:16px;border:2px solid var(--accent);background:#161816;overflow:hidden}.evidence-chrome{height:42px;display:flex;justify-content:space-between;align-items:center;padding:0 4px;color:#F4EFE4;font:800 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;letter-spacing:.9px}.evidence-window{width:100%;height:calc(100% - 42px);display:flex;justify-content:center;align-items:center;background:#fff;overflow:hidden}.evidence-window img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;display:block}.quote-wrap{margin-top:52px;max-width:900px;padding:32px 36px;border-left:7px solid var(--accent);background:var(--surface)}.quote-mark{color:var(--accent);font:950 88px/.55 Georgia,serif}.quote{margin-top:10px;font-size:46px;line-height:1.02;letter-spacing:-1.8px;font-weight:900;overflow-wrap:anywhere}.quote-source{margin-top:22px;font:800 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;opacity:.7;text-transform:uppercase}.breakdown{margin-top:52px;display:grid;grid-template-columns:1fr 44px 1fr 44px 1fr;gap:8px;align-items:center}.node{min-height:190px;padding:22px;background:var(--surface);border:2px solid var(--accent);display:flex;flex-direction:column;justify-content:center}.node .label{font:900 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px;text-transform:uppercase;opacity:.66}.node .value{margin-top:13px;font-size:25px;line-height:1;font-weight:900;overflow-wrap:anywhere}.arrow{text-align:center;font-size:34px;font-weight:950;color:var(--accent)}.timeline{margin-top:54px;padding-left:38px;border-left:5px solid var(--accent)}.timeline-item{position:relative;margin-bottom:28px}.timeline-item:before{content:"";position:absolute;left:-51px;top:0;width:16px;height:16px;border:5px solid var(--accent);background:var(--bg)}.timeline-date{color:var(--accent);font:900 15px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px;text-transform:uppercase}.timeline-text{margin-top:7px;font-size:30px;line-height:1.03;font-weight:850;overflow-wrap:anywhere}.compare-grid{margin-top:52px;display:grid;grid-template-columns:1fr 1fr;gap:18px}.compare-card{min-height:310px;padding:28px;background:var(--surface);border:2px solid var(--accent)}.compare-card.winner{border-top-width:8px}.compare-name{font-size:40px;line-height:.94;letter-spacing:-1.5px;font-weight:950;overflow-wrap:anywhere}.compare-row{margin-top:22px;padding-top:15px;border-top:1px solid var(--accent);display:flex;justify-content:space-between;gap:16px;font-size:18px;line-height:1.05;font-weight:800}.pattern{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:100px 78px;background:var(--bg)}.pattern:before{content:"";position:absolute;width:660px;height:660px;border:2px solid var(--accent);transform:rotate(45deg);opacity:.26}.pattern .big{position:relative;max-width:900px;font-size:128px;line-height:.79;letter-spacing:-7px;text-align:center;font-weight:950;text-transform:uppercase;overflow-wrap:anywhere}.payoff{margin-top:52px;max-width:900px;border-top:6px solid var(--accent);padding-top:28px;font-size:48px;line-height:.98;letter-spacing:-2px;font-weight:900;overflow-wrap:anywhere}.payoff-small{margin-top:25px;max-width:790px;font-size:25px;line-height:1.08;font-weight:650;overflow-wrap:anywhere}.grain{position:absolute;inset:0;opacity:.018;pointer-events:none;background-image:radial-gradient(#000 .7px,transparent .8px);background-size:5px 5px}.dark .grain{opacity:.045;background-image:radial-gradient(#fff .7px,transparent .8px)}
'''


def text(v):
    if isinstance(v, list): return " ".join(str(x) for x in v)
    return str(v or "").strip()

def esc(v): return html.escape(text(v))
def first(*vals):
    for v in vals:
        if text(v): return v
    return ""
def slug(v): return (re.sub(r"[^a-z0-9]+","-",text(v).lower()).strip("-")[:80] or "getbyterush-post")

def infer_template(story):
    design=story.get("design") if isinstance(story.get("design"),dict) else {}
    t=text(first(story.get("template"),design.get("template"))).lower()
    if t in TEMPLATE_THEME:return t
    return CATEGORY_TEMPLATE.get(text(first(story.get("format"),story.get("content_type"),story.get("story_type"),story.get("category"),story.get("type"))),"story")

def infer_theme(story,template):
    design=story.get("design") if isinstance(story.get("design"),dict) else {}
    mode=text(first(story.get("emotional_mode"),design.get("emotional_mode"))).lower()
    aliases={"urgent":"urgency","breaking":"urgency","money/scale":"money","money":"money","explainer":"explainer","experiment":"experiment","contradiction":"contradiction","investigation":"investigation","timeline":"timeline","comparison":"comparison","mystery":"mystery","wtf":"mystery","data":"data"}
    return "urgency" if story.get("emergency_mode") is True else aliases.get(mode,TEMPLATE_THEME.get(template,"story"))

def theme_config(story,theme_name):
    theme=dict(THEMES[theme_name]); d=story.get("design") if isinstance(story.get("design"),dict) else {}
    accent=text(d.get("accent_color")).upper()
    if accent in {x.upper() for x in sum([list(v.values()) for v in THEMES.values()],[])}: theme["accent"]=accent
    return theme

def background_mode(slide,theme_name):
    requested=text(first(slide.get("background_mode"),slide.get("background"))).lower()
    if requested in {"black","ink","dark","blackout"}:return True
    if requested in {"cream","light","white"}:return False
    return theme_name in {"urgency","money","mystery"}

def source_info(story,slide):
    ss=story.get("source_story") if isinstance(story.get("source_story"),dict) else {}
    return text(first(slide.get("source_label"),ss.get("source"),story.get("source"),"Official source")), text(first(slide.get("asset_url"),slide.get("source_url"),ss.get("url"),story.get("source_url")))

def visual_type(slide,index,total):
    v=text(first(slide.get("visual_type"),slide.get("layout"),slide.get("renderer"))).lower()
    if v:return v
    return "hook" if index==1 else "final" if index==total else "story"

def headline_class(h):
    n=len(text(h)); return "headline long" if n>105 else "headline tight" if n>68 else "headline"

def number_values(slide):
    raw=" ".join(text(slide.get(k)) for k in ("headline","body","visual_concept"))
    vals=re.findall(r"(?<![A-Za-z])(?:[+\-]?\$?\d+(?:\.\d+)?(?:%|x|×)?)(?![A-Za-z])",raw)
    return list(dict.fromkeys(vals))[:3]

def visual_markup(story,slide,index,total,template,theme_name,theme,evidence_uri):
    h=text(first(slide.get("headline"),slide.get("title"),slide.get("hook"))); b=text(first(slide.get("body"),slide.get("supporting_text"),slide.get("copy"))); c=text(first(slide.get("visual_concept"),slide.get("visual_strategy"),slide.get("asset_requirement"))); vt=visual_type(slide,index,total); source,url=source_info(story,slide); role=text(first(slide.get("role"),slide.get("scene_role"))).lower()
    if index==1 or vt=="hook":
        ss=story.get("source_story") if isinstance(story.get("source_story"),dict) else {}
        return f'<div class="eyebrow">{esc(first(slide.get("transition_hint"),"THE QUESTION"))}</div><div class="pair"><div class="pair-card primary"><div class="pair-label">SOURCE</div><div class="pair-title">{esc(first(ss.get("source"),"SOURCE"))}</div><div class="pair-copy">The development.</div></div><div class="vs">×</div><div class="pair-card"><div class="pair-label">ANGLE</div><div class="pair-title">{esc(first(slide.get("hook_type"),"THE SHIFT"))}</div><div class="pair-copy">The reason to keep swiping.</div></div></div>'
    if vt=="metric":
        vals=number_values(slide) or ["01"]; labels=["KEY SIGNAL","WHAT CHANGED","WHY IT MATTERS"]; return '<div class="metric-grid">'+"".join(f'<div class="metric-card"><div class="metric-value">{esc(v)}</div><div class="metric-label">{labels[i]}</div><div class="metric-note">{esc(source)}</div></div>' for i,v in enumerate(vals))+'</div>'
    if vt in {"screenshot","evidence"} or template=="receipts":
        if evidence_uri:
            host=urlparse(url).netloc or "SOURCE"
            return f'<div class="evidence-frame"><div class="evidence-chrome"><span>OFFICIAL SOURCE</span><span>{esc(host)}</span></div><div class="evidence-window"><img src="{esc(evidence_uri)}" alt="Official source evidence" /></div></div>'
        return f'<div class="quote-wrap"><div class="quote-mark">“</div><div class="quote">{esc(first(b,c,h))}</div><div class="quote-source">{esc(source)}</div></div>'
    if vt=="comparison":
        raw=first(c,h); parts=re.split(r"\s+vs\.?\s+|\s+versus\s+",raw,flags=re.I); left,right=(parts[0],parts[1]) if len(parts)>1 else (raw,"Alternative"); return f'<div class="compare-grid"><div class="compare-card winner"><div class="pair-label">A</div><div class="compare-name">{esc(left)}</div><div class="compare-row"><span>POSITION</span><span>PRIMARY</span></div><div class="compare-row"><span>USE</span><span>SOURCE DATA</span></div></div><div class="compare-card"><div class="pair-label">B</div><div class="compare-name">{esc(right)}</div><div class="compare-row"><span>POSITION</span><span>ALTERNATIVE</span></div><div class="compare-row"><span>USE</span><span>SOURCE DATA</span></div></div></div>'
    if vt=="timeline":
        events=slide.get("timeline") or slide.get("events") or []
        if isinstance(events,list) and events:
            out=[]
            for e in events[:5]:
                if isinstance(e,dict): d=first(e.get("date"),e.get("year"),"STEP"); v=first(e.get("text"),e.get("headline"),e.get("description"))
                else:d,v="STEP",e
                out.append(f'<div class="timeline-item"><div class="timeline-date">{esc(d)}</div><div class="timeline-text">{esc(v)}</div></div>')
            return '<div class="timeline">'+"".join(out)+'</div>'
        return f'<div class="timeline"><div class="timeline-item"><div class="timeline-date">BEFORE</div><div class="timeline-text">{esc(b or h)}</div></div><div class="timeline-item"><div class="timeline-date">NOW</div><div class="timeline-text">{esc(c or h)}</div></div></div>'
    if vt=="diagram":
        vals=[first(slide.get("input"),h),first(c,slide.get("system")),first(b,slide.get("output"))]; nodes=[]
        for label,val in zip(("INPUT","SYSTEM","OUTPUT"),vals): nodes.append(f'<div class="node"><div class="label">{label}</div><div class="value">{esc(val)}</div></div>')
        return '<div class="breakdown">'+ '<div class="arrow">→</div>'.join(nodes) + '</div>'
    if vt=="quote": return f'<div class="quote-wrap"><div class="quote-mark">“</div><div class="quote">{esc(first(b,h,c))}</div><div class="quote-source">{esc(source)}</div></div>'
    if vt in {"pattern_interrupt","pattern"} or role=="pattern_interrupt": return f'<div class="pattern"><div class="big">{esc(first(h,c,"WAIT."))}</div></div>'
    if vt=="final" or index==total: return f'<div class="payoff">{esc(first(h,b,c))}</div><div class="payoff-small">{esc(first(slide.get("implication"),b))}</div>'
    return f'<div class="breakdown"><div class="node"><div class="label">CONTEXT</div><div class="value">{esc(h)}</div></div><div class="arrow">→</div><div class="node"><div class="label">CHANGE</div><div class="value">{esc(c or b)}</div></div><div class="arrow">→</div><div class="node"><div class="label">IMPACT</div><div class="value">{esc(first(slide.get("implication"),b))}</div></div></div>'

def slide_html(story,slide,index,total,template,theme_name,theme,evidence_uri):
    h=text(first(slide.get("headline"),slide.get("title"),slide.get("hook"))); b=text(first(slide.get("body"),slide.get("supporting_text"),slide.get("copy"))); k=text(first(slide.get("kicker"),slide.get("label"),"GETBYTERUSH")); dark=background_mode(slide,theme_name); bg="#111311" if dark else theme["bg"]; fg="#F4EFE4" if dark else theme["fg"]; style=BASE_CSS+f'\n:root{{--bg:{bg};--fg:{fg};--accent:{theme["accent"]};--signal:{theme["signal"]};--surface:{theme["surface"]};}}'; body_html=f'<div class="body">{esc(b)}</div>' if b and index==1 else ""; visual=visual_markup(story,slide,index,total,template,theme_name,theme,evidence_uri); source,_=source_info(story,slide)
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{style}</style></head><body><section class="slide{ " dark" if dark else ""}"><div class="grain"></div><div class="meta"><span>GETBYTERUSH / {esc(template.replace("-"," "))}</span><span class="right">{index:02d} / {total:02d}</span></div><div class="rule"></div><div class="kicker">{esc(k)}</div><h1 class="{headline_class(h)}">{esc(h)}</h1>{body_html}{visual}<div class="footer"><div class="source">SOURCE / {esc(source)}</div><div class="brand">TESTED • EXPLAINED • REAL</div></div></section></body></html>'

def capture_evidence(url,out):
    if not url:return False
    try:
        out=Path(out).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"]); page=browser.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1); page.goto(url,wait_until="domcontentloaded",timeout=30000); page.wait_for_timeout(1600); page.screenshot(path=str(out),full_page=False); browser.close()
        return out.exists()
    except Exception as exc:
        print(f"WARNING: evidence capture failed: {exc}"); return False

def render_html(story,out_dir,template,theme_name,theme,evidence_path):
    hd=out_dir/"html"; hd.mkdir(parents=True,exist_ok=True); uri=Path(evidence_path).resolve().as_uri() if evidence_path and Path(evidence_path).exists() else None
    total=len(story["slides"])
    for i,s in enumerate(story["slides"],1): (hd/f"{i:02d}.html").write_text(slide_html(story,s,i,total,template,theme_name,theme,uri),encoding="utf-8")

def render_pngs_validate(out_dir,count):
    hd=Path(out_dir).resolve()/"html"; sd=Path(out_dir).resolve()/"slides"; sd.mkdir(parents=True,exist_ok=True); failures=[]
    selector=".meta,.kicker,h1,.body,.pair,.metric-grid,.evidence-frame,.quote-wrap,.breakdown,.timeline,.compare-grid,.pattern,.payoff,.payoff-small,.footer"
    text_sel="h1,.body,.pair-title,.pair-copy,.metric-label,.metric-value,.quote,.node .value,.timeline-text,.compare-name,.payoff,.payoff-small,.pattern .big"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"]); page=browser.new_page(viewport={"width":WIDTH,"height":HEIGHT},device_scale_factor=1)
        for i in range(1,count+1):
            hp=hd/f"{i:02d}.html"; png=sd/f"{i:02d}.png"; page.goto(hp.as_uri(),wait_until="load"); page.wait_for_timeout(80)
            result=page.evaluate("""({selector,textSel})=>{const W=1080,H=1350;const geometry=[],overflow=[];for(const el of document.querySelectorAll(selector)){if(el.classList.contains('grain'))continue;const r=el.getBoundingClientRect();if(r.left<0||r.top<0||r.right>W||r.bottom>H)geometry.push({cls:String(el.className),b:[r.left,r.top,r.right,r.bottom]})}for(const el of document.querySelectorAll(textSel)){if(el.scrollWidth>el.clientWidth+4)overflow.push({cls:String(el.className),t:(el.innerText||'').slice(0,100),c:el.clientWidth,s:el.scrollWidth})}return {geometry,overflow,canvas:[document.querySelector('.slide')?.getBoundingClientRect().width,document.querySelector('.slide')?.getBoundingClientRect().height]}}""",{"selector":selector,"textSel":text_sel})
            if result["geometry"] or result["overflow"]: failures.append({"slide":i,"details":result})
            page.screenshot(path=str(png),full_page=False); print(f"✓ slide-{i:02d}.png")
        browser.close()
    if failures: raise RuntimeError("Carousel layout validation failed: "+json.dumps(failures,ensure_ascii=False))
    print("✓ Production layout validation passed")

def main():
    if not INPUT.exists(): raise FileNotFoundError(f"Missing {INPUT}")
    story=json.loads(INPUT.read_text(encoding="utf-8"));
    if not story.get("selected"): return
    slides=story.get("slides") or []
    if not 5<=len(slides)<=9: raise ValueError(f"Carousel must contain 5–9 slides, got {len(slides)}")
    for i,s in enumerate(slides,1):
        h=text(first(s.get("headline"),s.get("title"),s.get("hook"))); b=text(first(s.get("body"),s.get("supporting_text"),s.get("copy")))
        if not h: raise ValueError(f"slide {i}: missing headline")
        if len(h)>140: raise ValueError(f"slide {i}: headline too long")
        if len(b)>450: raise ValueError(f"slide {i}: body too long")
    template=infer_template(story); theme_name=infer_theme(story,template); theme=theme_config(story,theme_name); created=datetime.now().astimezone(); ts=created.isoformat(timespec="seconds"); out=OUTPUT_ROOT/created.strftime("%Y-%m-%d")/f"{created.strftime('%H%M%S')}-{slug(story.get('story_title','getbyterush-post'))}"; out.mkdir(parents=True,exist_ok=False)
    for sub in ("slides","html","evidence"): (out/sub).mkdir(parents=True,exist_ok=True)
    ss=story.get("source_story") if isinstance(story.get("source_story"),dict) else {}; evidence=out/"evidence"/"source.png"; evidence=evidence if capture_evidence(text(ss.get("url")),evidence) else None
    print("="*72); print("GETBYTERUSH CAROUSEL V6"); print("Template :",template); print("Theme    :",theme_name); print("Accent   :",theme["accent"]); print("Slides   :",len(slides)); print("Evidence :",bool(evidence))
    render_html(story,out,template,theme_name,theme,evidence); render_pngs_validate(out,len(slides))
    payload=dict(story); payload.update({"status":"pending_approval","created_at":ts,"retention_days":RETENTION_DAYS,"delete_after":(created+timedelta(days=RETENTION_DAYS)).isoformat(),"rendering":{"renderer":"getbyterush-carousel-generator-v6","template":template,"theme":theme_name,"canvas":"1080x1350","production_ready":True},"instagram":{"published":False,"media_id":None,"permalink":None}}); (out/"post.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    for name,val in [("caption.txt",story.get("caption")),("hashtags.txt"," ".join(map(str,story.get("hashtags",[]))) if isinstance(story.get("hashtags"),list) else story.get("hashtags")),("pinned-comment.txt",story.get("pinned_comment")),("alt-text.txt",story.get("alt_text"))]: (out/name).write_text(text(val),encoding="utf-8")
    print("OUTPUT:",out); print("PRODUCTION_READY: true")

if __name__=="__main__": main()
