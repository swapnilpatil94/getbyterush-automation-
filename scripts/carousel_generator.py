#!/usr/bin/env python3
"""
GetByteRush — Production Carousel Generator v2

Purpose
-------
Render the editorial JSON produced by editorial_engine.py into a premium,
story-driven 1080x1350 Instagram carousel.

This renderer follows:
    design/getbyterush-carousel-design-system.md

It is intentionally deterministic. Gemini may choose the story/template/theme,
but this renderer ENFORCES the resulting design language.

Input
-----
    data/selected_story.json

Output
------
    output/posts/YYYY-MM-DD/HHMM-topic-slug/
        slides/01.png ... NN.png
        html/01.html ... NN.html
        evidence/source.png
        caption.txt
        hashtags.txt
        pinned-comment.txt
        alt-text.txt
        post.json

Requires
--------
    playwright
"""

import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright


INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")
RETENTION_DAYS = 7
WIDTH = 1080
HEIGHT = 1350


# ---------------------------------------------------------------------------
# BRAND / DESIGN SYSTEM
# ---------------------------------------------------------------------------

BRAND = {
    "cream": "#F4EFE4",
    "forest": "#12352B",
    "ink": "#111311",
    "gold": "#B99A5B",
    "white": "#FFFFFF",
}

THEMES = {
    "brand": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#B99A5B",
        "muted": "#59645F",
        "signal": "#B99A5B",
        "surface": "#EAE3D5",
    },
    "urgency": {
        "background": "#111311",
        "foreground": "#F4EFE4",
        "accent": "#E53935",
        "accent2": "#F4EFE4",
        "muted": "#B9B6AD",
        "signal": "#E53935",
        "surface": "#1D1F1D",
    },
    "experiment": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#4F7C70",
        "muted": "#59645F",
        "signal": "#4F7C70",
        "surface": "#E2E9E5",
    },
    "money": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#B99A5B",
        "muted": "#59645F",
        "signal": "#B99A5B",
        "surface": "#E9E0CC",
    },
    "explainer": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#3F6FA3",
        "muted": "#59645F",
        "signal": "#3F6FA3",
        "surface": "#E3E8EF",
    },
    "contradiction": {
        "background": "#111311",
        "foreground": "#F4EFE4",
        "accent": "#E8B949",
        "accent2": "#E53935",
        "muted": "#B9B6AD",
        "signal": "#E53935",
        "surface": "#20221F",
    },
    "receipts": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#6B7D75",
        "muted": "#59645F",
        "signal": "#C46B4D",
        "surface": "#E8E2D8",
    },
    "timeline": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#3F6FA3",
        "muted": "#59645F",
        "signal": "#B99A5B",
        "surface": "#E5E8E6",
    },
    "comparison": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#3F6FA3",
        "muted": "#59645F",
        "signal": "#B99A5B",
        "surface": "#E2E7E5",
    },
    "mystery": {
        "background": "#111311",
        "foreground": "#F4EFE4",
        "accent": "#B7E43B",
        "accent2": "#7B61A8",
        "muted": "#A9AAA2",
        "signal": "#B7E43B",
        "surface": "#20231E",
    },
    "data": {
        "background": "#F4EFE4",
        "foreground": "#111311",
        "accent": "#12352B",
        "accent2": "#3F6FA3",
        "muted": "#59645F",
        "signal": "#B99A5B",
        "surface": "#E3E7E9",
    },
}

TEMPLATE_THEME = {
    "story": "brand",
    "experiment": "experiment",
    "shock-number": "money",
    "breakdown": "explainer",
    "contradiction": "contradiction",
    "receipts": "receipts",
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
    "TECH_NEWS": "story",
    "MODEL_UPDATE": "story",
    "AI_AGENTS": "breakdown",
    "BUSINESS": "story",
}

VISUAL_TO_TEMPLATE = {
    "metric": "shock-number",
    "comparison": "comparison",
    "timeline": "timeline",
    "evidence": "receipts",
    "screenshot": "receipts",
    "diagram": "breakdown",
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def esc(value):
    return html.escape(str(value or ""))


def slugify(value):
    value = str(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:80] or "getbyterush-post"


def clean_text(value):
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value or "").strip()


def first_nonempty(*values):
    for value in values:
        if value is not None and str(value).strip():
            return value
    return ""


def infer_template(story):
    explicit = first_nonempty(
        story.get("template"),
        story.get("design", {}).get("template") if isinstance(story.get("design"), dict) else "",
    )
    explicit = str(explicit).strip().lower()
    if explicit in TEMPLATE_THEME:
        return explicit

    slides = story.get("slides", [])
    for slide in slides:
        visual = str(slide.get("visual_type", "")).lower()
        if visual in VISUAL_TO_TEMPLATE:
            return VISUAL_TO_TEMPLATE[visual]

    category = first_nonempty(
        story.get("content_type"),
        story.get("story_type"),
        story.get("category"),
        story.get("type"),
    )
    return CATEGORY_TEMPLATE.get(str(category), "story")


def infer_emotional_mode(story, template):
    explicit = first_nonempty(
        story.get("emotional_mode"),
        story.get("design", {}).get("emotional_mode") if isinstance(story.get("design"), dict) else "",
    )
    if explicit:
        return str(explicit).strip().lower()

    if story.get("emergency_mode") is True:
        return "urgency"

    return TEMPLATE_THEME.get(template, "brand")


def theme_for(story, template):
    mode = infer_emotional_mode(story, template)

    aliases = {
        "urgent": "urgency",
        "emergency": "urgency",
        "money/scale": "money",
        "money": "money",
        "explainer": "explainer",
        "experiment": "experiment",
        "contradiction": "contradiction",
        "receipts": "receipts",
        "timeline": "timeline",
        "comparison": "comparison",
        "mystery": "mystery",
        "data": "data",
    }

    theme_name = aliases.get(mode, mode)
    if theme_name not in THEMES:
        theme_name = TEMPLATE_THEME.get(template, "brand")

    # Emergency mode is an explicit override.
    if story.get("emergency_mode") is True:
        theme_name = "urgency"

    return theme_name, THEMES[theme_name]


def resolve_accent(story, theme):
    requested = first_nonempty(
        story.get("accent_color"),
        story.get("design", {}).get("accent_color") if isinstance(story.get("design"), dict) else "",
    )
    if requested and re.fullmatch(r"#[0-9a-fA-F]{6}", str(requested).strip()):
        return str(requested).strip()

    return theme["accent"]


def slide_role(slide, number, total):
    explicit = first_nonempty(
        slide.get("role"),
        slide.get("scene_role"),
    )
    if explicit:
        return str(explicit).lower()

    if number == 1:
        return "interrupt"
    if number == total:
        return "payoff"
    if number == 2:
        return "open_loop"
    if number == total - 1:
        return "reveal"
    return "proof"


def safe_headline(slide):
    return first_nonempty(
        slide.get("headline"),
        slide.get("title"),
        slide.get("hook"),
        slide.get("text"),
        "GetByteRush",
    )


def safe_body(slide):
    return first_nonempty(
        slide.get("body"),
        slide.get("supporting_text"),
        slide.get("copy"),
        slide.get("description"),
    )


def visual_concept(slide):
    return first_nonempty(
        slide.get("visual_concept"),
        slide.get("visual_strategy"),
        slide.get("visual_asset"),
        slide.get("visual"),
    )


def source_info(story, slide):
    source_story = story.get("source_story", {})
    if not isinstance(source_story, dict):
        source_story = {}

    source = first_nonempty(
        slide.get("source_label"),
        slide.get("source"),
        source_story.get("source"),
        source_story.get("publisher"),
        "GetByteRush",
    )

    url = first_nonempty(
        slide.get("asset_url"),
        slide.get("source_url"),
        source_story.get("url"),
    )

    return source, url


# ---------------------------------------------------------------------------
# EVIDENCE
# ---------------------------------------------------------------------------

def capture_evidence(url, output_path):
    if not url:
        print("⚠ No evidence URL provided.")
        return False

    try:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )

            page = browser.new_page(
                viewport={"width": 1440, "height": 1000},
                device_scale_factor=1,
            )

            print(f"Capturing evidence: {url}")

            page.goto(
                str(url),
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.wait_for_timeout(2200)

            for selector in [
                '[aria-label*="cookie" i]',
                '[id*="cookie" i]',
                '[class*="cookie" i]',
                '[aria-label*="consent" i]',
                '[id*="consent" i]',
                '[class*="consent" i]',
            ]:
                try:
                    page.locator(selector).first.evaluate("(el) => el.remove()")
                except Exception:
                    pass

            page.screenshot(path=str(output_path), full_page=False)
            browser.close()

        if output_path.exists():
            print(f"✓ Evidence saved: {output_path}")
            return True

    except Exception as exc:
        print(f"⚠ Evidence screenshot failed: {exc}")

    return False


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def css(theme, template):
    return f"""
    @page {{
      size: {WIDTH}px {HEIGHT}px;
      margin: 0;
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      margin: 0;
      padding: 0;
      width: {WIDTH}px;
      height: {HEIGHT}px;
      background: {theme["background"]};
    }}

    body {{
      font-family: Inter, Arial, Helvetica, sans-serif;
      color: {theme["foreground"]};
      overflow: hidden;
    }}

    :root {{
      --gb-cream: #F4EFE4;
      --gb-forest: #12352B;
      --gb-ink: #111311;
      --gb-gold: #B99A5B;
      --background: {theme["background"]};
      --foreground: {theme["foreground"]};
      --accent-primary: {theme["accent"]};
      --accent-secondary: {theme["accent2"]};
      --muted: {theme["muted"]};
      --signal: {theme["signal"]};
      --surface: {theme["surface"]};
    }}

    .slide {{
      position: relative;
      width: {WIDTH}px;
      height: {HEIGHT}px;
      padding: 78px 78px 70px;
      background: var(--background);
      color: var(--foreground);
      overflow: hidden;
    }}

    .slide.dark {{
      background: #111311;
      color: #F4EFE4;
    }}

    .slide.cream {{
      background: #F4EFE4;
      color: #111311;
    }}

    .top-meta {{
      position: absolute;
      left: 78px;
      right: 78px;
      top: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 2px;
      text-transform: uppercase;
      opacity: .82;
    }}

    .page-no {{
      font-family: "SFMono-Regular", Consolas, monospace;
      letter-spacing: 1px;
    }}

    .rule {{
      width: 84px;
      height: 5px;
      background: var(--accent-primary);
      margin-bottom: 28px;
    }}

    .kicker {{
      display: inline-flex;
      align-items: center;
      min-height: 42px;
      padding: 8px 14px;
      border: 1.5px solid var(--accent-primary);
      color: var(--accent-primary);
      font-size: 19px;
      font-weight: 850;
      letter-spacing: 1.7px;
      text-transform: uppercase;
      margin-bottom: 26px;
    }}

    .dark .kicker {{
      color: var(--accent-primary);
      border-color: var(--accent-primary);
    }}

    .headline {{
      margin: 0;
      max-width: 920px;
      font-size: 78px;
      line-height: .94;
      letter-spacing: -3.8px;
      font-weight: 900;
    }}

    .headline.small {{
      font-size: 62px;
      letter-spacing: -2.5px;
    }}

    .headline.huge {{
      font-size: 126px;
      line-height: .82;
      letter-spacing: -7px;
    }}

    .body {{
      margin-top: 30px;
      max-width: 810px;
      font-size: 32px;
      line-height: 1.18;
      font-weight: 520;
    }}

    .body strong {{
      font-weight: 900;
    }}

    .mono {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 20px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}

    .footer {{
      position: absolute;
      left: 78px;
      right: 78px;
      bottom: 52px;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 30px;
    }}

    .source {{
      max-width: 680px;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 16px;
      line-height: 1.25;
      opacity: .72;
      text-transform: uppercase;
      letter-spacing: .7px;
    }}

    .brand {{
      font-size: 17px;
      font-weight: 900;
      letter-spacing: 2.2px;
      text-transform: uppercase;
    }}

    .accent-word {{
      color: var(--accent-primary);
    }}

    .signal {{
      color: var(--signal);
    }}

    .number-wrap {{
      margin-top: 58px;
    }}

    .number {{
      font-family: Inter, Arial, sans-serif;
      font-size: 245px;
      line-height: .72;
      letter-spacing: -14px;
      font-weight: 950;
      color: var(--accent-primary);
    }}

    .number-label {{
      margin-top: 40px;
      max-width: 790px;
      font-size: 37px;
      line-height: 1.03;
      font-weight: 820;
    }}

    .stat-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-top: 54px;
    }}

    .stat {{
      padding: 32px;
      min-height: 235px;
      background: var(--surface);
      border-top: 5px solid var(--accent-primary);
    }}

    .stat .value {{
      font-size: 78px;
      line-height: .85;
      font-weight: 950;
      letter-spacing: -4px;
    }}

    .stat .label {{
      margin-top: 22px;
      font-size: 24px;
      line-height: 1.05;
      font-weight: 750;
    }}

    .evidence-frame {{
      position: absolute;
      left: 78px;
      right: 78px;
      top: 315px;
      bottom: 145px;
      background: #ddd;
      overflow: hidden;
      border: 1px solid var(--accent-primary);
    }}

    .evidence-frame img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center top;
    }}

    .evidence-tag {{
      position: absolute;
      top: 285px;
      left: 98px;
      padding: 9px 13px;
      background: var(--accent-primary);
      color: var(--background);
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 16px;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}

    .quote {{
      margin-top: 60px;
      max-width: 850px;
      padding-left: 32px;
      border-left: 7px solid var(--accent-primary);
      font-size: 52px;
      line-height: 1.02;
      font-weight: 850;
      letter-spacing: -2px;
    }}

    .diagram {{
      margin-top: 62px;
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .node {{
      flex: 1;
      min-height: 150px;
      padding: 28px;
      background: var(--surface);
      border: 1.5px solid var(--accent-primary);
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}

    .node .label {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 17px;
      text-transform: uppercase;
      letter-spacing: 1px;
      opacity: .75;
    }}

    .node .value {{
      margin-top: 13px;
      font-size: 31px;
      line-height: 1;
      font-weight: 900;
    }}

    .arrow {{
      font-size: 52px;
      font-weight: 900;
      color: var(--accent-primary);
    }}

    .timeline {{
      margin-top: 58px;
      position: relative;
      padding-left: 38px;
      border-left: 5px solid var(--accent-primary);
    }}

    .timeline-item {{
      margin-bottom: 38px;
      position: relative;
    }}

    .timeline-item::before {{
      content: "";
      position: absolute;
      left: -52px;
      top: 4px;
      width: 20px;
      height: 20px;
      background: var(--background);
      border: 5px solid var(--accent-primary);
    }}

    .timeline-date {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 19px;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: var(--accent-primary);
    }}

    .timeline-text {{
      margin-top: 7px;
      font-size: 32px;
      line-height: 1.06;
      font-weight: 760;
    }}

    .versus {{
      margin-top: 55px;
      display: grid;
      grid-template-columns: 1fr 120px 1fr;
      align-items: center;
      gap: 18px;
    }}

    .versus-card {{
      min-height: 270px;
      padding: 32px;
      background: var(--surface);
      border: 2px solid var(--accent-primary);
    }}

    .versus-card .name {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 18px;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}

    .versus-card .copy {{
      margin-top: 30px;
      font-size: 34px;
      line-height: 1;
      font-weight: 900;
    }}

    .vs {{
      text-align: center;
      font-size: 38px;
      font-weight: 950;
      color: var(--accent-primary);
    }}

    .mystery {{
      margin-top: 70px;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 25px;
      line-height: 1.25;
      color: var(--accent-primary);
      border-top: 1px solid var(--accent-primary);
      border-bottom: 1px solid var(--accent-primary);
      padding: 22px 0;
    }}

    .minimal {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding-bottom: 100px;
    }}

    .minimal .headline {{
      max-width: 900px;
    }}

    .payoff {{
      margin-top: 44px;
      max-width: 820px;
      font-size: 38px;
      line-height: 1.08;
      font-weight: 720;
    }}

    .gold-bar {{
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 12px;
      background: var(--accent-secondary);
    }}

    .blackout {{
      background: #111311 !important;
      color: #F4EFE4 !important;
    }}

    .blackout .headline {{
      color: #F4EFE4;
    }}

    .blackout .accent-word,
    .blackout .signal {{
      color: var(--accent-primary);
    }}

    .blackout .footer,
    .blackout .top-meta {{
      color: #F4EFE4;
    }}

    .grain {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: .045;
      background-image:
        radial-gradient(#000 0.6px, transparent 0.7px);
      background-size: 5px 5px;
    }}

    .blackout .grain {{
      opacity: .07;
      background-image:
        radial-gradient(#fff 0.6px, transparent 0.7px);
    }}
    """


# ---------------------------------------------------------------------------
# VISUAL BUILDERS
# ---------------------------------------------------------------------------

def visual_for_slide(
    slide,
    story,
    template,
    theme,
    evidence_uri,
    number,
    total,
):
    headline = safe_headline(slide)
    body = safe_body(slide)
    concept = visual_concept(slide)
    visual_type = str(slide.get("visual_type", "typography")).lower()
    role = slide_role(slide, number, total)

    # 1 — SHOCK NUMBER
    if template == "shock-number" or visual_type == "metric":
        match = re.search(r"(?<!\w)(\d+(?:\.\d+)?%?|\$[\d,.]+[A-Za-z]?)", headline + " " + concept)
        value = match.group(1) if match else first_nonempty(concept, headline[:8])
        label = body or headline
        return f"""
        <div class="number-wrap">
          <div class="number">{esc(value)}</div>
          <div class="number-label">{esc(label)}</div>
        </div>
        """

    # 2 — RECEIPTS / SCREENSHOT
    if template == "receipts" or visual_type in {"evidence", "screenshot"}:
        if evidence_uri:
            return f"""
            <div class="evidence-tag">REAL EVIDENCE</div>
            <div class="evidence-frame">
              <img src="{esc(evidence_uri)}" alt="Official source evidence">
            </div>
            """
        return f"""
        <div class="quote">
          {esc(first_nonempty(concept, body, "Evidence unavailable during render."))}
        </div>
        """

    # 3 — COMPARISON
    if template == "comparison" or visual_type == "comparison":
        parts = re.split(r"\s+vs\.?\s+|\s+versus\s+", concept or headline, flags=re.I)
        left = parts[0].strip() if parts else "A"
        right = parts[1].strip() if len(parts) > 1 else "B"
        return f"""
        <div class="versus">
          <div class="versus-card">
            <div class="name">OPTION A</div>
            <div class="copy">{esc(left)}</div>
          </div>
          <div class="vs">VS</div>
          <div class="versus-card">
            <div class="name">OPTION B</div>
            <div class="copy">{esc(right)}</div>
          </div>
        </div>
        """

    # 4 — TIMELINE
    if template == "timeline" or visual_type == "timeline":
        timeline = slide.get("timeline") or slide.get("events") or []
        if isinstance(timeline, list) and timeline:
            items = []
            for item in timeline[:5]:
                if isinstance(item, dict):
                    date = first_nonempty(item.get("date"), item.get("year"), "NEXT")
                    text = first_nonempty(item.get("text"), item.get("headline"), item.get("description"))
                else:
                    date = "STEP"
                    text = item
                items.append(
                    f'<div class="timeline-item"><div class="timeline-date">{esc(date)}</div>'
                    f'<div class="timeline-text">{esc(text)}</div></div>'
                )
            return '<div class="timeline">' + "".join(items) + "</div>"

        return f"""
        <div class="timeline">
          <div class="timeline-item">
            <div class="timeline-date">BEFORE</div>
            <div class="timeline-text">{esc(body or headline)}</div>
          </div>
          <div class="timeline-item">
            <div class="timeline-date">THEN</div>
            <div class="timeline-text">{esc(concept or "The situation changed.")}</div>
          </div>
          <div class="timeline-item">
            <div class="timeline-date">NOW</div>
            <div class="timeline-text">What happens next matters more than the original announcement.</div>
          </div>
        </div>
        """

    # 5 — BREAKDOWN / DIAGRAM
    if template == "breakdown" or visual_type == "diagram":
        labels = ["INPUT", "AI / SYSTEM", "OUTPUT"]
        texts = [
            headline,
            concept or "The mechanism",
            body or "The real-world consequence",
        ]
        nodes = []
        for label, text in zip(labels, texts):
            nodes.append(
                f'<div class="node"><div class="label">{esc(label)}</div>'
                f'<div class="value">{esc(text)}</div></div>'
            )
        return (
            '<div class="diagram">'
            + '<div class="arrow">→</div>'.join(nodes)
            + "</div>"
        )

    # 6 — WTF / MYSTERY
    if template == "wtf":
        return f"""
        <div class="mystery">
          {esc(first_nonempty(concept, body, "THE CLUE IS IN THE NEXT SLIDE."))}
        </div>
        """

    # 7 — DATA STORY
    if template == "data-story":
        numbers = re.findall(
            r"(?<!\w)(?:\d+(?:\.\d+)?%?|\$[\d,.]+[A-Za-z]?)",
            headline + " " + body + " " + concept,
        )
        if len(numbers) >= 2:
            return f"""
            <div class="stat-grid">
              <div class="stat">
                <div class="value">{esc(numbers[0])}</div>
                <div class="label">{esc(headline)}</div>
              </div>
              <div class="stat">
                <div class="value">{esc(numbers[1])}</div>
                <div class="label">{esc(body or concept)}</div>
              </div>
            </div>
            """
        return f"""
        <div class="number-wrap">
          <div class="number">{esc(numbers[0] if numbers else "01")}</div>
          <div class="number-label">{esc(body or concept or headline)}</div>
        </div>
        """

    # 8 — EXPERIMENT
    if template == "experiment":
        return f"""
        <div class="stat-grid">
          <div class="stat">
            <div class="value">TEST</div>
            <div class="label">{esc(first_nonempty(concept, "Real-world experiment"))}</div>
          </div>
          <div class="stat">
            <div class="value">RESULT</div>
            <div class="label">{esc(body or "The result changed the story.")}</div>
          </div>
        </div>
        """

    # 9 — CONTRADICTION
    if template == "contradiction":
        return f"""
        <div class="quote">
          {esc(first_nonempty(concept, body, "The numbers do not tell the whole story."))}
        </div>
        """

    # 10 — STORY default: visual rhythm by slide role
    if role in {"interrupt", "open_loop"}:
        return f"""
        <div class="mystery">
          {esc(first_nonempty(concept, "KEEP GOING →"))}
        </div>
        """

    if role in {"reveal", "payoff"}:
        return f"""
        <div class="payoff">
          {esc(first_nonempty(body, concept, headline))}
        </div>
        """

    if visual_type == "quote":
        return f'<div class="quote">{esc(body or headline)}</div>'

    return f"""
    <div class="stat-grid">
      <div class="stat">
        <div class="value">01</div>
        <div class="label">{esc(first_nonempty(concept, "THE DETAIL"))}</div>
      </div>
      <div class="stat">
        <div class="value">→</div>
        <div class="label">{esc(body or headline)}</div>
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# SLIDE HTML
# ---------------------------------------------------------------------------

def slide_html(
    slide,
    story,
    template,
    theme_name,
    theme,
    evidence_uri,
    number,
    total,
):
    headline = safe_headline(slide)
    body = safe_body(slide)
    kicker = first_nonempty(
        slide.get("kicker"),
        slide.get("label"),
        story.get("series"),
        "GETBYTERUSH",
    )
    role = slide_role(slide, number, total)

    # Per-slide background can be explicitly requested by editorial JSON.
    requested_bg = str(first_nonempty(
        slide.get("background"),
        slide.get("background_mode"),
    )).lower()

    blackout = requested_bg in {
        "black",
        "ink",
        "dark",
        "blackout",
    } or role == "pattern_interrupt"

    # Template-level visual rhythm.
    if number == 1:
        classes = "slide " + ("blackout" if blackout else "")
    elif role == "pattern_interrupt":
        classes = "slide blackout"
    elif number == total:
        classes = "slide minimal " + ("blackout" if blackout else "")
    else:
        classes = "slide " + ("blackout" if blackout else "")

    headline_class = "headline"
    if len(headline) > 80:
        headline_class += " small"

    # First slide is intentionally sparse.
    if number == 1:
        visual_html = ""
        if template == "shock-number":
            visual_html = visual_for_slide(
                slide, story, template, theme, evidence_uri, number, total
            )
        else:
            visual_html = f"""
            <div class="mystery">
              {esc(first_nonempty(
                  slide.get("transition_hint"),
                  "SWIPE → THE REST OF THE STORY",
              ))}
            </div>
            """
    else:
        visual_html = visual_for_slide(
            slide, story, template, theme, evidence_uri, number, total
        )

    # Final slide should be a payoff, not a generic "follow us" card.
    if number == total:
        visual_html = f"""
        <div class="payoff">
          {esc(first_nonempty(
              body,
              slide.get("payoff"),
              slide.get("implication"),
              "The important part is what happens next.",
          ))}
        </div>
        """

    source, _ = source_info(story, slide)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={WIDTH}, initial-scale=1">
<style>
{css(theme, template)}
</style>
</head>

<body>
<section class="{classes}">

  <div class="grain"></div>

  <div class="top-meta">
    <div>GETBYTERUSH / {esc(template.replace("-", " ").upper())}</div>
    <div class="page-no">{number:02d} / {total:02d}</div>
  </div>

  <div class="rule"></div>

  <div class="kicker">{esc(kicker)}</div>

  <h1 class="{headline_class}">
    {esc(headline)}
  </h1>

  {
      f'<div class="body">{esc(body)}</div>'
      if body and number != total and template not in {"receipts", "comparison", "timeline", "breakdown"}
      else ""
  }

  {visual_html}

  <div class="footer">
    <div class="source">SOURCE / {esc(source)}</div>
    <div class="brand">TESTED • EXPLAINED • REAL</div>
  </div>

</section>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

def render_html_files(story, out_dir, template, theme_name, theme, evidence_path):
    slides = story.get("slides", [])
    total = len(slides)

    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    evidence_uri = None
    if evidence_path:
        try:
            p = Path(evidence_path).resolve()
            if p.exists():
                evidence_uri = p.as_uri()
        except Exception as exc:
            print(f"⚠ Evidence URI unavailable: {exc}")

    for index, slide in enumerate(slides, start=1):
        # Normalize missing/incorrect numbering without modifying source data.
        slide_number = index

        content = slide_html(
            slide,
            story,
            template,
            theme_name,
            theme,
            evidence_uri,
            slide_number,
            total,
        )

        path = html_dir / f"{index:02d}.html"
        path.write_text(content, encoding="utf-8")


def render_pngs(out_dir, count):
    out_dir = Path(out_dir).resolve()
    html_dir = out_dir / "html"
    slides_dir = out_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        for index in range(1, count + 1):
            html_path = html_dir / f"{index:02d}.html"
            png_path = slides_dir / f"{index:02d}.png"

            if not html_path.exists():
                raise FileNotFoundError(f"Missing slide HTML: {html_path}")

            page = browser.new_page(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
            )

            # IMPORTANT: Playwright needs an absolute file URI.
            page.goto(
                html_path.resolve().as_uri(),
                wait_until="load",
            )

            page.screenshot(
                path=str(png_path),
                full_page=False,
            )

            page.close()
            print(f"✓ slide-{index:02d}.png")

        browser.close()


def write_metadata(story, out_dir, created_at, retention_days):
    caption = clean_text(story.get("caption"))
    hashtags = story.get("hashtags", [])

    if isinstance(hashtags, list):
        hashtags_text = " ".join(str(x) for x in hashtags)
    else:
        hashtags_text = str(hashtags or "")

    (out_dir / "caption.txt").write_text(
        caption,
        encoding="utf-8",
    )

    (out_dir / "hashtags.txt").write_text(
        hashtags_text,
        encoding="utf-8",
    )

    (out_dir / "pinned-comment.txt").write_text(
        clean_text(story.get("pinned_comment")),
        encoding="utf-8",
    )

    (out_dir / "alt-text.txt").write_text(
        clean_text(story.get("alt_text")),
        encoding="utf-8",
    )

    try:
        created_dt = datetime.fromisoformat(created_at)
        delete_after = (
            created_dt + timedelta(days=retention_days)
        ).isoformat()
    except Exception:
        delete_after = ""

    package = dict(story)

    template = infer_template(story)
    theme_name, theme = theme_for(story, template)

    design = dict(story.get("design") or {})
    design.update({
        "template": template,
        "emotional_mode": infer_emotional_mode(story, template),
        "background_mode": first_nonempty(
            story.get("background_mode"),
            design.get("background_mode"),
            "theme-driven",
        ),
        "accent_color": resolve_accent(story, theme),
        "renderer": "getbyterush-carousel-generator-v2",
    })

    package.update({
        "design": design,
        "post_id": (
            f"{slugify(story.get('story_title', 'getbyterush-post'))}-"
            f"{created_at.replace(':', '').replace('+', '-')}"
        ),
        "status": "pending_approval",
        "created_at": created_at,
        "retention_days": retention_days,
        "delete_after": delete_after,
        "package": {
            "slides_dir": "slides",
            "html_dir": "html",
            "evidence_dir": "evidence",
            "slide_count": len(story.get("slides", [])),
            "template": template,
            "theme": theme_name,
        },
        "instagram": {
            "published": False,
            "media_id": None,
            "permalink": None,
        },
    })

    (out_dir / "post.json").write_text(
        json.dumps(package, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run editorial_engine.py first."
        )

    story = json.loads(INPUT.read_text(encoding="utf-8"))

    if not story.get("selected"):
        print("No story selected. Nothing to render.")
        return

    slides = story.get("slides", [])
    if not slides:
        raise ValueError("Selected story contains no carousel slides.")

    title = story.get("story_title", "GetByteRush Post")

    created_dt = datetime.now().astimezone()
    created_at = created_dt.isoformat(timespec="seconds")

    date_dir = OUTPUT_ROOT / created_dt.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{created_dt.strftime('%H%M')}-{slugify(title)}"
    out_dir = date_dir / base_name

    if out_dir.exists():
        out_dir = date_dir / f"{created_dt.strftime('%H%M%S')}-{slugify(title)}"

    (out_dir / "slides").mkdir(parents=True, exist_ok=True)
    (out_dir / "html").mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence").mkdir(parents=True, exist_ok=True)

    template = infer_template(story)
    theme_name, theme = theme_for(story, template)

    # Optional source evidence.
    source_story = story.get("source_story", {})
    source_url = source_story.get("url", "") if isinstance(source_story, dict) else ""

    evidence_path = out_dir / "evidence" / "source.png"
    has_evidence = capture_evidence(source_url, evidence_path)

    if not has_evidence:
        evidence_path = None

    print("")
    print("=" * 72)
    print("GETBYTERUSH CAROUSEL V2")
    print("=" * 72)
    print(f"Template: {template}")
    print(f"Theme:    {theme_name}")
    print(f"Accent:   {resolve_accent(story, theme)}")
    print(f"Slides:   {len(slides)}")
    print("=" * 72)

    render_html_files(
        story,
        out_dir,
        template,
        theme_name,
        theme,
        evidence_path,
    )

    render_pngs(out_dir, len(slides))

    write_metadata(
        story,
        out_dir,
        created_at,
        RETENTION_DAYS,
    )

    print("")
    print("=" * 72)
    print("GETBYTERUSH CAROUSEL GENERATED")
    print("=" * 72)
    print(f"Output:   {out_dir}")
    print(f"Template: {template}")
    print(f"Theme:    {theme_name}")
    print(f"Evidence: {'YES' if has_evidence else 'NO'}")
    print("Status:   pending_approval")
    print("")
    print("✓ Ready for Telegram approval pipeline.")


if __name__ == "__main__":
    main()
