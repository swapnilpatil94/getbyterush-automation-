#!/usr/bin/env python3
import base64
import html
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

W, H = 1080, 1350
INPUT = Path("data/selected_story.json")
ROOT = Path("output/posts")
RETENTION_DAYS = 7
CREAM = "#F2EBDD"
INK = "#0B0D0C"
FOREST = "#12382E"
RED = "#B70C07"
GOLD = "#C8A45A"
BLUE = "#426A78"
LIME = "#B7E32B"
LEAK = re.compile(r"(callout graphic|visual concept|visual direction|visual strategy|design direction|layout instruction|highlight that|data graphic showing|contrast visual between|illustrate that|graphic showing|render this|create a|clean typography layout|diagram comparing|official diagram schematic|featured quote block|data metric visualization|summary graphics card)", re.I)


def clean(value):
    if isinstance(value, list): value = " ".join(str(x) for x in value)
    if isinstance(value, dict): return ""
    return re.sub(r"\s+", " ", str(value or "")).strip()

def esc(value): return html.escape(clean(value), quote=True)
def first(*values):
    for value in values:
        value = clean(value)
        if value: return value
    return ""
def words(text): return re.findall(r"\b[\w’'-]+\b", clean(text))

def punch(text, max_words=8, max_chars=66):
    text = clean(text)
    if not text: return "GetByteRush"
    if len(words(text)) <= max_words and len(text) <= max_chars: return text.rstrip(" .")
    sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    if len(words(sentence)) <= max_words and len(sentence) <= max_chars: return sentence.rstrip(" .")
    out = " ".join(words(text)[:max_words])
    if len(out) > max_chars: out = out[:max_chars].rsplit(" ", 1)[0]
    return out.rstrip(" ,.;:") + "…"

def support(text, max_chars=118):
    text = clean(text)
    if not text or LEAK.search(text): return ""
    if len(text) <= max_chars: return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"

def source(story, slide):
    src = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    return first(slide.get("source_label"), src.get("source"), story.get("source"), "Source")[:100], first(slide.get("asset_url"), slide.get("source_url"), src.get("url"), story.get("source_url"))

def theme(story): return "signal" if any(x in first(story.get("visual_production_notes"), story.get("emotional_mode")).lower() for x in ("red", "tension", "urgent", "conflict")) else "editorial"
def palette(name): return {"bg": CREAM, "fg": INK, "accent": RED, "secondary": FOREST} if name == "signal" else {"bg": CREAM, "fg": INK, "accent": FOREST, "secondary": RED}

def role(slide, i, total):
    explicit = first(slide.get("role"), slide.get("scene_role")).lower().replace(" ", "_")
    if explicit: return explicit
    vt = first(slide.get("visual_type"), slide.get("layout")).lower()
    if i == 1: return "hook"
    if vt in {"evidence", "screenshot", "receipt"}: return "evidence"
    if vt in {"metric", "number", "stat"}: return "metrics"
    if vt in {"quote", "statement"}: return "statement"
    if i == total: return "payoff"
    if vt in {"diagram", "flow", "process", "architecture"}: return "diagram"
    return "editorial"

def content(slide):
    return punch(first(slide.get("headline"), slide.get("title"), slide.get("hook"), slide.get("text")), 9, 70), support(first(slide.get("body"), slide.get("supporting_text"), slide.get("copy"), slide.get("description")), 125)

def extract_numbers(text):
    # Ignore embedded product/version numbers such as HBM4E; accept only meaningful metric units.
    return re.findall(r"(?<![A-Za-z])[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)(?![A-Za-z])", clean(text), re.I)

def metric_points(slide, headline, body):
    raw = slide.get("data_points") or slide.get("stats") or slide.get("metrics") or []
    out = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                v, l, d = first(item.get("value"), item.get("number"), item.get("stat")), first(item.get("label"), item.get("title"), item.get("name")), support(first(item.get("description"), item.get("body")), 70)
                if v and l: out.append((v, l, d))
    if out: return out[:3]
    full = headline + " " + body
    nums = extract_numbers(full)
    unique = []
    seen = set()
    for n in nums:
        norm = re.sub(r"\s+", "", n).replace("−", "-")
        if norm not in seen:
            seen.add(norm); unique.append(n)
    lower = full.lower(); points = []
    for n in unique[:3]:
        pos = lower.find(n.lower().replace("−", "-")); window = lower[max(0, pos-80):pos+110] if pos >= 0 else lower
        if "bandwidth" in window: lab = "BANDWIDTH"
        elif "power" in window: lab = "POWER"
        elif "die" in window or "compute space" in window or "space" in window: lab = "COMPUTE SPACE"
        elif "latency" in window: lab = "LATENCY"
        elif "memory" in window: lab = "MEMORY"
        else: lab = "KEY RESULT"
        points.append((n, lab, ""))
    return points

def capture(url, destination):
    if not url or not urlparse(url).scheme: return None
    destination = Path(destination).resolve(); destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=30000); page.wait_for_timeout(900); page.screenshot(path=str(destination), full_page=False); browser.close()
        return destination if destination.exists() else None
    except Exception as exc:
        print("WARNING: evidence capture failed:", exc); return None

def image_data_uri(path):
    if not path or not Path(path).exists(): return ""
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")

def css(p):
    return f"""
@page{{size:{W}px {H}px;margin:0}}*{{box-sizing:border-box}}html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden}}body{{font-family:Inter,Arial,Helvetica,sans-serif;background:{p['bg']};color:{p['fg']}}}.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{p['bg']};color:{p['fg']}}}.top,.foot{{position:absolute;left:58px;right:58px;display:flex;justify-content:space-between;align-items:center;z-index:20;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.5px;text-transform:uppercase}}.top{{top:34px}}.foot{{bottom:30px;opacity:.55}}.page{{border:1px solid currentColor;padding:7px 9px}}.kicker{{font:900 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.8px;text-transform:uppercase;color:{p['accent']}}}.micro{{font:800 10px/1.25 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.3px;text-transform:uppercase;opacity:.65}}.rule{{height:5px;background:{p['accent']}}}.hero{{position:absolute;left:58px;right:58px;top:160px}}h1{{margin:18px 0 0;max-width:930px;font-size:92px;line-height:.84;letter-spacing:-5px;font-weight:950}}.sub{{margin:20px 0 0;max-width:720px;font-size:20px;line-height:1.18;opacity:.7}}.ghost{{position:absolute;right:-6px;top:-26px;font:950 230px/.7 ui-monospace,monospace;letter-spacing:-18px;color:{p['fg']};opacity:.045}}
.hook-grid{{position:absolute;left:58px;right:58px;top:455px;bottom:105px;display:grid;grid-template-columns:1.48fr .78fr;gap:16px}}.hook-red{{background:{RED};color:{CREAM};padding:28px;position:relative;overflow:hidden}}.hook-red .big{{font-size:70px;line-height:.83;letter-spacing:-4px;font-weight:950;max-width:610px;margin-top:34px}}.hook-red:after{{content:"";position:absolute;left:28px;right:28px;bottom:25px;height:1px;background:rgba(242,235,221,.45)}}.hook-black{{background:{INK};color:{CREAM};padding:28px;position:relative;overflow:hidden}}.hook-black .symbol{{position:absolute;right:10px;bottom:12px;font:950 190px/.65 Arial;transform:rotate(-12deg);color:{RED};opacity:.8}}.hook-black .small{{position:absolute;left:28px;right:28px;bottom:30px;font-size:20px;line-height:1.05;font-weight:900}}
.split{{position:absolute;left:58px;right:58px;top:480px;bottom:105px;display:grid;grid-template-columns:1fr 1fr;gap:16px}}.block{{padding:28px;position:relative;overflow:hidden}}.block.light{{background:{CREAM};border:2px solid {INK}}}.block.dark{{background:{INK};color:{CREAM}}}.block.signal{{background:{RED};color:{CREAM}}}.block.forest{{background:{FOREST};color:{CREAM}}}.block .num{{position:absolute;right:18px;top:10px;font:950 78px/.8 ui-monospace,monospace;opacity:.12}}.block .label{{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.4px;text-transform:uppercase;opacity:.68}}.block strong{{display:block;margin-top:52px;font-size:48px;line-height:.88;letter-spacing:-2.5px;font-weight:950}}.block p{{margin-top:20px;max-width:390px;font-size:16px;line-height:1.18;opacity:.7}}
.evidence-wrap{{position:absolute;left:58px;right:58px;top:455px;bottom:102px}}.evidence-frame{{height:625px;background:#fff;border:2px solid {INK};padding:12px;position:relative;overflow:hidden;box-shadow:18px 18px 0 {FOREST}}}.evidence-frame img{{width:100%;height:100%;object-fit:contain;display:block;background:#fff}}.evidence-tag{{position:absolute;left:18px;top:18px;background:{RED};color:{CREAM};padding:9px 11px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.2px;z-index:2}}.evidence-caption{{margin-top:16px;display:flex;justify-content:space-between;font:800 10px/1.2 ui-monospace,monospace;letter-spacing:1.1px;text-transform:uppercase;opacity:.58}}
.metric-row{{position:absolute;left:58px;right:58px;top:500px;bottom:105px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px;align-items:start}}.metric{{min-height:400px;border-top:6px solid {INK};padding:22px 18px;position:relative}}.metric:nth-child(2){{background:{FOREST};color:{CREAM};border-top-color:{FOREST};transform:translateY(22px);box-shadow:13px 13px 0 {RED}}}.metric .value{{font:950 88px/.8 ui-monospace,monospace;letter-spacing:-7px;color:{RED}}}.metric:nth-child(2) .value{{color:{CREAM}}}.metric .label{{margin-top:38px;font-size:21px;line-height:.92;font-weight:950;letter-spacing:-.7px}}.metric .desc{{margin-top:15px;font-size:14px;line-height:1.2;opacity:.68}}
.statement-band{{position:absolute;left:0;right:0;top:420px;bottom:0;background:{INK};color:{CREAM};padding:60px 58px}}.statement-band.signal{{background:{RED};color:{CREAM}}}.statement-band .accent{{width:150px;height:6px;background:{RED};margin-bottom:30px}}.statement-band.signal .accent{{background:{CREAM}}}.statement-band strong{{display:block;max-width:900px;font-size:76px;line-height:.83;letter-spacing:-4.5px;font-weight:950}}.statement-band p{{margin-top:26px;max-width:680px;font-size:18px;line-height:1.18;opacity:.7}}
.payoff-wrap{{position:absolute;left:58px;right:58px;top:420px;bottom:98px;background:{INK};color:{CREAM};padding:60px 52px;overflow:hidden}}.payoff-wrap:after{{content:"→";position:absolute;right:-8px;bottom:-72px;font:950 280px/.7 Arial;color:{RED};opacity:.85}}.payoff-wrap .accent{{width:150px;height:6px;background:{LIME};margin-bottom:30px}}.payoff-wrap strong{{display:block;max-width:820px;font-size:78px;line-height:.83;letter-spacing:-4.5px;font-weight:950}}.payoff-wrap p{{margin-top:24px;max-width:650px;font-size:19px;line-height:1.18;opacity:.7}}.signature{{position:absolute;left:52px;bottom:30px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.5px;text-transform:uppercase;color:{GOLD}}}
"""

def html_for(slide, story, p, evidence_uri, i, total):
    headline, body = content(slide); r = role(slide, i, total); label = first(slide.get("kicker"), r.replace("_", " "), "GETBYTERUSH"); source_label, _ = source(story, slide)
    if r == "hook": return f'''<div class="hook-grid"><div class="hook-red"><div class="micro">01 / {esc(label)}</div><div class="big">{esc(punch(headline, 7, 54))}</div></div><div class="hook-black"><div class="micro">GETBYTERUSH / TECH • AI • INTERNET</div><div class="symbol">↗</div><div class="small">{esc(support(body, 75))}</div></div></div>'''
    if r == "evidence" and evidence_uri: return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:64px;max-width:900px">{esc(headline)}</h1></div><div class="evidence-wrap"><div class="evidence-frame"><span class="evidence-tag">VERIFIED EVIDENCE</span><img src="{evidence_uri}" alt="Verified source evidence"></div><div class="evidence-caption"><span>{esc(source_label)}</span><span>{i:02d} / {total:02d}</span></div></div>'''
    if r == "metrics":
        pts = metric_points(slide, headline, body); cards = [f'<div class="metric"><div class="value">{esc(v)}</div><div class="label">{esc(l)}</div><div class="desc">{esc(d)}</div></div>' for v,l,d in pts[:3]]
        if cards: return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:60px;max-width:900px">{esc(headline)}</h1></div><div class="metric-row">{"".join(cards)}</div>'''
        return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:62px;max-width:900px">{esc(headline)}</h1></div><div class="statement-band"><div class="accent"></div><strong>{esc(punch(body, 11, 98))}</strong></div>'''
    if r == "diagram":
        nums = extract_numbers(headline + " " + body); stat = nums[0] if nums else ""; left = first(slide.get("diagram_left"), slide.get("left_label"), "THE BOTTLENECK"); right = first(slide.get("diagram_right"), slide.get("right_label"), "THE SHIFT"); left_copy = support(first(slide.get("diagram_left_body"), slide.get("left_body")), 75); right_copy = support(first(slide.get("diagram_right_body"), slide.get("right_body")), 75)
        return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:62px;max-width:900px">{esc(headline)}</h1><p class="sub">{esc(body)}</p></div><div class="split"><div class="block light"><div class="label">{esc(left)}</div><div class="num">01</div><strong>{esc(punch(left_copy or body, 7, 46))}</strong><p>{esc(left_copy)}</p></div><div class="block forest"><div class="label">{esc(right)}</div><div class="num">02</div><strong>{esc(punch(right_copy or headline, 7, 46))}</strong><p>{esc(right_copy or (stat + " is the key signal." if stat else body))}</p></div></div>'''
    if r == "statement": return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:64px;max-width:900px">{esc(headline)}</h1></div><div class="statement-band {"signal" if i == 5 else ""}"><div class="accent"></div><strong>{esc(punch(body or headline, 10, 94))}</strong><p>{esc(source_label)}</p></div>'''
    if r == "payoff": return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:68px;max-width:900px">{esc(headline)}</h1></div><div class="payoff-wrap"><div class="accent"></div><strong>{esc(punch(headline, 9, 86))}</strong><p>{esc(body)}</p><div class="signature">GETBYTERUSH / TESTED • EXPLAINED • REAL</div></div>'''
    return f'''<div class="hero"><div class="kicker">{esc(label)}</div><h1 style="font-size:68px;max-width:900px">{esc(headline)}</h1></div><div class="split"><div class="block dark"><div class="label">{esc(label)}</div><div class="num">{i:02d}</div><strong>{esc(punch(headline, 7, 48))}</strong><p>{esc(support(body, 85))}</p></div><div class="block signal"><div class="label">THE TAKEAWAY</div><strong>{esc(punch(body or headline, 8, 48))}</strong><p>{esc(source_label)}</p></div></div>'''

def render_story(story, out_dir):
    slides = story.get("slides") or []; out_dir.mkdir(parents=True, exist_ok=True); evidence_path = None
    for slide in slides:
        if role(slide, int(slide.get("number", 0) or 0), len(slides)) == "evidence":
            _, url = source(story, slide)
            if url: evidence_path = capture(url, out_dir / "evidence" / "source.png")
            break
    p = palette(theme(story)); styles = css(p); html_dir = out_dir / "html"; png_dir = out_dir / "slides"; html_dir.mkdir(exist_ok=True); png_dir.mkdir(exist_ok=True); evidence_uri = image_data_uri(evidence_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]); page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1); total = len(slides)
        for i, slide in enumerate(slides, 1):
            body_html = html_for(slide, story, p, evidence_uri, i, total); source_label, _ = source(story, slide); page_html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{styles}</style></head><body><main class="slide"><div class="top"><span>GETBYTERUSH</span><span>TECH • AI • INTERNET</span><span class="page">{i:02d} / {total:02d}</span></div>{body_html}<div class="foot"><span>{esc(source_label)}</span><span>TESTED • EXPLAINED • REAL</span></div></main></body></html>'''; (html_dir / f"{i:02d}.html").write_text(page_html, encoding="utf-8"); page.set_content(page_html, wait_until="load"); page.screenshot(path=str(png_dir / f"{i:02d}.png"), full_page=False); print(f"✓ slide-{i:02d}.png")
        browser.close()
    (out_dir / "post.json").write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); title = clean(story.get("story_title", "GetByteRush")); why = clean(story.get("why_this_story", "")); (out_dir / "caption.txt").write_text(f"{title}\n\n{why}\n\n#GetByteRush #AI #Technology #Internet\n", encoding="utf-8"); (out_dir / "hashtags.txt").write_text("#GetByteRush #AI #Technology #Internet #TechNews #ArtificialIntelligence\n", encoding="utf-8"); (out_dir / "alt-text.txt").write_text(f"GetByteRush editorial carousel about {title}.", encoding="utf-8"); (out_dir / "pinned-comment.txt").write_text(first(story.get("pinned_comment"), "What changes next?"), encoding="utf-8")

def cleanup():
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    if not ROOT.exists(): return
    for day in list(ROOT.iterdir()):
        if not day.is_dir(): continue
        for package in list(day.iterdir()):
            if not package.is_dir(): continue
            try: stamp = datetime.strptime(package.name[:6], "%H%M%S"); package_time = datetime.combine(datetime.strptime(day.name, "%Y-%m-%d").date(), stamp.time())
            except Exception: continue
            if package_time < cutoff: shutil.rmtree(package, ignore_errors=True)
        try:
            if not any(day.iterdir()): day.rmdir()
        except OSError: pass

def main():
    if not INPUT.exists(): raise SystemExit("Missing data/selected_story.json")
    story = json.loads(INPUT.read_text(encoding="utf-8"))
    if not story.get("selected") or not isinstance(story.get("slides"), list) or not story["slides"]: raise SystemExit("selected_story.json is not a valid selected editorial package")
    now = datetime.now(); title_slug = re.sub(r"[^a-z0-9]+", "-", clean(story.get("story_title", "getbyterush-post")).lower()).strip("-")[:90]; package = ROOT / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}-{title_slug}"; cleanup(); print("=" * 72); print("GETBYTERUSH EDITORIAL POSTER RENDERER V4.2"); print("=" * 72); print(f"Theme:  {theme(story)}"); print(f"Slides: {len(story['slides'])}"); print("Gemini: 0"); render_story(story, package); print(f"✓ Output: {package}"); print("✓ Ready for visual QA")

if __name__ == "__main__": main()
