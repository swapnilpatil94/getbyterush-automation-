#!/usr/bin/env python3
"""
GetByteRush Carousel Generator

Input:
    data/selected_story.json

Output:
    output/posts/YYYY-MM-DD/HHMM-topic-slug/
        slides/
            01.png ... NN.png
        html/
            01.html ... NN.html
        evidence/
            source.png (when source screenshot succeeds)
        caption.txt
        hashtags.txt
        pinned-comment.txt
        alt-text.txt
        post.json

Requires:
    playwright
"""

import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright


# ============================================================
# PATHS
# ============================================================

INPUT = Path("data/selected_story.json")
OUTPUT_ROOT = Path("output/posts")
RETENTION_DAYS = 7


# ============================================================
# HELPERS
# ============================================================

def slugify(value):
    value = value.lower().strip()

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value,
    )

    return (
        value.strip("-")[:80]
        or "getbyterush-post"
    )


def esc(value):
    return html.escape(
        str(value or "")
    )


# ============================================================
# EVIDENCE SCREENSHOT
# ============================================================

def capture_evidence(
    url,
    output_path,
):
    """
    Capture an official source page screenshot.

    Returns:
        True  -> screenshot successfully created
        False -> screenshot unavailable

    Important:
        Evidence failure must NOT crash the carousel.
    """

    if not url:
        print(
            "⚠ No evidence URL provided."
        )

        return False

    try:

        output_path = Path(
            output_path
        ).resolve()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            page = browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
                device_scale_factor=1,
            )

            print(
                f"Capturing evidence: {url}"
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            page.wait_for_timeout(
                2500
            )

            # ------------------------------------------------
            # Remove obvious cookie/consent overlays
            # ------------------------------------------------

            for selector in [
                '[aria-label*="cookie" i]',
                '[id*="cookie" i]',
                '[class*="cookie" i]',
                '[aria-label*="consent" i]',
                '[id*="consent" i]',
                '[class*="consent" i]',
            ]:

                try:

                    page.locator(
                        selector
                    ).first.evaluate(
                        "(el) => el.remove()"
                    )

                except Exception:
                    pass

            # ------------------------------------------------
            # Screenshot
            # ------------------------------------------------

            page.screenshot(
                path=str(output_path),
                full_page=False,
            )

            browser.close()

        if output_path.exists():

            print(
                f"  ✓ Evidence saved: "
                f"{output_path}"
            )

            return True

        print(
            "⚠ Evidence screenshot was "
            "not created."
        )

        return False

    except Exception as exc:

        print(
            f"⚠ Evidence screenshot failed: "
            f"{exc}"
        )

        return False


# ============================================================
# CSS
# ============================================================

def base_css():

    return """
    @page {
      size: 1080px 1350px;
      margin: 0;
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      margin: 0;
      padding: 0;
      width: 1080px;
      height: 1350px;
      background: #f4eddd;
    }

    body {
      font-family:
        Inter,
        Arial,
        Helvetica,
        sans-serif;

      color: #102b24;

      overflow: hidden;
    }

    .slide {
      position: relative;

      width: 1080px;
      height: 1350px;

      padding:
        82px
        82px
        70px;

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

      border:
        1.5px solid
        #b99a55;

      color: #102b24;

      padding:
        10px
        16px;

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

      margin:
        30px
        0
        40px;
    }

    .card {
      margin-top: 40px;

      padding: 34px;

      border:
        2px solid
        #102b24;

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

      border:
        2px solid
        #102b24;

      border-radius: 22px;

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

      margin:
        24px
        0;

      color: #b99a55;
    }

    .evidence-frame {
      position: absolute;

      left: 82px;
      right: 82px;
      bottom: 150px;

      height: 540px;

      border:
        3px solid
        #102b24;

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

      padding:
        10px
        16px;

      border-radius: 999px;

      font-size: 18px;

      font-weight: 700;
    }

    .timeline {
      margin-top: 65px;

      border-left:
        5px solid
        #b99a55;

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

      border-left:
        7px solid
        #b99a55;

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

    .no-evidence {
      position: absolute;

      left: 82px;
      right: 82px;
      bottom: 180px;

      padding: 38px;

      border:
        2px dashed
        #53635e;

      border-radius: 24px;

      background: #eee6d6;

      font-size: 27px;

      line-height: 1.2;

      color: #53635e;
    }
    """


# ============================================================
# SLIDE HTML
# ============================================================

def slide_html(
    slide,
    story,
    evidence_path,
    total,
):

    number = slide.get(
        "number",
        1,
    )

    kicker = slide.get(
        "kicker",
        "",
    )

    headline = slide.get(
        "headline",
        "",
    )

    body = slide.get(
        "body",
        "",
    )

    visual_type = slide.get(
        "visual_type",
        "typography",
    )

    visual_concept = slide.get(
        "visual_concept",
        "",
    )

    source_label = slide.get(
        "source_label",
        "",
    )

    source_url = (
        slide.get("asset_url")
        or
        story.get(
            "source_story",
            {},
        ).get(
            "url",
            "",
        )
    )

    footer = esc(
        source_label
        or
        story.get(
            "source_story",
            {},
        ).get(
            "source",
            "GetByteRush",
        )
    )

    # ========================================================
    # ABSOLUTE EVIDENCE URI
    #
    # FIX:
    # Path.as_uri() requires an absolute path.
    # ========================================================

    evidence_uri = None

    if evidence_path is not None:

        try:

            evidence_file = Path(
                evidence_path
            ).resolve()

            if evidence_file.exists():

                evidence_uri = (
                    evidence_file.as_uri()
                )

        except Exception as exc:

            print(
                f"⚠ Could not prepare "
                f"evidence URI: {exc}"
            )

            evidence_uri = None

    # ========================================================
    # HEADER
    # ========================================================

    header = f"""
      <div class="gold-line"></div>

      {
          f'<div class="kicker">'
          f'{esc(kicker)}'
          f'</div>'
          if kicker
          else ''
      }

      <h1 class="headline">
        {esc(headline)}
      </h1>
    """

    # ========================================================
    # METRIC
    # ========================================================

    if visual_type == "metric":

        first_word = (
            headline.split()[0]
            if headline.split()
            else ""
        )

        visual = f"""
          <div class="metric-row">

            <div class="metric">

              <div class="value">
                {esc(first_word)}
              </div>

              <div class="label">
                {esc(
                    visual_concept
                    or body
                )}
              </div>

            </div>

          </div>
        """

    # ========================================================
    # COMPARISON
    # ========================================================

    elif visual_type == "comparison":

        visual = f"""
          <div class="card">

            <div
              style="
                font-size:28px;
                font-weight:800;
                text-transform:uppercase;
                letter-spacing:1px;
              "
            >
              THE CONTRAST
            </div>

            <div
              style="
                font-size:58px;
                font-weight:900;
                line-height:1;
                margin-top:22px;
              "
            >
              {
                  esc(
                      visual_concept
                      or body
                  )
              }
            </div>

          </div>
        """

    # ========================================================
    # TIMELINE
    # ========================================================

    elif visual_type == "timeline":

        visual = f"""
          <div class="timeline">

            <div class="timeline-item">

              <div class="timeline-date">
                BEFORE
              </div>

              <div class="timeline-text">
                {esc(body)}
              </div>

            </div>

            <div class="timeline-item">

              <div class="timeline-date">
                THEN
              </div>

              <div class="timeline-text">
                {esc(visual_concept)}
              </div>

            </div>

          </div>
        """

    # ========================================================
    # QUOTE
    # ========================================================

    elif visual_type == "quote":

        visual = f"""
          <div class="quote">
            {esc(body)}
          </div>
        """

    # ========================================================
    # SCREENSHOT / EVIDENCE
    # ========================================================

    elif visual_type in {
        "screenshot",
        "evidence",
    }:

        if evidence_uri:

            visual = f"""
              <div class="evidence-frame">

                <img
                  src="{esc(evidence_uri)}"
                  alt="Official source evidence"
                />

              </div>

              <div class="evidence-label">
                OFFICIAL SOURCE
              </div>
            """

        else:

            # Do not fabricate evidence.
            # Show a neutral fallback instead.

            visual = f"""
              <div class="no-evidence">

                <strong>
                  SOURCE EVIDENCE
                </strong>

                <br><br>

                The official source screenshot
                was unavailable during rendering.

                <br><br>

                {esc(source_url)}

              </div>
            """

    # ========================================================
    # DIAGRAM
    # ========================================================

    elif visual_type == "diagram":

        visual = f"""
          <div class="card">

            <div
              style="
                font-size:42px;
                font-weight:900;
              "
            >
              {esc(visual_concept)}
            </div>

            <div class="arrow">
              ↓
            </div>

            <div
              style="
                font-size:30px;
                line-height:1.2;
              "
            >
              {esc(body)}
            </div>

          </div>
        """

    # ========================================================
    # FINAL
    # ========================================================

    elif (
        visual_type == "final"
        or number == total
    ):

        return f"""<!doctype html>

<html>

<head>

<meta charset="utf-8">

<style>
{base_css()}
</style>

</head>

<body>

<section class="slide final">

  <div class="gold-line"></div>

  {
      f'<div class="kicker">'
      f'{esc(kicker)}'
      f'</div>'
      if kicker
      else ''
  }

  <h1 class="headline">
    {esc(headline)}
  </h1>

  <div class="body">
    {esc(body)}
  </div>

  <div class="source">
    {footer}
  </div>

  <div class="brand">
    getByteRush
  </div>

</section>

</body>

</html>
"""

    # ========================================================
    # DEFAULT TYPOGRAPHY
    # ========================================================

    else:

        visual = f"""
          <div class="card">

            <div
              style="
                font-size:28px;
                font-weight:800;
                text-transform:uppercase;
                letter-spacing:1px;
              "
            >
              {
                  esc(
                      visual_concept
                      or
                      "THE DETAIL"
                  )
              }
            </div>

            <div
              style="
                font-size:32px;
                line-height:1.22;
                margin-top:22px;
              "
            >
              {esc(body)}
            </div>

          </div>
        """

    # ========================================================
    # BODY
    #
    # Visual-heavy layouts already contain body copy.
    # ========================================================

    body_html = ""

    if visual_type not in {
        "metric",
        "comparison",
        "timeline",
        "quote",
        "screenshot",
        "evidence",
        "diagram",
    }:

        body_html = f"""
          <div class="body">
            {esc(body)}
          </div>
        """

    # ========================================================
    # FINAL HTML
    # ========================================================

    return f"""<!doctype html>

<html>

<head>

<meta charset="utf-8">

<style>
{base_css()}
</style>

</head>

<body>

<section class="slide">

  {header}

  {body_html}

  {visual}

  <div class="source">
    {footer}
  </div>

  <div class="brand">
    getByteRush
  </div>

</section>

</body>

</html>
"""


# ============================================================
# WRITE HTML FILES
# ============================================================

def render_html_files(
    story,
    out_dir,
    evidence_path,
):

    slides = story.get(
        "slides",
        [],
    )

    if not slides:

        raise ValueError(
            "Story contains no slides."
        )

    for slide in slides:

        number = slide.get(
            "number",
            1,
        )

        path = (
            out_dir
            /
            "html"
            /
            f"{number:02d}.html"
        )

        content = slide_html(
            slide,
            story,
            evidence_path,
            len(slides),
        )

        path.write_text(
            content,
            encoding="utf-8",
        )


# ============================================================
# RENDER PNG
# ============================================================

def render_pngs(
    out_dir,
    count,
):

    out_dir = Path(
        out_dir
    ).resolve()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        for i in range(
            1,
            count + 1,
        ):

            html_path = (
                out_dir
                /
                "html"
                /
                f"{i:02d}.html"
            )

            png_path = (
                out_dir
                /
                "slides"
                /
                f"{i:02d}.png"
            )

            if not html_path.exists():

                raise FileNotFoundError(
                    f"Missing slide HTML: "
                    f"{html_path}"
                )

            page = browser.new_page(
                viewport={
                    "width": 1080,
                    "height": 1350,
                },
                device_scale_factor=1,
            )

            # ------------------------------------------------
            # IMPORTANT:
            # Always use absolute URI for local HTML.
            # ------------------------------------------------

            html_uri = (
                html_path
                .resolve()
                .as_uri()
            )

            page.goto(
                html_uri,
                wait_until="load",
            )

            page.screenshot(
                path=str(
                    png_path
                ),
                full_page=False,
            )

            page.close()

            print(
                f"  ✓ slide-{i:02d}.png"
            )

        browser.close()


# ============================================================
# METADATA
# ============================================================

def write_metadata(
    story,
    out_dir,
    created_at,
    retention_days=RETENTION_DAYS,
):
    """
    Write all publish-ready metadata into the post package.

    The original story payload is preserved and augmented with
    lifecycle/publishing metadata so Telegram/Instagram steps
    can consume the same package later.
    """

    (out_dir / "caption.txt").write_text(
        story.get(
            "caption",
            "",
        ),
        encoding="utf-8",
    )

    hashtags = story.get(
        "hashtags",
        [],
    )

    if isinstance(
        hashtags,
        list,
    ):

        hashtags_text = " ".join(
            str(tag)
            for tag in hashtags
        )

    else:

        hashtags_text = str(
            hashtags or ""
        )

    (
        out_dir
        / "hashtags.txt"
    ).write_text(
        hashtags_text,
        encoding="utf-8",
    )

    (
        out_dir
        / "pinned-comment.txt"
    ).write_text(
        story.get(
            "pinned_comment",
            "",
        ),
        encoding="utf-8",
    )

    (
        out_dir
        / "alt-text.txt"
    ).write_text(
        story.get(
            "alt_text",
            "",
        ),
        encoding="utf-8",
    )

    try:
        created_dt = datetime.fromisoformat(
            created_at
        )
        delete_after = (
            created_dt
            + timedelta(days=retention_days)
        ).isoformat()
    except Exception:
        delete_after = ""

    # Preserve the complete editorial story while adding
    # lifecycle fields required by the future approval/publish
    # pipeline.
    package = dict(story)

    package.update(
        {
            "post_id": (
                f"{slugify(story.get('story_title', 'getbyterush-post'))}"
                f"-{created_at.replace(':', '').replace('+', '-')}"
            ),
            "status": "pending_approval",
            "created_at": created_at,
            "retention_days": retention_days,
            "delete_after": delete_after,
            "package": {
                "slides_dir": "slides",
                "html_dir": "html",
                "evidence_dir": "evidence",
                "slide_count": len(
                    story.get("slides", [])
                ),
            },
            "instagram": {
                "published": False,
                "media_id": None,
                "permalink": None,
            },
        }
    )

    (
        out_dir
        / "post.json"
    ).write_text(
        json.dumps(
            package,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # INPUT CHECK
    # ========================================================

    if not INPUT.exists():

        raise FileNotFoundError(
            f"Missing {INPUT}. "
            "Run editorial_engine.py first."
        )

    story = json.loads(
        INPUT.read_text(
            encoding="utf-8"
        )
    )

    # ========================================================
    # SELECTION CHECK
    # ========================================================

    if not story.get(
        "selected"
    ):

        print(
            "No story selected. "
            "Nothing to render."
        )

        return

    # ========================================================
    # SLIDE CHECK
    # ========================================================

    slides = story.get(
        "slides",
        [],
    )

    if not slides:

        raise ValueError(
            "Selected story contains "
            "no carousel slides."
        )

    # ========================================================
    # OUTPUT DIRECTORY
    #
    # Every generated post gets an isolated package:
    #
    # output/posts/
    #   YYYY-MM-DD/
    #     HHMM-topic-slug/
    #       slides/
    #       html/
    #       evidence/
    #       post.json
    #       caption.txt
    #       hashtags.txt
    #       pinned-comment.txt
    #       alt-text.txt
    #
    # This makes Telegram approval, Instagram publishing and
    # retention cleanup deterministic.
    # ========================================================

    title = story.get(
        "story_title",
        "GetByteRush Post",
    )

    created_dt = datetime.now().astimezone()
    created_at = created_dt.isoformat(
        timespec="seconds"
    )

    date_dir = (
        OUTPUT_ROOT
        /
        created_dt.strftime("%Y-%m-%d")
    )

    package_name = (
        f"{created_dt.strftime('%H%M')}-"
        f"{slugify(title)}"
    )

    out_dir = (
        date_dir
        /
        package_name
    )

    # Avoid accidental collision if two runs happen during
    # the same minute for the same story.
    if out_dir.exists():
        suffix = created_dt.strftime("%S")
        out_dir = (
            date_dir
            /
            f"{created_dt.strftime('%H%M%S')}-"
            f"{slugify(title)}"
        )

    slides_dir = out_dir / "slides"
    html_dir = out_dir / "html"
    evidence_dir = out_dir / "evidence"

    slides_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    html_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # SOURCE URL
    # ========================================================

    source_story = story.get(
        "source_story",
        {},
    )

    source_url = source_story.get(
        "url",
        "",
    )

    # ========================================================
    # EVIDENCE
    # ========================================================

    evidence_path = (
        evidence_dir
        /
        "source.png"
    ).resolve()

    has_evidence = capture_evidence(
        source_url,
        evidence_path,
    )

    if not has_evidence:

        evidence_path = None

    # ========================================================
    # HTML
    # ========================================================

    print("")
    print(
        "Rendering HTML slides..."
    )

    render_html_files(
        story,
        out_dir,
        evidence_path,
    )

    # ========================================================
    # PNG
    # ========================================================

    print(
        "Rendering PNG slides..."
    )

    render_pngs(
        out_dir,
        len(slides),
    )

    # ========================================================
    # METADATA
    # ========================================================

    write_metadata(
        story,
        out_dir,
        created_at,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print("")
    print(
        "=" * 70
    )

    print(
        "GETBYTERUSH CAROUSEL GENERATED"
    )

    print(
        "=" * 70
    )

    print(
        f"Story:  {title}"
    )

    print(
        f"Slides: {len(slides)}"
    )

    print(
        f"Output: {out_dir}"
    )

    print(
        f"Evidence: "
        f"{'YES' if has_evidence else 'NO'}"
    )

    print("")

    for i in range(
        1,
        len(slides) + 1,
    ):

        print(
            f"  ✓ slide-{i:02d}.png"
        )

    print("")

    print(
        "✓ Carousel generation complete."
    )


if __name__ == "__main__":

    main()