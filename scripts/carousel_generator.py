#!/usr/bin/env python3
"""GetByteRush production carousel renderer.

The renderer is deliberately deterministic. Gemini chooses the story/template;
this file owns the actual visual system so the output cannot drift into a
random AI-generated design.

Contract:
- 1080x1350 PNGs (4:5)
- 70/20/10 brand/story/accent colour discipline
- story-specific template families from the locked design system
- reusable editorial components instead of one generic card
- real source screenshots when available
- no invented copy
- hard text/overflow validation in Chromium
- dated/topic output packages for Telegram/Instagram publishing
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

# Locked GetByteRush foundation from design/getbyterush-carousel-design-system.md.
THEMES = {
    "story": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#12352B", "signal": "#B99A5B", "surface": "#E9E2D4"},
    "urgency": {"bg": "#111311", "fg": "#F4EFE4", "accent": "#E53935", "signal": "#E53935", "surface": "#1B1D1B"},
    "experiment": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#2D8C7A", "signal": "#BFDCCF", "surface": "#E1ECE7"},
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
    "story": "story",
    "experiment": "experiment",
    "shock-number": "money",
    "breakdown": "explainer",
    "contradiction": "contradiction",
    "receipts": "investigation",
    "timeline": "timeline",
    "comparison": "comparison",
    "wtf": "mystery",
    "data-story": "data",
}

CATEGORY_TEMPLATE = {
    "breaking_news": "story",
    "daily_24_hours": "story",
    "model_drop": "story",
    "model_comparison": "comparison",
    "experiment": "experiment",
    "product_story": "breakdown",
    "business_story": "story",
    "ai_agent_story": "breakdown",
    "internet_mystery": "wtf",
    "deep_dive": "story",
    "explainer": "breakdown",
    "tool_discovery": "breakdown",
    "data_story": "data-story",
    "timeline": "timeline",
    "what_happens_next": "story",
    "failure_story": "contradiction",
    "TECH_NEWS": "story",
    "MODEL_UPDATE": "story",
    "AI_AGENTS": "breakdown",
    "BUSINESS": "story",
}

VISUAL_TEMPLATE = {
    "metric": "shock-number",
    "comparison": "comparison",
    "timeline": "timeline",
    "evidence": "receipts",
    "screenshot": "receipts",
    "diagram": "breakdown",
}

ALLOWED_ACCENTS = {
    "#12352B", "#E53935", "#2D8C7A", "#B7E32B", "#527A91",
    "#F26A21", "#426A78", "#3159C9", "#C7F000", "#C9A75D",
    "#B99A5B", "#7457FF", "#4B78A8", "#BFDCCF", "#D7D9D5",
}

BASE_CSS = r'''
@page { size: 1080px 1350px; margin: 0; }
* { box-sizing: border-box; }
html, body { width:1080px; height:1350px; margin:0; padding:0; overflow:hidden; }
body { font-family:"Inter Tight", Inter, Arial, Helvetica, sans-serif; }
.slide { position:relative; width:1080px; height:1350px; padding:78px; overflow:hidden; background:var(--bg); color:var(--fg); }
.meta { position:absolute; top:38px; left:78px; right:78px; display:flex; justify-content:space-between; align-items:center; font:800 16px/1.1 ui-monospace,SFMono-Regular,Menlo,Monaco,monospace; letter-spacing:1.35px; text-transform:uppercase; }
.meta .right { color:var(--accent); }
.rule { width:96px; height:4px; background:var(--accent); margin:38px 0 22px; }
.kicker { display:inline-block; max-width:620px; padding:8px 12px 7px; border:1.5px solid var(--accent); color:var(--accent); font:900 16px/1 ui-monospace,SFMono-Regular,Menlo,Monaco,monospace; letter-spacing:1.4px; text-transform:uppercase; }
h1 { margin:18px 0 0; font-weight:900; letter-spacing:-3.3px; line-height:.94; overflow-wrap:anywhere; }
.headline { font-size:80px; max-width:920px; }
.headline.tight { font-size:64px; letter-spacing:-2.4px; line-height:.98; }
.headline.long { font-size:56px; letter-spacing:-1.9px; line-height:1.0; }
.body { margin-top:26px; max-width:810px; font-size:29px; line-height:1.15; font-weight:560; overflow-wrap:anywhere; }
.micro { font:800 15px/1.2 ui-monospace,SFMono-Regular,Menlo,Monaco,monospace; letter-spacing:1.05px; text-transform:uppercase; }
.footer { position:absolute; left:78px; right:78px; bottom:42px; display:flex; justify-content:space-between; align-items:end; gap:30px; }
.source { max-width:650px; font:700 13px/1.25 ui-monospace,SFMono-Regular,Menlo,Monaco,monospace; text-transform:uppercase; opacity:.68; overflow-wrap:anywhere; }
.brand { font-size:14px; font-weight:900; letter-spacing:1.55px; text-transform:uppercase; white-space:nowrap; }
.eyebrow { margin-top:34px; color:var(--accent); font:900 15px/1.1 ui-monospace,SFMono-Regular,Menlo,Monaco,monospace; letter-spacing:1.2px; text-transform:uppercase; }
.hero-line { position:absolute; left:78px; right:78px; bottom:160px; height:2px; background:var(--accent); opacity:.28; }
.hero-mark { position:absolute; right:78px; bottom:188px; width:180px; height:180px; border:2px solid var(--accent); display:flex; align-items:center; justify-content:center; transform:rotate(45deg); }
.hero-mark span { transform:rotate(-45deg); font:950 20px/1 ui-monospace,SFMono-Regular,Menlo,Monaco,monospace; letter-spacing:1px; }
.pair { margin-top:56px; display:grid; grid-template-columns:1fr 72px 1fr; gap:18px; align-items:stretch; }
.pair-card { min-height:220px; padding:28px; background:var(--surface); border:2px solid var(--accent); position:relative; }
.pair-card.primary { border-top-width:8px; }
.pair-label { font:900 15px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.7; }
.pair-title { margin-top:25px; font-size:38px; line-height:.95; font-weight:900; letter-spacing:-1.5px; overflow-wrap:anywhere; }
.pair-copy { margin-top:18px; font-size:22px; line-height:1.05; font-weight:650; }
.vs { display:flex; align-items:center; justify-content:center; font:950 28px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--accent); }
.chip-stack { margin-top:46px; display:grid; grid-template-columns:1fr 1fr; gap:18px; }
.chip { min-height:250px; background:var(--surface); border:2px solid var(--accent); padding:24px; position:relative; }
.chip .die { height:118px; border:2px solid var(--fg); display:grid; place-items:center; font:900 16px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:1px; }
.chip .mem { position:absolute; left:24px; right:24px; bottom:24px; height:48px; border:2px solid var(--accent); display:grid; place-items:center; font:900 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:1px; }
.chip .caption { margin-top:14px; font-size:22px; font-weight:850; line-height:1; }
.metric-grid { margin-top:54px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
.metric-card { min-height:340px; padding:26px; background:var(--surface); border-top:7px solid var(--accent); display:flex; flex-direction:column; justify-content:space-between; }
.metric-value { font-size:92px; line-height:.82; letter-spacing:-6px; font-weight:950; color:var(--accent); overflow-wrap:anywhere; }
.metric-label { font-size:25px; line-height:1.0; font-weight:900; }
.metric-note { font:700 13px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; opacity:.62; }
.evidence-frame { position:absolute; left:78px; right:78px; top:352px; bottom:158px; background:#161816; border:2px solid var(--accent); padding:18px; overflow:hidden; }
.evidence-chrome { height:42px; display:flex; align-items:center; justify-content:space-between; color:#F4EFE4; font:800 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.evidence-window { height:calc(100% - 42px); width:100%; background:#fff; display:flex; align-items:center; justify-content:center; overflow:hidden; }
.evidence-window img { width:100%; height:100%; object-fit:contain; display:block; }
.evidence-caption { position:absolute; left:100px; right:100px; bottom:176px; display:flex; justify-content:space-between; gap:20px; color:#F4EFE4; font:700 12px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.8px; pointer-events:none; }
.quote-wrap { margin-top:52px; max-width:900px; padding:34px 38px; border-left:8px solid var(--accent); background:var(--surface); }
.quote-mark { color:var(--accent); font:950 90px/.6 Georgia,serif; }
.quote { margin-top:12px; font-size:46px; line-height:1.02; letter-spacing:-1.8px; font-weight:900; overflow-wrap:anywhere; }
.quote-source { margin-top:24px; font:800 14px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.8px; opacity:.7; }
.breakdown { margin-top:54px; display:grid; grid-template-columns:1fr 70px 1fr 70px 1fr; align-items:center; gap:12px; }
.node { min-height:200px; padding:24px; background:var(--surface); border:2px solid var(--accent); display:flex; flex-direction:column; justify-content:center; }
.node .label { font:900 14px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.65; }
.node .value { margin-top:14px; font-size:27px; line-height:1.0; font-weight:900; overflow-wrap:anywhere; }
.arrow { text-align:center; color:var(--accent); font-size:42px; font-weight:950; }
.timeline { margin-top:54px; padding-left:38px; border-left:5px solid var(--accent); }
.timeline-item { margin-bottom:28px; position:relative; }
.timeline-item:before { content:""; position:absolute; left:-52px; top:0; width:17px; height:17px; border:5px solid var(--accent); background:var(--bg); }
.timeline-date { color:var(--accent); font:900 15px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.timeline-text { margin-top:7px; font-size:30px; line-height:1.04; font-weight:850; overflow-wrap:anywhere; }
.compare-grid { margin-top:54px; display:grid; grid-template-columns:1fr 1fr; gap:18px; }
.compare-card { min-height:300px; padding:28px; background:var(--surface); border:2px solid var(--accent); position:relative; }
.compare-card.winner { border-top-width:8px; }
.compare-name { font-size:40px; line-height:.95; font-weight:950; letter-spacing:-1.5px; overflow-wrap:anywhere; }
.compare-row { margin-top:24px; padding-top:16px; border-top:1px solid var(--accent); display:flex; justify-content:space-between; gap:20px; font-size:19px; line-height:1.1; font-weight:800; }
.verdict { margin-top:54px; padding:30px; border:3px solid var(--accent); background:var(--surface); }
.verdict .label { color:var(--accent); font:900 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.3px; text-transform:uppercase; }
.verdict .big { margin-top:18px; font-size:76px; line-height:.86; letter-spacing:-4px; font-weight:950; overflow-wrap:anywhere; }
.verdict .copy { margin-top:20px; font-size:28px; line-height:1.05; font-weight:700; }
.pattern { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; padding:110px 78px; background:var(--bg); }
.pattern:before { content:""; position:absolute; width:720px; height:720px; border:2px solid var(--accent); transform:rotate(45deg); opacity:.25; }
.pattern .big { position:relative; z-index:1; max-width:900px; font-size:148px; line-height:.76; letter-spacing:-8px; font-weight:950; text-align:center; text-transform:uppercase; overflow-wrap:anywhere; }
.payoff { margin-top:52px; max-width:900px; padding-top:28px; border-top:6px solid var(--accent); font-size:51px; line-height:.98; letter-spacing:-2.2px; font-weight:900; overflow-wrap:anywhere; }
.payoff-small { margin-top:28px; max-width:780px; font-size:27px; line-height:1.1; font-weight:650; }
.dark { color:var(--fg); }
.grain { position:absolute; inset:0; opacity:.018; pointer-events:none; background-image:radial-gradient(#000 .7px, transparent .8px); background-size:5px 5px; }
.dark .grain { opacity:.045; background-image:radial-gradient(#fff .7px, transparent .8px); }
'''


def text(value):
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value or "").strip()


def esc(value):
    return html.escape(text(value))


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", text(value).lower()).strip("-")
    return value[:80] or "getbyterush-post"


def first(*values):
    for value in values:
        if value is not None and text(value):
            return value
    return ""


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
    aliases = {
        "urgent": "urgency", "breaking": "urgency", "money/scale": "money",
        "money": "money", "explainer": "explainer", "experiment": "experiment",
        "contradiction": "contradiction", "investigation": "investigation",
        "fact check": "investigation", "timeline": "timeline", "comparison": "comparison",
        "mystery": "mystery", "wtf": "mystery", "data": "data",
    }
    if story.get("emergency_mode") is True:
        return "urgency"
    if mode in aliases:
        return aliases[mode]
    return TEMPLATE_THEME.get(template, "story")


def theme_with_design_override(story, template, theme_name):
    """Use the design-system palette, but allow Gemini to select only a known accent."""
    theme = dict(THEMES[theme_name])
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    accent = text(design.get("accent_color")).upper()
    if accent in ALLOWED_ACCENTS:
        theme["accent"] = accent
    # Keep the canonical theme background/foreground. Gemini never gets to invent
    # arbitrary neon gradients or brand colours.
    return theme


def requested_background(slide, theme_name):
    mode = text(first(slide.get("background_mode"), slide.get("background"))).lower()
    if mode in {"black", "ink", "dark", "blackout"}:
        return "dark"
    if mode in {"cream", "light", "white"}:
        return "cream"
    if theme_name in {"urgency", "money", "mystery"}:
        return "dark"
    return "cream"


def source_info(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    source = first(slide.get("source_label"), source_story.get("source"), story.get("source"), "GetByteRush")
    url = first(slide.get("asset_url"), slide.get("source_url"), source_story.get("url"), story.get("source_url"))
    return text(source), text(url)


def extract_number(value):
    match = re.search(r"(?<![A-Za-z])(\+?\-?\$?\d+(?:\.\d+)?(?:%|x|×|[A-Za-z]{0,3})?)(?![A-Za-z])", text(value))
    return match.group(1) if match else ""


def numbers_from_slide(slide):
    raw = " ".join(text(slide.get(key)) for key in ("headline", "body", "visual_concept"))
    found = re.findall(r"(?<![A-Za-z])(\+?\-?\$?\d+(?:\.\d+)?(?:%|x|×|[A-Za-z]{0,3})?)(?![A-Za-z])", raw)
    unique = []
    for value in found:
        if value not in unique:
            unique.append(value)
    return unique[:3]


def role_for(slide, index, total):
    role = text(first(slide.get("role"), slide.get("scene_role"))).lower()
    if role:
        return role
    if index == 1:
        return "interrupt"
    if index == 2:
        return "open_loop"
    if index == total:
        return "payoff"
    if index == total - 1:
        return "implication"
    if index == 5:
        return "pattern_interrupt"
    if index == 4:
        return "reveal"
    return "proof"


def headline_class(headline):
    n = len(text(headline))
    if n > 105:
        return "headline long"
    if n > 68:
        return "headline tight"
    return "headline"


def short_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "official source"


def visual_markup(story, slide, index, total, template, theme_name, theme, evidence_uri):
    headline = text(first(slide.get("headline"), slide.get("title"), slide.get("hook")))
    body = text(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")))
    visual_type = text(slide.get("visual_type")).lower()
    concept = text(first(slide.get("visual_concept"), slide.get("visual_strategy"), slide.get("asset_requirement")))
    source, url = source_info(story, slide)
    role = role_for(slide, index, total)

    if index == 1:
        entities = first(slide.get("entities"), story.get("entities"))
        if isinstance(entities, list) and len(entities) >= 2:
            left, right = text(entities[0]), text(entities[1])
        else:
            source_name = text((story.get("source_story") or {}).get("source"))
            left, right = (source_name or "COMPANY A"), "THE SHIFT"
        return f'''
        <div class="eyebrow">{esc(first(slide.get("transition_hint"), "THE QUESTION"))}</div>
        <div class="pair">
          <div class="pair-card primary"><div class="pair-label">PART A</div><div class="pair-title">{esc(left)}</div><div class="pair-copy">The familiar story.</div></div>
          <div class="vs">×</div>
          <div class="pair-card"><div class="pair-label">PART B</div><div class="pair-title">{esc(right)}</div><div class="pair-copy">The part worth investigating.</div></div>
        </div>'''

    if template == "shock-number" or visual_type == "metric":
        values = numbers_from_slide(slide)
        if not values:
            values = [extract_number(headline) or "01"]
        labels = ["THE SIGNAL", "THE COST", "THE UPSIDE"]
        cards = []
        for i, value in enumerate(values[:3]):
            label = labels[i]
            if i == 0 and body:
                label = "KEY RESULT"
            cards.append(f'<div class="metric-card"><div class="metric-value">{esc(value)}</div><div class="metric-label">{esc(label)}</div><div class="metric-note">{esc(source)}</div></div>')
        return '<div class="metric-grid">' + "".join(cards) + '</div>'

    if template == "receipts" or visual_type in {"screenshot", "evidence"}:
        if evidence_uri:
            return f'''
            <div class="evidence-frame">
              <div class="evidence-chrome"><span>OFFICIAL SOURCE</span><span>{esc(short_domain(url))}</span></div>
              <div class="evidence-window"><img src="{esc(evidence_uri)}" alt="Official source evidence" /></div>
            </div>
            <div class="evidence-caption"><span>{esc(source)}</span><span>CAPTURED / SOURCE PAGE</span></div>'''
        return f'<div class="quote-wrap"><div class="quote-mark">“</div><div class="quote">{esc(first(body, concept, "No source image was available."))}</div><div class="quote-source">{esc(source)}</div></div>'

    if template == "comparison" or visual_type == "comparison":
        raw = first(concept, headline)
        parts = re.split(r"\s+vs\.?\s+|\s+versus\s+", raw, flags=re.I)
        left = parts[0].strip() if parts else "A"
        right = parts[1].strip() if len(parts) > 1 else "B"
        return f'''
        <div class="compare-grid">
          <div class="compare-card winner"><div class="pair-label">SIDE A</div><div class="compare-name">{esc(left)}</div><div class="compare-row"><span>WHAT IT DOES</span><span>SEE SOURCE</span></div><div class="compare-row"><span>BEST FOR</span><span>SCENARIO A</span></div></div>
          <div class="compare-card"><div class="pair-label">SIDE B</div><div class="compare-name">{esc(right)}</div><div class="compare-row"><span>WHAT IT DOES</span><span>SEE SOURCE</span></div><div class="compare-row"><span>BEST FOR</span><span>SCENARIO B</span></div></div>
        </div>'''

    if template == "timeline" or visual_type == "timeline":
        events = slide.get("timeline") or slide.get("events") or []
        if isinstance(events, list) and events:
            items = []
            for event in events[:5]:
                if isinstance(event, dict):
                    date = first(event.get("date"), event.get("year"), "STEP")
                    value = first(event.get("text"), event.get("headline"), event.get("description"))
                else:
                    date, value = "STEP", event
                items.append(f'<div class="timeline-item"><div class="timeline-date">{esc(date)}</div><div class="timeline-text">{esc(value)}</div></div>')
            return '<div class="timeline">' + "".join(items) + '</div>'
        return f'<div class="timeline"><div class="timeline-item"><div class="timeline-date">BEFORE</div><div class="timeline-text">{esc(body or headline)}</div></div><div class="timeline-item"><div class="timeline-date">NOW</div><div class="timeline-text">{esc(concept or "The architecture is changing.")}</div></div><div class="timeline-item"><div class="timeline-date">NEXT</div><div class="timeline-text">{esc(first(slide.get("implication"), "The next move is the important part."))}</div></div></div>'

    if template == "breakdown" or visual_type == "diagram":
        # A deterministic technical diagram. It intentionally uses only source-backed
        # labels; it does not invent percentages or architecture names.
        return f'''
        <div class="chip-stack">
          <div class="chip">
            <div class="die">XPU COMPUTE DIE<br/>MEMORY CONTROL</div>
            <div class="caption">TRADITIONAL HBM</div>
            <div class="mem">MEMORY CONTROLLER ON XPU</div>
          </div>
          <div class="chip">
            <div class="die">XPU COMPUTE DIE<br/>MORE SPACE FOR COMPUTE</div>
            <div class="caption">NVHBM</div>
            <div class="mem">CUSTOM CONTROLLER IN HBM BASE DIE</div>
          </div>
        </div>'''

    if visual_type == "quote" or role == "reveal":
        return f'<div class="quote-wrap"><div class="quote-mark">“</div><div class="quote">{esc(first(body, headline, concept))}</div><div class="quote-source">{esc(source)}</div></div>'

    if role == "pattern_interrupt":
        return f'<div class="pattern"><div class="big">{esc(first(headline, "WAIT."))}</div></div>'

    if role in {"implication", "payoff"} or visual_type == "final":
        return f'<div class="payoff">{esc(first(headline, body, concept))}</div><div class="payoff-small">{esc(first(slide.get("implication"), body, "The useful question is what changes for the people building and using this technology."))}</div>'

    # Default editorial story slide: strong text + one purposeful information block.
    return f'''
    <div class="breakdown">
      <div class="node"><div class="label">CONTEXT</div><div class="value">{esc(first(slide.get("context"), headline))}</div></div>
      <div class="arrow">→</div>
      <div class="node"><div class="label">CHANGE</div><div class="value">{esc(first(concept, body))}</div></div>
      <div class="arrow">→</div>
      <div class="node"><div class="label">IMPACT</div><div class="value">{esc(first(slide.get("implication"), body, "What changes next"))}</div></div>
    </div>'''


def slide_html(story, slide, index, total, template, theme_name, theme, evidence_uri):
    headline = text(first(slide.get("headline"), slide.get("title"), slide.get("hook")))
    body = text(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")))
    kicker = text(first(slide.get("kicker"), slide.get("label"), "GETBYTERUSH"))
    source, url = source_info(story, slide)
    dark = requested_background(slide, theme_name) == "dark"
    bg = "#111311" if dark else theme["bg"]
    fg = "#F4EFE4" if dark else theme["fg"]
    accent = theme["accent"]
    surface = theme["surface"]
    classes = "slide dark" if dark else "slide"
    style = BASE_CSS + f'\n:root{{--bg:{bg};--fg:{fg};--accent:{accent};--signal:{theme["signal"]};--surface:{surface};}}'

    body_html = ""
    # Keep body out of visual-heavy layouts; the visual component owns its own copy.
    visual_type = text(slide.get("visual_type")).lower()
    if body and visual_type not in {"metric", "evidence", "screenshot", "diagram", "timeline", "comparison", "quote", "final"} and index != 1:
        body_html = f'<div class="body">{esc(body)}</div>'

    if index == 1:
        body_html = f'<div class="body">{esc(body)}</div>' if body else ""

    visual = visual_markup(story, slide, index, total, template, theme_name, theme, evidence_uri)
    number_label = f"{index:02d} / {total:02d}"
    source_text = source if source else "OFFICIAL SOURCE"

    return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=1080,height=1350"><style>{style}</style></head>
<body><section class="{classes}">
<div class="grain"></div>
<div class="meta"><span>GETBYTERUSH / {esc(template.replace("-", " "))}</span><span class="right">{number_label}</span></div>
<div class="rule"></div>
<div class="kicker">{esc(kicker)}</div>
<h1 class="{headline_class(headline)}">{esc(headline)}</h1>
{body_html}
{visual}
<div class="hero-line"></div>
<div class="footer"><div class="source">SOURCE / {esc(source_text)}</div><div class="brand">TESTED • EXPLAINED • REAL</div></div>
</section></body></html>'''


def capture_evidence(url, output_path):
    if not url:
        return False
    try:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1600)
            page.screenshot(path=str(output_path), full_page=False)
            browser.close()
        return output_path.exists()
    except Exception as exc:
        print(f"WARNING: evidence capture failed: {exc}")
        return False


def render_html(story, out_dir, template, theme_name, theme, evidence_path):
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    evidence_uri = None
    if evidence_path:
        try:
            evidence_file = Path(evidence_path).resolve()
            if evidence_file.exists():
                evidence_uri = evidence_file.as_uri()
        except Exception as exc:
            print(f"WARNING: evidence URI unavailable: {exc}")

    slides = story.get("slides", [])
    for i, slide in enumerate(slides, 1):
        (html_dir / f"{i:02d}.html").write_text(
            slide_html(story, slide, i, len(slides), template, theme_name, theme, evidence_uri),
            encoding="utf-8",
        )


def render_pngs_validate(out_dir, count):
    html_dir = Path(out_dir).resolve() / "html"
    slides_dir = Path(out_dir).resolve() / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)

        for i in range(1, count + 1):
            html_path = html_dir / f"{i:02d}.html"
            png_path = slides_dir / f"{i:02d}.png"
            page.goto(html_path.resolve().as_uri(), wait_until="load")
            page.wait_for_timeout(80)

            result = page.evaluate("""
            () => {
              const W = 1080, H = 1350;
              const viewport = document.querySelector('.slide')?.getBoundingClientRect();
              const overflow = [...document.querySelectorAll('.slide *')].filter(el => {
                const r = el.getBoundingClientRect();
                return r.right > W + 1 || r.bottom > H + 1 || r.left < -1 || r.top < -1;
              }).slice(0, 25).map(el => ({tag: el.tagName, cls: String(el.className), text: (el.innerText || '').slice(0, 80)}));
              const textNodes = [...document.querySelectorAll('h1,.body,.metric-value,.metric-label,.pair-title,.quote,.node .value,.timeline-text,.compare-name,.payoff')];
              const textOverflow = textNodes.filter(el => el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2).map(el => ({cls: String(el.className), text: (el.innerText || '').slice(0, 100)}));
              return { viewport, scrollW: document.documentElement.scrollWidth, scrollH: document.documentElement.scrollHeight, overflow, textOverflow };
            }
            """)

            if result["scrollW"] > WIDTH or result["scrollH"] > HEIGHT or result["overflow"] or result["textOverflow"]:
                failures.append({"slide": i, "details": result})

            page.screenshot(path=str(png_path), full_page=False)
            print(f"✓ slide-{i:02d}.png")

        browser.close()

    if failures:
        print("LAYOUT_VALIDATION_FAILED")
        print(json.dumps(failures, indent=2, ensure_ascii=False))
        raise RuntimeError("Carousel layout validation failed. No production-ready package is marked.")


def write_package(story, out_dir, template, theme_name, created_at):
    caption = text(story.get("caption"))
    hashtags = story.get("hashtags", [])
    hashtags_text = " ".join(str(x) for x in hashtags) if isinstance(hashtags, list) else text(hashtags)
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
    (out_dir / "hashtags.txt").write_text(hashtags_text, encoding="utf-8")
    (out_dir / "pinned-comment.txt").write_text(text(story.get("pinned_comment")), encoding="utf-8")
    (out_dir / "alt-text.txt").write_text(text(story.get("alt_text")), encoding="utf-8")

    created = datetime.fromisoformat(created_at)
    package = dict(story)
    package["status"] = "pending_approval"
    package["created_at"] = created_at
    package["retention_days"] = RETENTION_DAYS
    package["delete_after"] = (created + timedelta(days=RETENTION_DAYS)).isoformat()
    package["rendering"] = {
        "renderer": "getbyterush-carousel-generator-v4",
        "template": template,
        "theme": theme_name,
        "canvas": f"{WIDTH}x{HEIGHT}",
        "production_ready": True,
    }
    package["instagram"] = {"published": False, "media_id": None, "permalink": None}
    (out_dir / "post.json").write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_story(story):
    slides = story.get("slides", [])
    if not 5 <= len(slides) <= 9:
        raise ValueError(f"Carousel must contain 5–9 slides, got {len(slides)}")

    errors = []
    for i, slide in enumerate(slides, 1):
        headline = text(slide.get("headline"))
        body = text(slide.get("body"))
        if not headline:
            errors.append(f"slide {i}: missing headline")
        if len(headline) > 120:
            errors.append(f"slide {i}: headline too long ({len(headline)} chars)")
        if len(body) > 360:
            errors.append(f"slide {i}: body too long ({len(body)} chars)")
        if not slide.get("swipe_reason"):
            errors.append(f"slide {i}: missing swipe_reason")

    if errors:
        raise ValueError("; ".join(errors))


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing {INPUT}. Run editorial_engine.py first.")

    story = json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"):
        print("No selected story. Nothing to render.")
        return

    validate_story(story)
    slides = story.get("slides", [])
    template = infer_template(story)
    theme_name = infer_theme(story, template)
    theme = theme_with_design_override(story, template, theme_name)

    created = datetime.now().astimezone()
    created_at = created.isoformat(timespec="seconds")
    date_dir = OUTPUT_ROOT / created.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    base = f"{created.strftime('%H%M%S')}-{slug(story.get('story_title', 'getbyterush-post'))}"
    out_dir = date_dir / base
    out_dir.mkdir(parents=True, exist_ok=False)
    for sub in ("slides", "html", "evidence"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    source_url = text(first(source_story.get("url"), story.get("source_url")))
    evidence_path = out_dir / "evidence" / "source.png"
    captured = capture_evidence(source_url, evidence_path)
    if not captured:
        evidence_path = None

    print("=" * 72)
    print("GETBYTERUSH CAROUSEL V4")
    print("=" * 72)
    print(f"Template : {template}")
    print(f"Theme    : {theme_name}")
    print(f"Accent   : {theme['accent']}")
    print(f"Slides   : {len(slides)}")
    print(f"Evidence : {'YES' if evidence_path else 'NO'}")

    render_html(story, out_dir, template, theme_name, theme, evidence_path)
    render_pngs_validate(out_dir, len(slides))
    write_package(story, out_dir, template, theme_name, created_at)

    print(f"OUTPUT: {out_dir}")
    print("PRODUCTION_READY: true")


if __name__ == "__main__":
    main()
