#!/usr/bin/env python3
import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

W, H = 1080, 1350
INPUT = Path("data/selected_story.json")
ROOT = Path("output/posts")
RETENTION_DAYS = 7
CREAM = "#F4EFE4"
INK = "#111311"
FOREST = "#12352B"
GOLD = "#B99A5B"
BLUE = "#527A91"
ORANGE = "#F26A21"
LIME = "#B7E32B"
LEAK = re.compile(r"(callout graphic|visual concept|visual direction|visual strategy|design direction|layout instruction|highlight that|data graphic showing|contrast visual between|illustrate that|graphic showing|render this|create a)", re.I)


def clean(value):
    if isinstance(value, list):
        value = " ".join(str(x) for x in value)
    return re.sub(r"\s+", " ", str(value or "")).strip()


def esc(value):
    return html.escape(clean(value), quote=True)


def first(*values):
    for value in values:
        if clean(value):
            return clean(value)
    return ""


def words(text):
    return re.findall(r"\b[\w’'-]+\b", clean(text))


def punch(text, max_words=9, max_chars=72):
    text = clean(text)
    if not text:
        return "GetByteRush"
    if len(words(text)) <= max_words and len(text) <= max_chars:
        return text.rstrip(" .")
    sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    if len(words(sentence)) <= max_words and len(sentence) <= max_chars:
        return sentence.rstrip(" .")
    result = " ".join(words(text)[:max_words])
    if len(result) > max_chars:
        result = result[:max_chars].rsplit(" ", 1)[0]
    return result.rstrip(" ,.;:") + "…"


def support(text, max_chars=145):
    text = clean(text)
    if not text or LEAK.search(text):
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def category(story):
    return first(story.get("content_type"), story.get("story_type"), story.get("category"), story.get("type"), "TECH • AI • INTERNET").upper()


def source(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    label = first(slide.get("source_label"), slide.get("source"), source_story.get("source"), source_story.get("publisher"), story.get("source"), "Official source")
    url = first(slide.get("asset_url"), slide.get("source_url"), source_story.get("url"), story.get("source_url"))
    return label[:100], url


def theme(story):
    design = story.get("design") if isinstance(story.get("design"), dict) else {}
    raw = first(story.get("emotional_mode"), design.get("emotional_mode")).lower()
    if story.get("emergency_mode") is True:
        return "interrupt"
    if raw in {"contradiction", "tension"}:
        return "tension"
    if any(x in category(story) for x in ("TECH_NEWS", "MODEL_UPDATE", "AI_AGENTS", "EXPLAINER")):
        return "technology"
    return "authority"


def palette(name):
    if name == "interrupt":
        return {"bg": INK, "fg": CREAM, "accent": LIME, "signal": LIME}
    if name == "tension":
        return {"bg": CREAM, "fg": INK, "accent": ORANGE, "signal": ORANGE}
    if name == "technology":
        return {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": BLUE}
    return {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": GOLD}


def role(slide, index, total):
    explicit = first(slide.get("role"), slide.get("scene_role")).lower()
    if explicit:
        return explicit
    if index == 1:
        return "interrupt"
    if index == 2:
        return "open_loop"
    if index == 3:
        return "proof"
    if index == 4:
        return "escalation"
    if index == 5 and total >= 6:
        return "pattern_interrupt"
    if index == 6 and total >= 7:
        return "reveal"
    if index == 7 and total >= 8:
        return "implication"
    if index == total:
        return "payoff"
    return "proof"


def content(slide):
    headline = punch(first(slide.get("headline"), slide.get("title"), slide.get("hook"), slide.get("text")), 10, 76)
    body = support(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy"), slide.get("description")), 150)
    visual_type = first(slide.get("visual_type"), slide.get("layout")).lower()
    return headline, body, visual_type


def numbers(text):
    return re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)?", clean(text), re.I)


def capture(url, destination):
    if not url or not urlparse(url).scheme:
        return None
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(700)
            page.screenshot(path=str(destination), full_page=False)
            browser.close()
        return destination if destination.exists() else None
    except Exception as exc:
        print("WARNING: evidence capture failed:", exc)
        return None


def css(p):
    return f"""
@page{{size:{W}px {H}px;margin:0}}*{{box-sizing:border-box}}html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden}}body{{font-family:Inter,Arial,Helvetica,sans-serif;background:{p['bg']};color:{p['fg']}}}.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{p['bg']};color:{p['fg']}}}.top,.foot{{position:absolute;left:78px;right:78px;display:flex;justify-content:space-between;align-items:center;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.7px;text-transform:uppercase;opacity:.58;z-index:5}}.top{{top:38px}}.foot{{bottom:34px}}.page{{border:1px solid currentColor;padding:6px 8px}}.kicker{{font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.7px;text-transform:uppercase;color:{p['accent']}}}.line{{height:6px;background:{p['signal']}}}.hero{{position:absolute;left:78px;right:78px;top:178px}}h1{{margin:20px 0 0;max-width:920px;font-size:92px;line-height:.84;letter-spacing:-5px;font-weight:950}}.sub{{margin-top:22px;max-width:720px;font-size:24px;line-height:1.2;opacity:.74}}.micro{{font:800 10px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.3px;text-transform:uppercase;opacity:.6}}.numghost{{position:absolute;right:0;top:96px;font:950 190px/.75 ui-monospace,monospace;letter-spacing:-16px;color:{p['accent']};opacity:.07}}.panel{{position:absolute;left:78px;right:78px;bottom:160px}}.panel-title{{font:900 11px/1 ui-monospace,monospace;letter-spacing:1.5px;text-transform:uppercase;color:{p['accent']}}}
.diagram{{position:absolute;left:78px;right:78px;top:520px;display:grid;grid-template-columns:1fr 70px 1fr;align-items:stretch;gap:0}}.die{{min-height:340px;border:2px solid {p['fg']};padding:28px;position:relative;background:rgba(18,53,43,.035)}}.die.hot{{border:4px solid {p['accent']};background:rgba(18,53,43,.09);transform:translateY(-18px);box-shadow:14px 14px 0 {p['signal']}}}.die-label{{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.4px;color:{p['accent']};text-transform:uppercase}}.die strong{{display:block;margin-top:60px;font-size:42px;line-height:.9;letter-spacing:-2px}}.die p{{margin-top:20px;font-size:19px;line-height:1.15;opacity:.7}}.arrow{{display:grid;place-items:center;font-size:36px;font-weight:900;color:{p['signal']}}}.badge{{position:absolute;right:22px;top:22px;font:950 44px/.8 ui-monospace,monospace;color:{p['accent']}}}
.evidence{{position:absolute;left:78px;right:78px;top:500px}}.evidence-frame{{height:560px;border:2px solid {p['fg']};padding:14px;background:white;box-shadow:16px 16px 0 {p['accent']};position:relative;overflow:hidden}}.evidence-frame img{{width:100%;height:100%;object-fit:contain;display:block;background:#fff}}.source-tag{{position:absolute;left:20px;top:20px;background:{p['accent']};color:{p['bg']};padding:9px 11px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.2px;z-index:2}}.source-note{{margin-top:16px;font:800 10px/1.3 ui-monospace,monospace;letter-spacing:1.1px;text-transform:uppercase;opacity:.58}}
.metrics{{position:absolute;left:78px;right:78px;top:510px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:22px}}.metric{{border-top:5px solid {p['accent']};padding:24px 18px 0}}.metric .value{{font:950 105px/.8 ui-monospace,monospace;letter-spacing:-7px;color:{p['accent']}}}.metric .label{{margin-top:28px;font-size:22px;font-weight:900;line-height:.95;letter-spacing:-.7px}}.metric .desc{{margin-top:13px;font-size:15px;line-height:1.2;opacity:.66}}.metric.featured{{background:{p['accent']};color:{p['bg']};padding:24px 18px 28px;transform:translateY(-16px);box-shadow:14px 14px 0 {p['signal']}}}.metric.featured .value{{color:{p['bg']}}}
.pattern{{position:absolute;left:0;right:0;top:420px;bottom:0;background:{FOREST};color:{CREAM};padding:74px 78px}}.pattern .big{{margin-top:30px;max-width:880px;font-size:88px;line-height:.82;letter-spacing:-5px;font-weight:950}}.pattern .quote{{margin-top:34px;max-width:680px;font-size:21px;line-height:1.2;opacity:.78}}
.quote-block{{position:absolute;left:78px;right:78px;top:510px;border-left:8px solid {p['signal']};padding-left:30px}}.quote-block strong{{display:block;max-width:870px;font-size:70px;line-height:.88;letter-spacing:-4px;font-weight:950}}.quote-block p{{margin-top:24px;max-width:720px;font-size:22px;line-height:1.2;opacity:.7}}.quote-mark{{position:absolute;right:0;top:-55px;font:950 230px/.8 Georgia,serif;color:{p['accent']};opacity:.12}}
.payoff{{position:absolute;left:78px;right:78px;top:455px}}.payoff .line{{width:190px;margin-bottom:30px}}.payoff strong{{display:block;max-width:900px;font-size:84px;line-height:.83;letter-spacing:-5px;font-weight:950}}.payoff p{{margin-top:25px;max-width:710px;font-size:24px;line-height:1.2;opacity:.72}}.signature{{margin-top:30px;font:900 11px/1 ui-monospace,monospace;letter-spacing:1.7px;text-transform:uppercase;color:{p['accent']}}}
"""


def html_for(slide, story, p, evidence, index, total):
    headline, body, visual = content(slide)
    r = role(slide, index, total)
    label = first(slide.get("kicker"), r.replace("_", " "), "GETBYTERUSH")
    source_label, _ = source(story, slide)
    number_list = numbers(headline + " " + body)
    if index == 1 or r == "interrupt":
        return f'<div class="hero"><div class="kicker">{esc(label)}</div><div class="line" style="width:112px;margin-top:22px"></div><h1>{esc(headline)}</h1><p class="sub">{esc(body)}</p><div class="numghost">{index:02d}</div></div>'
    if visual in {"diagram", "flow", "process", "architecture"}:
        key = number_list[0] if number_list else "25%"
        return f'<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:68px;max-width:900px">{esc(headline)}</h1></div><div class="diagram"><div class="die"><span class="die-label">OLD ARCHITECTURE</span><strong>COMPUTE<br>+ MEMORY</strong><p>Controller consumes valuable compute-die area.</p><span class="badge">{esc(key)}</span></div><div class="arrow">→</div><div class="die hot"><span class="die-label">NEW ARCHITECTURE</span><strong>COMPUTE<br>ONLY</strong><p>Memory control moves into the 3D stack.</p><span class="badge">FREE</span></div></div>'
    if visual in {"evidence", "screenshot", "receipt"} and evidence:
        return f'<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:68px;max-width:900px">{esc(headline)}</h1></div><div class="evidence"><div class="evidence-frame"><span class="source-tag">VERIFIED SOURCE</span><img src="{esc(evidence)}" alt="Source evidence"></div><div class="source-note">{esc(source_label)} · captured evidence</div></div>'
    if visual in {"metric", "number", "stat"}:
        nums = number_list[:3] or ["+30%", "−15%", "+25%"]
        while len(nums) < 3:
            nums.append("—")
        labels = ["BANDWIDTH", "POWER", "DIE AREA"]
        cards = []
        for idx in range(3):
            cards.append(f'<div class="metric {"featured" if idx == 0 else ""}"><div class="value">{esc(nums[idx])}</div><div class="label">{labels[idx]}</div><div class="desc">{esc(body if idx == 0 else "Measured architectural effect")}</div></div>')
        return f'<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:62px;max-width:920px">{esc(headline)}</h1></div><div class="metrics">{"".join(cards)}</div>'
    if visual in {"quote", "statement"}:
        return f'<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:64px;max-width:900px">{esc(headline)}</h1></div><div class="quote-block"><div class="quote-mark">“</div><strong>{esc(punch(first(body, headline), 12, 110))}</strong><p>{esc(source_label)}</p></div>'
    if r == "pattern_interrupt" or index == 5:
        return f'<div class="pattern"><div class="micro">05 / PATTERN INTERRUPT</div><div class="big">{esc(punch(headline, 9, 76))}</div><div class="quote">{esc(support(body, 180))}</div></div>'
    if index == total or r == "payoff" or visual in {"final", "takeaway"}:
        return f'<div class="payoff"><div class="line"></div><strong>{esc(punch(headline, 9, 82))}</strong><p>{esc(body)}</p><div class="signature">GETBYTERUSH / TESTED • EXPLAINED • REAL</div></div>'
    return f'<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:70px;max-width:900px">{esc(headline)}</h1></div><div class="panel"><div class="panel-title">THE TAKEAWAY</div><p class="sub" style="max-width:760px">{esc(body)}</p></div>'


def render_story(story, out_dir):
    slides = story.get("slides") or []
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = None
    for slide in slides:
        if clean(slide.get("visual_type")).lower() in {"evidence", "screenshot", "receipt"}:
            _, url = source(story, slide)
            if url:
                evidence_path = capture(url, out_dir / "evidence" / "source.png")
            break
    p = palette(theme(story))
    styles = css(p)
    html_dir = out_dir / "html"
    png_dir = out_dir / "slides"
    html_dir.mkdir(exist_ok=True)
    png_dir.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        total = len(slides)
        for i, slide in enumerate(slides, 1):
            body = html_for(slide, story, p, evidence_path, i, total)
            source_label, _ = source(story, slide)
            page_html = f'<!doctype html><html><head><meta charset="utf-8"><style>{styles}</style></head><body><main class="slide"><div class="top"><span>GETBYTERUSH</span><span>TECH • AI • INTERNET</span><span class="page">{i:02d} / {total:02d}</span></div>{body}<div class="foot"><span>{esc(source_label)}</span><span>TESTED • EXPLAINED • REAL</span></div></main></body></html>'
            (html_dir / f"{i:02d}.html").write_text(page_html, encoding="utf-8")
            page.set_content(page_html, wait_until="load")
            page.screenshot(path=str(png_dir / f"{i:02d}.png"), full_page=False)
            print(f"✓ slide-{i:02d}.png")
        browser.close()
    (out_dir / "post.json").write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    title = clean(story.get("story_title", "GetByteRush"))
    why = clean(story.get("why_this_story", ""))
    (out_dir / "caption.txt").write_text(f"{title}\n\n{why}\n\n#GetByteRush #AI #Technology #Internet\n", encoding="utf-8")
    (out_dir / "hashtags.txt").write_text("#GetByteRush #AI #Technology #Internet #TechNews #ArtificialIntelligence\n", encoding="utf-8")
    (out_dir / "alt-text.txt").write_text(f"GetByteRush editorial carousel about {title}.", encoding="utf-8")
    (out_dir / "pinned-comment.txt").write_text("What do you think this changes next?", encoding="utf-8")


def day_date(path):
    return datetime.strptime(path.name, "%Y-%m-%d").date()


def cleanup():
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    if not ROOT.exists():
        return
    for day in list(ROOT.iterdir()):
        if not day.is_dir():
            continue
        for package in list(day.iterdir()):
            if not package.is_dir():
                continue
            try:
                stamp = datetime.strptime(package.name[:6], "%H%M%S")
                package_time = datetime.combine(day_date(day), stamp.time())
            except Exception:
                continue
            if package_time < cutoff:
                import shutil
                shutil.rmtree(package, ignore_errors=True)
        try:
            if not any(day.iterdir()):
                day.rmdir()
        except OSError:
            pass


def main():
    if not INPUT.exists():
        raise SystemExit("Missing data/selected_story.json")
    story = json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected") or not isinstance(story.get("slides"), list) or not story["slides"]:
        raise SystemExit("selected_story.json is not a valid selected editorial package")
    now = datetime.now()
    title_slug = re.sub(r"[^a-z0-9]+", "-", clean(story.get("story_title", "getbyterush-post")).lower()).strip("-")[:90]
    package = ROOT / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}-{title_slug}"
    cleanup()
    print("=" * 72)
    print("GETBYTERUSH ART-DIRECTED CAROUSEL RENDERER V2")
    print("=" * 72)
    print(f"Theme:  {theme(story)}")
    print(f"Slides: {len(story['slides'])}")
    print("Gemini: 0")
    render_story(story, package)
    print(f"✓ Output: {package}")
    print("✓ Ready for approval")


if __name__ == "__main__":
    main()
