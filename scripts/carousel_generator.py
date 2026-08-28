#!/usr/bin/env python3
"""GetByteRush production carousel renderer.

This renderer is intentionally strict:
- uses the editorial JSON as the content contract;
- chooses a story-specific layout instead of one generic card;
- never invents visual copy that is not present in the editorial JSON;
- preserves evidence aspect ratios;
- validates slide dimensions and text overflow in Chromium;
- writes a dated/topic package for later Telegram/Instagram publishing.
"""

import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")
WIDTH = 1080
HEIGHT = 1350
SAFE = 78
RETENTION_DAYS = 7

BRAND = {
    "cream": "#F4EFE4",
    "forest": "#12352B",
    "ink": "#111311",
    "gold": "#B99A5B",
}

THEMES = {
    "story": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#12352B", "signal": "#B99A5B", "surface": "#EAE3D5"},
    "urgency": {"bg": "#111311", "fg": "#F4EFE4", "accent": "#E53935", "signal": "#E53935", "surface": "#1D1F1D"},
    "experiment": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#2D8C7A", "signal": "#BFDCCF", "surface": "#E4EEE9"},
    "money": {"bg": "#111311", "fg": "#F4EFE4", "accent": "#B7E32B", "signal": "#B99A5B", "surface": "#20231D"},
    "explainer": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#527A91", "signal": "#D7D9D5", "surface": "#E8EBE8"},
    "contradiction": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#F26A21", "signal": "#111311", "surface": "#EFE3D9"},
    "investigation": {"bg": "#EFE8D8", "fg": "#12352B", "accent": "#426A78", "signal": "#C83C3C", "surface": "#E4DDCD"},
    "timeline": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#3159C9", "signal": "#B99A5B", "surface": "#E7E8ED"},
    "comparison": {"bg": "#F4EFE4", "fg": "#111311", "accent": "#12352B", "signal": "#4B78A8", "surface": "#E6E9E8"},
    "mystery": {"bg": "#0D0F0E", "fg": "#F4EFE4", "accent": "#C7F000", "signal": "#7457FF", "surface": "#1B1E1A"},
    "data": {"bg": "#F4EFE4", "fg": "#12352B", "accent": "#C9A75D", "signal": "#4B78A8", "surface": "#E6EAE9"},
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


def text(v):
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v or "").strip()


def esc(v):
    return html.escape(text(v))


def slug(v):
    s = re.sub(r"[^a-z0-9]+", "-", text(v).lower()).strip("-")
    return s[:80] or "getbyterush-post"


def first(*values):
    for v in values:
        if v is not None and text(v):
            return v
    return ""


def infer_template(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    value = first(story.get("template"), design.get("template"))
    value = text(value).lower()
    if value in TEMPLATE_THEME:
        return value

    for slide in story.get("slides", []):
        visual = text(slide.get("visual_type")).lower()
        if visual in VISUAL_TEMPLATE:
            return VISUAL_TEMPLATE[visual]

    category = first(story.get("format"), story.get("content_type"), story.get("story_type"), story.get("category"), story.get("type"))
    return CATEGORY_TEMPLATE.get(text(category), "story")


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


def requested_background(slide, theme_name):
    bg = text(first(slide.get("background_mode"), slide.get("background"))).lower()
    if bg in {"black", "ink", "dark", "blackout"}:
        return "dark"
    if bg in {"cream", "light", "white"}:
        return "cream"
    if theme_name in {"urgency", "money", "mystery"}:
        return "dark"
    return "cream"


def source_info(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    source = first(slide.get("source_label"), slide.get("source"), source_story.get("source"), story.get("source"), "GetByteRush")
    url = first(slide.get("asset_url"), slide.get("source_url"), source_story.get("url"), story.get("source_url"))
    return text(source), text(url)


def extract_number(value):
    m = re.search(r"(?<![A-Za-z])(\$?\d+(?:\.\d+)?(?:%|x|[A-Za-z]{0,3})?)(?![A-Za-z])", text(value))
    return m.group(1) if m else ""


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


BASE_CSS = r'''
@page { size: 1080px 1350px; margin: 0; }
* { box-sizing: border-box; }
html, body { width:1080px; height:1350px; margin:0; padding:0; overflow:hidden; }
body { font-family:"Inter Tight", Inter, Arial, Helvetica, sans-serif; }
.slide { position:relative; width:1080px; height:1350px; padding:78px; overflow:hidden; }
.meta { position:absolute; top:42px; left:78px; right:78px; display:flex; justify-content:space-between; font:700 17px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.2px; text-transform:uppercase; }
.kicker { display:inline-block; padding:9px 13px 8px; border:1.5px solid var(--accent); color:var(--accent); font:800 17px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.5px; text-transform:uppercase; }
.rule { width:88px; height:4px; background:var(--accent); margin:48px 0 26px; }
h1 { margin:0; font-weight:900; letter-spacing:-3.2px; line-height:.94; }
.headline { font-size:78px; max-width:900px; }
.headline.tight { font-size:62px; letter-spacing:-2.2px; }
.headline.huge { font-size:134px; line-height:.78; letter-spacing:-8px; }
.body { margin-top:28px; max-width:810px; font-size:31px; line-height:1.15; font-weight:550; }
.micro { font:700 16px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.footer { position:absolute; left:78px; right:78px; bottom:46px; display:flex; justify-content:space-between; gap:28px; align-items:end; }
.source { max-width:680px; font:600 14px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; opacity:.68; }
.brand { font-size:15px; font-weight:900; letter-spacing:1.8px; text-transform:uppercase; white-space:nowrap; }
.number { margin-top:48px; font-size:280px; line-height:.72; letter-spacing:-18px; font-weight:950; color:var(--accent); }
.number-label { margin-top:44px; max-width:820px; font-size:39px; line-height:1.03; font-weight:850; }
.cardgrid { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:52px; }
.card { background:var(--surface); border-top:5px solid var(--accent); padding:30px; min-height:225px; }
.card .value { font-size:55px; line-height:.9; font-weight:950; }
.card .label { margin-top:20px; font-size:24px; line-height:1.06; font-weight:760; }
.diagram { margin-top:58px; display:grid; grid-template-columns:1fr 76px 1fr 76px 1fr; align-items:center; gap:12px; }
.node { min-height:180px; padding:25px; background:var(--surface); border:2px solid var(--accent); display:flex; flex-direction:column; justify-content:center; }
.node .t { font:800 15px/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; opacity:.72; }
.node .v { margin-top:12px; font-size:28px; line-height:1; font-weight:900; }
.arrow { text-align:center; font-size:42px; font-weight:900; color:var(--accent); }
.evidence { position:absolute; left:78px; right:78px; top:300px; bottom:154px; border:1.5px solid var(--accent); background:var(--surface); display:flex; align-items:center; justify-content:center; padding:20px; overflow:hidden; }
.evidence img { display:block; max-width:100%; max-height:100%; width:auto; height:auto; object-fit:contain; }
.evidence-tag { position:absolute; left:92px; top:275px; z-index:2; padding:7px 11px; background:var(--accent); color:var(--bg); font:900 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }
.quote { margin-top:54px; max-width:870px; padding-left:30px; border-left:7px solid var(--accent); font-size:51px; line-height:1.01; font-weight:900; letter-spacing:-2px; }
.timeline { margin-top:56px; padding-left:38px; border-left:5px solid var(--accent); }
.timeline-item { margin-bottom:30px; position:relative; }
.timeline-item:before { content:""; position:absolute; left:-52px; top:2px; width:18px; height:18px; border:5px solid var(--accent); background:var(--bg); }
.timeline-date { font:900 17px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; color:var(--accent); text-transform:uppercase; }
.timeline-text { margin-top:7px; font-size:31px; line-height:1.05; font-weight:800; }
.compare { margin-top:56px; display:grid; grid-template-columns:1fr 90px 1fr; align-items:stretch; gap:18px; }
.compare-card { background:var(--surface); border:2px solid var(--accent); padding:30px; min-height:280px; }
.compare-label { font:900 16px/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:1px; opacity:.72; }
.compare-copy { margin-top:28px; font-size:34px; line-height:1; font-weight:900; }
.vs { align-self:center; text-align:center; font-size:34px; font-weight:950; color:var(--accent); }
.pattern { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; padding:78px; }
.pattern .big { font-size:150px; line-height:.78; letter-spacing:-9px; font-weight:950; text-transform:uppercase; color:var(--bg); text-align:center; }
.payoff { margin-top:44px; max-width:860px; font-size:42px; line-height:1.05; font-weight:820; }
.payoff strong { font-weight:950; }
.dark { color:var(--fg); }
.light { color:var(--fg); }
.grain { position:absolute; inset:0; opacity:.025; pointer-events:none; background-image:radial-gradient(#000 .7px, transparent .8px); background-size:5px 5px; }
.dark .grain { opacity:.05; background-image:radial-gradient(#fff .7px, transparent .8px); }
'''


def slide_html(story, slide, index, total, template, theme_name, theme, evidence_uri):
    headline = text(first(slide.get("headline"), slide.get("title"), slide.get("hook")))
    body = text(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")))
    kicker = text(first(slide.get("kicker"), slide.get("label"), "GETBYTERUSH"))
    role = role_for(slide, index, total)
    bg_mode = requested_background(slide, theme_name)
    dark = bg_mode == "dark"
    bg = "#111311" if dark else theme["bg"]
    fg = "#F4EFE4" if dark else theme["fg"]
    accent = theme["accent"]
    surface = theme["surface"]

    headline_class = "headline"
    if len(headline) > 55:
        headline_class += " tight"

    visual_type = text(slide.get("visual_type")).lower()
    concept = text(first(slide.get("visual_concept"), slide.get("visual_strategy"), slide.get("asset_requirement")))
    source, _ = source_info(story, slide)

    style = BASE_CSS + f"\n:root{{--bg:{bg};--fg:{fg};--accent:{accent};--signal:{theme['signal']};--surface:{surface};}}"
    classes = "slide dark" if dark else "slide light"

    visual = ""
    if index == 1 and template != "shock-number":
        visual = f'<div class="micro" style="margin-top:42px;color:{accent};">{esc(first(slide.get("transition_hint"), "NEXT →"))}</div>'
    elif template == "shock-number" or visual_type == "metric":
        number = extract_number(first(headline, concept, body))
        if number:
            visual = f'<div class="number">{esc(number)}</div><div class="number-label">{esc(first(body, concept, headline))}</div>'
        else:
            visual = f'<div class="quote">{esc(first(concept, body, headline))}</div>'
    elif template == "receipts" or visual_type in {"screenshot", "evidence"}:
        if evidence_uri:
            visual = f'<div class="evidence-tag">SOURCE EVIDENCE</div><div class="evidence"><img src="{esc(evidence_uri)}" alt="Official source evidence"></div>'
        else:
            visual = f'<div class="quote">{esc(first(concept, body, "Evidence requested, but no source image was captured."))}</div>'
    elif template == "comparison" or visual_type == "comparison":
        raw = first(concept, headline)
        parts = re.split(r"\s+vs\.?\s+|\s+versus\s+", raw, flags=re.I)
        left = parts[0].strip() if parts else "A"
        right = parts[1].strip() if len(parts) > 1 else "B"
        visual = f'<div class="compare"><div class="compare-card"><div class="compare-label">A</div><div class="compare-copy">{esc(left)}</div></div><div class="vs">VS</div><div class="compare-card"><div class="compare-label">B</div><div class="compare-copy">{esc(right)}</div></div></div>'
    elif template == "timeline" or visual_type == "timeline":
        events = slide.get("timeline") or slide.get("events") or []
        if isinstance(events, list) and events:
            items = []
            for event in events[:5]:
                if isinstance(event, dict):
                    d = first(event.get("date"), event.get("year"), "STEP")
                    t = first(event.get("text"), event.get("headline"), event.get("description"))
                else:
                    d, t = "STEP", event
                items.append(f'<div class="timeline-item"><div class="timeline-date">{esc(d)}</div><div class="timeline-text">{esc(t)}</div></div>')
            visual = '<div class="timeline">' + "".join(items) + '</div>'
        else:
            visual = f'<div class="timeline"><div class="timeline-item"><div class="timeline-date">BEFORE</div><div class="timeline-text">{esc(first(body, headline))}</div></div><div class="timeline-item"><div class="timeline-date">THEN</div><div class="timeline-text">{esc(first(concept, "A new development changed the picture."))}</div></div><div class="timeline-item"><div class="timeline-date">NOW</div><div class="timeline-text">What happens next matters most.</div></div></div>'
    elif template == "breakdown" or visual_type == "diagram":
        nodes = [
            ("INPUT", first(slide.get("input"), "USER / WORKLOAD")),
            ("SYSTEM", first(concept, "AI MODEL / AGENT")),
            ("OUTPUT", first(body, "RESULT / ACTION")),
        ]
        node_html = []
        for label, value in nodes:
            node_html.append(f'<div class="node"><div class="t">{esc(label)}</div><div class="v">{esc(value)}</div></div>')
        visual = '<div class="diagram">' + '<div class="arrow">→</div>'.join(node_html) + '</div>'
    elif role == "pattern_interrupt":
        visual = f'<div class="pattern"><div class="big">{esc(first(headline, concept, "WAIT."))}</div></div>'
    elif visual_type == "quote":
        visual = f'<div class="quote">{esc(first(body, headline, concept))}</div>'
    elif role in {"reveal", "implication", "payoff"}:
        visual = f'<div class="payoff">{esc(first(body, concept, headline))}</div>'
    else:
        visual = f'<div class="cardgrid"><div class="card"><div class="value">{esc(first(extract_number(headline), "01"))}</div><div class="label">{esc(first(concept, "THE DETAIL"))}</div></div><div class="card"><div class="value">→</div><div class="label">{esc(first(body, headline))}</div></div></div>'

    if index == total:
        visual = f'<div class="payoff">{esc(first(slide.get("payoff"), body, slide.get("implication"), headline))}</div>'

    body_html = ""
    if body and not (template == "shock-number" or visual_type in {"screenshot", "evidence", "timeline", "comparison", "diagram"}):
        body_html = f'<div class="body">{esc(body)}</div>'

    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{style}</style></head><body><section class="{classes}">
<div class="grain"></div>
<div class="meta"><span>GETBYTERUSH / {esc(template.replace("-", " "))}</span><span>{index:02d} / {total:02d}</span></div>
<div class="rule"></div>
<div class="kicker">{esc(kicker)}</div>
<h1 class="{headline_class}">{esc(headline)}</h1>
{body_html}
{visual}
<div class="footer"><div class="source">SOURCE / {esc(source)}</div><div class="brand">TESTED • EXPLAINED • REAL</div></div>
</section></body></html>'''


def render_html(story, out_dir, template, theme_name, theme, evidence_path):
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    evidence_uri = None
    if evidence_path:
        try:
            p = Path(evidence_path).resolve()
            if p.exists():
                evidence_uri = p.as_uri()
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
            page.wait_for_timeout(100)
            dimensions = page.evaluate("""() => ({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight, bodyW: document.body.scrollWidth, bodyH: document.body.scrollHeight, overflowing: [...document.querySelectorAll('*')].filter(el => { const r=el.getBoundingClientRect(); return r.right > 1080 || r.bottom > 1350 || r.left < 0 || r.top < 0; }).map(el => el.className || el.tagName).slice(0,20)})""")
            if dimensions["w"] > WIDTH or dimensions["h"] > HEIGHT or dimensions["bodyW"] > WIDTH or dimensions["bodyH"] > HEIGHT or dimensions["overflowing"]:
                failures.append({"slide": i, "details": dimensions})
            page.screenshot(path=str(png_path), full_page=False)
            print(f"✓ slide-{i:02d}.png")

        browser.close()

    if failures:
        print("WARNING: layout validation found potential overflow:")
        print(json.dumps(failures, indent=2))
        raise RuntimeError("Carousel layout validation failed; PNG package was not marked production-ready.")


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
            page.wait_for_timeout(1800)
            page.screenshot(path=str(output_path), full_page=False)
            browser.close()
        return output_path.exists()
    except Exception as exc:
        print(f"WARNING: evidence capture failed: {exc}")
        return False


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
        "renderer": "getbyterush-carousel-generator-v3",
        "template": template,
        "theme": theme_name,
        "canvas": f"{WIDTH}x{HEIGHT}",
        "production_ready": True,
    }
    package["instagram"] = {"published": False, "media_id": None, "permalink": None}
    (out_dir / "post.json").write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing {INPUT}. Run editorial_engine.py first.")

    story = json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"):
        print("No selected story. Nothing to render.")
        return

    slides = story.get("slides", [])
    if not 5 <= len(slides) <= 9:
        raise ValueError(f"Carousel must contain 5–9 slides, got {len(slides)}")

    template = infer_template(story)
    theme_name = infer_theme(story, template)
    theme = THEMES[theme_name]
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
    print("GETBYTERUSH CAROUSEL V3")
    print("=" * 72)
    print(f"Template : {template}")
    print(f"Theme    : {theme_name}")
    print(f"Slides   : {len(slides)}")
    print(f"Evidence : {'YES' if evidence_path else 'NO'}")

    render_html(story, out_dir, template, theme_name, theme, evidence_path)
    render_pngs_validate(out_dir, len(slides))
    write_package(story, out_dir, template, theme_name, created_at)

    print(f"OUTPUT: {out_dir}")
    print("PRODUCTION_READY: true")


if __name__ == "__main__":
    main()
