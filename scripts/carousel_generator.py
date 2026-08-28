#!/usr/bin/env python3
"""GetByteRush deterministic Instagram carousel renderer.

Renderer only: consumes saved editorial JSON. Never calls Gemini.
Design authority: design/getbyterush-carousel-design-system.md
Canvas: 1080x1350.
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
WIDTH, HEIGHT = 1080, 1350
RETENTION_DAYS = 7

BRAND = {"cream":"#F4EFE4", "forest":"#12352B", "ink":"#111311", "gold":"#B99A5B"}
THEMES = {
    "brand": {"bg":"#F4EFE4","fg":"#111311","accent":"#12352B","signal":"#B99A5B","surface":"#E9E2D5"},
    "urgency": {"bg":"#111311","fg":"#F4EFE4","accent":"#E53935","signal":"#E53935","surface":"#1D201D"},
    "experiment": {"bg":"#F4EFE4","fg":"#12352B","accent":"#2D8C7A","signal":"#2D8C7A","surface":"#E3ECE7"},
    "money": {"bg":"#F4EFE4","fg":"#111311","accent":"#12352B","signal":"#B99A5B","surface":"#E9E0CC"},
    "explainer": {"bg":"#F4EFE4","fg":"#111311","accent":"#12352B","signal":"#3F6FA3","surface":"#E3E8EF"},
    "contradiction": {"bg":"#F4EFE4","fg":"#111311","accent":"#F26A21","signal":"#F26A21","surface":"#EFE1D7"},
    "investigation": {"bg":"#EFE8D8","fg":"#12352B","accent":"#426A78","signal":"#C83C3C","surface":"#E2DBCC"},
    "timeline": {"bg":"#F4EFE4","fg":"#12352B","accent":"#3159C9","signal":"#3159C9","surface":"#E5E8EF"},
    "comparison": {"bg":"#F4EFE4","fg":"#111311","accent":"#12352B","signal":"#B99A5B","surface":"#E5E8E6"},
    "mystery": {"bg":"#0D0F0E","fg":"#F4EFE4","accent":"#C7F000","signal":"#C7F000","surface":"#1A1D1A"},
    "data": {"bg":"#F4EFE4","fg":"#12352B","accent":"#C9A75D","signal":"#C9A75D","surface":"#E6E9E8"},
}
TEMPLATE_THEME = {"story":"brand","experiment":"experiment","shock-number":"money","breakdown":"explainer","contradiction":"contradiction","receipts":"investigation","timeline":"timeline","comparison":"comparison","wtf":"mystery","data-story":"data"}
CATEGORY_TEMPLATE = {"breaking_news":"story","daily_24_hours":"story","model_drop":"story","model_comparison":"comparison","experiment":"experiment","product_story":"breakdown","business_story":"story","ai_agent_story":"breakdown","internet_mystery":"wtf","deep_dive":"story","explainer":"breakdown","tool_discovery":"breakdown","data_story":"data-story","timeline":"timeline","TECH_NEWS":"story","MODEL_UPDATE":"story","AI_AGENTS":"breakdown","BUSINESS":"story"}


def text(v):
    if isinstance(v, list): return " ".join(str(x) for x in v).strip()
    return str(v or "").strip()


def esc(v): return html.escape(text(v), quote=True)


def first(*values):
    for v in values:
        if text(v): return v
    return ""


def clean(v, n=None):
    s = re.sub(r"\s+", " ", text(v)).strip()
    return s if not n else s[:n].rstrip()


def slug(v):
    return (re.sub(r"[^a-z0-9]+", "-", text(v).lower()).strip("-")[:80] or "getbyterush-post")


def template_for(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    explicit = clean(first(story.get("template"), design.get("template"))).lower()
    if explicit in TEMPLATE_THEME: return explicit
    for s in story.get("slides", []):
        v = clean(first(s.get("visual_type"), s.get("layout"))).lower()
        if v in {"metric","comparison","timeline","evidence","screenshot","diagram"}:
            return {"metric":"shock-number","comparison":"comparison","timeline":"timeline","evidence":"receipts","screenshot":"receipts","diagram":"breakdown"}[v]
    return CATEGORY_TEMPLATE.get(clean(first(story.get("content_type"),story.get("story_type"),story.get("category"),story.get("type"))), "story")


def theme_for(story, template):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    mode = clean(first(story.get("emotional_mode"), design.get("emotional_mode"))).lower()
    aliases = {"urgent":"urgency","breaking":"urgency","emergency":"urgency","money/scale":"money","money":"money","explainer":"explainer","experiment":"experiment","contradiction":"contradiction","investigation":"investigation","receipts":"investigation","timeline":"timeline","comparison":"comparison","mystery":"mystery","wtf":"mystery","data":"data"}
    name = aliases.get(mode, TEMPLATE_THEME.get(template, "brand"))
    if story.get("emergency_mode") is True: name = "urgency"
    return name if name in THEMES else "brand"


def role(slide, i, total):
    r = clean(first(slide.get("role"), slide.get("scene_role"))).lower()
    if r: return r
    if i == 1: return "interrupt"
    if i == 2: return "open_loop"
    if i == total: return "payoff"
    if i == total - 1: return "reveal"
    if i == 5: return "pattern_interrupt"
    return "proof"


def headline(slide): return first(slide.get("headline"),slide.get("title"),slide.get("hook"),slide.get("text"),"GetByteRush")
def body(slide): return first(slide.get("body"),slide.get("supporting_text"),slide.get("copy"),slide.get("description"))
def concept(slide): return first(slide.get("visual_concept"),slide.get("visual_strategy"),slide.get("visual_asset"),slide.get("visual"))


def source_info(story, slide):
    ss = story.get("source_story") if isinstance(story.get("source_story"),dict) else {}
    return clean(first(slide.get("source_label"),slide.get("source"),ss.get("source"),ss.get("publisher"),story.get("source"),"Official source")), clean(first(slide.get("asset_url"),slide.get("source_url"),ss.get("url"),story.get("source_url")))


def evidence(story, out):
    _, url = source_info(story, {})
    if not url: return None
    try:
        p = Path(out).resolve(); p.parent.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
            page = b.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1)
            page.goto(url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_timeout(1800)
            for sel in ['[aria-label*="cookie" i]','[id*="cookie" i]','[class*="cookie" i]','[aria-label*="consent" i]','[id*="consent" i]','[class*="consent" i]']:
                try: page.locator(sel).first.evaluate("el=>el.remove()")
                except Exception: pass
            page.screenshot(path=str(p),full_page=False)
            b.close()
        return p if p.exists() else None
    except Exception as e:
        print(f"WARNING: evidence capture failed: {e}"); return None


def css(t):
    return f'''@page{{size:{WIDTH}px {HEIGHT}px;margin:0}}*{{box-sizing:border-box}}html,body{{margin:0;padding:0;width:{WIDTH}px;height:{HEIGHT}px;overflow:hidden}}body{{font-family:Inter,Arial,Helvetica,sans-serif;background:{t["bg"]};color:{t["fg"]}}}.slide{{position:relative;width:{WIDTH}px;height:{HEIGHT}px;padding:76px 78px 72px;background:{t["bg"]};color:{t["fg"]};overflow:hidden}}.slide.dark{{background:#111311;color:#F4EFE4}}.grain{{position:absolute;inset:0;opacity:.025;pointer-events:none;background-image:radial-gradient(currentColor .55px,transparent .7px);background-size:7px 7px}}.meta{{position:absolute;top:38px;left:78px;right:78px;display:flex;justify-content:space-between;font:800 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.5px;text-transform:uppercase;opacity:.62}}.page{{color:{t["signal"]}}}.rule{{width:86px;height:5px;background:{t["accent"]};margin-top:28px;margin-bottom:22px}}.kicker{{display:inline-block;max-width:700px;padding:8px 11px;border:1px solid {t["accent"]};color:{t["accent"]};font:900 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px;text-transform:uppercase}}h1{{position:relative;z-index:2;max-width:900px;margin:18px 0 0;font-size:72px;line-height:.93;letter-spacing:-3.5px;font-weight:900;overflow-wrap:anywhere}}h1.tight{{font-size:60px;line-height:.95}}h1.hero{{font-size:118px;line-height:.82;letter-spacing:-7px;max-width:920px}}.body{{position:relative;z-index:2;max-width:760px;margin-top:22px;font-size:25px;line-height:1.18;font-weight:550;overflow-wrap:anywhere}}.footer{{position:absolute;left:78px;right:78px;bottom:40px;display:flex;justify-content:space-between;align-items:flex-end;gap:25px;font:700 11px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;opacity:.6}}.footer .source{{max-width:670px;overflow-wrap:anywhere}}.brand{{white-space:nowrap;letter-spacing:1.5px}}.hook-rail{{position:absolute;left:78px;top:575px;right:78px;border-top:1px solid {t["accent"]};padding-top:18px;font:800 15px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;color:{t["accent"]};letter-spacing:1px;text-transform:uppercase}}.metric{{position:absolute;left:78px;right:78px;top:540px;display:flex;flex-direction:column;align-items:flex-start}}.metric-value{{font-size:235px;line-height:.7;font-weight:950;letter-spacing:-14px;color:{t["accent"]}}}.metric-label{{margin-top:45px;max-width:800px;font-size:31px;line-height:1.02;font-weight:900}}.evidence{{position:absolute;left:78px;right:78px;top:345px;height:690px;border:2px solid {t["accent"]};background:#171917;box-shadow:16px 16px 0 {t["accent"]};padding:13px;overflow:hidden}}.evidence img{{display:block;width:100%;height:100%;object-fit:contain;background:white}}.evbar{{position:absolute;left:78px;top:304px;padding:8px 10px;background:{t["accent"]};color:{t["bg"]};font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px}}.compare{{position:absolute;left:78px;right:78px;top:555px;display:grid;grid-template-columns:1fr 74px 1fr;gap:15px;align-items:center}}.compare-card{{min-height:300px;padding:28px;background:{t["surface"]};border:2px solid {t["accent"]};display:flex;flex-direction:column;justify-content:space-between}}.compare-label{{font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:{t["signal"]}}.compare-name{{font-size:42px;line-height:.95;font-weight:950;letter-spacing:-2px;overflow-wrap:anywhere}}.vs{{font:950 22px/1 ui-monospace,SFMono-Regular,Menlo,monospace;text-align:center;color:{t["accent"]}}.diagram{{position:absolute;left:78px;right:78px;top:565px;display:grid;grid-template-columns:1fr 50px 1fr 50px 1fr;gap:8px;align-items:center}}.node{{min-height:230px;padding:24px;background:{t["surface"]};border:2px solid {t["accent"]}}.node-label{{font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:{t["signal"]}}.node-value{{margin-top:18px;font-size:26px;line-height:1;font-weight:900;overflow-wrap:anywhere}}.arrow{{font-size:30px;text-align:center;color:{t["accent"]};font-weight:900}}.timeline{{position:absolute;left:95px;right:78px;top:540px;border-left:5px solid {t["accent"]};padding-left:35px}}.timeline-item{{position:relative;margin-bottom:27px}}.timeline-item:before{{content:"";position:absolute;left:-47px;top:0;width:12px;height:12px;border:4px solid {t["accent"]};background:{t["bg"]}}}.date{{font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:{t["signal"]};letter-spacing:1px;text-transform:uppercase}}.timeline-copy{{margin-top:7px;font-size:28px;line-height:1.02;font-weight:850;max-width:800px;overflow-wrap:anywhere}}.quote{{position:absolute;left:78px;right:78px;top:565px;padding:28px 32px;border-left:8px solid {t["accent"]};background:{t["surface"]};font-size:46px;line-height:1;letter-spacing:-2px;font-weight:900;overflow-wrap:anywhere}}.pattern{{position:absolute;inset:500px 0 0;background:{t["accent"]};color:{t["bg"]};padding:50px 78px}}.pattern .big{{font-size:88px;line-height:.84;letter-spacing:-5px;font-weight:950;max-width:900px;overflow-wrap:anywhere}}.payoff{{position:absolute;left:78px;right:78px;top:555px;border-top:7px solid {t["accent"]};padding-top:25px;font-size:54px;line-height:.92;letter-spacing:-2.5px;font-weight:950;overflow-wrap:anywhere}}.payoff-small{{position:absolute;left:78px;right:78px;top:900px;max-width:760px;font-size:23px;line-height:1.2;opacity:.75}}.dark .compare-card,.dark .node,.dark .quote{{background:#1A1D1A}}'''


def visual(slide, story, template, tname, t, uri, i, total):
    vt=clean(first(slide.get("visual_type"),slide.get("layout"))).lower(); r=role(slide,i,total); h=clean(headline(slide),180); b=clean(body(slide),320); c=clean(concept(slide),220); source,_=source_info(story,slide)
    if i==1 and vt not in {"metric","screenshot","evidence"}:
        q=clean(first(slide.get("transition_hint"),"SWIPE TO SEE WHAT CHANGED"),80)
        return f'<div class="hook-rail">{esc(q)}</div>'
    if vt=="metric" or template=="shock-number":
        vals=re.findall(r"(?<![A-Za-z])(?:\$?\d+(?:[,.]\d+)?(?:%|x|×|B|M|K)?)(?![A-Za-z])", " ".join([h,b,c]))
        return f'<div class="metric"><div class="metric-value">{esc(vals[0] if vals else first(c,"01"))}</div><div class="metric-label">{esc(first(b,c,h))}</div></div>'
    if vt in {"screenshot","evidence"} or template=="receipts":
        if uri:
            host=urlparse(source_info(story,slide)[1]).netloc or "OFFICIAL SOURCE"
            return f'<div class="evbar">OFFICIAL SOURCE · {esc(host)}</div><div class="evidence"><img src="{esc(uri)}" alt="Official source evidence" /></div>'
        return f'<div class="quote">SOURCE EVIDENCE UNAVAILABLE<br><span style="font-size:20px">{esc(source)}</span></div>'
    if vt=="comparison" or template=="comparison":
        parts=re.split(r"\s+vs\.?\s+|\s+versus\s+",c or h,flags=re.I); a=clean(parts[0] if parts else h,90); z=clean(parts[1] if len(parts)>1 else "Alternative",90)
        return f'<div class="compare"><div class="compare-card"><div class="compare-label">A / PRIMARY</div><div class="compare-name">{esc(a)}</div><div class="compare-label">THE CURRENT PATH</div></div><div class="vs">VS</div><div class="compare-card"><div class="compare-label">B / ALTERNATIVE</div><div class="compare-name">{esc(z)}</div><div class="compare-label">THE NEW PATH</div></div></div>'
    if vt=="timeline" or template=="timeline":
        ev=slide.get("timeline") or slide.get("events") or []
        if not isinstance(ev,list) or not ev: ev=[{"date":"BEFORE","text":first(b,h)},{"date":"NOW","text":first(c,h)}]
        items=[]
        for e in ev[:4]:
            if isinstance(e,dict): d=first(e.get("date"),e.get("year"),"STEP"); v=first(e.get("text"),e.get("headline"),e.get("description"))
            else: d="STEP"; v=e
            items.append(f'<div class="timeline-item"><div class="date">{esc(d)}</div><div class="timeline-copy">{esc(v)}</div></div>')
        return '<div class="timeline">'+''.join(items)+'</div>'
    if vt=="diagram" or template=="breakdown":
        vals=[first(slide.get("input"),h),first(slide.get("system"),c,"THE SYSTEM"),first(slide.get("output"),b,"THE IMPACT")]
        ns=[]
        for lab,val in zip(("INPUT","SYSTEM","OUTPUT"),vals): ns.append(f'<div class="node"><div class="node-label">{lab}</div><div class="node-value">{esc(clean(val,120))}</div></div>')
        return '<div class="diagram">'+ '<div class="arrow">→</div>'.join(ns) + '</div>'
    if vt=="quote" or template=="contradiction": return f'<div class="quote">{esc(first(b,c,h))}</div>'
    if vt in {"pattern_interrupt","pattern"} or r=="pattern_interrupt": return f'<div class="pattern"><div class="big">{esc(first(c,h,"WAIT."))}</div></div>'
    if r in {"reveal","payoff"} or i==total:
        return f'<div class="payoff">{esc(first(b,slide.get("payoff"),slide.get("implication"),c,h))}</div><div class="payoff-small">{esc(first(slide.get("implication"),c))}</div>'
    # Editorial default: one strong visual statement, not fake cards or filler numbers.
    return f'<div class="quote">{esc(first(c,b,h))}</div>'


def slide_html(story, slide, i, total, template, tname, t, uri):
    h=clean(headline(slide),160); b=clean(body(slide),360); r=role(slide,i,total); dark=clean(first(slide.get("background"),slide.get("background_mode"))).lower() in {"black","dark","ink","blackout"} or r=="pattern_interrupt" or tname=="mystery"
    hc="hero" if i==1 and len(h)<60 else "tight" if len(h)>82 else ""
    source,_=source_info(story,slide)
    visual_html=visual(slide,story,template,tname,t,uri,i,total)
    # Body is shown only when the chosen visual does not already carry the copy.
    vt=clean(first(slide.get("visual_type"),slide.get("layout"))).lower()
    body_html=f'<div class="body">{esc(b)}</div>' if b and vt not in {"metric","comparison","timeline","diagram","quote","screenshot","evidence"} and i not in {total} else ""
    cls="slide dark" if dark else "slide"
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{css(t)}</style></head><body><section class="{cls}"><div class="grain"></div><div class="meta"><span>GETBYTERUSH / {esc(template.replace("-"," ").upper())}</span><span class="page">{i:02d} / {total:02d}</span></div><div class="rule"></div><div class="kicker">{esc(first(slide.get("kicker"),slide.get("label"),story.get("series"),"TECH • AI • INTERNET"))}</div><h1 class="{hc}">{esc(h)}</h1>{body_html}{visual_html}<div class="footer"><div class="source">SOURCE / {esc(source)}</div><div class="brand">TESTED • EXPLAINED • REAL</div></div></section></body></html>'''


def render_html(story,out_dir,template,tname,t,ev):
    hd=out_dir/"html"; hd.mkdir(parents=True,exist_ok=True); uri=Path(ev).resolve().as_uri() if ev and Path(ev).exists() else None
    total=len(story.get("slides",[]))
    for i,s in enumerate(story.get("slides",[]),1): (hd/f"{i:02d}.html").write_text(slide_html(story,s,i,total,template,tname,t,uri),encoding="utf-8")


def render_pngs(out_dir,count):
    root=Path(out_dir).resolve(); hd=root/"html"; sd=root/"slides"; sd.mkdir(parents=True,exist_ok=True); failures=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        for i in range(1,count+1):
            hp=hd/f"{i:02d}.html"; pp=sd/f"{i:02d}.png"
            page=b.new_page(viewport={"width":WIDTH,"height":HEIGHT},device_scale_factor=1)
            page.goto(hp.resolve().as_uri(),wait_until="load")
            # Hard geometry QA: nothing may escape the 1080x1350 canvas or the bottom footer zone.
            bad=page.evaluate('''() => { const W=1080,H=1350; const sels=['h1','.body','.kicker','.hook-rail','.metric','.evidence','.compare','.diagram','.timeline','.quote','.pattern','.payoff','.payoff-small','.footer']; const out=[]; for(const sel of sels){for(const el of document.querySelectorAll(sel)){const r=el.getBoundingClientRect(); if(r.left < -1 || r.top < -1 || r.right > W+1 || r.bottom > H+1) out.push(sel+':'+Math.round(r.left)+','+Math.round(r.top)+','+Math.round(r.right)+','+Math.round(r.bottom));}} return out;}''')
            if bad: failures.append({"slide":i,"overflow":bad})
            page.screenshot(path=str(pp),full_page=False); page.close(); print(f"✓ slide-{i:02d}.png")
        b.close()
    if failures: raise RuntimeError("Carousel layout validation failed: "+json.dumps(failures,ensure_ascii=False))
    print("✓ Production layout validation passed")


def metadata(story,out,created):
    delete=(created+timedelta(days=RETENTION_DAYS)).isoformat()
    payload=dict(story); payload.update({"status":"pending_approval","created_at":created.isoformat(timespec="seconds"),"retention_days":RETENTION_DAYS,"delete_after":delete,"rendering":{"renderer":"getbyterush-carousel-generator-v7","template":template_for(story),"theme":theme_for(story,template_for(story)),"canvas":"1080x1350","production_ready":True},"instagram":{"published":False,"media_id":None,"permalink":None}})
    (out/"post.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    vals={"caption.txt":story.get("caption",""),"hashtags.txt":" ".join(map(str,story.get("hashtags",[]))) if isinstance(story.get("hashtags"),list) else story.get("hashtags","") ,"pinned-comment.txt":story.get("pinned_comment",""),"alt-text.txt":story.get("alt_text","")}
    for name,val in vals.items(): (out/name).write_text(text(val),encoding="utf-8")


def main():
    if not INPUT.exists(): raise FileNotFoundError(f"Missing {INPUT}. Run editorial_engine.py first.")
    story=json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"): print("No story selected. Nothing to render."); return
    slides=story.get("slides") or []
    if not slides: raise ValueError("Selected story contains no carousel slides.")
    title=story.get("story_title","GetByteRush Post"); created=datetime.now().astimezone(); out=OUTPUT_ROOT/created.strftime("%Y-%m-%d")/f"{created.strftime('%H%M%S')}-{slug(title)}"; out.mkdir(parents=True,exist_ok=False)
    for d in ("slides","html","evidence"): (out/d).mkdir(parents=True,exist_ok=True)
    template=template_for(story); tname=theme_for(story,template); t=dict(THEMES[tname]); design=story.get("design") if isinstance(story.get("design"),dict) else {}; requested=clean(first(story.get("accent_color"),design.get("accent_color"))); t["accent"]=requested if re.fullmatch(r"#[0-9a-fA-F]{6}",requested) else t["accent"]
    ev=evidence(story,out/"evidence"/"source.png")
    print("="*72); print("GETBYTERUSH CAROUSEL V7"); print("Template:",template); print("Theme:",tname); print("Accent:",t["accent"]); print("Slides:",len(slides)); print("Evidence:",bool(ev)); print("Gemini: 0"); print("="*72)
    render_html(story,out,template,tname,t,ev); render_pngs(out,len(slides)); metadata(story,out,created); print("OUTPUT:",out); print("PRODUCTION_READY: true")

if __name__=="__main__": main()
