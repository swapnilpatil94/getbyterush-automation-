#!/usr/bin/env python3
"""GetByteRush premium editorial carousel renderer.

Renderer-only: consumes data/selected_story.json. Never calls Gemini.
The renderer treats the carousel as one continuous visual story and maps
story roles, emotional intent, evidence, color psychology and retention
heuristics into deterministic HTML/CSS at 1080x1350.
"""
import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

WIDTH = 1080
HEIGHT = 1350
INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")
RETENTION_DAYS = 7

# ---------------------------------------------------------------------------
# GetByteRush brand tokens
# ---------------------------------------------------------------------------
CREAM = "#F4EFE4"
INK = "#111311"
FOREST = "#12352B"
GOLD = "#B99A5B"
RED = "#E53935"
TEAL = "#2D8C7A"
BLUE = "#3159C9"
ORANGE = "#F26A21"
LIME = "#B7E43B"
WHITE = "#FFFFFF"

# Color choices are deliberate editorial heuristics, not decorative defaults.
# Each mode creates a different emotional signal while retaining the brand DNA.
THEMES = {
    "brand": {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": GOLD, "surface": "#E9E2D5", "mode": "authority"},
    "explainer": {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": BLUE, "surface": "#E8EDF4", "mode": "clarity"},
    "experiment": {"bg": CREAM, "fg": INK, "accent": TEAL, "signal": TEAL, "surface": "#E1ECE8", "mode": "discovery"},
    "money": {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": GOLD, "surface": "#E9E0CC", "mode": "value"},
    "urgency": {"bg": INK, "fg": CREAM, "accent": RED, "signal": RED, "surface": "#20221F", "mode": "urgency"},
    "comparison": {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": GOLD, "surface": "#E8E3D8", "mode": "competition"},
    "timeline": {"bg": CREAM, "fg": INK, "accent": BLUE, "signal": BLUE, "surface": "#E6EAF2", "mode": "progression"},
    "contradiction": {"bg": CREAM, "fg": INK, "accent": ORANGE, "signal": ORANGE, "surface": "#F0E2D7", "mode": "tension"},
    "investigation": {"bg": "#EFE8D8", "fg": INK, "accent": "#426A78", "signal": RED, "surface": "#E3DED1", "mode": "investigation"},
    "mystery": {"bg": "#0D0F0E", "fg": CREAM, "accent": LIME, "signal": LIME, "surface": "#181C18", "mode": "novelty"},
    "data": {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": GOLD, "surface": "#E7E1D5", "mode": "pattern"},
}

TEMPLATE_BY_CATEGORY = {
    "breaking_news": "story", "daily_24_hours": "story", "model_drop": "story",
    "model_comparison": "comparison", "experiment": "experiment", "product_story": "breakdown",
    "business_story": "story", "ai_agent_story": "breakdown", "internet_mystery": "wtf",
    "deep_dive": "story", "explainer": "breakdown", "tool_discovery": "breakdown",
    "TECH_NEWS": "story", "MODEL_UPDATE": "story", "AI_AGENTS": "breakdown", "BUSINESS": "story",
}

THEME_BY_TEMPLATE = {
    "story": "brand", "experiment": "experiment", "shock-number": "money", "breakdown": "explainer",
    "contradiction": "contradiction", "receipts": "investigation", "timeline": "timeline",
    "comparison": "comparison", "wtf": "mystery", "data-story": "data",
}

ALIASES = {
    "urgent": "urgency", "breaking": "urgency", "emergency": "urgency", "money/scale": "money",
    "explainer": "explainer", "experiment": "experiment", "contradiction": "contradiction",
    "receipts": "investigation", "investigation": "investigation", "timeline": "timeline",
    "comparison": "comparison", "mystery": "mystery", "data": "data", "pattern": "data",
}


def text(value):
    if isinstance(value, list):
        return " ".join(str(x) for x in value).strip()
    return str(value or "").strip()


def esc(value):
    return html.escape(text(value), quote=True)


def clean(value, limit=None):
    value = re.sub(r"\s+", " ", text(value)).strip()
    if limit and len(value) > limit:
        cut = value[:limit].rsplit(" ", 1)[0]
        value = cut.rstrip(" ,.;:")
    return value


def first(*values):
    for value in values:
        if text(value):
            return value
    return ""


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", text(value).lower()).strip("-")[:90] or "getbyterush-post"


def infer_template(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    explicit = clean(first(story.get("template"), design.get("template"))).lower()
    if explicit in THEME_BY_TEMPLATE:
        return explicit
    for slide in story.get("slides", []):
        visual = clean(first(slide.get("visual_type"), slide.get("layout"))).lower()
        if visual in {"metric", "number", "stat"}:
            return "shock-number"
        if visual in {"comparison", "versus"}:
            return "comparison"
        if visual in {"timeline", "history"}:
            return "timeline"
        if visual in {"evidence", "screenshot", "receipt"}:
            return "receipts"
    category = clean(first(story.get("content_type"), story.get("story_type"), story.get("category"), story.get("type")))
    return TEMPLATE_BY_CATEGORY.get(category, "story")


def infer_theme(story, template):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    raw = clean(first(story.get("emotional_mode"), design.get("emotional_mode"))).lower()
    name = ALIASES.get(raw, raw) if raw else THEME_BY_TEMPLATE.get(template, "brand")
    if story.get("emergency_mode") is True:
        name = "urgency"
    if name not in THEMES:
        name = THEME_BY_TEMPLATE.get(template, "brand")
    return name, THEMES[name]


def slide_role(slide, index, total):
    explicit = clean(first(slide.get("role"), slide.get("scene_role"))).lower()
    if explicit:
        return explicit
    if index == 1:
        return "interrupt"
    if index == 2:
        return "open_loop"
    if index == total:
        return "payoff"
    if index == total - 1:
        return "reveal"
    if index == 5:
        return "pattern_interrupt"
    return "proof"


def slide_copy(slide):
    headline = clean(first(slide.get("headline"), slide.get("title"), slide.get("hook"), slide.get("text")), 150)
    body = clean(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy"), slide.get("description")), 280)
    concept = clean(first(slide.get("visual_concept"), slide.get("visual_strategy"), slide.get("visual")), 220)
    return headline or "GetByteRush", body, concept


def source_info(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    source = clean(first(slide.get("source_label"), slide.get("source"), source_story.get("source"), source_story.get("publisher"), story.get("source"), "Official source"), 90)
    url = clean(first(slide.get("asset_url"), slide.get("source_url"), source_story.get("url"), story.get("source_url")))
    return source, url


def evidence_uri(path):
    if not path:
        return ""
    return Path(path).resolve().as_uri()


def capture_evidence(url, destination):
    if not url or not urlparse(url).scheme:
        print("Evidence: unavailable")
        return None
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1400)
            for selector in (
                '[aria-label*="cookie" i]', '[id*="cookie" i]', '[class*="cookie" i]',
                '[aria-label*="consent" i]', '[id*="consent" i]', '[class*="consent" i]'
            ):
                try:
                    page.locator(selector).first.evaluate("el => el.remove()")
                except Exception:
                    pass
            page.screenshot(path=str(destination), full_page=False)
            browser.close()
        if destination.exists():
            print(f"Evidence: {destination}")
            return destination
    except Exception as exc:
        print(f"WARNING: evidence capture failed: {exc}")
    return None


def metric_value(slide):
    raw = " ".join((clean(slide.get("headline")), clean(slide.get("visual_concept")), clean(slide.get("body"))))
    matches = re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)?", raw, flags=re.I)
    return matches[0] if matches else "01"


def bg_class(role, index):
    if role == "pattern_interrupt":
        return "dark"
    if role in {"interrupt", "open_loop"} and index % 3 == 0:
        return "dark"
    return ""


def css(theme):
    values = {
        "bg": theme["bg"], "fg": theme["fg"], "accent": theme["accent"], "signal": theme["signal"], "surface": theme["surface"],
    }
    return Template(r'''
@page { size:1080px 1350px; margin:0; }
* { box-sizing:border-box; }
html,body { margin:0; padding:0; width:1080px; height:1350px; overflow:hidden; }
body { background:$bg; color:$fg; font-family:Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }
:root {
  --cream:#F4EFE4; --ink:#111311; --forest:#12352B; --gold:#B99A5B;
  --bg:$bg; --fg:$fg; --accent:$accent; --signal:$signal; --surface:$surface;
}
.slide { position:relative; width:1080px; height:1350px; overflow:hidden; padding:76px 78px 72px; background:var(--bg); color:var(--fg); }
.slide.dark { background:#111311; color:#F4EFE4; }
.slide.dark .top,.slide.dark .footer { color:#F4EFE4; }
.slide.dark .micro-rule { background:var(--accent); }
.slide::before { content:""; position:absolute; inset:0; pointer-events:none; opacity:.045; background:linear-gradient(90deg, transparent 0 89px, currentColor 89px 90px, transparent 90px 100%); }
.grain { position:absolute; inset:0; pointer-events:none; opacity:.018; background-image:radial-gradient(currentColor .55px, transparent .7px); background-size:8px 8px; }
.top { position:absolute; left:78px; right:78px; top:38px; display:flex; justify-content:space-between; align-items:center; font:800 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.8px; text-transform:uppercase; opacity:.62; }
.top .brand { letter-spacing:2.5px; }
.page { padding:5px 8px; border:1px solid currentColor; }
.kicker { display:inline-flex; align-items:center; gap:8px; max-width:790px; padding:8px 11px; border-left:4px solid var(--accent); background:color-mix(in srgb, var(--accent) 8%, transparent); color:var(--accent); font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.5px; text-transform:uppercase; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.kicker::before { content:""; width:7px; height:7px; background:var(--signal); display:inline-block; flex:none; }
.hero-head { margin-top:24px; max-width:930px; }
h1 { margin:0; font-size:72px; line-height:.91; letter-spacing:-4px; font-weight:950; overflow-wrap:anywhere; text-wrap:balance; }
h1.hero { font-size:105px; line-height:.82; letter-spacing:-6.4px; max-width:930px; }
h1.compact { font-size:57px; line-height:.94; letter-spacing:-2.7px; }
.body { margin-top:22px; max-width:740px; font-size:23px; line-height:1.24; font-weight:540; letter-spacing:-.2px; opacity:.78; overflow-wrap:anywhere; }
.micro-rule { width:86px; height:5px; margin-top:24px; background:var(--accent); }
.footer { position:absolute; left:78px; right:78px; bottom:34px; display:flex; justify-content:space-between; gap:24px; font:800 10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.5; }
.footer .source { max-width:700px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hero-index { position:absolute; right:70px; top:165px; font:950 190px/.8 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:-16px; color:var(--accent); opacity:.09; }
.hook-mark { position:absolute; left:78px; bottom:118px; width:18px; height:18px; border:3px solid var(--signal); }

/* Premium information objects */
.metric { position:absolute; left:78px; right:78px; top:545px; }
.metric-value { font:950 248px/.7 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:-16px; color:var(--accent); }
.metric-accent { width:150px; height:7px; margin-top:44px; background:var(--signal); }
.metric-caption { margin-top:22px; max-width:820px; font-size:31px; line-height:1.01; font-weight:920; letter-spacing:-1.2px; overflow-wrap:anywhere; }
.metric-note { margin-top:14px; max-width:690px; font:800 11px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.56; }

.evidence-wrap { position:absolute; left:78px; right:78px; top:355px; height:720px; display:grid; grid-template-rows:1fr 42px; gap:0; }
.evidence-frame { position:relative; min-height:0; padding:14px; background:#151715; border:2px solid var(--fg); box-shadow:18px 18px 0 var(--accent); overflow:hidden; }
.evidence-frame img { display:block; width:100%; height:100%; object-fit:contain; object-position:center; background:#fff; }
.evidence-label { position:absolute; z-index:2; left:14px; top:14px; padding:8px 10px; max-width:520px; background:var(--accent); color:var(--bg); font:900 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.evidence-caption { align-self:end; display:flex; justify-content:space-between; gap:20px; font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.58; }

.compare { position:absolute; left:78px; right:78px; top:535px; display:grid; grid-template-columns:1fr 62px 1fr; gap:14px; align-items:center; }
.compare-card { min-height:300px; padding:28px; background:var(--surface); border:2px solid var(--fg); display:flex; flex-direction:column; justify-content:space-between; }
.compare-card.winner { border:4px solid var(--accent); transform:translateY(-10px); box-shadow:12px 12px 0 var(--signal); }
.compare-card small { color:var(--accent); font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.compare-card strong { max-width:360px; font-size:40px; line-height:.96; font-weight:950; letter-spacing:-2.2px; overflow-wrap:anywhere; }
.compare-card em { font-style:normal; font:900 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; opacity:.55; text-transform:uppercase; }
.vs { color:var(--accent); text-align:center; font:950 18px/1 ui-monospace,SFMono-Regular,Menlo,monospace; }

.diagram { position:absolute; left:78px; right:78px; top:560px; display:grid; grid-template-columns:1fr 38px 1fr 38px 1fr; gap:10px; align-items:center; }
.node { min-height:230px; padding:24px; background:var(--surface); border:2px solid var(--fg); }
.node small { display:block; color:var(--accent); font:900 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.node b { display:block; margin-top:22px; font-size:25px; line-height:1.02; font-weight:900; letter-spacing:-.8px; overflow-wrap:anywhere; }
.arrow { color:var(--signal); text-align:center; font-size:28px; font-weight:950; }

.timeline { position:absolute; left:78px; right:78px; top:585px; display:flex; align-items:center; gap:10px; }
.time-node { flex:1; min-width:0; min-height:190px; padding:18px; border-top:4px solid var(--accent); background:var(--surface); display:flex; flex-direction:column; justify-content:space-between; }
.time-node b { color:var(--accent); font:950 39px/.8 ui-monospace,SFMono-Regular,Menlo,monospace; }
.time-node span { font:900 10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.7px; text-transform:uppercase; overflow-wrap:anywhere; }
.timeline-line { position:absolute; left:10px; right:10px; top:-14px; height:2px; background:var(--signal); z-index:-1; }

.quote { position:absolute; left:78px; right:78px; top:545px; border-top:6px solid var(--accent); padding:26px 8px 0; }
.quote-mark { color:var(--signal); font:950 84px/.5 Georgia,serif; }
.quote blockquote { margin:24px 0 20px; max-width:900px; font-size:49px; line-height:1; letter-spacing:-2.5px; font-weight:950; overflow-wrap:anywhere; }
.quote small { color:var(--accent); font:900 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }

.pattern { position:absolute; left:0; right:0; top:440px; bottom:0; padding:70px 78px; background:var(--accent); color:var(--bg); overflow:hidden; }
.pattern::after { content:""; position:absolute; width:440px; height:440px; right:-150px; bottom:-150px; border:70px solid currentColor; border-radius:50%; opacity:.08; }
.pattern-tag { font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:2px; text-transform:uppercase; }
.pattern-big { margin-top:28px; max-width:870px; font-size:78px; line-height:.88; font-weight:950; letter-spacing:-4px; overflow-wrap:anywhere; }

.reveal { position:absolute; left:78px; right:78px; top:550px; display:grid; grid-template-columns:118px 1fr; gap:26px; align-items:start; }
.reveal-num { color:var(--accent); font:950 74px/.8 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:-5px; }
.reveal-copy strong { display:block; max-width:840px; font-size:53px; line-height:.95; font-weight:950; letter-spacing:-2.8px; overflow-wrap:anywhere; }
.reveal-copy p { margin:20px 0 0; max-width:760px; font-size:24px; line-height:1.2; opacity:.78; overflow-wrap:anywhere; }

.object { position:absolute; left:78px; right:78px; top:555px; display:grid; grid-template-columns:76px 5px 1fr; gap:20px; align-items:start; }
.object-index { color:var(--accent); font:950 54px/.9 ui-monospace,SFMono-Regular,Menlo,monospace; }
.object-rule { width:5px; min-height:175px; background:var(--signal); }
.object-copy strong { display:block; max-width:800px; font-size:49px; line-height:.97; font-weight:950; letter-spacing:-2.3px; overflow-wrap:anywhere; }
.object-copy p { margin:18px 0 0; max-width:730px; font-size:24px; line-height:1.2; opacity:.78; overflow-wrap:anywhere; }

.payoff { position:absolute; left:78px; right:78px; top:510px; }
.payoff-line { width:170px; height:7px; margin-bottom:28px; background:var(--signal); }
.payoff strong { display:block; max-width:900px; font-size:68px; line-height:.9; letter-spacing:-3.5px; font-weight:950; overflow-wrap:anywhere; }
.payoff p { max-width:760px; margin-top:22px; font-size:25px; line-height:1.18; opacity:.78; overflow-wrap:anywhere; }
.payoff .signature { margin-top:28px; color:var(--accent); font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:2px; text-transform:uppercase; }

/* Design QA guardrails */
.safe { position:absolute; left:78px; right:78px; top:120px; bottom:92px; pointer-events:none; border:1px solid transparent; }
[data-qa="headline"] { max-height:365px; overflow:hidden; }
[data-qa="body"] { max-height:150px; overflow:hidden; }
''').substitute(**values)


def visual_markup(slide, story, theme, evidence, index, total):
    headline, body, concept = slide_copy(slide)
    visual_type = clean(first(slide.get("visual_type"), slide.get("layout"))).lower()
    current_role = slide_role(slide, index, total)
    accent = theme["accent"]
    source, _ = source_info(story, slide)
    esc_h = esc(headline)
    esc_b = esc(body)
    esc_c = esc(concept)
    ev = evidence_uri(evidence)

    if current_role == "interrupt" or index == 1:
        return f'<div class="hero-index">{index:02d}</div><div class="hero-head"><div class="kicker">{esc(story.get("content_type", "TECH / AI / INTERNET"))}</div><div class="micro-rule"></div><h1 class="hero" data-qa="headline">{esc_h}</h1><div class="body" data-qa="body">{esc_b}</div></div><div class="hook-mark"></div>'

    if current_role == "pattern_interrupt":
        return f'<div class="pattern"><div class="pattern-tag">PATTERN INTERRUPT / {index:02d}</div><div class="pattern-big">{esc_h}</div></div>'

    if visual_type in {"metric", "number", "stat"} or current_role in {"reveal"} and re.search(r"\d", headline):
        return f'<div class="hero-head"><div class="kicker">THE NUMBER</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="metric"><div class="metric-value">{esc(metric_value(slide))}</div><div class="metric-accent"></div><div class="metric-caption">{esc_b or esc_h}</div><div class="metric-note">{esc_c or "Signal extracted from the source story"}</div></div>'

    if (visual_type in {"evidence", "screenshot", "receipt"} or evidence) and ev:
        return f'<div class="hero-head"><div class="kicker">PRIMARY EVIDENCE</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="evidence-wrap"><div class="evidence-frame"><div class="evidence-label">{esc(source)} / SOURCE</div><img src="{esc(ev)}" alt="Official source evidence" /></div><div class="evidence-caption"><span>{esc_c or "Source capture"}</span><span>REAL RECEIPT</span></div></div>'

    if visual_type in {"comparison", "versus"}:
        parts = [clean(x, 90) for x in re.split(r"\s+vs\.?\s+|\s+versus\s+", headline, flags=re.I) if clean(x)]
        left = parts[0] if parts else "A"
        right = parts[1] if len(parts) > 1 else "B"
        return f'<div class="hero-head"><div class="kicker">THE MATCHUP</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="compare"><div class="compare-card winner"><small>CONTENDER A</small><strong>{esc(left)}</strong><em>strength / trade-off</em></div><div class="vs">VS</div><div class="compare-card"><small>CONTENDER B</small><strong>{esc(right)}</strong><em>strength / trade-off</em></div></div>'

    if visual_type in {"timeline", "history"}:
        milestones = slide.get("milestones") if isinstance(slide.get("milestones"), list) else []
        if not milestones:
            milestones = ["ORIGIN", "TURN", "NOW"]
        nodes = []
        for i, item in enumerate(milestones[:5]):
            if isinstance(item, dict):
                year = clean(first(item.get("year"), item.get("date"), str(i + 1)))
                label = clean(first(item.get("label"), item.get("title"), item.get("text")), 55)
            else:
                year, label = str(i + 1), clean(item, 55)
            nodes.append(f'<div class="time-node"><b>{esc(year)}</b><span>{esc(label)}</span></div>')
        return f'<div class="hero-head"><div class="kicker">THE TIMELINE</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="timeline"><div class="timeline-line"></div>{"".join(nodes)}</div>'

    if visual_type in {"diagram", "architecture", "flow"}:
        labels = [x for x in re.split(r"\s*(?:→|->|→)\s*", concept) if clean(x)]
        if len(labels) < 3:
            labels = ["INPUT", "SYSTEM", "OUTCOME"]
        nodes = []
        for i, label in enumerate(labels[:3]):
            nodes.append(f'<div class="node"><small>STEP {i+1:02d}</small><b>{esc(clean(label, 75))}</b></div>')
            if i < min(2, len(labels)-1):
                nodes.append('<div class="arrow">→</div>')
        return f'<div class="hero-head"><div class="kicker">HOW IT WORKS</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="diagram">{"".join(nodes)}</div>'

    if current_role == "payoff":
        return f'<div class="hero-head"><div class="kicker">THE TAKEAWAY</div></div><div class="payoff"><div class="payoff-line"></div><strong>{esc_h}</strong><p>{esc_b}</p><div class="signature">GETBYTERUSH / TESTED • EXPLAINED • REAL</div></div>'

    if current_role == "reveal":
        return f'<div class="hero-head"><div class="kicker">THE REVEAL</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="reveal"><div class="reveal-num">{index:02d}</div><div class="reveal-copy"><strong>{esc_c or esc_h}</strong><p>{esc_b}</p></div></div>'

    if visual_type in {"quote", "statement"}:
        return f'<div class="hero-head"><div class="kicker">WHAT THEY SAID</div><h1 class="compact" data-qa="headline">{esc_h}</h1></div><div class="quote"><div class="quote-mark">“</div><blockquote>{esc_b or esc_h}</blockquote><small>{esc(source)}</small></div>'

    return f'<div class="hero-head"><div class="kicker">{esc(current_role.replace("_", " "))}</div><h1 data-qa="headline">{esc_h}</h1><div class="body" data-qa="body">{esc_b}</div><div class="micro-rule"></div></div><div class="object"><div class="object-index">{index:02d}</div><div class="object-rule"></div><div class="object-copy"><strong>{esc_c or "What changes here"}</strong><p>{esc_b}</p></div></div>'


def render_html_files(story, out_dir, template, theme_name, theme, evidence):
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    slides = story.get("slides", [])
    total = len(slides)
    stylesheet = css(theme)
    for index, slide in enumerate(slides, 1):
        current_role = slide_role(slide, index, total)
        dark = bg_class(current_role, index)
        source, _ = source_info(story, slide)
        markup = visual_markup(slide, story, theme, evidence, index, total)
        page = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=1080, initial-scale=1"><title>GetByteRush {index:02d}</title><style>{stylesheet}</style></head><body><main class="slide {dark}"><div class="grain"></div><div class="top"><span class="brand">GETBYTERUSH</span><span>TECH • AI • INTERNET</span><span class="page">{index:02d} / {total:02d}</span></div>{markup}<div class="safe"></div><div class="footer"><span class="source">{esc(source)}</span><span>TESTED • EXPLAINED • REAL</span></div></main></body></html>'''
        (html_dir / f"{index:02d}.html").write_text(page, encoding="utf-8")


def render_pngs(out_dir, count):
    html_dir = out_dir / "html"
    slides_dir = out_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        for index in range(1, count + 1):
            html_path = html_dir / f"{index:02d}.html"
            png_path = slides_dir / f"{index:02d}.png"
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
            page.goto(html_path.resolve().as_uri(), wait_until="load")
            page.screenshot(path=str(png_path), full_page=False)
            # Hard geometry checks prevent accidental page-size regressions.
            box = page.locator(".slide").bounding_box()
            if not box or round(box["width"]) != WIDTH or round(box["height"]) != HEIGHT:
                raise RuntimeError(f"Slide {index:02d} geometry invalid: {box}")
            page.close()
            print(f"✓ slide-{index:02d}.png")
        browser.close()


def write_metadata(story, out_dir, created_at, retention_days, template, theme_name, theme):
    caption = clean(story.get("caption"))
    hashtags = story.get("hashtags", [])
    hashtags_text = " ".join(str(x) for x in hashtags) if isinstance(hashtags, list) else text(hashtags)
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
    (out_dir / "hashtags.txt").write_text(hashtags_text, encoding="utf-8")
    (out_dir / "pinned-comment.txt").write_text(clean(story.get("pinned_comment")), encoding="utf-8")
    (out_dir / "alt-text.txt").write_text(clean(story.get("alt_text")), encoding="utf-8")
    try:
        delete_after = (datetime.fromisoformat(created_at) + timedelta(days=retention_days)).isoformat()
    except Exception:
        delete_after = ""
    package = dict(story)
    design = dict(story.get("design") or {})
    design.update({
        "template": template,
        "emotional_mode": design.get("emotional_mode") or theme["mode"],
        "accent_color": theme["accent"],
        "background_mode": "theme-driven",
        "renderer": "getbyterush-carousel-generator-v3",
        "psychology": {
            "color_mode": theme["mode"],
            "retention_strategy": "curiosity → evidence → pattern → payoff",
            "composition": "role-driven editorial rhythm",
            "brand_language": "premium editorial / internet-native",
        },
    })
    package.update({
        "design": design,
        "post_id": f"{slug(story.get('story_title', 'getbyterush-post'))}-{created_at.replace(':', '').replace('+', '-')}",
        "status": "pending_approval",
        "created_at": created_at,
        "retention_days": retention_days,
        "delete_after": delete_after,
        "package": {"slides_dir": "slides", "html_dir": "html", "evidence_dir": "evidence", "slide_count": len(story.get("slides", [])), "template": template, "theme": theme_name},
        "instagram": {"published": False, "media_id": None, "permalink": None},
    })
    (out_dir / "post.json").write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing {INPUT}. Run editorial_engine.py first.")
    story = json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"):
        print("No story selected. Nothing to render.")
        return
    slides = story.get("slides", [])
    if not slides:
        raise ValueError("Selected story contains no carousel slides.")

    created_dt = datetime.now().astimezone()
    created_at = created_dt.isoformat(timespec="seconds")
    title = story.get("story_title", "GetByteRush Post")
    date_dir = OUTPUT_ROOT / created_dt.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    out_dir = date_dir / f"{created_dt.strftime('%H%M%S')}-{slug(title)}"
    (out_dir / "slides").mkdir(parents=True, exist_ok=True)
    (out_dir / "html").mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence").mkdir(parents=True, exist_ok=True)

    template = infer_template(story)
    theme_name, theme = infer_theme(story, template)
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    evidence = capture_evidence(source_story.get("url", ""), out_dir / "evidence" / "source.png")

    print("=" * 72)
    print("GETBYTERUSH PREMIUM CAROUSEL RENDERER")
    print("=" * 72)
    print(f"Template: {template}")
    print(f"Theme:    {theme_name} ({theme['mode']})")
    print(f"Accent:   {theme['accent']}")
    print(f"Slides:   {len(slides)}")
    print("Gemini:   0")
    print("=" * 72)

    render_html_files(story, out_dir, template, theme_name, theme, evidence)
    render_pngs(out_dir, len(slides))
    write_metadata(story, out_dir, created_at, RETENTION_DAYS, template, theme_name, theme)

    print("✓ Carousel generated")
    print(f"✓ Output: {out_dir}")
    print("✓ Ready for approval")


if __name__ == "__main__":
    main()
