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
- modern editorial compositions
"""

import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")
WIDTH, HEIGHT, SAFE = 1080, 1350, 78
RETENTION_DAYS = 7

THEMES = {
    "story": {"background":"#F4EFE4","foreground":"#111311","accent":"#12352B","accent2":"#B99A5B","muted":"#59645F","signal":"#B99A5B","surface":"#EAE3D5"},
    "urgency": {"background":"#111311","foreground":"#F4EFE4","accent":"#E53935","accent2":"#F4EFE4","muted":"#B9B6AD","signal":"#E53935","surface":"#1D1F1D"},
    "experiment": {"background":"#F4EFE4","foreground":"#12352B","accent":"#2D8C7A","accent2":"#4F7C70","muted":"#59645F","signal":"#2D8C7A","surface":"#E4EEE9"},
    "money": {"background":"#111311","foreground":"#F4EFE4","accent":"#B7E32B","accent2":"#B99A5B","muted":"#A9AAA2","signal":"#B7E32B","surface":"#20231D"},
    "explainer": {"background":"#F4EFE4","foreground":"#12352B","accent":"#527A91","accent2":"#3F6FA3","muted":"#59645F","signal":"#527A91","surface":"#E5E9E8"},
    "contradiction": {"background":"#F4EFE4","foreground":"#111311","accent":"#F26A21","accent2":"#111311","muted":"#59645F","signal":"#F26A21","surface":"#EFE1D7"},
    "investigation": {"background":"#EFE8D8","foreground":"#12352B","accent":"#426A78","accent2":"#C83C3C","muted":"#59645F","signal":"#C83C3C","surface":"#E2DBCC"},
    "timeline": {"background":"#F4EFE4","foreground":"#12352B","accent":"#3159C9","accent2":"#B99A5B","muted":"#59645F","signal":"#3159C9","surface":"#E5E8EF"},
    "comparison": {"background":"#F4EFE4","foreground":"#111311","accent":"#12352B","accent2":"#4B78A8","muted":"#59645F","signal":"#B99A5B","surface":"#E5E8E6"},
    "mystery": {"background":"#0D0F0E","foreground":"#F4EFE4","accent":"#C7F000","accent2":"#7457FF","muted":"#A9AAA2","signal":"#C7F000","surface":"#1A1D1A"},
    "data": {"background":"#F4EFE4","foreground":"#12352B","accent":"#C9A75D","accent2":"#4B78A8","muted":"#59645F","signal":"#C9A75D","surface":"#E6E9E8"},
}

TEMPLATE_THEME = {"story":"story","experiment":"experiment","shock-number":"money","breakdown":"explainer","contradiction":"contradiction","receipts":"investigation","timeline":"timeline","comparison":"comparison","wtf":"mystery","data-story":"data"}
CATEGORY_TEMPLATE = {"breaking_news":"story","daily_24_hours":"story","model_drop":"story","model_comparison":"comparison","experiment":"experiment","product_story":"breakdown","business_story":"story","ai_agent_story":"breakdown","internet_mystery":"wtf","deep_dive":"story","explainer":"breakdown","tool_discovery":"breakdown","data_story":"data-story","timeline":"timeline","what_happens_next":"story","failure_story":"contradiction","TECH_NEWS":"story","MODEL_UPDATE":"story","AI_AGENTS":"breakdown","BUSINESS":"story"}


def esc(value):
    if isinstance(value, list): value = " ".join(str(x) for x in value)
    return html.escape(str(value or "").strip())


def clean_text(value):
    if isinstance(value, list): return " ".join(str(x) for x in value).strip()
    return str(value or "").strip()


def first_nonempty(*values):
    for value in values:
        if clean_text(value): return value
    return ""


def slugify(value):
    return (re.sub(r"[^a-z0-9]+","-",clean_text(value).lower()).strip("-")[:80] or "getbyterush-post")


def infer_template(story):
    design = story.get("design") if isinstance(story.get("design"),dict) else {}
    explicit = clean_text(first_nonempty(story.get("template"),design.get("template"))).lower()
    if explicit in TEMPLATE_THEME: return explicit
    category = clean_text(first_nonempty(story.get("content_type"),story.get("story_type"),story.get("category"),story.get("type")))
    return CATEGORY_TEMPLATE.get(category,"story")


def infer_emotional_mode(story, template):
    design = story.get("design") if isinstance(story.get("design"),dict) else {}
    mode = clean_text(first_nonempty(story.get("emotional_mode"),design.get("emotional_mode"))).lower()
    aliases = {"urgent":"urgency","breaking":"urgency","emergency":"urgency","money":"money","money/scale":"money","explainer":"explainer","experiment":"experiment","contradiction":"contradiction","investigation":"investigation","timeline":"timeline","comparison":"comparison","mystery":"mystery","wtf":"mystery","data":"data"}
    return "urgency" if story.get("emergency_mode") is True else aliases.get(mode,TEMPLATE_THEME.get(template,"story"))


def theme_for(story, template):
    name = infer_emotional_mode(story,template)
    return name if name in THEMES else "story"


def resolve_accent(story, theme):
    design = story.get("design") if isinstance(story.get("design"),dict) else {}
    requested = clean_text(first_nonempty(story.get("accent_color"),design.get("accent_color")))
    if re.fullmatch(r"#[0-9a-fA-F]{6}",requested): return requested
    return THEMES[theme]["accent"]


def slide_role(slide, number, total):
    explicit = clean_text(first_nonempty(slide.get("role"),slide.get("scene_role"))).lower()
    if explicit: return explicit
    if number == 1: return "interrupt"
    if number == 2: return "open_loop"
    if number == total: return "payoff"
    if number == total-1: return "reveal"
    if number == 4: return "escalation"
    if number == 5: return "pattern_interrupt"
    return "proof"


def safe_headline(slide): return first_nonempty(slide.get("headline"),slide.get("title"),slide.get("hook"),slide.get("text"),"GetByteRush")
def safe_body(slide): return first_nonempty(slide.get("body"),slide.get("supporting_text"),slide.get("copy"),slide.get("description"))
def visual_concept(slide): return first_nonempty(slide.get("visual_concept"),slide.get("visual_strategy"),slide.get("visual_asset"),slide.get("visual"))


def source_info(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"),dict) else {}
    source = first_nonempty(slide.get("source_label"),slide.get("source"),source_story.get("source"),source_story.get("publisher"),"Official source")
    url = first_nonempty(slide.get("asset_url"),slide.get("source_url"),source_story.get("url"),story.get("source_url"))
    return clean_text(source), clean_text(url)


def capture_evidence(url, output_path):
    if not url: return False
    try:
        output_path = Path(output_path).resolve(); output_path.parent.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1)
            page.goto(url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_timeout(900)
            page.screenshot(path=str(output_path),full_page=False)
            browser.close()
        return output_path.exists()
    except Exception as exc:
        print(f"⚠ Evidence capture failed: {exc}")
        return False


def css(theme, template):
    t=THEMES[theme]
    return f'''@page{{size:{WIDTH}px {HEIGHT}px;margin:0}}*{{box-sizing:border-box}}html,body{{margin:0;width:{WIDTH}px;height:{HEIGHT}px;overflow:hidden}}body{{font-family:Inter,Arial,Helvetica,sans-serif;background:{t["background"]};color:{t["foreground"]}}}:root{{--bg:{t["background"]};--fg:{t["foreground"]};--accent:{t["accent"]};--accent2:{t["accent2"]};--muted:{t["muted"]};--signal:{t["signal"]};--surface:{t["surface"]}}}.slide{{position:relative;width:{WIDTH}px;height:{HEIGHT}px;padding:78px;overflow:hidden;background:var(--bg);color:var(--fg)}}.slide:before{{content:"";position:absolute;inset:0;pointer-events:none;opacity:.025;background-image:radial-gradient(currentColor .55px,transparent .65px);background-size:6px 6px}}.slide.blackout{{background:#111311;color:#F4EFE4}}.top-meta{{position:absolute;top:42px;left:78px;right:78px;display:flex;justify-content:space-between;font:800 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.3px;text-transform:uppercase;opacity:.68}}.page-no{{color:var(--accent)}}.rule{{width:108px;height:5px;background:var(--accent);margin:40px 0 24px}}.kicker{{display:inline-block;max-width:760px;padding:8px 12px;border:1px solid var(--accent);color:var(--accent);font:900 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.2px;text-transform:uppercase}}.headline{{position:relative;z-index:2;max-width:900px;margin:20px 0 0;font-size:76px;line-height:.91;letter-spacing:-4px;font-weight:950;overflow-wrap:anywhere}}.headline.small{{font-size:62px;line-height:.94;letter-spacing:-3px}}.headline.huge{{font-size:128px;line-height:.79;letter-spacing:-8px}}.body{{position:relative;z-index:2;max-width:780px;margin-top:24px;font-size:27px;line-height:1.13;font-weight:560;overflow-wrap:anywhere}}.footer{{position:absolute;left:78px;right:78px;bottom:42px;z-index:5;display:flex;justify-content:space-between;align-items:flex-end;gap:24px}}.source{{max-width:650px;font:700 12px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace;opacity:.62;text-transform:uppercase;overflow-wrap:anywhere}}.brand{{font:900 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.7px;white-space:nowrap}}.mystery{{position:absolute;left:78px;right:78px;top:610px;max-width:850px;font-size:82px;line-height:.84;letter-spacing:-5px;font-weight:950;color:var(--accent);text-transform:uppercase;overflow-wrap:anywhere}}.number-wrap{{position:absolute;left:78px;right:78px;top:520px}}.number{{font-size:260px;line-height:.7;letter-spacing:-15px;font-weight:950;color:var(--accent)}}.number-label{{margin-top:38px;max-width:820px;font-size:34px;line-height:1.02;font-weight:900}}.stat-grid{{position:absolute;left:78px;right:78px;top:610px;display:grid;grid-template-columns:1fr 1fr;gap:18px}}.stat{{min-height:255px;padding:28px;background:var(--surface);border:1px solid color-mix(in srgb,var(--fg) 24%,transparent);border-top:7px solid var(--accent);display:flex;flex-direction:column;justify-content:space-between}}.stat .value{{font-size:76px;line-height:.78;letter-spacing:-4px;font-weight:950;color:var(--accent)}}.stat .label{{font-size:22px;line-height:1.04;font-weight:800;overflow-wrap:anywhere}}.evidence-tag{{position:absolute;z-index:3;top:282px;left:78px;padding:8px 11px;background:var(--accent);color:var(--bg);font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px}}.evidence-frame{{position:absolute;left:78px;right:78px;top:320px;bottom:150px;padding:14px;border:2px solid var(--accent);background:#171917;box-shadow:18px 18px 0 var(--accent);overflow:hidden}}.evidence-frame img{{width:100%;height:100%;object-fit:contain;object-position:center;display:block;background:#fff}}.versus{{position:absolute;left:78px;right:78px;top:620px;display:grid;grid-template-columns:1fr 78px 1fr;gap:16px;align-items:center}}.versus-card{{min-height:270px;padding:28px;background:var(--surface);border:2px solid var(--accent);display:flex;flex-direction:column;justify-content:space-between}}.versus-card .name{{font:900 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);letter-spacing:1px}}.versus-card .copy{{font-size:39px;line-height:.93;letter-spacing:-1.5px;font-weight:950;overflow-wrap:anywhere}}.vs{{text-align:center;font:950 25px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent)}}.timeline{{position:absolute;left:95px;right:78px;top:575px;border-left:5px solid var(--accent);padding-left:34px}}.timeline-item{{position:relative;margin-bottom:28px}}.timeline-item:before{{content:"";position:absolute;left:-46px;top:1px;width:13px;height:13px;border:4px solid var(--accent);background:var(--bg)}}.timeline-date{{font:900 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);letter-spacing:1px;text-transform:uppercase}}.timeline-text{{margin-top:7px;max-width:800px;font-size:29px;line-height:1.03;font-weight:850;overflow-wrap:anywhere}}.diagram{{position:absolute;left:78px;right:78px;top:600px;display:grid;grid-template-columns:1fr 55px 1fr 55px 1fr;align-items:center;gap:8px}}.diagram .node{{min-height:205px;padding:24px;background:var(--surface);border:2px solid var(--accent)}}.diagram .node .label{{font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);letter-spacing:1px}}.diagram .node .value{{margin-top:18px;font-size:25px;line-height:1;font-weight:900;overflow-wrap:anywhere}}.diagram .arrow{{text-align:center;font-size:32px;font-weight:950;color:var(--accent)}}.quote{{position:absolute;left:78px;right:78px;top:600px;padding:30px 34px;border-left:8px solid var(--accent);background:var(--surface);font-size:48px;line-height:.98;letter-spacing:-2px;font-weight:900;overflow-wrap:anywhere}}.payoff{{position:absolute;left:78px;right:78px;top:600px;max-width:900px;padding-top:25px;border-top:7px solid var(--accent);font-size:54px;line-height:.92;letter-spacing:-2.5px;font-weight:950;overflow-wrap:anywhere}}.dark .stat,.blackout .stat{{background:#1D201D;border-color:#353935}}.blackout .versus-card,.blackout .diagram .node,.blackout .quote{{background:#1A1D1A}}'''


def visual_for_slide(slide,story,template,theme,evidence_uri,number,total):
    headline=safe_headline(slide); body=safe_body(slide); concept=visual_concept(slide); vt=str(slide.get("visual_type","typography")).lower(); role=slide_role(slide,number,total); source,_=source_info(story,slide)
    if template=="receipts" or vt in {"evidence","screenshot"}:
        if evidence_uri:return f'<div class="evidence-tag">REAL EVIDENCE · {esc(source)}</div><div class="evidence-frame"><img src="{esc(evidence_uri)}" alt="Official source evidence"></div>'
        return f'<div class="quote">{esc(first_nonempty(concept,body,"Evidence unavailable during render."))}</div>'
    if template=="shock-number" or vt=="metric":
        nums=re.findall(r"(?<![A-Za-z])(?:\$?\d+(?:\.\d+)?(?:%|x|×)?)(?![A-Za-z])"," ".join(map(clean_text,[headline,body,concept])))
        return f'<div class="number-wrap"><div class="number">{esc(nums[0] if nums else first_nonempty(concept,"01"))}</div><div class="number-label">{esc(first_nonempty(body,concept,headline))}</div></div>'
    if template=="comparison" or vt=="comparison":
        parts=re.split(r"\s+vs\.?\s+|\s+versus\s+",concept or headline,flags=re.I); left=parts[0].strip() if parts else "A"; right=parts[1].strip() if len(parts)>1 else "B"
        return f'<div class="versus"><div class="versus-card"><div class="name">OPTION A</div><div class="copy">{esc(left)}</div></div><div class="vs">VS</div><div class="versus-card"><div class="name">OPTION B</div><div class="copy">{esc(right)}</div></div></div>'
    if template=="timeline" or vt=="timeline":
        events=slide.get("timeline") or slide.get("events") or []
        if isinstance(events,list) and events:
            items=[]
            for item in events[:4]:
                if isinstance(item,dict): d=first_nonempty(item.get("date"),item.get("year"),"STEP"); val=first_nonempty(item.get("text"),item.get("headline"),item.get("description"))
                else: d="STEP"; val=item
                items.append(f'<div class="timeline-item"><div class="timeline-date">{esc(d)}</div><div class="timeline-text">{esc(val)}</div></div>')
            return '<div class="timeline">'+''.join(items)+'</div>'
        return f'<div class="timeline"><div class="timeline-item"><div class="timeline-date">BEFORE</div><div class="timeline-text">{esc(first_nonempty(body,headline))}</div></div><div class="timeline-item"><div class="timeline-date">NOW</div><div class="timeline-text">{esc(first_nonempty(concept,"The system changed."))}</div></div></div>'
    if template=="breakdown" or vt=="diagram":
        vals=[headline,concept or "THE SYSTEM",body or "THE IMPACT"]; labels=["INPUT","MECHANISM","IMPACT"]; nodes=[]
        for label,val in zip(labels,vals): nodes.append(f'<div class="node"><div class="label">{label}</div><div class="value">{esc(val)}</div></div>')
        return '<div class="diagram">'+'<div class="arrow">→</div>'.join(nodes)+'</div>'
    if template=="wtf" or role in {"interrupt","open_loop","pattern_interrupt"}: return f'<div class="mystery">{esc(first_nonempty(concept,slide.get("transition_hint"),"KEEP GOING →"))}</div>'
    if template=="data-story":
        nums=re.findall(r"(?<![A-Za-z])(?:\$?\d+(?:\.\d+)?(?:%|x|×)?)(?![A-Za-z])"," ".join(map(clean_text,[headline,body,concept])))
        if len(nums)>=2:return f'<div class="stat-grid"><div class="stat"><div class="value">{esc(nums[0])}</div><div class="label">{esc(headline)}</div></div><div class="stat"><div class="value">{esc(nums[1])}</div><div class="label">{esc(first_nonempty(body,concept))}</div></div></div>'
    if template=="experiment": return f'<div class="stat-grid"><div class="stat"><div class="value">TEST</div><div class="label">{esc(first_nonempty(concept,"REAL-WORLD TEST"))}</div></div><div class="stat"><div class="value">RESULT</div><div class="label">{esc(first_nonempty(body,"THE RESULT"))}</div></div></div>'
    if template=="contradiction" or vt=="quote": return f'<div class="quote">{esc(first_nonempty(concept,body,headline))}</div>'
    if role in {"reveal","payoff"}: return f'<div class="payoff">{esc(first_nonempty(body,slide.get("payoff"),slide.get("implication"),concept,headline))}</div>'
    return f'<div class="quote">{esc(first_nonempty(concept,body,headline))}</div>'


def slide_html(slide,story,template,theme_name,theme,evidence_uri,number,total):
    headline=clean_text(safe_headline(slide)); body=clean_text(safe_body(slide)); role=slide_role(slide,number,total)
    requested=clean_text(first_nonempty(slide.get("background"),slide.get("background_mode"))).lower()
    blackout=requested in {"black","ink","dark","blackout"} or role=="pattern_interrupt" or (number==1 and theme_name in {"urgency","mystery"})
    classes="slide blackout" if blackout else "slide"
    if number==total: classes+=" minimal"
    hc="headline huge" if number==1 and len(headline)<55 else "headline small" if len(headline)>78 else "headline"
    source,_=source_info(story,slide)
    visual=visual_for_slide(slide,story,template,theme_name,evidence_uri,number,total)
    body_html=f'<div class="body">{esc(body)}</div>' if body and number!=total and len(body)<280 else ""
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width={WIDTH}, initial-scale=1"><style>{css(theme_name,template)}</style></head><body><section class="{classes}"><div class="top-meta"><div>GETBYTERUSH / {esc(template.replace("-"," ").upper())}</div><div class="page-no">{number:02d} / {total:02d}</div></div><div class="rule"></div><div class="kicker">{esc(first_nonempty(slide.get("kicker"),slide.get("label"),story.get("series"),"GETBYTERUSH"))}</div><h1 class="{hc}">{esc(headline)}</h1>{body_html}{visual}<div class="footer"><div class="source">SOURCE / {esc(source)}</div><div class="brand">TESTED • EXPLAINED • REAL</div></div></section></body></html>'''


def render_html_files(story,out_dir,template,theme_name,theme,evidence_path):
    html_dir=out_dir/"html"; html_dir.mkdir(parents=True,exist_ok=True); evidence_uri=None
    if evidence_path:
        try:
            p=Path(evidence_path).resolve()
            if p.exists(): evidence_uri=p.as_uri()
        except Exception as exc: print(f"⚠ Evidence URI unavailable: {exc}")
    for index,slide in enumerate(story.get("slides",[]),1):
        (html_dir/f"{index:02d}.html").write_text(slide_html(slide,story,template,theme_name,theme,evidence_uri,index,len(story.get("slides",[]))),encoding="utf-8")


def render_pngs(out_dir,count):
    out_dir=Path(out_dir).resolve(); html_dir=out_dir/"html"; slides_dir=out_dir/"slides"; slides_dir.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        for index in range(1,count+1):
            page=browser.new_page(viewport={"width":WIDTH,"height":HEIGHT},device_scale_factor=1)
            page.goto((html_dir/f"{index:02d}.html").resolve().as_uri(),wait_until="load")
            page.screenshot(path=str(slides_dir/f"{index:02d}.png"),full_page=False)
            page.close()
        browser.close()


def write_metadata(story,out_dir,created_at,retention_days):
    (out_dir/"caption.txt").write_text(clean_text(story.get("caption")),encoding="utf-8")
    hashtags=story.get("hashtags",[]); (out_dir/"hashtags.txt").write_text(" ".join(map(str,hashtags)) if isinstance(hashtags,list) else clean_text(hashtags),encoding="utf-8")
    (out_dir/"pinned-comment.txt").write_text(clean_text(story.get("pinned_comment")),encoding="utf-8")
    (out_dir/"alt-text.txt").write_text(clean_text(story.get("alt_text")),encoding="utf-8")
    created_dt=datetime.fromisoformat(created_at); delete_after=(created_dt+timedelta(days=retention_days)).isoformat()
    design=dict(story.get("design") or {}); template=infer_template(story); theme_name=theme_for(story,template)
    design.update({"template":template,"emotional_mode":infer_emotional_mode(story,template),"accent_color":resolve_accent(story,theme_name),"renderer":"getbyterush-carousel-generator-v3"})
    package=dict(story); package.update({"design":design,"post_id":f"{slugify(story.get('story_title','getbyterush-post'))}-{created_at.replace(':','').replace('+','-')}","status":"pending_approval","created_at":created_at,"retention_days":retention_days,"delete_after":delete_after,"package":{"slides_dir":"slides","html_dir":"html","evidence_dir":"evidence","slide_count":len(story.get("slides",[])),"template":template,"theme":theme_name},"instagram":{"published":False,"media_id":None,"permalink":None}})
    (out_dir/"post.json").write_text(json.dumps(package,indent=2,ensure_ascii=False),encoding="utf-8")


def main():
    if not INPUT.exists(): raise FileNotFoundError(f"Missing {INPUT}. Run editorial_engine.py first.")
    story=json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"): print("No story selected. Nothing to render."); return
    slides=story.get("slides",[])
    if not slides: raise ValueError("Selected story contains no carousel slides.")
    created_dt=datetime.now().astimezone(); created_at=created_dt.isoformat(timespec="seconds"); title=story.get("story_title","GetByteRush Post")
    date_dir=OUTPUT_ROOT/created_dt.strftime("%Y-%m-%d"); date_dir.mkdir(parents=True,exist_ok=True); out_dir=date_dir/f"{created_dt.strftime('%H%M')}-{slugify(title)}"
    if out_dir.exists(): out_dir=date_dir/f"{created_dt.strftime('%H%M%S')}-{slugify(title)}"
    for d in ("slides","html","evidence"): (out_dir/d).mkdir(parents=True,exist_ok=True)
    template=infer_template(story); theme_name=theme_for(story,template); theme=THEMES[theme_name]; source_story=story.get("source_story",{}); source_url=source_story.get("url","") if isinstance(source_story,dict) else ""
    evidence_path=out_dir/"evidence"/"source.png"; has_evidence=capture_evidence(source_url,evidence_path); evidence_path=evidence_path if has_evidence else None
    print("\n"+"="*72+"\nGETBYTERUSH CAROUSEL V3\n"+"="*72); print(f"Template: {template}\nTheme: {theme_name}\nAccent: {resolve_accent(story,theme_name)}\nSlides: {len(slides)}")
    render_html_files(story,out_dir,template,theme_name,theme,evidence_path); render_pngs(out_dir,len(slides)); write_metadata(story,out_dir,created_at,RETENTION_DAYS)
    print(f"Output: {out_dir}\nEvidence: {'YES' if has_evidence else 'NO'}\nStatus: pending_approval")

if __name__ == "__main__": main()
