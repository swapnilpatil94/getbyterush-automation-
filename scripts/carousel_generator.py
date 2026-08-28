#!/usr/bin/env python3
"""GetByteRush production carousel renderer.

Strict production renderer:
- 1080x1350 output
- story-level theme + slide-level visual routing
- source evidence uses preserved aspect ratio
- no invented editorial copy
- content-aware overflow validation (not false positives from line boxes)
- dated packages for Telegram/Instagram publishing
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
WIDTH = 1080
HEIGHT = 1350
SAFE = 78
RETENTION_DAYS = 7

THEMES = {
    "story": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#12352B", "signal": "#B99A5B", "surface": "#EAE3D5"},
    "urgency": {"bg": "#111311", "fg": "#F4EFE4", "accent": "#E53935", "signal": "#E53935", "surface": "#1D1F1D"},
    "experiment": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#2D8C7A", "signal": "#BFDCCF", "surface": "#E4EEE9"},
    "money": {"bg": "#111311", "fg": "#F4EFE4", "accent": "#B7E32B", "signal": "#B99A5B", "surface": "#20231D"},
    "explainer": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#527A91", "signal": "#D7D9D5", "surface": "#E5E9E8"},
    "contradiction": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#F26A21", "signal": "#111311", "surface": "#EFE1D7"},
    "investigation": {"bg": "#EFE8D8", "fg": "#12352B", "accent": "#426A78", "signal": "#C83C3C", "surface": "#E2DBCC"},
    "timeline": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#3159C9", "signal": "#B99A5B", "surface": "#E5E8EF"},
    "comparison": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#12352B", "signal": "#4B78A8", "surface": "#E5E8E6"},
    "mystery": {"bg": "#0D0F0E", "fg": "#F4EFE4", "accent": "#C7F000", "signal": "#7457FF", "surface": "#1A1D1A"},
    "data": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#C9A75D", "signal": "#4B78A8", "surface": "#E6E9E8"},
}

TEMPLATE_THEME = {
    "story": "story", "experiment": "experiment", "shock-number": "money",
    "breakdown": "explainer", "contradiction": "contradiction", "receipts": "investigation",
    "timeline": "timeline", "comparison": "comparison", "wtf": "mystery", "data-story": "data",
}

CATEGORY_TEMPLATE = {
    "breaking_news": "story", "daily_24_hours": "story", "model_drop": "story",
    "model_comparison": "comparison", "experiment": "experiment", "product_story": "breakdown",
    "business_story": "story", "ai_agent_story": "breakdown", "internet_mystery": "wtf",
    "deep_dive": "story", "explainer": "breakdown", "tool_discovery": "breakdown",
    "data_story": "data-story", "timeline": "timeline", "what_happens_next": "story",
    "failure_story": "contradiction", "TECH_NEWS": "story", "MODEL_UPDATE": "story",
    "AI_AGENTS": "breakdown", "BUSINESS": "story",
}

VISUAL_TEMPLATE = {
    "metric": "shock-number", "comparison": "comparison", "timeline": "timeline",
    "evidence": "receipts", "screenshot": "receipts", "diagram": "breakdown",
}

ALLOWED_ACCENTS = {
    "#12352B", "#E53935", "#2D8C7A", "#B7E32B", "#527A91", "#F26A21", "#426A78",
    "#3159C9", "#C7F000", "#C9A75D", "#B99A5B", "#7457FF", "#4B78A8", "#BFDCCF", "#D7D9D5",
}

BASE_CSS = r'''
@page { size:1080px 1350px; margin:0; }
* { box-sizing:border-box; }
html,body { width:1080px; height:1350px; margin:0; padding:0; overflow:hidden; }
body { font-family:"Inter Tight",Inter,Arial,Helvetica,sans-serif; }
.slide { position:relative; width:1080px; height:1350px; padding:78px; overflow:hidden; background:var(--bg); color:var(--fg); }
.meta { position:absolute; top:40px; left:78px; right:78px; display:flex; justify-content:space-between; align-items:center; font:800 16px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.25px; text-transform:uppercase; }
.meta .right { color:var(--accent); }
.rule { width:92px; height:4px; background:var(--accent); margin:44px 0 24px; }
.kicker { display:inline-block; max-width:640px; padding:9px 12px 8px; border:1.5px solid var(--accent); color:var(--accent); font:900 16px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.35px; text-transform:uppercase; }
.headline { max-width:900px; margin:18px 0 0; font-size:78px; line-height:.94; letter-spacing:-3.1px; font-weight:900; overflow-wrap:anywhere; }
.headline.tight { font-size:64px; letter-spacing:-2.3px; line-height:.97; }
.headline.long { font-size:54px; letter-spacing:-1.7px; line-height:1.02; }
.body { max-width:800px; margin-top:26px; font-size:29px; line-height:1.14; font-weight:550; overflow-wrap:anywhere; }
.micro { font:800 15px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.footer { position:absolute; left:78px; right:78px; bottom:44px; display:flex; justify-content:space-between; align-items:flex-end; gap:24px; }
.source { max-width:640px; font:700 13px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; opacity:.68; overflow-wrap:anywhere; }
.brand { font-size:14px; font-weight:900; letter-spacing:1.6px; white-space:nowrap; text-transform:uppercase; }
.eyebrow { margin-top:36px; font:900 15px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--accent); letter-spacing:1.1px; text-transform:uppercase; }
.pair { margin-top:54px; display:grid; grid-template-columns:1fr 70px 1fr; gap:18px; align-items:stretch; }
.pair-card { min-height:220px; padding:28px; background:var(--surface); border:2px solid var(--accent); }
.pair-card.primary { border-top-width:8px; }
.pair-label { font:900 15px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.68; }
.pair-title { margin-top:22px; font-size:37px; line-height:.95; font-weight:900; letter-spacing:-1.4px; overflow-wrap:anywhere; }
.pair-copy { margin-top:18px; font-size:22px; line-height:1.04; font-weight:700; }
.vs { display:flex; justify-content:center; align-items:center; color:var(--accent); font:950 28px/1 ui-monospace,SFMono-Regular,Menlo,monospace; }
.number { margin-top:48px; color:var(--accent); font-size:250px; line-height:.73; letter-spacing:-15px; font-weight:950; }
.number-label { margin-top:38px; max-width:820px; font-size:38px; line-height:1.02; font-weight:850; }
.metric-grid { margin-top:52px; display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.metric-card { min-height:315px; padding:26px; background:var(--surface); border-top:7px solid var(--accent); display:flex; flex-direction:column; justify-content:space-between; }
.metric-value { color:var(--accent); font-size:82px; line-height:.82; letter-spacing:-5px; font-weight:950; overflow-wrap:anywhere; }
.metric-label { font-size:23px; line-height:1.0; font-weight:900; }
.metric-note { font:700 12px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; opacity:.62; text-transform:uppercase; }
.evidence-frame { position:absolute; left:78px; right:78px; top:310px; bottom:150px; padding:16px; border:2px solid var(--accent); background:#161816; overflow:hidden; }
.evidence-chrome { height:42px; display:flex; justify-content:space-between; align-items:center; padding:0 4px; color:#F4EFE4; font:800 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.9px; }
.evidence-window { width:100%; height:calc(100% - 42px); display:flex; justify-content:center; align-items:center; background:#fff; overflow:hidden; }
.evidence-window img { max-width:100%; max-height:100%; width:auto; height:auto; object-fit:contain; display:block; }
.evidence-caption { position:absolute; left:96px; right:96px; bottom:165px; display:flex; justify-content:space-between; color:#F4EFE4; font:700 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.7px; pointer-events:none; }
.quote-wrap { margin-top:52px; max-width:900px; padding:32px 36px; border-left:7px solid var(--accent); background:var(--surface); }
.quote-mark { color:var(--accent); font:950 88px/.55 Georgia,serif; }
.quote { margin-top:10px; font-size:46px; line-height:1.02; letter-spacing:-1.8px; font-weight:900; overflow-wrap:anywhere; }
.quote-source { margin-top:22px; font:800 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace; opacity:.7; text-transform:uppercase; }
.breakdown { margin-top:52px; display:grid; grid-template-columns:1fr 64px 1fr 64px 1fr; gap:10px; align-items:center; }
.node { min-height:190px; padding:23px; background:var(--surface); border:2px solid var(--accent); display:flex; flex-direction:column; justify-content:center; }
.node .label { font:900 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.66; }
.node .value { margin-top:13px; font-size:27px; line-height:1; font-weight:900; overflow-wrap:anywhere; }
.arrow { text-align:center; font-size:39px; font-weight:950; color:var(--accent); }
.timeline { margin-top:54px; padding-left:38px; border-left:5px solid var(--accent); }
.timeline-item { position:relative; margin-bottom:28px; }
.timeline-item:before { content:""; position:absolute; left:-51px; top:0; width:16px; height:16px; border:5px solid var(--accent); background:var(--bg); }
.timeline-date { color:var(--accent); font:900 15px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.timeline-text { margin-top:7px; font-size:30px; line-height:1.03; font-weight:850; overflow-wrap:anywhere; }
.compare-grid { margin-top:52px; display:grid; grid-template-columns:1fr 1fr; gap:18px; }
.compare-card { min-height:310px; padding:28px; background:var(--surface); border:2px solid var(--accent); }
.compare-card.winner { border-top-width:8px; }
.compare-name { font-size:40px; line-height:.94; letter-spacing:-1.5px; font-weight:950; overflow-wrap:anywhere; }
.compare-row { margin-top:22px; padding-top:15px; border-top:1px solid var(--accent); display:flex; justify-content:space-between; gap:16px; font-size:18px; line-height:1.05; font-weight:800; }
.pattern { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; padding:100px 78px; background:var(--bg); }
.pattern:before { content:""; position:absolute; width:660px; height:660px; border:2px solid var(--accent); transform:rotate(45deg); opacity:.26; }
.pattern .big { position:relative; max-width:900px; font-size:142px; line-height:.77; letter-spacing:-8px; text-align:center; font-weight:950; text-transform:uppercase; overflow-wrap:anywhere; }
.payoff { margin-top:52px; max-width:900px; border-top:6px solid var(--accent); padding-top:28px; font-size:49px; line-height:.98; letter-spacing:-2px; font-weight:900; overflow-wrap:anywhere; }
.payoff-small { margin-top:25px; max-width:790px; font-size:26px; line-height:1.08; font-weight:650; overflow-wrap:anywhere; }
.grain { position:absolute; inset:0; opacity:.018; pointer-events:none; background-image:radial-gradient(#000 .7px,transparent .8px); background-size:5px 5px; }
.dark .grain { opacity:.045; background-image:radial-gradient(#fff .7px,transparent .8px); }
'''


def text(value):
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value or "").strip()


def esc(value):
    return html.escape(text(value))


def first(*values):
    for value in values:
        if value is not None and text(value):
            return value
    return ""


def slug(value):
    return (re.sub(r"[^a-z0-9]+", "-", text(value).lower()).strip("-")[:80] or "getbyterush-post")


def infer_template(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    candidate = text(first(story.get("template"), design.get("template"))).lower()
    if candidate in TEMPLATE_THEME:
        return candidate
    category = text(first(story.get("format"), story.get("content_type"), story.get("story_type"), story.get("category"), story.get("type")))
    return CATEGORY_TEMPLATE.get(category, "story")


def infer_theme(story, template):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    mode = text(first(story.get("emotional_mode"), design.get("emotional_mode"))).lower()
    aliases = {"urgent":"urgency", "breaking":"urgency", "money/scale":"money", "money":"money", "explainer":"explainer", "experiment":"experiment", "contradiction":"contradiction", "investigation":"investigation", "timeline":"timeline", "comparison":"comparison", "mystery":"mystery", "wtf":"mystery", "data":"data"}
    if story.get("emergency_mode") is True:
        return "urgency"
    return aliases.get(mode, TEMPLATE_THEME.get(template, "story"))


def theme_with_design_override(story, theme_name):
    theme = dict(THEMES[theme_name])
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    accent = text(design.get("accent_color")).upper()
    if accent in ALLOWED_ACCENTS:
        theme["accent"] = accent
    return theme


def background_for(slide, theme_name):
    requested = text(first(slide.get("background_mode"), slide.get("background"))).lower()
    if requested in {"black","ink","dark","blackout"}:
        return "dark"
    if requested in {"cream","light","white"}:
        return "cream"
    return "dark" if theme_name in {"urgency","money","mystery"} else "cream"


def source_info(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    source = first(slide.get("source_label"), slide.get("source"), source_story.get("source"), story.get("source"), "Official source")
    url = first(slide.get("asset_url"), slide.get("source_url"), source_story.get("url"), story.get("source_url"))
    return text(source), text(url)


def visual_type_for(slide, index, total):
    explicit = text(first(slide.get("visual_type"), slide.get("layout"), slide.get("renderer"))).lower()
    if explicit:
        return explicit
    if index == 1:
        return "hook"
    if index == total:
        return "final"
    return "story"


def headline_class(headline):
    n = len(text(headline))
    if n > 105:
        return "headline long"
    if n > 68:
        return "headline tight"
    return "headline"


def number_values(slide):
    raw = " ".join(text(slide.get(k)) for k in ("headline","body","visual_concept"))
    values = re.findall(r"(?<![A-Za-z])(\+?\-?\$?\d+(?:\.\d+)?(?:%|x|×|[A-Za-z]{0,3})?)(?![A-Za-z])", raw)
    out=[]
    for v in values:
        if v not in out:
            out.append(v)
    return out[:3]


def visual_markup(story, slide, index, total, template, theme_name, theme, evidence_uri):
    headline = text(first(slide.get("headline"), slide.get("title"), slide.get("hook")))
    body = text(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")))
    concept = text(first(slide.get("visual_concept"), slide.get("visual_strategy"), slide.get("asset_requirement")))
    visual_type = visual_type_for(slide, index, total)
    source, url = source_info(story, slide)
    role = text(first(slide.get("role"), slide.get("scene_role"))).lower()

    if index == 1 or visual_type == "hook":
        title = text(first(slide.get("hook"), headline))
        source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
        left = text(first(source_story.get("source"), "THE SOURCE"))
        right = text(first(slide.get("hook_type"), "THE SHIFT"))
        return f'<div class="eyebrow">{esc(first(slide.get("transition_hint"),"THE QUESTION"))}</div><div class="pair"><div class="pair-card primary"><div class="pair-label">SOURCE</div><div class="pair-title">{esc(left)}</div><div class="pair-copy">The development.</div></div><div class="vs">×</div><div class="pair-card"><div class="pair-label">ANGLE</div><div class="pair-title">{esc(right)}</div><div class="pair-copy">The reason to keep swiping.</div></div></div>'

    if visual_type == "metric" or template == "shock-number":
        values = number_values(slide)
        if not values:
            values = ["01"]
        cards=[]
        labels=["KEY SIGNAL","WHAT CHANGED","WHY IT MATTERS"]
        for i,v in enumerate(values):
            cards.append(f'<div class="metric-card"><div class="metric-value">{esc(v)}</div><div class="metric-label">{esc(labels[i])}</div><div class="metric-note">{esc(source)}</div></div>')
        return '<div class="metric-grid">'+"".join(cards)+'</div>'

    if visual_type in {"screenshot","evidence"} or template == "receipts":
        if evidence_uri:
            return f'<div class="evidence-frame"><div class="evidence-chrome"><span>OFFICIAL SOURCE</span><span>{esc(urlparse(url).netloc or "SOURCE")}</span></div><div class="evidence-window"><img src="{esc(evidence_uri)}" alt="Official source evidence" /></div></div><div class="evidence-caption"><span>{esc(source)}</span><span>SOURCE CAPTURE</span></div>'
        return f'<div class="quote-wrap"><div class="quote-mark">“</div><div class="quote">{esc(first(body,concept))}</div><div class="quote-source">{esc(source)}</div></div>'

    if visual_type == "comparison" or template == "comparison":
        raw=first(concept,headline)
        parts=re.split(r"\s+vs\.?\s+|\s+versus\s+",raw,flags=re.I)
        left,right=(parts[0].strip(), parts[1].strip()) if len(parts)>1 else (raw,"Alternative")
        return f'<div class="compare-grid"><div class="compare-card winner"><div class="pair-label">A</div><div class="compare-name">{esc(left)}</div><div class="compare-row"><span>POSITION</span><span>PRIMARY</span></div><div class="compare-row"><span>USE</span><span>SOURCE DATA</span></div></div><div class="compare-card"><div class="pair-label">B</div><div class="compare-name">{esc(right)}</div><div class="compare-row"><span>POSITION</span><span>ALTERNATIVE</span></div><div class="compare-row"><span>USE</span><span>SOURCE DATA</span></div></div></div>'

    if visual_type == "timeline" or template == "timeline":
        events=slide.get("timeline") or slide.get("events") or []
        if isinstance(events,list) and events:
            items=[]
            for e in events[:5]:
                if isinstance(e,dict):
                    d=first(e.get("date"),e.get("year"),"STEP"); v=first(e.get("text"),e.get("headline"),e.get("description"))
                else: d,v="STEP",e
                items.append(f'<div class="timeline-item"><div class="timeline-date">{esc(d)}</div><div class="timeline-text">{esc(v)}</div></div>')
            return '<div class="timeline">'+"".join(items)+'</div>'
        return f'<div class="timeline"><div class="timeline-item"><div class="timeline-date">BEFORE</div><div class="timeline-text">{esc(first(body,headline))}</div></div><div class="timeline-item"><div class="timeline-date">NOW</div><div class="timeline-text">{esc(first(concept,headline))}</div></div><div class="timeline-item"><div class="timeline-date">NEXT</div><div class="timeline-text">{esc(first(slide.get("implication"),body))}</div></div></div>'

    if visual_type == "diagram" or template == "breakdown":
        labels=["INPUT","SYSTEM","OUTPUT"]
        vals=[first(slide.get("input"),headline), first(concept,slide.get("system")), first(body,slide.get("output"))]
        nodes=[]
        for label,value in zip(labels,vals):
            nodes.append(f'<div class="node"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div></div>')
        return '<div class="breakdown">'+ '<div class="arrow">→</div>'.join(nodes)+'</div>'

    if role == "pattern_interrupt" or visual_type == "pattern_interrupt":
        return f'<div class="pattern"><div class="big">{esc(first(headline,concept,"WAIT."))}</div></div>'

    if visual_type == "quote" or role == "reveal":
        return f'<div class="quote-wrap"><div class="quote-mark">“</div><div class="quote">{esc(first(body,headline,concept))}</div><div class="quote-source">{esc(source)}</div></div>'

    if visual_type == "final" or index == total:
        return f'<div class="payoff">{esc(first(headline,body,concept))}</div><div class="payoff-small">{esc(first(slide.get("implication"),body))}</div>'

    return f'<div class="breakdown"><div class="node"><div class="label">CONTEXT</div><div class="value">{esc(first(slide.get("context"),headline))}</div></div><div class="arrow">→</div><div class="node"><div class="label">CHANGE</div><div class="value">{esc(first(concept,body))}</div></div><div class="arrow">→</div><div class="node"><div class="label">IMPACT</div><div class="value">{esc(first(slide.get("implication"),body))}</div></div></div>'


def slide_html(story,slide,index,total,template,theme_name,theme,evidence_uri):
    headline=text(first(slide.get("headline"),slide.get("title"),slide.get("hook")))
    body=text(first(slide.get("body"),slide.get("supporting_text"),slide.get("copy")))
    kicker=text(first(slide.get("kicker"),slide.get("label"),"GETBYTERUSH"))
    dark=background_for(slide,theme_name)=="dark"
    bg="#111311" if dark else theme["bg"]
    fg="#F4EFE4" if dark else theme["fg"]
    accent=theme["accent"]
    surface=theme["surface"]
    style=BASE_CSS+f'\n:root{{--bg:{bg};--fg:{fg};--accent:{accent};--signal:{theme["signal"]};--surface:{surface};}}'
    visual_type=visual_type_for(slide,index,total)
    body_html=f'<div class="body">{esc(body)}</div>' if body and index==1 else ""
    if body and index!=1 and visual_type not in {"metric","screenshot","evidence","timeline","comparison","diagram","quote","final"}:
        body_html=f'<div class="body">{esc(body)}</div>'
    visual=visual_markup(story,slide,index,total,template,theme_name,theme,evidence_uri)
    source,_=source_info(story,slide)
    classes="slide dark" if dark else "slide"
    return f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=1080,height=1350"><style>{style}</style></head><body><section class="{classes}"><div class="grain"></div><div class="meta"><span>GETBYTERUSH / {esc(template.replace("-"," "))}</span><span class="right">{index:02d} / {total:02d}</span></div><div class="rule"></div><div class="kicker">{esc(kicker)}</div><h1 class="{headline_class(headline)}">{esc(headline)}</h1>{body_html}{visual}<div class="footer"><div class="source">SOURCE / {esc(source)}</div><div class="brand">TESTED • EXPLAINED • REAL</div></div></section></body></html>'


def capture_evidence(url,out):
    if not url:return False
    try:
        out=Path(out).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
            page=browser.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1)
            page.goto(url,wait_until="domcontentloaded",timeout=30000); page.wait_for_timeout(1800)
            page.screenshot(path=str(out),full_page=False); browser.close()
        return out.exists()
    except Exception as exc:
        print(f"WARNING: evidence capture failed: {exc}"); return False


def render_html(story,out_dir,template,theme_name,theme,evidence_path):
    html_dir=out_dir/"html"; html_dir.mkdir(parents=True,exist_ok=True)
    evidence_uri=None
    if evidence_path:
        p=Path(evidence_path).resolve()
        if p.exists(): evidence_uri=p.as_uri()
    for i,slide in enumerate(story.get("slides",[]),1):
        (html_dir/f"{i:02d}.html").write_text(slide_html(story,slide,i,len(story["slides"]),template,theme_name,theme,evidence_uri),encoding="utf-8")


def render_pngs_validate(out_dir,count):
    html_dir=Path(out_dir).resolve()/"html"; slides_dir=Path(out_dir).resolve()/"slides"; slides_dir.mkdir(parents=True,exist_ok=True)
    failures=[]
    critical_selector=".meta, .kicker, h1, .body, .pair, .number, .number-label, .metric-grid, .evidence-frame, .evidence-caption, .quote-wrap, .breakdown, .timeline, .compare-grid, .pattern, .payoff, .payoff-small, .footer"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        page=browser.new_page(viewport={"width":WIDTH,"height":HEIGHT},device_scale_factor=1)
        for i in range(1,count+1):
            path=html_dir/f"{i:02d}.html"; png=slides_dir/f"{i:02d}.png"
            page.goto(path.resolve().as_uri(),wait_until="load"); page.wait_for_timeout(120)
            result=page.evaluate("""
            (selector) => {
              const W=1080,H=1350, margin=2;
              const els=[...document.querySelectorAll(selector)];
              const geometry=[];
              for(const el of els){const r=el.getBoundingClientRect(); if(r.right>W+margin||r.left<-margin||r.bottom>H+margin||r.top<-margin) geometry.push({tag:el.tagName,cls:String(el.className),bounds:[r.left,r.top,r.right,r.bottom]});}
              const textEls=[...document.querySelectorAll('h1,.body,.pair-title,.number-label,.metric-label,.metric-value,.quote,.node .value,.timeline-text,.compare-name,.payoff,.payoff-small,.pattern .big')];
              const overflow=[];
              for(const el of textEls){ if(el.clientWidth>0 && el.clientHeight>0 && (el.scrollWidth>el.clientWidth+3 || el.scrollHeight>el.clientHeight+3)) overflow.push({cls:String(el.className),text:(el.innerText||'').slice(0,120),client:[el.clientWidth,el.clientHeight],scroll:[el.scrollWidth,el.scrollHeight]}); }
              return {geometry,overflow,doc:[document.documentElement.scrollWidth,document.documentElement.scrollHeight]};
            }
            """,critical_selector)
            if result.geometry or result.overflow or result.doc[0]>WIDTH or result.doc[1]>HEIGHT:
                failures.append({"slide":i,"details":result})
            page.screenshot(path=str(png),full_page=False); print(f"✓ slide-{i:02d}.png")
        browser.close()
    if failures:
        print("PRODUCTION_LAYOUT_VALIDATION_FAILED")
        print(json.dumps(failures,indent=2,ensure_ascii=False))
        raise RuntimeError("Carousel layout validation failed.")


def write_package(story,out_dir,template,theme_name,created_at):
    (out_dir/"caption.txt").write_text(text(story.get("caption")),encoding="utf-8")
    hashtags=story.get("hashtags",[]); (out_dir/"hashtags.txt").write_text(" ".join(map(str,hashtags)) if isinstance(hashtags,list) else text(hashtags),encoding="utf-8")
    (out_dir/"pinned-comment.txt").write_text(text(story.get("pinned_comment")),encoding="utf-8")
    (out_dir/"alt-text.txt").write_text(text(story.get("alt_text")),encoding="utf-8")
    created=datetime.fromisoformat(created_at)
    payload=dict(story)
    payload.update({"status":"pending_approval","created_at":created_at,"retention_days":RETENTION_DAYS,"delete_after":(created+timedelta(days=RETENTION_DAYS)).isoformat(),"rendering":{"renderer":"getbyterush-carousel-generator-v5","template":template,"theme":theme_name,"canvas":"1080x1350","production_ready":True},"instagram":{"published":False,"media_id":None,"permalink":None}})
    (out_dir/"post.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")


def validate_story(story):
    slides=story.get("slides",[])
    if not 5<=len(slides)<=9: raise ValueError(f"Carousel must contain 5–9 slides, got {len(slides)}")
    errors=[]
    for i,s in enumerate(slides,1):
        h=text(first(s.get("headline"),s.get("title"),s.get("hook"))); b=text(first(s.get("body"),s.get("supporting_text"),s.get("copy")))
        if not h: errors.append(f"slide {i}: missing headline")
        if len(h)>130: errors.append(f"slide {i}: headline too long")
        if len(b)>400: errors.append(f"slide {i}: body too long")
    if errors: raise ValueError("; ".join(errors))


def main():
    if not INPUT.exists(): raise FileNotFoundError(f"Missing {INPUT}")
    story=json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"): print("No selected story. Nothing to render."); return
    validate_story(story)
    slides=story["slides"]; template=infer_template(story); theme_name=infer_theme(story,template); theme=theme_with_design_override(story,theme_name)
    created=datetime.now().astimezone(); created_at=created.isoformat(timespec="seconds")
    date_dir=OUTPUT_ROOT/created.strftime("%Y-%m-%d"); date_dir.mkdir(parents=True,exist_ok=True)
    out_dir=date_dir/f"{created.strftime('%H%M%S')}-{slug(story.get('story_title','getbyterush-post'))}"; out_dir.mkdir(parents=True,exist_ok=False)
    for sub in ("slides","html","evidence"): (out_dir/sub).mkdir(parents=True,exist_ok=True)
    source_story=story.get("source_story") if isinstance(story.get("source_story"),dict) else {}; source_url=text(first(source_story.get("url"),story.get("source_url")))
    evidence_path=out_dir/"evidence"/"source.png"
    if not capture_evidence(source_url,evidence_path): evidence_path=None
    print("="*72); print("GETBYTERUSH CAROUSEL V5"); print(f"Template : {template}"); print(f"Theme    : {theme_name}"); print(f"Accent   : {theme['accent']}"); print(f"Slides   : {len(slides)}"); print(f"Evidence : {'YES' if evidence_path else 'NO'}")
    render_html(story,out_dir,template,theme_name,theme,evidence_path); render_pngs_validate(out_dir,len(slides)); write_package(story,out_dir,template,theme_name,created_at)
    print(f"OUTPUT: {out_dir}"); print("PRODUCTION_READY: true")


if __name__=="__main__": main()
