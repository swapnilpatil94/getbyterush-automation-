#!/usr/bin/env python3
"""
GetByteRush Carousel Generator

Input:
    data/selected_story.json

Output:
    output/posts/<slug>/
        slide-01.png ... slide-NN.png
        slide-01.html ... slide-NN.html
        caption.txt
        hashtags.txt
        pinned-comment.txt
        alt-text.txt
        post.json
        evidence.png (when source screenshot succeeds)

Requires:
    playwright
"""

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:80] or "getbyterush-post"


def esc(value):
    return html.escape(str(value or ""))


def capture_evidence(url, output_path):
    if not url:
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox"],
            )
            page = browser.new_page(
                viewport={"width": 1440, "height": 1000},
                device_scale_factor=1,
            )
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.wait_for_timeout(2500)

            # Remove obvious cookie/consent overlays when possible.
            for selector in [
                '[aria-label*="cookie" i]',
                '[id*="cookie" i]',
                '[class*="cookie" i]',
            ]:
                try:
                    page.locator(selector).first.evaluate(
                        "(el) => el.remove()"
                    )
                except Exception:
                    pass

            page.screenshot(
                path=str(output_path),
                full_page=False,
            )

            browser.close()

        return output_path.exists()

    except Exception as exc:
        print(f"⚠ Evidence screenshot failed: {exc}")
        return False


def base_css():
    return """
    @page { size: 1080px 1350px; margin: 0; }

    * { box-sizing: border-box; }

    html, body {
      margin: 0;
      padding: 0;
      width: 1080px;
      height: 1350px;
      background: #f4eddd;
    }

    body {
      font-family: Inter, Arial, Helvetica, sans-serif;
      color: #102b24;
      overflow: hidden;
    }

    .slide {
      position: relative;
      width: 1080px;
      height: 1350px;
      padding: 82px 82px 70px;
      background: #f4eddd;
      overflow: hidden;
    }

    .gold-line {
      width: 74px;
      height: 5px;
      background: #b99a55;
      margin-bottom: 28px;
    }

    .kicker {
      display: inline-block;
      border: 1.5px solid #b99a55;
      color: #102b24;
      padding: 10px 16px;
      border-radius: 999px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      margin-bottom: 32px;
    }

    .headline {
      font-size: 74px;
      line-height: 0.98;
      letter-spacing: -3px;
      font-weight: 800;
      max-width: 890px;
      margin: 0;
    }

    .body {
      margin-top: 36px;
      font-size: 31px;
      line-height: 1.25;
      max-width: 800px;
      color: #203a33;
    }

    .source {
      position: absolute;
      left: 82px;
      bottom: 56px;
      font-size: 17px;
      color: #53635e;
      max-width: 780px;
    }

    .brand {
      position: absolute;
      right: 82px;
      bottom: 54px;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 1.5px;
    }

    .number {
      font-size: 190px;
      line-height: .8;
      letter-spacing: -10px;
      font-weight: 900;
      margin: 30px 0 40px;
    }

    .card {
      margin-top: 40px;
      padding: 34px;
      border: 2px solid #102b24;
      border-radius: 24px;
      background: #f8f2e6;
    }

    .metric-row {
      display: flex;
      gap: 24px;
      margin-top: 48px;
    }

    .metric {
      flex: 1;
      padding: 34px;
      border-radius: 22px;
      border: 2px solid #102b24;
      background: #f8f2e6;
    }

    .metric .value {
      font-size: 86px;
      line-height: .9;
      font-weight: 900;
      letter-spacing: -4px;
    }

    .metric .label {
      margin-top: 20px;
      font-size: 24px;
      line-height: 1.1;
      font-weight: 700;
    }

    .arrow {
      font-size: 70px;
      font-weight: 900;
      margin: 24px 0;
      color: #b99a55;
    }

    .evidence-frame {
      position: absolute;
      left: 82px;
      right: 82px;
      bottom: 150px;
      height: 540px;
      border: 3px solid #102b24;
      border-radius: 26px;
      overflow: hidden;
      background: #fff;
    }

    .evidence-frame img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: top;
    }

    .evidence-label {
      position: absolute;
      left: 110px;
      bottom: 118px;
      background: #102b24;
      color: #f4eddd;
      padding: 10px 16px;
      border-radius: 999px;
      font-size: 18px;
      font-weight: 700;
    }

    .timeline {
      margin-top: 65px;
      border-left: 5px solid #b99a55;
      padding-left: 38px;
    }

    .timeline-item {
      margin-bottom: 44px;
    }

    .timeline-date {
      font-size: 22px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .timeline-text {
      margin-top: 8px;
      font-size: 31px;
      line-height: 1.15;
      font-weight: 700;
    }

    .quote {
      margin-top: 55px;
      padding: 42px;
      border-left: 7px solid #b99a55;
      background: #e9dfcc;
      font-size: 40px;
      line-height: 1.08;
      font-weight: 700;
    }

    .final {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding-bottom: 120px;
    }

    .final .headline {
      font-size: 82px;
    }

    .final .body {
      font-size: 35px;
      max-width: 820px;
    }
    """


def slide_html(slide, story, evidence_path, total):
    number = slide.get("number", 1)
    kicker = slide.get("kicker", "")
    headline = slide.get("headline", "")
    body = slide.get("body", "")
    visual_type = slide.get("visual_type", "typography")
    visual_concept = slide.get("visual_concept", "")
    source_label = slide.get("source_label", "")
    source_url = slide.get("asset_url") or story.get("source_story", {}).get("url", "")

    footer = esc(source_label or story.get("source_story", {}).get("source", "GetByteRush"))

    header = f"""
      <div class="gold-line"></div>
      {f'<div class="kicker">{esc(kicker)}</div>' if kicker else ''}
      <h1 class="headline">{esc(headline)}</h1>
    """

    if visual_type == "metric":
        visual = f"""
          <div class="metric-row">
            <div class="metric">
              <div class="value">{esc(headline.split()[0])}</div>
              <div class="label">{esc(visual_concept or body)}</div>
            </div>
          </div>
        """

    elif visual_type == "comparison":
        visual = f"""
          <div class="card">
            <div style="font-size:28px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">
              THE CONTRAST
            </div>
            <div style="font-size:58px;font-weight:900;line-height:1;margin-top:22px;">
              {esc(visual_concept or body)}
            </div>
          </div>
        """

    elif visual_type == "timeline":
        visual = f"""
          <div class="timeline">
            <div class="timeline-item">
              <div class="timeline-date">Before</div>
              <div class="timeline-text">{esc(body)}</div>
            </div>
            <div class="timeline-item">
              <div class="timeline-date">Then</div>
              <div class="timeline-text">{esc(visual_concept)}</div>
            </div>
          </div>
        """

    elif visual_type == "quote":
        visual = f"""
          <div class="quote">{esc(body)}</div>
        """

    elif visual_type in {"screenshot", "evidence"} and evidence_path:
        visual = f"""
          <div class="evidence-frame">
            <img src="{esc(evidence_path.as_uri())}" />
          </div>
          <div class="evidence-label">OFFICIAL SOURCE</div>
        """

    elif visual_type == "diagram":
        visual = f"""
          <div class="card">
            <div style="font-size:42px;font-weight:900;">
              {esc(visual_concept)}
            </div>
            <div class="arrow">↓</div>
            <div style="font-size:30px;line-height:1.2;">
              {esc(body)}
            </div>
          </div>
        """

    elif visual_type == "final" or number == total:
        return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><style>{base_css()}</style></head>
<body>
<section class="slide final">
  <div class="gold-line"></div>
  {f'<div class="kicker">{esc(kicker)}</div>' if kicker else ''}
  <h1 class="headline">{esc(headline)}</h1>
  <div class="body">{esc(body)}</div>
  <div class="source">{footer}</div>
  <div class="brand">getByteRush</div>
</section>
</body>
</html>"""

    else:
        visual = f"""
          <div class="card">
            <div style="font-size:28px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">
              {esc(visual_concept or "THE DETAIL")}
            </div>
            <div style="font-size:32px;line-height:1.22;margin-top:22px;">
              {esc(body)}
            </div>
          </div>
        """

    # For visual-heavy slides, don't duplicate body if the visual already carries it.
    body_html = ""
    if visual_type not in {"metric", "comparison", "timeline", "quote", "screenshot", "evidence", "diagram"}:
        body_html = f'<div class="body">{esc(body)}</div>'

    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><style>{base_css()}</style></head>
<body>
<section class="slide">
  {header}
  {body_html}
  {visual}
  <div class="source">{footer}</div>
  <div class="brand">getByteRush</div>
</section>
</body>
</html>"""


def render_html_files(story, out_dir, evidence_path):
    slides = story["slides"]

    for slide in slides:
        number = slide["number"]
        path = out_dir / f"slide-{number:02d}.html"
        path.write_text(
            slide_html(
                slide,
                story,
                evidence_path,
                len(slides),
            ),
            encoding="utf-8",
        )


def render_pngs(out_dir, count):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )

        for i in range(1, count + 1):
            html_path = out_dir / f"slide-{i:02d}.html"
            png_path = out_dir / f"slide-{i:02d}.png"

            page = browser.new_page(
                viewport={"width": 1080, "height": 1350},
                device_scale_factor=1,
            )
            page.goto(
                html_path.resolve().as_uri(),
                wait_until="load",
            )
            page.screenshot(
                path=str(png_path),
                full_page=False,
            )
            page.close()

        browser.close()


def write_metadata(story, out_dir):
    (out_dir / "caption.txt").write_text(
        story.get("caption", ""),
        encoding="utf-8",
    )

    (out_dir / "hashtags.txt").write_text(
        " ".join(story.get("hashtags", [])),
        encoding="utf-8",
    )

    (out_dir / "pinned-comment.txt").write_text(
        story.get("pinned_comment", ""),
        encoding="utf-8",
    )

    (out_dir / "alt-text.txt").write_text(
        story.get("alt_text", ""),
        encoding="utf-8",
    )

    (out_dir / "post.json").write_text(
        json.dumps(story, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run editorial_engine.py first."
        )

    story = json.loads(INPUT.read_text(encoding="utf-8"))

    if not story.get("selected"):
        print("No story selected. Nothing to render.")
        return

    title = story["story_title"]
    out_dir = OUTPUT_ROOT / slugify(title)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_url = story.get("source_story", {}).get("url", "")
    evidence_path = out_dir / "evidence.png"

    has_evidence = capture_evidence(source_url, evidence_path)
    if not has_evidence:
        evidence_path = None

    render_html_files(story, out_dir, evidence_path)
    render_pngs(out_dir, len(story["slides"]))
    write_metadata(story, out_dir)

    print("")
    print("=" * 70)
    print("GETBYTERUSH CAROUSEL GENERATED")
    print("=" * 70)
    print(f"Story:  {title}")
    print(f"Slides: {len(story['slides'])}")
    print(f"Output: {out_dir}")
    print("")

    for i in range(1, len(story["slides"]) + 1):
        print(f"  ✓ slide-{i:02d}.png")


if __name__ == "__main__":
    main()
