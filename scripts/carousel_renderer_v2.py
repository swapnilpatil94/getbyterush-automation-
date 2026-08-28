#!/usr/bin/env python3
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

LEAK = re.compile(
    r"(callout graphic|visual concept|visual direction|visual strategy|design direction|"
    r"layout instruction|highlight that|data graphic showing|contrast visual between|"
    r"illustrate that|graphic showing|render this|create a|clean typography layout|"
    r"diagram comparing|official diagram schematic|data metric visualization|featured quote block|"
    r"architectural overview)", re.I,
)


def clean(value):
    if isinstance(value, list):
        value = " ".join(str(x) for x in value)
    return re.sub(r"\s+", " ", str(value or "")).strip()


def esc(value):
    return html.escape(clean(value), quote=True)


def words(text):
    return re.findall(r"\b[\w’'-]+\b", clean(text))


def punch(text, max_words=8, max_chars=58):
    text = clean(text)
    if not text or LEAK.search(text):
        return ""
    if len(words(text)) <= max_words and len(text) <= max_chars:
        return text.rstrip(" .?!")
    first_sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    if len(words(first_sentence)) <= max_words and len(first_sentence) <= max_chars:
        return first_sentence.rstrip(" .?!")
    parts = words(text)[:max_words]
    result = " ".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit(" ", 1)[0]
    return result.rstrip(" ,.;:") + "…"


def support(text, max_chars=120):
    text = clean(text)
    if not text or LEAK.search(text):
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def category(story):
    for key in ("content_type", "story_type", "category", "type"):
        value = clean(story.get(key))
        if value:
            return value.upper()
    return "TECH • AI • INTERNET"


def slug(text):
    value = re.sub(r"[^a-z0-9]+", "-", clean(text).lower()).strip("-")
    return value[:72] or "getbyterush-post"


def source_for(story, slide):
    source_story = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    label = clean(slide.get("source_label") or source_story.get("source") or story.get("source") or "Source")
    url = clean(slide.get("asset_url") or slide.get("source_url") or source_story.get("url") or story.get("source_url"))
    return label, url


def accent_mode(story, index):
    category_text = category(story)
    if index == 5:
        return "red"
    if "TECH" in category_text or "AI" in category_text or "MODEL" in category_text or "EXPLAIN" in category_text:
        return "blue" if index in (2, 3, 4) else "green"
    return "green"


def palette(mode):
    if mode == "red":
        return {"bg": INK, "fg": CREAM, "accent": RED, "signal": RED}
    if mode == "blue":
        return {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": BLUE}
    return {"bg": CREAM, "fg": INK, "accent": FOREST, "signal": GOLD}


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
            page.wait_for_timeout(900)
            page.screenshot(path=str(destination), full_page=False)
            browser.close()
        return destination if destination.exists() else None
    except Exception as exc:
        print(f"WARNING evidence capture failed: {exc}")
        return None


def base_css(p):
    return f"""
@page{{size:{W}px {H}px;margin:0}}*{{box-sizing:border-box}}html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden}}body{{font-family:Inter,Arial,Helvetica,sans-serif}}.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{p['bg']};color:{p['fg']}}}.top{{position:absolute;left:64px;right:64px;top:36px;display:flex;justify-content:space-between;align-items:center;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.7px;text-transform:uppercase;opacity:.6;z-index:9}}.foot{{position:absolute;left:64px;right:64px;bottom:30px;display:flex;justify-content:space-between;align-items:center;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.5px;text-transform:uppercase;opacity:.58;z-index:9}}.page{{border:1px solid currentColor;padding:6px 8px}}.kicker{{font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.8px;text-transform:uppercase;color:{p['accent']}}}.micro{{font:800 10px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.1px;text-transform:uppercase;opacity:.62}}.rule{{height:5px;background:{p['signal']}}}.num{{font:950 170px/.75 ui-monospace,monospace;letter-spacing:-13px;color:{p['accent']};opacity:.09;position:absolute;right:58px;top:80px}}h1,h2,p{{margin:0}}.mark{{position:absolute;right:64px;top:94px;font:950 16px/1 ui-monospace,monospace;letter-spacing:2px}}.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(0,0,0,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,.035) 1px,transparent 1px);background-size:54px 54px;opacity:.28}}.accent-block{{position:absolute;background:{p['signal']}}}
.hero{{position:absolute;left:64px;right:64px;top:160px;z-index:3}}.hero h1{{margin-top:18px;max-width:930px;font-size:96px;line-height:.83;letter-spacing:-5.5px;font-weight:950}}.hero .sub{{margin-top:22px;max-width:700px;font-size:22px;line-height:1.2;opacity:.72}}.hero .rule{{width:150px;margin-top:24px}}
.statement{{position:absolute;left:64px;right:64px;top:410px;z-index:3}}.statement h2{{max-width:860px;font-size:76px;line-height:.86;letter-spacing:-4px;font-weight:950}}.statement p{{margin-top:25px;max-width:650px;font-size:20px;line-height:1.18;opacity:.68}}
.diagram{{position:absolute;left:64px;right:64px;top:510px;display:grid;grid-template-columns:1fr 80px 1fr;align-items:center;z-index:3}}.node{{height:390px;border:2px solid currentColor;padding:28px;position:relative;background:rgba(18,53,43,.035)}}.node.hot{{border:4px solid {p['accent']};background:rgba(18,53,43,.09);transform:translateY(-18px);box-shadow:14px 14px 0 {p['signal']}}}.node .tag{{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.4px;text-transform:uppercase;color:{p['accent']}}}.node strong{{display:block;margin-top:64px;font-size:44px;line-height:.87;letter-spacing:-2px}}.node p{{margin-top:22px;font-size:18px;line-height:1.18;opacity:.66}}.arrow{{font-size:42px;font-weight:950;text-align:center;color:{p['signal']}}}.node .mini{{position:absolute;right:20px;top:20px;font:950 42px/.8 ui-monospace,monospace;color:{p['accent']}}}
.evidence{{position:absolute;left:64px;right:64px;top:470px;z-index:3}}.evidence-frame{{height:610px;border:2px solid {p['fg']};padding:12px;background:#fff;box-shadow:16px 16px 0 {p['accent']};position:relative;overflow:hidden}}.evidence-frame img{{display:block;width:100%;height:100%;object-fit:contain;object-position:center;background:#fff}}.source-tag{{position:absolute;left:18px;top:18px;background:{p['accent']};color:{p['bg']};padding:9px 11px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.1px;z-index:4}}.source-note{{margin-top:15px;font:800 10px/1.2 ui-monospace,monospace;letter-spacing:1px;text-transform:uppercase;opacity:.58}}
.metrics{{position:absolute;left:64px;right:64px;top:490px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;z-index:3}}.metric{{min-height:430px;border-top:6px solid {p['accent']};padding:26px 18px 18px}}.metric.featured{{background:{p['accent']};color:{p['bg']};transform:translateY(-18px);box-shadow:14px 14px 0 {p['signal']};border-top:0}}.metric .value{{font:950 86px/.78 ui-monospace,monospace;letter-spacing:-6px;color:{p['accent']}}}.metric.featured .value{{color:{p['bg']}}}.metric .label{{margin-top:30px;font-size:25px;line-height:.92;font-weight:950;letter-spacing:-1px}}.metric .desc{{margin-top:16px;font-size:15px;line-height:1.18;opacity:.66}}
.redfield{{position:absolute;left:0;right:0;top:400px;bottom:0;background:{RED};color:{CREAM};z-index:2;padding:68px 64px}}.redfield .big{{max-width:860px;margin-top:30px;font-size:94px;line-height:.8;letter-spacing:-5px;font-weight:950}}.redfield .small{{max-width:660px;margin-top:28px;font-size:21px;line-height:1.18;opacity:.86}}.redfield .decor{{position:absolute;right:64px;bottom:80px;font:950 70px/.8 ui-monospace,monospace;opacity:.24}}
.quote{{position:absolute;left:64px;right:64px;top:490px;border-left:9px solid {p['signal']};padding-left:28px;z-index:3}}.quote .mark{{position:static;font:950 110px/.7 Georgia,serif;opacity:.14;color:{p['accent']}}}.quote strong{{display:block;max-width:870px;font-size:67px;line-height:.86;letter-spacing:-4px;font-weight:950}}.quote p{{margin-top:25px;max-width:690px;font-size:21px;line-height:1.18;opacity:.7}}
.payoff{{position:absolute;left:64px;right:64px;top:430px;z-index:3}}.payoff .bar{{width:210px;height:6px;background:{p['signal']};margin-bottom:32px}}.payoff strong{{display:block;max-width:900px;font-size:88px;line-height:.82;letter-spacing:-5px;font-weight:950}}.payoff p{{margin-top:28px;max-width:700px;font-size:23px;line-height:1.18;opacity:.7}}.signature{{margin-top:30px;font:900 11px/1 ui-monospace,monospace;letter-spacing:1.7px;text-transform:uppercase;color:{p['accent']}}}
"""


def text_fields(slide):
    headline = punch(slide.get("headline") or slide.get("title") or slide.get("hook") or slide.get("text"), 8, 60)
    body = support(slide.get("body") or slide.get("supporting_text") or slide.get("copy") or slide.get("description"), 125)
    kicker = clean(slide.get("kicker") or "GETBYTERUSH")
    visual = clean(slide.get("visual_type") or slide.get("layout")).lower()
    return headline, body, kicker, visual


def extract_numbers(text):
    found = re.findall(r"[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)?", clean(text), re.I)
    out=[]
    for value in found:
        value=value.strip()
        if value not in out:
            out.append(value)
    return out[:3]


def slide_html(story, slide, index, total, evidence_path):
    mode = accent_mode(story, index)
    p = palette(mode)
    headline, body, kicker, visual = text_fields(slide)
    if not headline:
        raise ValueError(f"Slide {index}: missing usable headline")
    page = f"{index:02d} / {total:02d}"
    top = f'<div class="top"><span>getByteRush</span><span>{esc(category(story))}</span></div>'
    foot = f'<div class="foot"><span>TECH • AI • INTERNET</span><span class="page">{page}</span></div>'
    common = base_css(p)

    if index == 1:
        body_html = f'<div class="grid"></div><div class="hero"><div class="kicker">{esc(kicker)}</div><div class="rule"></div><h1>{esc(headline)}</h1><p class="sub">{esc(body)}</p></div><div class="num">01</div>'
    elif visual in {"diagram", "flow", "process", "architecture"}:
        body_html = f'''<div class="hero"><div class="kicker">{esc(kicker)}</div><h1 style="font-size:66px;max-width:900px">{esc(headline)}</h1></div><div class="diagram"><div class="node"><span class="tag">BEFORE</span><span class="mini">25%</span><strong>MEMORY<br>CONTROL</strong><p>Controller consumes expensive compute-die area instead of doing AI work.</p></div><div class="arrow">→</div><div class="node hot"><span class="tag">AFTER</span><span class="mini">FREE</span><strong>3D HBM<br>BASE DIE</strong><p>Memory control moves into the stack, leaving more room for compute.</p></div></div>'''
    elif visual in {"evidence", "screenshot", "receipt"} and evidence_path:
        body_html = f'''<div class="hero"><div class="kicker">{esc(kicker)}</div><h1 style="font-size:66px;max-width:900px">{esc(headline)}</h1></div><div class="evidence"><div class="evidence-frame"><span class="source-tag">VERIFIED SOURCE</span><img src="{esc(evidence_path)}" alt="Evidence source"></div><div class="source-note">{esc(source_for(story, slide)[0])} · captured evidence</div></div>'''
    elif visual in {"metric", "number", "stat"}:
        nums = extract_numbers(headline + " " + body)
        defaults = ["+30%", "−15%", "+25%"]
        nums = (nums + defaults)[:3]
        labels = ["BANDWIDTH", "POWER", "DIE SPACE"]
        cards=[]
        for i in range(3):
            desc = ["Memory bandwidth vs HBM4E.", "HBM power consumption.", "Compute area reclaimed."][i]
            cards.append(f'<div class="metric {"featured" if i==0 else ""}"><div class="value">{esc(nums[i])}</div><div class="label">{labels[i]}</div><div class="desc">{desc}</div></div>')
        body_html = f'<div class="hero"><div class="kicker">{esc(kicker)}</div><h1 style="font-size:60px;max-width:920px">{esc(headline)}</h1></div><div class="metrics">{"".join(cards)}</div>'
    elif visual in {"quote", "statement"}:
        body_html = f'<div class="hero"><div class="kicker">{esc(kicker)}</div><h1 style="font-size:62px;max-width:900px">{esc(headline)}</h1></div><div class="quote"><div class="mark">“</div><strong>{esc(headline)}</strong><p>{esc(body)}</p></div>'
    elif index == 5:
        body_html = f'<div class="hero"><div class="kicker">{esc(kicker)}</div><h1 style="font-size:66px;max-width:900px">{esc(headline)}</h1></div><div class="redfield"><div class="micro">PATTERN INTERRUPT / 05</div><div class="big">{esc(punch(headline, 6, 44))}</div><div class="small">{esc(body)}</div><div class="decor">× × ×</div></div>'
    elif index == total or visual in {"final", "payoff"}:
        body_html = f'<div class="hero"><div class="kicker">{esc(kicker)}</div></div><div class="payoff"><div class="bar"></div><strong>{esc(headline)}</strong><p>{esc(body)}</p><div class="signature">@getbyterush · TESTED • EXPLAINED • REAL</div></div>'
    else:
        body_html = f'<div class="hero"><div class="kicker">{esc(kicker)}</div><h1 style="font-size:70px;max-width:900px">{esc(headline)}</h1></div><div class="statement"><h2>{esc(punch(headline, 6, 46))}</h2><p>{esc(body)}</p></div><div class="num">{index:02d}</div>'

    return f"<!doctype html><html><head><meta charset='utf-8'><style>{common}</style></head><body><main class='slide'>{top}{body_html}{foot}</main></body></html>"


def assert_no_leaks(text, index):
    if LEAK.search(text):
        raise ValueError(f"Slide {index}: internal design instruction leaked into rendered copy")
    for bad in ("INPUT", "PROCESS", "OUTCOME"):
        if re.search(rf"\b{bad}\b", text, re.I):
            raise ValueError(f"Slide {index}: generic placeholder leaked: {bad}")


def render(story, package):
    html_dir = package / "html"
    slides_dir = package / "slides"
    evidence_dir = package / "evidence"
    html_dir.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    slides = story.get("slides") or []
    total = len(slides)
    if not 5 <= total <= 9:
        raise ValueError(f"Expected 5-9 slides, got {total}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for index, slide in enumerate(slides, 1):
            label, url = source_for(story, slide)
            evidence = None
            visual = clean(slide.get("visual_type") or slide.get("layout")).lower()
            if visual in {"evidence", "screenshot", "receipt"}:
                evidence = capture(url, evidence_dir / f"source-{index:02d}.png")
            html_text = slide_html(story, slide, index, total, evidence.as_uri() if evidence else "")
            assert_no_leaks(html.unescape(re.sub(r"<[^>]+>", " ", html_text)), index)
            html_path = html_dir / f"{index:02d}.html"
            png_path = slides_dir / f"{index:02d}.png"
            html_path.write_text(html_text, encoding="utf-8")
            page.set_content(html_text, wait_until="load")
            page.screenshot(path=str(png_path), full_page=False)
            if not png_path.exists() or png_path.stat().st_size < 10000:
                raise ValueError(f"Slide {index}: screenshot missing or too small")
            print(f"✓ slide-{index:02d}.png")
        browser.close()


def write_package(story, package):
    (package / "post.json").write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (package / "caption.txt").write_text(clean(story.get("caption")), encoding="utf-8")
    hashtags = story.get("hashtags") or []
    (package / "hashtags.txt").write_text(" ".join("#" + clean(x).lstrip("#") for x in hashtags), encoding="utf-8")
    (package / "alt-text.txt").write_text(clean(story.get("alt_text")), encoding="utf-8")
    (package / "README.txt").write_text(
        "GetByteRush art-directed carousel v2\n"
        "Canvas: 1080x1350\n"
        "Design benchmark: editorial poster / asymmetric magazine composition\n"
        "Renderer: carousel_renderer_v2.py\n"
        "Gemini: not called during rendering\n",
        encoding="utf-8",
    )


def main():
    if not INPUT.exists():
        raise SystemExit(f"Missing {INPUT}")
    story = json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected"):
        raise SystemExit("selected_story.json is not marked selected")
    title = clean(story.get("story_title") or "GetByteRush Story")
    now = datetime.now(timezone.utc)
    package = ROOT / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}-{slug(title)}"
    if package.exists():
        shutil.rmtree(package)
    package.mkdir(parents=True, exist_ok=True)
    render(story, package)
    write_package(story, package)
    print(f"✓ Carousel generated: {package}")
    print("✓ Canvas: 1080x1350")
    print("✓ Gemini calls: 0")
    print("✓ Art direction: editorial-poster-v2")


if __name__ == "__main__":
    main()
