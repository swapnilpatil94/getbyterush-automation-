#!/usr/bin/env python3
import html,json,re
from datetime import datetime,timedelta
from pathlib import Path
from string import Template
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

W,H=1080,1350
INPUT=Path("data/selected_story.json")
ROOT=Path("output/posts")
RETENTION=7
CREAM="#F4EFE4";INK="#111311";FOREST="#12352B";GOLD="#B99A5B";BLUE="#3159C9";ORANGE="#F26A21";LIME="#B7E43B"
THEMES={
 "authority":{"bg":CREAM,"fg":INK,"accent":FOREST,"signal":GOLD,"mode":"authority"},
 "technology":{"bg":CREAM,"fg":INK,"accent":FOREST,"signal":BLUE,"mode":"clarity"},
 "tension":{"bg":CREAM,"fg":INK,"accent":ORANGE,"signal":ORANGE,"mode":"tension"},
 "interrupt":{"bg":INK,"fg":CREAM,"accent":LIME,"signal":LIME,"mode":"novelty"},
}
LEAK=re.compile(r"(callout graphic|visual concept|visual direction|visual strategy|design direction|layout instruction|highlight that|data graphic showing|contrast visual between|illustrate that|graphic showing|render this|create a)",re.I)
def tx(v):
    return " ".join(map(str,v)) if isinstance(v,list) else str(v or "").strip()
def cl(v): return re.sub(r"\s+"," ",tx(v)).strip()
def esc(v): return html.escape(cl(v),quote=True)
def first(*vs):
    return next((v for v in vs if cl(v)),"")
def slug(v): return re.sub(r"[^a-z0-9]+","-",cl(v).lower()).strip("-")[:90] or "getbyterush-post"
def punch(v,n=9,c=78):
    s=cl(v)
    if not s:return "GetByteRush"
    if len(s)<=c and len(re.findall(r"\b[\w’'-]+\b",s))<=n:return s
    p=re.split(r"(?<=[.!?])\s+",s)[0]
    if len(p)<=c and len(re.findall(r"\b[\w’'-]+\b",p))<=n:return p.rstrip(" .")
    out=" ".join(re.findall(r"\b[\w’'-]+\b",s)[:n])[:c]
    return out.rsplit(" ",1)[0].rstrip(" ,.;:")+"…"
def support(v,c=150):
    s=cl(v)
    if not s or LEAK.search(s):return ""
    return s if len(s)<=c else s[:c].rsplit(" ",1)[0].rstrip(" ,.;:")+"…"
def category(story): return cl(first(story.get("content_type"),story.get("story_type"),story.get("category"),story.get("type"))).upper()
def theme_for(story):
    d=story.get("design") if isinstance(story.get("design"),dict) else {}
    raw=cl(first(story.get("emotional_mode"),d.get("emotional_mode"))).lower()
    if story.get("emergency_mode") is True:return "interrupt"
    if raw in {"contradiction","tension"}:return "tension"
    if category(story) in {"TECH_NEWS","MODEL_UPDATE","AI_AGENTS","EXPLAINER"}:return "technology"
    return "authority"
def role(s,i,total):
    x=cl(first(s.get("role"),s.get("scene_role"))).lower()
    return x or ("interrupt" if i==1 else "payoff" if i==total else "pattern_interrupt" if i==3 else "reveal" if i==total-1 else "proof")
def content(s):
    h=punch(first(s.get("headline"),s.get("title"),s.get("hook"),s.get("text")),10,78)
    b=support(first(s.get("body"),s.get("supporting_text"),s.get("copy"),s.get("description")),170)
    v=cl(first(s.get("visual_type"),s.get("layout"))).lower()
    c=cl(first(s.get("visual_concept"),s.get("visual_strategy"),s.get("visual")))
    return h,b,v,c
def metric(s):
    raw=" ".join(cl(s.get(k)) for k in ("headline","body","visual_concept"))
    m=re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)?",raw,re.I)
    return m[0] if m else "01"
def source(story,s):
    ss=story.get("source_story") if isinstance(story.get("source_story"),dict) else {}
    return cl(first(s.get("source_label"),s.get("source"),ss.get("source"),ss.get("publisher"),story.get("source"),"Official source"))[:90],cl(first(s.get("asset_url"),s.get("source_url"),ss.get("url"),story.get("source_url")))
def capture(url,dest):
    if not url or not urlparse(url).scheme:return None
    dest=Path(dest).resolve();dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as pw:
            b=pw.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
            p=b.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1)
            p.goto(url,wait_until="domcontentloaded",timeout=30000);p.wait_for_timeout(900);p.screenshot(path=str(dest),full_page=False);b.close()
        return dest if dest.exists() else None
    except Exception as e:
        print("WARNING: evidence capture failed:",e);return None

def css(t):
    return Template("""
@page{size:1080px 1350px;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;width:1080px;height:1350px;overflow:hidden}body{background:$bg;color:$fg;font-family:Inter,Arial,sans-serif}
.slide{position:relative;width:1080px;height:1350px;padding:76px 78px 72px;background:var(--bg);color:var(--fg);overflow:hidden}.slide.dark{background:#111311;color:#F4EFE4}:root{--bg:$bg;--fg:$fg;--accent:$accent;--signal:$signal}
.grain{position:absolute;inset:0;opacity:.018;background-image:radial-gradient(currentColor .55px,transparent .7px);background-size:8px 8px}.top,.footer{position:absolute;left:78px;right:78px;display:flex;justify-content:space-between;gap:20px;font:800 10px/1.2 ui-monospace,monospace;letter-spacing:1.5px;text-transform:uppercase;opacity:.55}.top{top:38px}.footer{bottom:34px}.footer span:first-child{max-width:680px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.page{padding:5px 8px;border:1px solid currentColor}
.kicker{display:inline-block;color:var(--accent);border-left:4px solid var(--signal);padding:8px 11px;font:900 11px/1 ui-monospace,monospace;letter-spacing:1.6px;text-transform:uppercase}.rule{width:110px;height:6px;background:var(--signal);margin-top:24px}.hero{position:absolute;left:78px;right:78px;top:178px}.hero h1{margin:24px 0 0;max-width:910px;font-size:92px;line-height:.85;letter-spacing:-5px;font-weight:950;overflow-wrap:anywhere}.hero p{margin:24px 0 0;max-width:710px;font-size:25px;line-height:1.2;opacity:.74}.index{position:absolute;right:0;top:100px;font:950 170px/.8 ui-monospace,monospace;letter-spacing:-14px;color:var(--accent);opacity:.08}
.evidence{position:absolute;left:78px;right:78px;top:545px}.evidence-frame{height:560px;border:2px solid var(--fg);background:#fff;box-shadow:16px 16px 0 var(--accent);padding:12px;overflow:hidden}.evidence-frame img{width:100%;height:100%;display:block;object-fit:contain;background:#fff}.tag{position:absolute;left:18px;top:18px;background:var(--accent);color:var(--bg);padding:8px 10px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1px}.note{margin-top:16px;font:800 10px/1.3 ui-monospace,monospace;text-transform:uppercase;opacity:.55}
.statement{position:absolute;left:78px;right:78px;top:500px}.statement strong{display:block;max-width:900px;font-size:82px;line-height:.86;letter-spacing:-4.5px;font-weight:950}.statement p{margin-top:24px;max-width:700px;font-size:24px;line-height:1.2;opacity:.72}
.metric{position:absolute;left:78px;right:78px;top:500px}.metric .value{font:950 260px/.7 ui-monospace,monospace;letter-spacing:-18px;color:var(--accent)}.metric .line{width:180px;height:7px;margin-top:42px;background:var(--signal)}.metric .caption{margin-top:20px;max-width:800px;font-size:30px;line-height:1;font-weight:900;letter-spacing:-1px}
.flow{position:absolute;left:78px;right:78px;top:540px;display:grid;grid-template-columns:1fr 42px 1fr 42px 1fr;gap:10px;align-items:center}.node{min-height:230px;padding:24px;border-top:5px solid var(--accent);background:color-mix(in srgb,var(--accent) 7%,transparent)}.node small{display:block;color:var(--accent);font:900 10px/1 ui-monospace,monospace}.node b{display:block;margin-top:24px;font-size:32px;line-height:.98;font-weight:950}.arrow{text-align:center;color:var(--signal);font-size:30px;font-weight:950}
.compare{position:absolute;left:78px;right:78px;top:525px;display:grid;grid-template-columns:1fr 70px 1fr;gap:16px;align-items:center}.card{min-height:300px;padding:28px;border:2px solid var(--fg);background:color-mix(in srgb,var(--accent) 7%,transparent)}.card:last-child{border:4px solid var(--accent);transform:translateY(-12px);box-shadow:12px 12px 0 var(--signal)}.card small{color:var(--accent);font:900 10px/1 ui-monospace,monospace;text-transform:uppercase}.card strong{display:block;margin-top:70px;font-size:40px;line-height:.94;letter-spacing:-2px;font-weight:950}.vs{text-align:center;color:var(--accent);font:950 16px/1 ui-monospace,monospace}
.pattern{position:absolute;left:0;right:0;top:420px;bottom:0;padding:72px 78px;background:var(--accent);color:var(--bg)}.pattern small{font:900 11px/1 ui-monospace,monospace;letter-spacing:2px;text-transform:uppercase}.pattern strong{display:block;margin-top:30px;max-width:850px;font-size:88px;line-height:.84;letter-spacing:-5px;font-weight:950}
.reveal{position:absolute;left:78px;right:78px;top:510px;display:grid;grid-template-columns:90px 1fr;gap:24px}.reveal .num{color:var(--accent);font:950 72px/.8 ui-monospace,monospace}.reveal strong{display:block;max-width:850px;font-size:55px;line-height:.92;letter-spacing:-3px;font-weight:950}.reveal p{margin-top:20px;max-width:730px;font-size:24px;line-height:1.2;opacity:.74}
.payoff{position:absolute;left:78px;right:78px;top:470px}.payoff .line{width:190px;height:7px;background:var(--signal);margin-bottom:28px}.payoff strong{display:block;max-width:900px;font-size:82px;line-height:.84;letter-spacing:-4.5px;font-weight:950}.payoff p{margin-top:24px;max-width:720px;font-size:25px;line-height:1.18;opacity:.74}.sig{margin-top:30px;color:var(--accent);font:900 11px/1 ui-monospace,monospace;letter-spacing:2px}
""").substitute(bg=t["bg"],fg=t["fg"],accent=t["accent"],signal=t["signal"])
def labels(s):
    h,b,v,c=content(s);q=(h+" "+b+" "+c).lower()
    if "cpu" in q and "gpu" in q:return ["GPU","CPU","AGENT"]
    if "agent" in q:return ["PROMPT","TOOL","ACTION"]
    return ["INPUT","PROCESS","OUTCOME"]
def markup(s,story,t,evi,i,total):
    h,b,v,c=content(s);r=role(s,i,total);src,_=source(story,s);ev=Path(evi).resolve().as_uri() if evi else ""
    if r=="interrupt" or i==1:return f'<div class="hero"><span class="kicker">GETBYTERUSH / {esc(category(story) or "TECH • AI • INTERNET")}</span><div class="rule"></div><h1>{esc(h)}</h1><p>{esc(b)}</p><span class="index">{i:02d}</span></div>'
    if r=="pattern_interrupt":return f'<div class="pattern"><small>03 / PATTERN INTERRUPT</small><strong>{esc(punch(first(h,b),7,58))}</strong></div>'
    if v in {"metric","number","stat"} or re.search(r"\b\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB)\b",h,re.I):return f'<div class="hero"><span class="kicker">THE SIGNAL</span><h1 style="font-size:68px">{esc(h)}</h1></div><div class="metric"><div class="value">{esc(metric(s))}</div><div class="line"></div><div class="caption">{esc(b or h)}</div></div>'
    if v in {"comparison","versus","compare"}:return f'<div class="hero"><span class="kicker">THE SHIFT</span><h1 style="font-size:70px">{esc(h)}</h1></div><div class="compare"><div class="card"><small>BEFORE</small><strong>GPU-FIRST</strong></div><div class="vs">VS</div><div class="card"><small>NOW</small><strong>HYBRID AI</strong></div></div>'
    if v in {"diagram","flow","process","architecture"} or any(x in c.lower() for x in ("diagram","flow","architecture")):
        ls=labels(s);nodes="".join(f'<div class="node"><small>{j+1:02d}</small><b>{esc(x)}</b></div>'+('<div class="arrow">→</div>' if j<2 else "") for j,x in enumerate(ls))
        return f'<div class="hero"><span class="kicker">HOW IT WORKS</span><h1 style="font-size:70px">{esc(h)}</h1></div><div class="flow">{nodes}</div>'
    if v in {"evidence","screenshot","receipt"} and ev:return f'<div class="hero"><span class="kicker">SOURCE / PROOF</span><h1 style="font-size:70px">{esc(h)}</h1></div><div class="evidence"><div class="evidence-frame"><span class="tag">VERIFIED SOURCE</span><img src="{esc(ev)}" alt="Source evidence"></div><div class="note">{esc(src)} · source capture</div></div>'
    if r=="reveal":return f'<div class="hero"><span class="kicker">THE REVEAL</span><h1 style="font-size:70px">{esc(h)}</h1></div><div class="reveal"><div class="num">{i:02d}</div><div><strong>{esc(punch(first(b,h),10,86))}</strong><p>{esc(b)}</p></div></div>'
    if r=="payoff" or i==total:return f'<div class="hero"><span class="kicker">THE TAKEAWAY</span></div><div class="payoff"><div class="line"></div><strong>{esc(punch(h,9,80))}</strong><p>{esc(b)}</p><div class="sig">GETBYTERUSH / TESTED • EXPLAINED • REAL</div></div>'
    return f'<div class="hero"><span class="kicker">{esc(r.replace("_"," "))}</span><h1 style="font-size:70px">{esc(h)}</h1></div><div class="statement"><strong>{esc(punch(first(b,h),7,62))}</strong><p>{esc(support(b,120))}</p></div>'
def render_html(story,out,t,evi):
    hd=out/"html";hd.mkdir(parents=True,exist_ok=True);sheet=css(t);total=len(story["slides"])
    for i,s in enumerate(story["slides"],1):
        dark="dark" if role(s,i,total)=="pattern_interrupt" else "";src,_=source(story,s)
        page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=1080, initial-scale=1"><style>{sheet}</style></head><body><main class="slide {dark}"><div class="grain"></div><div class="top"><span>GETBYTERUSH</span><span>TECH • AI • INTERNET</span><span class="page">{i:02d} / {total:02d}</span></div>{markup(s,story,t,evi,i,total)}<div class="footer"><span>{esc(src)}</span><span>TESTED • EXPLAINED • REAL</span></div></main></body></html>'''
        (hd/f"{i:02d}.html").write_text(page,encoding="utf-8")
def render_pngs(out,count):
    hd=out/"html";sd=out/"slides";sd.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        for i in range(1,count+1):
            p=b.new_page(viewport={"width":W,"height":H},device_scale_factor=1);p.goto((hd/f"{i:02d}.html").resolve().as_uri(),wait_until="load");p.screenshot(path=str(sd/f"{i:02d}.png"),full_page=False)
            box=p.locator(".slide").bounding_box()
            if not box or round(box["width"])!=W or round(box["height"])!=H:raise RuntimeError(f"Slide {i:02d} geometry invalid")
            if LEAK.search(p.locator("body").inner_text()):raise RuntimeError(f"Slide {i:02d} contains internal design text")
            p.close();print(f"✓ slide-{i:02d}.png")
        b.close()
def metadata(story,out,created,tn,t):
    (out/"caption.txt").write_text(cl(story.get("caption")),encoding="utf-8");hs=story.get("hashtags",[]);(out/"hashtags.txt").write_text(" ".join(map(str,hs)) if isinstance(hs,list) else cl(hs),encoding="utf-8")
    (out/"pinned-comment.txt").write_text(cl(story.get("pinned_comment")),encoding="utf-8");(out/"alt-text.txt").write_text(cl(story.get("alt_text")),encoding="utf-8")
    delete=(datetime.fromisoformat(created)+timedelta(days=RETENTION)).isoformat();p=dict(story);d=dict(story.get("design") or {})
    d.update({"renderer":"getbyterush-carousel-generator-v4-art-directed","emotional_mode":d.get("emotional_mode") or tn,"accent_color":t["accent"],"composition":"art-directed editorial engines","psychology":{"color_mode":t["mode"],"retention_strategy":"interrupt → curiosity → proof → pattern → payoff","copy_rule":"punchy minimal; design metadata never rendered"}})
    p.update({"design":d,"post_id":f"{slug(story.get('story_title'))}-{created.replace(':','').replace('+','-')}","status":"pending_approval","created_at":created,"retention_days":RETENTION,"delete_after":delete,"package":{"slides_dir":"slides","html_dir":"html","evidence_dir":"evidence","slide_count":len(story["slides"]),"theme":tn}})
    (out/"post.json").write_text(json.dumps(p,indent=2,ensure_ascii=False),encoding="utf-8")
def main():
    if not INPUT.exists():raise FileNotFoundError(f"Missing {INPUT}")
    story=json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"):print("No story selected. Nothing to render.");return
    if not story.get("slides"):raise ValueError("Selected story contains no carousel slides.")
    now=datetime.now().astimezone();created=now.isoformat(timespec="seconds");out=ROOT/now.strftime("%Y-%m-%d")/f"{now.strftime('%H%M%S')}-{slug(story.get('story_title','getbyterush-post'))}"
    for x in ("slides","html","evidence"):(out/x).mkdir(parents=True,exist_ok=True)
    tn=theme_for(story);t=THEMES[tn];ss=story.get("source_story") if isinstance(story.get("source_story"),dict) else {};ev=capture(ss.get("url",""),out/"evidence"/"source.png")
    print(f"GETBYTERUSH V4 | theme={tn} | slides={len(story['slides'])} | Gemini=0");render_html(story,out,t,ev);render_pngs(out,len(story["slides"]));metadata(story,out,created,tn,t);print("✓ Carousel generated");print(f"✓ Output: {out}")
if __name__=="__main__":main()
