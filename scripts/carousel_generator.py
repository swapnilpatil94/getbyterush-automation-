#!/usr/bin/env python3
"""GetByteRush deterministic carousel renderer.

Renderer-only: consumes saved editorial JSON and never calls Gemini.
Canvas: 1080x1350.
"""
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

WIDTH, HEIGHT = 1080, 1350
ROOT = Path("output/posts")
INPUT = Path("data/selected_story.json")
CREAM = "#F4EFE4"
INK = "#111311"
FOREST = "#12352B"
GOLD = "#B99A5B"
RED = "#E53935"
TEAL = "#2D8C7A"
BLUE = "#3159C9"
ORANGE = "#F26A21"
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
    "mystery": ("#0D0F0E", CREAM, "#C7F000", "#C7F000"),
    "data": (CREAM, FOREST, GOLD, GOLD),
}

def txt(v):
    return " ".join(str(x) for x in v).strip() if isinstance(v, list) else str(v or "").strip()

def esc(v): return html.escape(txt(v), quote=True)

def first(*values):
    for value in values:
        if txt(value): return value
    return ""

def clean(v, limit=None):
    s = re.sub(r"\s+", " ", txt(v)).strip()
    if limit and len(s) > limit: s = s[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return s

def slug(v):
    return re.sub(r"[^a-z0-9]+", "-", txt(v).lower()).strip("-")[:90] or "getbyterush-post"

def theme_for(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    raw = clean(first(story.get("emotional_mode"), design.get("emotional_mode"))).lower()
    aliases = {"urgent":"urgency", "breaking":"urgency", "money":"money", "explainer":"explainer", "experiment":"experiment", "comparison":"comparison", "timeline":"timeline", "contradiction":"contradiction", "investigation":"investigation", "mystery":"mystery", "data":"data"}
    name = aliases.get(raw, "brand")
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

def source_info(story, slide=None):
    slide = slide or {}
    ss = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    return clean(first(slide.get("source_label"), slide.get("source"), ss.get("source"), ss.get("publisher"), story.get("source"), "Official source"), 100), clean(first(slide.get("asset_url"), slide.get("source_url"), ss.get("url"), story.get("source_url")))

def asset_path(slide, package):
    for key in ("local_asset", "asset_path", "image_path"):
        if slide.get(key):
            p = Path(txt(slide[key]))
            if p.exists(): return p
    if clean(first(slide.get("visual_type"), slide.get("layout"))).lower() in {"evidence", "screenshot", "receipt"}:
        p = package / "evidence" / "source.png"
        if p.exists(): return p
    return None

def capture_evidence(url, destination):
    if not url or not urlparse(url).scheme: return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            for selector in ['[aria-label*="cookie" i]', '[id*="cookie" i]', '[class*="cookie" i]', '[aria-label*="consent" i]', '[id*="consent" i]', '[class*="consent" i]']:
                try: page.locator(selector).first.evaluate("el => el.remove()")
                except Exception: pass
            page.screenshot(path=str(destination), full_page=False)
            browser.close()
        return destination if destination.exists() else None
    except Exception as exc:
        print("WARNING: evidence capture failed:", exc)
        return None

def metric(slide):
    raw = " ".join([clean(slide.get("headline")), clean(slide.get("visual_concept")), clean(slide.get("body"))])
    matches = re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|M|B|K)?", raw, flags=re.I)
    return matches[0] if matches else "01"

def visual(slide, story, theme, image_uri, i, total):
    bg, fg, accent, signal = theme
    vt = clean(first(slide.get("visual_type"), slide.get("layout"))).lower()
    r = role(slide, i, total)
    concept = clean(first(slide.get("visual_concept"), slide.get("visual_strategy"), slide.get("visual")), 220)
    body = clean(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")), 260)
    headline = clean(first(slide.get("headline"), slide.get("title"), slide.get("hook")), 160)
    label = clean(first(slide.get("source_label"), "OFFICIAL SOURCE"), 70)
    if vt in {"evidence", "screenshot", "receipt"} and image_uri:
        return '<div class="evidence"><div class="ev-label">%s</div><img src="%s" alt="official source evidence"></div>' % (esc(label), esc(image_uri))
    if vt == "metric":
        return '<div class="metric"><div class="metric-value">%s</div><div class="metric-line"></div><div class="metric-caption">%s</div></div>' % (esc(metric(slide)), esc(clean(first(concept, body), 130)))
    if vt == "comparison":
        parts = re.split(r"\s+(?:vs\.?|versus)\s+", concept, flags=re.I)
        left = clean(parts[0] if parts else "BEFORE", 70); right = clean(parts[1] if len(parts) > 1 else "NOW", 70)
        return '<div class="compare"><div class="compare-card"><small>BEFORE</small><strong>%s</strong></div><div class="vs">VS</div><div class="compare-card"><small>NOW</small><strong>%s</strong></div></div>' % (esc(left), esc(right))
    if vt == "timeline":
        return '<div class="timeline"><div class="time-node"><b>01</b><span>ORIGIN</span></div><i></i><div class="time-node"><b>02</b><span>SHIFT</span></div><i></i><div class="time-node"><b>03</b><span>IMPACT</span></div><p>%s</p></div>' % esc(concept or body)
    if vt == "diagram":
        return '<div class="diagram"><div class="node"><small>INPUT</small><b>%s</b></div><div class="arrow">→</div><div class="node"><small>CHANGE</small><b>%s</b></div><div class="arrow">→</div><div class="node"><small>RESULT</small><b>%s</b></div></div>' % (esc(clean(first(slide.get("diagram_input"), "CURRENT STACK"), 45)), esc(clean(first(concept, "NEW ARCHITECTURE"), 55)), esc(clean(first(slide.get("impact"), body, "MORE CAPACITY"), 55)))
    if vt == "quote":
        return '<div class="quote"><span>“</span><blockquote>%s</blockquote><small>%s</small></div>' % (esc(clean(first(slide.get("quote"), body, concept), 240)), esc(label))
    if r == "pattern_interrupt":
        return '<div class="pattern"><div class="pattern-tag">THE SHIFT</div><div class="pattern-big">%s</div></div>' % esc(clean(first(headline, concept), 150))
    if r in {"payoff", "final"} or vt == "final":
        return '<div class="payoff"><div class="payoff-rule"></div><strong>%s</strong><p>%s</p></div>' % (esc(clean(first(headline, concept), 150)), esc(clean(first(body, concept), 180)))
    if r == "reveal":
        return '<div class="reveal"><div class="reveal-num">%02d</div><strong>%s</strong><p>%s</p></div>' % (i, esc(clean(first(headline, concept), 150)), esc(clean(first(body, concept), 180)))
    return '<div class="editorial-object"><div class="object-index">%02d</div><div class="object-rule"></div><strong>%s</strong><p>%s</p></div>' % (i, esc(clean(first(concept, headline), 150)), esc(clean(first(body, concept), 190)))

def stylesheet(theme):
    bg, fg, accent, signal = theme
    surface = "#E9E2D5" if bg == CREAM else "#1D201D"
    return """@page { size:1080px 1350px; margin:0; } * { box-sizing:border-box; } html,body { margin:0; width:1080px; height:1350px; overflow:hidden; } body { background:%s; color:%s; font-family:Inter,Arial,Helvetica,sans-serif; } .slide { position:relative; width:1080px; height:1350px; overflow:hidden; background:%s; color:%s; padding:78px; } .grain { position:absolute; inset:0; opacity:.025; pointer-events:none; background-image:radial-gradient(currentColor .55px,transparent .7px); background-size:7px 7px; } .top { position:absolute; top:38px; left:78px; right:78px; display:flex; justify-content:space-between; font:800 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.6px; opacity:.58; text-transform:uppercase; } .kicker { display:inline-block; margin-top:48px; padding:8px 11px; border:1px solid %s; color:%s; font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; max-width:680px; } h1 { margin:20px 0 0; max-width:900px; font-size:72px; line-height:.92; letter-spacing:-3.5px; font-weight:900; overflow-wrap:anywhere; } h1.hero { font-size:112px; line-height:.81; letter-spacing:-7px; max-width:920px; } .body { margin-top:20px; max-width:750px; font-size:24px; line-height:1.2; font-weight:550; opacity:.82; overflow-wrap:anywhere; } .footer { position:absolute; left:78px; right:78px; bottom:40px; display:flex; justify-content:space-between; gap:20px; font:700 11px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; opacity:.56; } .footer .source { max-width:730px; overflow-wrap:anywhere; } .num { white-space:nowrap; } .swipe { position:absolute; left:78px; top:555px; font:900 13px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; color:%s; letter-spacing:1px; text-transform:uppercase; max-width:760px; } .metric { position:absolute; left:78px; right:78px; top:535px; } .metric-value { font-size:245px; line-height:.7; letter-spacing:-15px; font-weight:950; color:%s; } .metric-line { width:120px; height:7px; margin-top:48px; background:%s; } .metric-caption { margin-top:22px; max-width:800px; font-size:30px; line-height:1; font-weight:900; } .evidence { position:absolute; left:78px; right:78px; top:350px; height:690px; padding:14px; background:#151715; border:2px solid %s; box-shadow:16px 16px 0 %s; overflow:hidden; } .evidence img { display:block; width:100%%; height:100%%; object-fit:contain; background:white; } .ev-label { position:absolute; z-index:3; left:14px; top:14px; padding:8px 10px; background:%s; color:%s; font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; max-width:470px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; } .compare { position:absolute; left:78px; right:78px; top:550px; display:grid; grid-template-columns:1fr 70px 1fr; gap:16px; align-items:center; } .compare-card { min-height:290px; padding:28px; background:%s; border:2px solid %s; display:flex; flex-direction:column; justify-content:space-between; } .compare-card small { font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:%s; } .compare-card strong { font-size:40px; line-height:.95; font-weight:950; letter-spacing:-2px; overflow-wrap:anywhere; } .vs { font:950 20px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:%s; text-align:center; } .diagram { position:absolute; left:78px; right:78px; top:555px; display:grid; grid-template-columns:1fr 48px 1fr 48px 1fr; gap:8px; align-items:center; } .node { min-height:225px; padding:24px; border:2px solid %s; background:%s; } .node small { display:block; color:%s; font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; } .node b { display:block; margin-top:20px; font-size:25px; line-height:1; overflow-wrap:anywhere; } .arrow { color:%s; font-size:32px; text-align:center; font-weight:900; } .timeline { position:absolute; left:95px; right:78px; top:565px; display:flex; align-items:center; gap:14px; flex-wrap:wrap; } .time-node { min-width:155px; padding:18px; border:2px solid %s; display:flex; flex-direction:column; gap:10px; } .time-node b { font-size:38px; line-height:.8; color:%s; } .time-node span { font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; } .timeline i { height:3px; flex:1; background:%s; min-width:35px; } .timeline p { width:100%%; max-width:800px; font-size:27px; line-height:1.05; font-weight:800; overflow-wrap:anywhere; } .quote { position:absolute; left:78px; right:78px; top:555px; padding:30px 34px; border-left:8px solid %s; background:%s; } .quote > span { font-size:86px; line-height:.35; color:%s; } .quote blockquote { margin:30px 0 25px; font-size:45px; line-height:1; letter-spacing:-2px; font-weight:900; overflow-wrap:anywhere; } .quote small { font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:%s; } .editorial-object { position:absolute; left:78px; right:78px; top:555px; } .object-index { font:900 16px/1 ui-monospace,SFMono-Regular,Menlo,monospace; color:%s; } .object-rule { width:110px; height:5px; margin:22px 0; background:%s; } .editorial-object strong { display:block; max-width:850px; font-size:55px; line-height:.92; letter-spacing:-2.5px; font-weight:950; overflow-wrap:anywhere; } .editorial-object p { max-width:720px; margin-top:25px; font-size:23px; line-height:1.2; opacity:.72; overflow-wrap:anywhere; } .pattern { position:absolute; inset:500px 0 0; padding:50px 78px; background:%s; color:%s; } .pattern-tag { font:900 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1.5px; } .pattern-big { margin-top:35px; max-width:900px; font-size:88px; line-height:.84; letter-spacing:-5px; font-weight:950; overflow-wrap:anywhere; } .reveal { position:absolute; left:78px; right:78px; top:545px; } .reveal-num { font:950 150px/.65 Arial,sans-serif; color:%s; letter-spacing:-10px; } .reveal strong { display:block; margin-top:45px; max-width:850px; font-size:57px; line-height:.9; letter-spacing:-3px; font-weight:950; overflow-wrap:anywhere; } .reveal p { max-width:720px; margin-top:22px; font-size:22px; line-height:1.2; opacity:.72; } .payoff { position:absolute; left:78px; right:78px; top:545px; } .payoff-rule { width:100%%; height:7px; background:%s; margin-bottom:28px; } .payoff strong { display:block; max-width:880px; font-size:64px; line-height:.88; letter-spacing:-3.5px; font-weight:950; overflow-wrap:anywhere; } .payoff p { max-width:760px; margin-top:28px; font-size:23px; line-height:1.2; opacity:.72; }""" % (bg, fg, bg, fg, accent, accent, accent, accent, accent, accent, accent, accent, accent, accent, surface, accent, signal, accent, accent, accent, surface, accent, signal, accent, accent, surface, signal, accent, accent, accent, accent, accent, accent, surface, accent, signal, accent, signal, surface, signal, accent, fg, accent, accent, accent, accent, accent, accent)

def html_page(story, slide, i, total, theme, visual_html):
    bg, fg, accent, signal = theme
    r = role(slide, i, total)
    kicker = clean(first(slide.get("kicker"), slide.get("label"), r.replace("_", " ")), 45)
    h = clean(first(slide.get("headline"), slide.get("title"), slide.get("hook"), "GetByteRush"), 170)
    b = clean(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy")), 320)
    source, _ = source_info(story, slide)
    hero = " hero" if i == 1 else ("" if len(h) < 90 else " tight")
    swipe = clean(first(slide.get("swipe_reason"), slide.get("transition_hint"), "SWIPE → NEXT"), 100)
    return '<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body><main class="slide"><div class="grain"></div><div class="top"><span>getByteRush</span><span>TECH • AI • INTERNET</span></div><div class="kicker">%s</div><h1 class="%s">%s</h1><div class="body">%s</div>%s%s<div class="footer"><span class="source">%s</span><span class="num">%02d / %02d</span></div></main></body></html>' % (stylesheet(theme), esc(kicker), hero.strip(), esc(h), esc(b), visual_html, ('<div class="swipe">%s</div>' % esc(swipe)) if i == 1 else '', esc(source), i, total)

def choose_package(story):
    title = slug(story.get("story_title") or story.get("title") or "getbyterush-post")
    stamp = clean(story.get("created_at"))
    try: dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception: dt = datetime.now(timezone.utc)
    return ROOT / dt.strftime("%Y-%m-%d") / (dt.strftime("%H%M%S") + "-" + title)

def main():
    import sys
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT
    story = json.loads(source.read_text(encoding="utf-8"))
    slides = story.get("slides") or []
    if not slides: raise SystemExit("Editorial contains no slides")
    package = choose_package(story)
    slides_dir = package / "slides"; html_dir = package / "html"; evidence_dir = package / "evidence"
    slides_dir.mkdir(parents=True, exist_ok=True); html_dir.mkdir(parents=True, exist_ok=True); evidence_dir.mkdir(parents=True, exist_ok=True)
    theme = THEMES[theme_for(story)]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
        for i, slide in enumerate(slides, 1):
            vt = clean(first(slide.get("visual_type"), slide.get("layout"))).lower()
            image = asset_path(slide, package)
            if vt in {"evidence", "screenshot", "receipt"} and image is None:
                _, url = source_info(story, slide)
                if url: image = capture_evidence(url, evidence_dir / "source.png")
            uri = image.resolve().as_uri() if image and image.exists() else ""
            content = html_page(story, slide, i, len(slides), theme, visual(slide, story, theme, uri, i, len(slides)))
            html_file = html_dir / (f"{i:02d}.html"); html_file.write_text(content, encoding="utf-8")
            page.goto(html_file.resolve().as_uri(), wait_until="load")
            page.screenshot(path=str(slides_dir / f"{i:02d}.png"), full_page=False)
            dims = page.evaluate("""() => ({w:document.documentElement.scrollWidth,h:document.documentElement.scrollHeight,bw:document.body.scrollWidth,bh:document.body.scrollHeight})""")
            if max(dims["w"], dims["bw"]) > WIDTH or max(dims["h"], dims["bh"]) > HEIGHT: raise RuntimeError(f"Slide {i:02d} overflowed canvas: {dims}")
        browser.close()
    (package / "post.json").write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for filename, key in (("caption.txt", "caption"), ("alt-text.txt", "alt_text"), ("pinned-comment.txt", "pinned_comment")):
        if story.get(key): (package / filename).write_text(txt(story[key]) + "\n", encoding="utf-8")
    if story.get("hashtags"):
        tags = story["hashtags"] if isinstance(story["hashtags"], list) else [story["hashtags"]]
        (package / "hashtags.txt").write_text(" ".join("#" + re.sub(r"[^A-Za-z0-9_]", "", txt(x)) for x in tags) + "\n", encoding="utf-8")
    print("GETBYTERUSH_RENDER_OK"); print("PACKAGE=%s" % package); print("SLIDES=%d" % len(slides)); print("CANVAS=1080x1350"); print("GEMINI_CALL=0")

if __name__ == "__main__": main()
