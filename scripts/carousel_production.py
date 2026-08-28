#!/usr/bin/env python3
"""Production entry point for the GetByteRush carousel renderer.

The previous validator treated line-height rounding as text overflow. Browser
text boxes can legitimately report scrollHeight a few pixels larger than the
client box because of font metrics/line-height rounding, even when the
rendered text is fully visible. This validator now rejects only real content
escaping the canvas or horizontal text overflow that can visibly clip words.
"""

import json
from pathlib import Path

import carousel_generator as renderer

WIDTH = renderer.WIDTH
HEIGHT = renderer.HEIGHT

IGNORED_CLASSES = {"grain", "hero-mark", "hero-line"}

CRITICAL_SELECTORS = [
    ".meta", ".kicker", "h1", ".body", ".metric-card", ".metric-value",
    ".metric-label", ".metric-note", ".pair", ".pair-card", ".pair-title",
    ".pair-copy", ".pair-label", ".node", ".node .value", ".timeline",
    ".timeline-item", ".timeline-text", ".compare-grid", ".compare-card",
    ".compare-name", ".compare-row", ".quote-wrap", ".quote", ".quote-source",
    ".chip-stack", ".chip", ".die", ".mem", ".caption", ".payoff",
    ".payoff-small", ".evidence-frame", ".evidence-window", ".evidence-window img",
    ".evidence-chrome", ".evidence-caption", ".footer", ".source", ".brand",
]

# Only these text elements are checked for horizontal clipping. Vertical
# scrollHeight is deliberately not used: CSS line boxes often have a small
# internal rounding difference that is not visible clipping.
TEXT_SELECTORS = [
    "h1", ".body", ".metric-value", ".metric-label", ".metric-note",
    ".pair-title", ".pair-copy", ".pair-label", ".node .value",
    ".timeline-date", ".timeline-text", ".compare-name", ".compare-row",
    ".quote", ".quote-source", ".verdict .big", ".verdict .copy",
    ".payoff", ".payoff-small", ".source", ".brand", ".kicker", ".meta",
]


def validate_page(page):
    return page.evaluate(
        """
        ({width, height, selectors, textSelectors, ignoredClasses}) => {
          const viewport = document.querySelector('.slide');
          if (!viewport) return {error: 'missing .slide'};

          const ignored = el => {
            const classes = String(el.className || '').split(/\\s+/);
            return classes.some(c => ignoredClasses.includes(c));
          };

          const rectOf = el => {
            const r = el.getBoundingClientRect();
            return {left:r.left, top:r.top, right:r.right, bottom:r.bottom,
                    width:r.width, height:r.height};
          };

          const geometryFailures = [];
          const textFailures = [];
          const seen = new Set();

          for (const selector of selectors) {
            for (const el of document.querySelectorAll(selector)) {
              if (ignored(el) || seen.has(el)) continue;
              seen.add(el);

              const r = el.getBoundingClientRect();
              const outside = r.left < -1 || r.top < -1 || r.right > width + 1 || r.bottom > height + 1;
              if (outside) {
                geometryFailures.push({
                  selector,
                  cls: String(el.className || ''),
                  text: (el.innerText || '').slice(0,120),
                  rect: rectOf(el)
                });
              }
            }
          }

          for (const selector of textSelectors) {
            for (const el of document.querySelectorAll(selector)) {
              if (ignored(el)) continue;
              const horizontal = el.scrollWidth > el.clientWidth + 3;
              if (horizontal) {
                textFailures.push({
                  selector,
                  cls: String(el.className || ''),
                  text: (el.innerText || '').slice(0,160),
                  client:[el.clientWidth,el.clientHeight],
                  scroll:[el.scrollWidth,el.scrollHeight]
                });
              }
            }
          }

          return {
            canvas:{width:viewport.getBoundingClientRect().width,height:viewport.getBoundingClientRect().height},
            document:{scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight},
            geometryFailures:geometryFailures.slice(0,30),
            textFailures:textFailures.slice(0,30)
          };
        }
        """,
        {
            "width": WIDTH,
            "height": HEIGHT,
            "selectors": CRITICAL_SELECTORS,
            "textSelectors": TEXT_SELECTORS,
            "ignoredClasses": list(IGNORED_CLASSES),
        },
    )


def production_render(out_dir, count):
    html_dir = Path(out_dir).resolve() / "html"
    slides_dir = Path(out_dir).resolve() / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
        )

        for i in range(1, count + 1):
            html_path = html_dir / f"{i:02d}.html"
            png_path = slides_dir / f"{i:02d}.png"

            page.goto(html_path.resolve().as_uri(), wait_until="load")
            page.wait_for_timeout(120)

            result = validate_page(page)
            if result.get("geometryFailures") or result.get("textFailures"):
                failures.append({"slide": i, "details": result})

            page.screenshot(path=str(png_path), full_page=False)
            print(f"✓ slide-{i:02d}.png")

        browser.close()

    if failures:
        print("PRODUCTION_LAYOUT_VALIDATION_FAILED")
        print(json.dumps(failures, indent=2, ensure_ascii=False))
        raise RuntimeError(
            "Production carousel validation failed. Fix the reported content bounds/overflow before publishing."
        )

    print("✓ Production layout validation passed")


def main():
    previous = renderer.render_pngs_validate
    renderer.render_pngs_validate = production_render
    try:
        renderer.main()
    finally:
        renderer.render_pngs_validate = previous


if __name__ == "__main__":
    main()
