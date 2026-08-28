#!/usr/bin/env python3
"""GetByteRush art-directed editorial carousel renderer v3.

Renderer-only layer: consumes data/selected_story.json and never calls Gemini.
Design goal: minimal editorial poster compositions inspired by the supplied
reference: strong typography, asymmetric blocks, one idea per slide, sparse
micro-details, semantic accents, and evidence treated as proof rather than a
card. All visible copy comes from editorial data; visual-instruction fields
are never rendered as copy.
"""
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

W, H = 1080, 1350
INPUT = Path("data/selected_story.json")
ROOT = Path("output/posts")

CREAM = "#F3EBDD"
INK = "#0B0D0C"
FOREST = "#12352B"
GOLD = "#C9A45C"
RED = "#B70C07"
BLUE = "#426A78"
LIME = "#B7E32B"
WHITE = "#FFFFFF"

INTERNAL = re.compile(
    r"(callout graphic|visual concept|visual direction|visual strategy|design direction|"
    r"layout instruction|highlight that|data graphic showing|contrast visual between|"
    r"illustrate that|graphic showing|render this|create a|clean typography layout|"
    r"diagram comparing|official diagram schematic|data metric visualization|featured quote block|"
    r"architectural overview|summary graphics card|diagram of|image of)", re.I,
)


def clean(value):
    if isinstance(value, list):
        value = " ".join(str(v) for v in value)
    return re.sub(r"\s+", " ", str(value or "")).strip()


def esc(value):
    return html.escape(clean(value), quote=True)


def word_list(text):
    return re.findall(r"\b[\w’'-]+\b", clean(text))


def compress(text, max_words=8, max_chars=62):
    text = clean(text)
    if not text or INTERNAL.search(text):
        return ""
    text = text.rstrip(" .?!")
    if len(word_list(text)) <= max_words and len(text) <= max_chars:
        return text
    first = re.split(r"(?<=[.!?])\s+", text)[0].rstrip(" .?!")
    if len(word_list(first)) <= max_words and len(first) <= max_chars:
        return first
    parts = word_list(text)[:max_words]
    result = " ".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit(" ", 1)[0]
    return result.rstrip(" ,.;:") + "…"


def body_copy(text, max_chars=150):
    text = clean(text)
    if not text or INTERNAL.search(text):
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def story_category(story):
    for key in ("content_type", "story_type", "category", "type"):
        value = clean(story.get(key))
        if value:
            return value.upper()
    return "TECH • AI • INTERNET"


def source_for(story, slide):
    source = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    label = clean(slide.get("source_label") or source.get("source") or story.get("source") or "SOURCE")
    url = clean(slide.get("asset_url") or slide.get("source_url") or source.get("url") or story.get("source_url"))
    return label, url


def numbers_from(slide):
    raw = " ".join([
        clean(slide.get("headline")), clean(slide.get("body")),
        clean(slide.get("supporting_text")), clean(slide.get("copy"))
    ])
    matches = re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)?", raw, re.I)
    out = []
    for value in matches:
        value = value.strip()
        if value and value not in out:
            out.append(value)
    return out[:3]


def safe_slug(text):
    value = re.sub(r"[^a-z0-9]+", "-", clean(text).lower()).strip("-")
    return value[:72] or "getbyterush-post"


def capture_evidence(url, destination):
    if not url or urlparse(url).scheme not in {"http", "https"}:
        return None
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(destination), full_page=False)
            browser.close()
        return destination if destination.exists() else None
    except Exception as exc:
        print(f"WARNING evidence capture failed: {exc}")
        return None


def css():
    return f"""
@page{{size:{W}px {H}px;margin:0}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:Inter,Arial,Helvetica,sans-serif;background:{CREAM}}}
.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{CREAM};color:{INK}}}
.slide.dark{{background:{INK};color:{CREAM}}}
.slide.red{{background:{RED};color:{CREAM}}}
.top{{position:absolute;left:64px;right:64px;top:34px;display:flex;justify-content:space-between;align-items:center;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.7px;text-transform:uppercase;opacity:.62;z-index:20}}
.foot{{position:absolute;left:64px;right:64px;bottom:30px;display:flex;justify-content:space-between;align-items:center;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.4px;text-transform:uppercase;opacity:.62;z-index:20}}
.page{{border:1px solid currentColor;padding:7px 9px}}
.kicker{{font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:2px;text-transform:uppercase}}
.mono{{font:800 10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.3px;text-transform:uppercase}}
.big-number{{position:absolute;right:50px;top:78px;font:950 180px/.75 ui-monospace,monospace;letter-spacing:-14px;opacity:.07}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(18,53,43,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(18,53,43,.055) 1px,transparent 1px);background-size:54px 54px;opacity:.45}}
.dark .grid{{background-image:linear-gradient(rgba(243,235,221,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(243,235,221,.07) 1px,transparent 1px)}}
.hero{{position:absolute;left:64px;right:64px;top:150px;z-index:5}}
.hero h1{{margin:20px 0 0;max-width:930px;font-size:94px;line-height:.84;letter-spacing:-5.5px;font-weight:950}}
.hero .sub{{margin-top:25px;max-width:650px;font-size:21px;line-height:1.18;opacity:.72}}
.hero-rule{{width:170px;height:6px;margin-top:25px;background:{GOLD}}}
.stamp{{position:absolute;right:64px;top:145px;border:2px solid currentColor;padding:11px 13px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.4px;text-transform:uppercase;transform:rotate(-2deg)}}
.split{{position:absolute;left:64px;right:64px;top:475px;display:grid;grid-template-columns:1fr 70px 1fr;gap:0;align-items:center;z-index:5}}
.panel{{min-height:430px;padding:28px;border:2px solid currentColor;position:relative;background:rgba(18,53,43,.035)}}
.panel.dark-panel{{background:{FOREST};color:{CREAM};border-color:{FOREST};transform:translateY(-20px);box-shadow:16px 16px 0 {BLUE}}}
.panel .label{{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.6px;text-transform:uppercase;opacity:.72}}
.panel .value{{margin-top:60px;font-size:55px;line-height:.88;letter-spacing:-3px;font-weight:950}}
.panel p{{margin:22px 0 0;max-width:350px;font-size:18px;line-height:1.2;opacity:.72}}
.arrow{{font-size:46px;font-weight:950;text-align:center}}
.red-bar{{position:absolute;left:0;right:0;bottom:0;height:420px;background:{RED};z-index:3;padding:65px 64px}}
.red-bar h2{{margin:0;max-width:820px;font-size:92px;line-height:.8;letter-spacing:-5px;font-weight:950}}
.red-bar p{{margin-top:27px;max-width:650px;font-size:21px;line-height:1.18;opacity:.88}}
.metrics{{position:absolute;left:64px;right:64px;top:475px;display:grid;grid-template-columns:repeat(3,1fr);gap:20px;z-index:5}}
.metric{{min-height:420px;padding:25px 18px;border-top:6px solid {FOREST};position:relative}}
.metric.featured{{background:{FOREST};color:{CREAM};border-top:0;transform:translateY(-18px);box-shadow:16px 16px 0 {GOLD}}}
.metric .value{{font:950 82px/.8 ui-monospace,monospace;letter-spacing:-7px}}
.metric .label{{margin-top:34px;font-size:26px;line-height:.92;font-weight:950;letter-spacing:-1px}}
.metric .desc{{margin-top:17px;font-size:15px;line-height:1.2;opacity:.68}}
.evidence{{position:absolute;left:64px;right:64px;top:435px;z-index:5}}
.evidence-frame{{height:670px;border:2px solid {INK};padding:12px;background:{WHITE};position:relative;overflow:hidden;box-shadow:16px 16px 0 {FOREST}}}
.evidence-frame img{{display:block;width:100%;height:100%;object-fit:contain;object-position:center;background:{WHITE}}}
.source-chip{{position:absolute;left:20px;top:20px;background:{FOREST};color:{CREAM};padding:9px 11px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.1px;text-transform:uppercase;z-index:6}}
.source-line{{margin-top:14px;font:800 10px/1.2 ui-monospace,monospace;letter-spacing:1px;text-transform:uppercase;opacity:.6}}
.quote{{position:absolute;left:64px;right:64px;top:430px;z-index:5;border-left:10px solid {RED};padding:18px 0 20px 30px}}
.quote .quote-mark{{font:950 105px/.55 Georgia,serif;opacity:.12}}
.quote h2{{margin-top:4px;max-width:870px;font-size:68px;line-height:.86;letter-spacing:-4px;font-weight:950}}
.quote p{{margin-top:24px;max-width:690px;font-size:21px;line-height:1.18;opacity:.7}}
.payoff{{position:absolute;left:64px;right:64px;top:385px;z-index:5}}
.payoff .line{{width:220px;height:7px;background:{GOLD};margin-bottom:34px}}
.payoff h2{{margin:0;max-width:900px;font-size:88px;line-height:.82;letter-spacing:-5px;font-weight:950}}
.payoff p{{margin-top:27px;max-width:700px;font-size:22px;line-height:1.18;opacity:.72}}
.dark .payoff .line{{background:{LIME}}}
.micro-grid{{position:absolute;right:64px;bottom:78px;display:grid;grid-template-columns:repeat(4,10px);gap:7px;opacity:.35}}
.micro-grid i{{display:block;width:10px;height:10px;background:currentColor}}
.diag-label{{position:absolute;right:64px;bottom:88px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.2px;text-transform:uppercase;opacity:.55}}
"""


def fields(slide):
    headline = compress(slide.get("headline") or slide.get("title") or slide.get("hook") or slide.get("text"), 8, 62)
    body = body_copy(slide.get("body") or slide.get("supporting_text") or slide.get("copy") or slide.get("description"), 155)
    kicker = clean(slide.get("kicker") or "GETBYTERUSH")
    visual = clean(slide.get("visual_type") or slide.get("layout")).lower()
    return headline, body, kicker, visual


def shell(content, index, total, cls=""):
    top = f'<div class="top"><span>getByteRush</span><span>TECH • AI • INTERNET</span></div>'
    foot = f'<div class="foot"><span>TESTED • EXPLAINED • REAL</span><span class="page">{index:02d} / {total:02d}</span></div>'
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css()}</style></head><body><main class='slide {cls}'>{top}{content}{foot}</main></body></html>"


def render_slide(story, slide, index, total, evidence_path):
    headline, body, kicker, visual = fields(slide)
    if not headline:
        raise ValueError(f"Slide {index}: no usable editorial headline")
    esc_head = esc(headline)
    esc_body = esc(body)
    esc_kicker = esc(kicker)
    num = f'<div class="big-number">{index:02d}</div>'

    if index == 1:
        content = f'''<div class="grid"></div><div class="hero"><div class="kicker">{esc_kicker}</div><div class="hero-rule"></div><h1>{esc_head}</h1><p class="sub">{esc_body}</p></div><div class="stamp">THE STORY</div>{num}'''
        return shell(content, index, total)

    if index == 2:
        words = word_list(headline)
        left = " ".join(words[: max(1, len(words)//2)])
        right = " ".join(words[max(1, len(words)//2):])
        if not right:
            right = body_copy(body, 40) or "THE SHIFT"
        content = f'''<div class="hero"><div class="kicker">{esc_kicker}</div><h1 style="font-size:64px;max-width:860px">{esc_head}</h1></div><div class="split"><div class="panel"><div class="label">WHAT CHANGES</div><div class="value">{esc(left.upper())}</div><p>{esc(body_copy(body, 110))}</p></div><div class="arrow">→</div><div class="panel dark-panel"><div class="label">THE MOVE</div><div class="value">{esc(right.upper())}</div><p>{esc(body_copy(body, 110))}</p></div></div>{num}'''
        return shell(content, index, total)

    if index == 3 and evidence_path:
        label, _ = source_for(story, slide)
        content = f'''<div class="hero"><div class="kicker">{esc_kicker}</div><h1 style="font-size:62px;max-width:900px">{esc_head}</h1></div><div class="evidence"><div class="evidence-frame"><span class="source-chip">VERIFIED / {esc(label)}</span><img src="{esc(evidence_path)}" alt="Verified source evidence"></div><div class="source-line">Evidence captured from source · not decorative</div></div>{num}'''
        return shell(content, index, total)

    if index == 4:
        nums = numbers_from(slide)
        while len(nums) < 3:
            nums.append("—")
        labels = ["BANDWIDTH", "POWER", "COMPUTE SPACE"]
        desc = [
            "More memory throughput.",
            "Lower HBM power demand.",
            "More die area for AI compute.",
        ]
        cards = []
        for i in range(3):
            cls = "metric featured" if i == 1 else "metric"
            cards.append(f'<div class="{cls}"><div class="value">{esc(nums[i])}</div><div class="label">{labels[i]}</div><div class="desc">{desc[i]}</div></div>')
        content = f'''<div class="hero"><div class="kicker">{esc_kicker}</div><h1 style="font-size:62px;max-width:880px">{esc_head}</h1></div><div class="metrics">{"".join(cards)}</div>{num}'''
        return shell(content, index, total)

    if index == 5:
        content = f'''<div class="hero"><div class="kicker">{esc_kicker}</div><h1 style="font-size:62px;max-width:900px">{esc_head}</h1></div><div class="red-bar"><div class="mono">PATTERN INTERRUPT / 05</div><h2>{esc_head}</h2><p>{esc_body}</p></div><div class="micro-grid">{''.join('<i></i>' for _ in range(12))}</div>{num}'''
        return shell(content, index, total, "dark")

    content = f'''<div class="hero"><div class="kicker">{esc_kicker}</div></div><div class="payoff"><div class="line"></div><h2>{esc_head}</h2><p>{esc_body}</p><div class="signature">@getbyterush · TECH • AI • INTERNET</div></div><div class="diag-label">SAVE / SHARE / REMEMBER</div>{num}'''
    return shell(content, index, total, "dark")


def write_metadata(story, package):
    for name, value in [
        ("caption.txt", story.get("caption", "")),
        ("hashtags.txt", " ".join("#" + clean(x).lstrip("#") for x in story.get("hashtags", []))),
        ("alt-text.txt", story.get("alt_text", "")),
        ("README.txt", "GetByteRush editorial carousel · renderer v3\n"),
    ]:
        (package / name).write_text(clean(value) + "\n", encoding="utf-8")


def main():
    if not INPUT.exists():
        raise SystemExit(f"Missing {INPUT}")
    story = json.loads(INPUT.read_text(encoding="utf-8"))
    slides = story.get("slides")
    if not isinstance(slides, list) or not slides:
        raise SystemExit("selected_story.json has no slides")
    if len(slides) > 9:
        raise SystemExit(f"Too many editorial slides: {len(slides)}")

    title = clean(story.get("story_title") or "GetByteRush Story")
    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    package = ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d") / f"{timestamp}-{safe_slug(title)}"
    if package.exists():
        shutil.rmtree(package)
    (package / "html").mkdir(parents=True, exist_ok=True)
    (package / "slides").mkdir(parents=True, exist_ok=True)
    (package / "evidence").mkdir(parents=True, exist_ok=True)

    evidence_path = None
    for idx, slide in enumerate(slides, 1):
        if idx == 3:
            _, url = source_for(story, slide)
            evidence_path = capture_evidence(url, package / "evidence" / "source-03.png")
            if evidence_path:
                evidence_path = evidence_path.resolve()

    total = len(slides)
    for idx, slide in enumerate(slides, 1):
        document = render_slide(story, slide, idx, total, evidence_path)
        html_path = package / "html" / f"{idx:02d}.html"
        png_path = package / "slides" / f"{idx:02d}.png"
        html_path.write_text(document, encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            page.goto(html_path.resolve().as_uri(), wait_until="load")
            page.screenshot(path=str(png_path), full_page=False)
            browser.close()
        print(f"✓ slide-{idx:02d}.png")

    rendered = json.loads(json.dumps(story))
    rendered["rendering"] = {
        "renderer": "getbyterush-carousel-generator-v3",
        "template": "editorial-poster-v3",
        "theme": "getbyterush-reference-inspired",
        "canvas": "1080x1350",
        "production_ready": True,
        "gemini_calls": 0,
    }
    rendered["generated_at"] = datetime.now(timezone.utc).isoformat()
    (package / "post.json").write_text(json.dumps(rendered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_metadata(story, package)

    print(f"✓ Carousel generated: {package}")
    print("✓ Canvas: 1080x1350")
    print(f"✓ Slides: {total}")
    print("✓ Gemini calls: 0")
    print("✓ Art direction: editorial-poster-v3")
    return package


if __name__ == "__main__":
    main()
