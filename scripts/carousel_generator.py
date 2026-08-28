#!/usr/bin/env python3
"""GetByteRush deterministic carousel renderer.

Renderer-only: consumes data/selected_story.json and never calls Gemini.
1080x1350 Instagram canvas. The renderer is deliberately deterministic.
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

CREAM = "#F4EFE4"
INK = "#111311"
FOREST = "#12352B"
GOLD = "#B99A5B"
RED = "#E53935"
TEAL = "#2D8C7A"
BLUE = "#3159C9"
ORANGE = "#F26A21"
LIME = "#B7E43B"

THEMES = {
    "brand": (CREAM, INK, FOREST, GOLD),
    "explainer": (CREAM, INK, FOREST, BLUE),
    "experiment": (CREAM, FOREST, TEAL, TEAL),
    "money": (CREAM, INK, FOREST, GOLD),
    "urgency": (INK, CREAM, RED, RED),
    "comparison": (CREAM, INK, FOREST, GOLD),
    "timeline": (CREAM, FOREST, BLUE, BLUE),
    "contradiction": (CREAM, INK, ORANGE, ORANGE),
    "investigation": ("#EFE8D8", FOREST, "#426A78", RED),
    "mystery": ("#0D0F0E", CREAM, LIME, LIME),
    "data": (CREAM, FOREST, GOLD, GOLD),
}


def text(value):
    if isinstance(value, list):
        return " ".join(str(x) for x in value).strip()
    return str(value or "").strip()


def esc(value):
    return html.escape(text(value), quote=True)


def first(*values):
    for value in values:
        if text(value):
            return value
    return ""


def clean(value, limit=None):
    result = re.sub(r"\s+", " ", text(value)).strip()
    if limit and len(result) > limit:
        result = result[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return result


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", text(value).lower()).strip("-")[:90] or "getbyterush-post"


def theme_for(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    raw = clean(first(story.get("emotional_mode"), design.get("emotional_mode"))).lower()
    aliases = {
        "urgent": "urgency", "breaking": "urgency", "money/scale": "money",
        "money": "money", "explainer": "explainer", "experiment": "experiment",
        "comparison": "comparison", "timeline": "timeline", "contradiction": "contradiction",
        "investigation": "investigation", "mystery": "mystery", "data": "data",
    }
    name = aliases.get(raw, "brand")
    if story.get("emergency_mode") is True:
        name = "urgency"
    return name, THEMES[name]


def role(slide, index, total):
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


def source_info(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    source = clean(first(
        slide.get("source_label"), slide.get("source"), source_story.get("source"),
        source_story.get("publisher"), story.get("source"), "Official source"
    ), 100)
    url = clean(first(
        slide.get("asset_url"), slide.get("source_url"), source_story.get("url"), story.get("source_url")
    ))
    return source, url


def metric_value(slide):
    raw = " ".join([
        clean(slide.get("headline")), clean(slide.get("visual_concept")), clean(slide.get("body"))
    ])
    found = re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|M|B|K)?", raw, flags=re.I)
    return found[0] if found else "01"


def capture_evidence(url, destination):
    if not url or not urlparse(url).scheme:
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
        return destination if destination.exists() else None
    except Exception as exc:
        print(f"WARNING: evidence capture failed: {exc}")
        return None


def css(theme):
    bg, fg, accent, signal = theme
    surface = "#E9E2D5" if bg == CREAM else "#1D201D"
    return Template(r'''
@page { size: 1080px 1350px; margin: 0; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; width:1080px; height:1350px; overflow:hidden; }
body { background:$bg; color:$fg; font-family: Inter, Arial, Helvetica, sans-serif; }
.slide { position:relative; width:1080px; height:1350px; overflow:hidden; padding:78px; background:$bg; color:$fg; }
.slide.dark { background:#111311; color:#F4EFE4; }
.grain { position:absolute; inset:0; pointer-events:none; opacity:.028; background-image:radial-gradient(currentColor .55px, transparent .7px); background-size:7px 7px; }
.top { position:absolute; top:38px; left:78px; right:78px; display:flex; justify-content:space-between; font:800 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.6px; opacity:.58; text-transform:uppercase; }
.kicker { display:inline-block; margin-top:46px; padding:8px 11px; border:1px solid $accent; color:$accent; font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; max-width:720px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.rule { width:84px; height:5px; background:$accent; margin-top:22px; }
h1 { margin:20px 0 0; max-width:900px; font-size:72px; line-height:.92; letter-spacing:-3.5px; font-weight:900; overflow-wrap:anywhere; }
h1.hero { font-size:104px; line-height:.82; letter-spacing:-6px; max-width:920px; }
h1.compact { font-size:56px; line-height:.94; letter-spacing:-2.6px; }
.body { margin-top:20px; max-width:760px; font-size:24px; line-height:1.22; font-weight:550; opacity:.82; overflow-wrap:anywhere; }
.footer { position:absolute; left:78px; right:78px; bottom:38px; display:flex; justify-content:space-between; gap:20px; font:700 11px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; opacity:.56; }
.footer .source { max-width:720px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.metric { position:absolute; left:78px; right:78px; top:545px; }
.metric-value { font-size:245px; line-height:.72; letter-spacing:-15px; font-weight:950; color:$accent; }
.metric-line { width:120px; height:7px; margin-top:46px; background:$signal; }
.metric-caption { margin-top:22px; max-width:800px; font-size:30px; line-height:1.02; font-weight:900; }
.evidence { position:absolute; left:78px; right:78px; top:365px; height:690px; padding:14px; background:#151715; border:2px solid $fg; box-shadow:16px 16px 0 $accent; overflow:hidden; }
.evidence img { display:block; width:100%; height:100%; object-fit:contain; object-position:center; background:white; }
.ev-label { position:absolute; z-index:2; left:14px; top:14px; max-width:470px; padding:8px 10px; background:$accent; color:$bg; font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.compare { position:absolute; left:78px; right:78px; top:560px; display:grid; grid-template-columns:1fr 68px 1fr; gap:14px; align-items:center; }
.compare-card { min-height:280px; padding:28px; background:$surface; border:2px solid $fg; display:flex; flex-direction:column; justify-content:space-between; }
.compare-card small { font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:$accent; }
.compare-card strong { font-size:39px; line-height:.98; font-weight:950; letter-spacing:-2px; overflow-wrap:anywhere; }
.vs { font:950 20px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:$accent; text-align:center; }
.diagram { position:absolute; left:78px; right:78px; top:565px; display:grid; grid-template-columns:1fr 44px 1fr 44px 1fr; gap:8px; align-items:center; }
.node { min-height:220px; padding:24px; border:2px solid $fg; background:$surface; }
.node small { display:block; color:$accent; font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; }
.node b { display:block; margin-top:20px; font-size:24px; line-height:1.02; overflow-wrap:anywhere; }
.arrow { color:$signal; font-size:30px; text-align:center; font-weight:900; }
.timeline { position:absolute; left:78px; right:78px; top:575px; display:flex; align-items:center; gap:12px; }
.time-node { min-width:160px; padding:18px; border:2px solid $fg; display:flex; flex-direction:column; gap:10px; }
.time-node b { font-size:38px; line-height:.8; color:$accent; }
.time-node span { font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; }
.timeline i { height:3px; flex:1; background:$signal; }
.timeline-copy { position:absolute; left:0; top:145px; max-width:850px; font-size:27px; line-height:1.1; font-weight:850; overflow-wrap:anywhere; }
.quote { position:absolute; left:78px; right:78px; top:555px; border-top:6px solid $accent; padding:28px 8px; }
.quote-mark { font-size:84px; line-height:.45; color:$accent; }
.quote blockquote { margin:30px 0 20px; max-width:860px; font-size:48px; line-height:1.02; letter-spacing:-2px; font-weight:900; overflow-wrap:anywhere; }
.quote small { font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:$accent; text-transform:uppercase; }
.pattern { position:absolute; left:0; right:0; top:440px; bottom:0; padding:74px 78px; background:$accent; color:$bg; }
.pattern-tag { font:900 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:2px; }
.pattern-big { margin-top:28px; max-width:850px; font-size:76px; line-height:.9; font-weight:950; letter-spacing:-4px; overflow-wrap:anywhere; }
.reveal { position:absolute; left:78px; right:78px; top:555px; display:grid; grid-template-columns:130px 1fr; gap:28px; align-items:start; }
.reveal-num { font:950 72px/.8 ui-monospace,SFMono-Regular,Menlo,monospace; color:$accent; }
.reveal strong { font-size:50px; line-height:.98; letter-spacing:-2px; font-weight:950; overflow-wrap:anywhere; }
.reveal p { grid-column:2; margin:18px 0 0; max-width:760px; font-size:25px; line-height:1.18; opacity:.8; overflow-wrap:anywhere; }
.editorial-object { position:absolute; left:78px; right:78px; top:555px; display:grid; grid-template-columns:90px 14px 1fr; gap:18px; align-items:start; }
.object-index { font:950 58px/.9 ui-monospace,SFMono-Regular,Menlo,monospace; color:$accent; }
.object-rule { width:4px; min-height:150px; background:$signal; }
.editorial-object strong { font-size:48px; line-height:.98; letter-spacing:-2px; font-weight:950; overflow-wrap:anywhere; }
.editorial-object p { grid-column:3; margin:18px 0 0; max-width:760px; font-size:25px; line-height:1.18; opacity:.8; overflow-wrap:anywhere; }
.payoff { position:absolute; left:78px; right:78px; top:520px; }
.payoff-rule { width:150px; height:7px; background:$accent; margin-bottom:28px; }
.payoff strong { display:block; max-width:850px; font-size:64px; line-height:.94; letter-spacing:-3px; font-weight:950; overflow-wrap:anywhere; }
.payoff p { max-width:760px; margin-top:22px; font-size:25px; line-height:1.18; opacity:.8; overflow-wrap:anywhere; }
.dark { background:#111311 !important; color:#F4EFE4 !important; }
.dark .kicker { color:$accent; border-color:$accent; }
.dark .footer,.dark .top { color:#F4EFE4; }
''').substitute(bg=bg, fg=fg, accent=accent, signal=signal, surface=surface)


def visual_markup(slide, story, theme, evidence_uri, index, total):
    _, _, accent, _ = theme
    visual_type = clean(first(slide.get("visual_type"), slide.get("layout"))).lower()
    current_role = role(slide, index, total)
    concept = clean(first(slide.get("visual_concept"), slide.get("visual_strategy"), slide.get("visual")), 220)
    body = clean(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")), 260)
    headline = clean(first(slide.get("headline"), slide.get("title"), slide.get("hook")), 160)
    label = clean(first(slide.get("source_label"), "OFFICIAL SOURCE"), 70)

    if visual_type in {"evidence", "screenshot", "receipt"} and evidence_uri:
        return f'<div class="evidence"><div class="ev-label">{esc(label)}</div><img src="{esc(evidence_uri)}" alt="Official source evidence"></div>'
    if visual_type == "metric":
        return f'<div class="metric"><div class="metric-value">{esc(metric_value(slide))}</div><div class="metric-line"></div><div class="metric-caption">{esc(clean(first(concept, body), 130))}</div></div>'
    if visual_type == "comparison":
        parts = re.split(r"\s+(?:vs\.?|versus)\s+", concept or headline, flags=re.I)
        left = clean(parts[0] if parts else "A", 70)
        right = clean(parts[1] if len(parts) > 1 else "B", 70)
        return f'<div class="compare"><div class="compare-card"><small>OPTION A</small><strong>{esc(left)}</strong></div><div class="vs">VS</div><div class="compare-card"><small>OPTION B</small><strong>{esc(right)}</strong></div></div>'
    if visual_type == "timeline":
        return f'<div class="timeline"><div class="time-node"><b>01</b><span>ORIGIN</span></div><i></i><div class="time-node"><b>02</b><span>SHIFT</span></div><i></i><div class="time-node"><b>03</b><span>IMPACT</span></div><div class="timeline-copy">{esc(concept or body)}</div></div>'
    if visual_type == "diagram":
        a = clean(first(slide.get("diagram_input"), "CURRENT STACK"), 45)
        b = clean(first(concept, "NEW ARCHITECTURE"), 55)
        c = clean(first(slide.get("impact"), body, "REAL-WORLD RESULT"), 55)
        return f'<div class="diagram"><div class="node"><small>INPUT</small><b>{esc(a)}</b></div><div class="arrow">→</div><div class="node"><small>CHANGE</small><b>{esc(b)}</b></div><div class="arrow">→</div><div class="node"><small>RESULT</small><b>{esc(c)}</b></div></div>'
    if visual_type == "quote":
        quote = clean(first(slide.get("quote"), body, concept), 240)
        return f'<div class="quote"><div class="quote-mark">“</div><blockquote>{esc(quote)}</blockquote><small>{esc(label)}</small></div>'
    if current_role == "pattern_interrupt":
        return f'<div class="pattern"><div class="pattern-tag">THE SHIFT</div><div class="pattern-big">{esc(clean(first(headline, concept), 150))}</div></div>'
    if current_role == "reveal":
        return f'<div class="reveal"><div class="reveal-num">{index:02d}</div><div><strong>{esc(clean(first(headline, concept), 150))}</strong><p>{esc(clean(first(body, concept), 180))}</p></div></div>'
    if current_role == "payoff" or index == total:
        return f'<div class="payoff"><div class="payoff-rule"></div><strong>{esc(clean(first(headline, concept), 150))}</strong><p>{esc(clean(first(body, concept), 180))}</p></div>'
    return f'<div class="editorial-object"><div class="object-index">{index:02d}</div><div class="object-rule"></div><div><strong>{esc(clean(first(concept, headline), 150))}</strong><p>{esc(clean(first(body, concept), 190))}</p></div></div>'


def slide_html(story, slide, index, total, theme, evidence_uri):
    bg, fg, accent, signal = theme
    headline = clean(first(slide.get("headline"), slide.get("title"), slide.get("hook"), "GetByteRush"), 150)
    body = clean(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")), 300)
    kicker = clean(first(slide.get("kicker"), slide.get("label"), story.get("series"), "GETBYTERUSH"), 60)
    source, _ = source_info(story, slide)
    current_role = role(slide, index, total)
    dark = clean(first(slide.get("background"), slide.get("background_mode"))).lower() in {"black", "ink", "dark", "blackout"} or current_role == "pattern_interrupt" or bg == INK
    classes = "slide dark" if dark else "slide"
    headline_class = "hero" if index == 1 else ("compact" if len(headline) > 88 else "")
    body_html = "" if index != 1 and clean(first(slide.get("visual_type"), slide.get("layout"))).lower() in {"evidence", "screenshot", "receipt", "metric", "comparison", "timeline", "diagram", "quote"} else (f'<div class="body">{esc(body)}</div>' if body else "")
    visual = visual_markup(slide, story, theme, evidence_uri, index, total)
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=1080, initial-scale=1"><style>{css((INK, CREAM, accent, signal) if dark else theme)}</style></head><body><section class="{classes}"><div class="grain"></div><div class="top"><span>GETBYTERUSH / {esc(current_role.replace("_", " "))}</span><span>{index:02d} / {total:02d}</span></div><div class="kicker">{esc(kicker)}</div><div class="rule"></div><h1 class="{headline_class}">{esc(headline)}</h1>{body_html}{visual}<div class="footer"><div class="source">SOURCE / {esc(source)}</div><div>TESTED • EXPLAINED • REAL</div></div></section></body></html>'''


def render(story, out_dir, theme):
    slides = story.get("slides") or []
    if not slides:
        raise ValueError("Selected story contains no carousel slides.")
    html_dir = out_dir / "html"
    slides_dir = out_dir / "slides"
    html_dir.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(parents=True, exist_ok=True)
    evidence_uri = None
    evidence_path = out_dir / "evidence" / "source.png"
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    captured = capture_evidence(source_story.get("url", ""), evidence_path)
    if captured:
        evidence_uri = captured.resolve().as_uri()
    for index, slide in enumerate(slides, 1):
        path = html_dir / f"{index:02d}.html"
        path.write_text(slide_html(story, slide, index, len(slides), theme, evidence_uri), encoding="utf-8")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        for index in range(1, len(slides) + 1):
            html_path = (html_dir / f"{index:02d}.html").resolve()
            png_path = slides_dir / f"{index:02d}.png"
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
            page.goto(html_path.as_uri(), wait_until="load")
            page.screenshot(path=str(png_path), full_page=False)
            page.close()
        browser.close()
    return len(slides), bool(captured)


def write_metadata(story, out_dir, created_at, theme_name):
    caption = clean(story.get("caption"))
    hashtags = story.get("hashtags", [])
    hashtags_text = " ".join(str(x) for x in hashtags) if isinstance(hashtags, list) else text(hashtags)
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
    (out_dir / "hashtags.txt").write_text(hashtags_text, encoding="utf-8")
    (out_dir / "pinned-comment.txt").write_text(clean(story.get("pinned_comment")), encoding="utf-8")
    (out_dir / "alt-text.txt").write_text(clean(story.get("alt_text")), encoding="utf-8")
    created_dt = datetime.fromisoformat(created_at)
    package = dict(story)
    design = dict(story.get("design") or {})
    design.update({"renderer": "getbyterush-carousel-renderer-v9", "theme": theme_name})
    package.update({
        "design": design,
        "post_id": f"{slug(story.get('story_title', 'getbyterush-post'))}-{created_at.replace(':', '').replace('+', '-')}",
        "status": "pending_approval",
        "created_at": created_at,
        "retention_days": RETENTION_DAYS,
        "delete_after": (created_dt + timedelta(days=RETENTION_DAYS)).isoformat(),
        "package": {"slides_dir": "slides", "html_dir": "html", "evidence_dir": "evidence", "slide_count": len(story.get("slides", [])), "theme": theme_name},
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
    title = story.get("story_title", "GetByteRush Post")
    created_dt = datetime.now().astimezone()
    created_at = created_dt.isoformat(timespec="seconds")
    date_dir = OUTPUT_ROOT / created_dt.strftime("%Y-%m-%d")
    out_dir = date_dir / f"{created_dt.strftime('%H%M%S')}-{slug(title)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence").mkdir(parents=True, exist_ok=True)
    theme_name, theme = theme_for(story)
    count, has_evidence = render(story, out_dir, theme)
    write_metadata(story, out_dir, created_at, theme_name)
    print("=" * 72)
    print("GETBYTERUSH CAROUSEL V9")
    print("=" * 72)
    print(f"Theme: {theme_name}")
    print(f"Slides: {count}")
    print(f"Evidence: {'YES' if has_evidence else 'NO'}")
    print(f"Gemini: 0")
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
