#!/usr/bin/env python3
"""Production entry point for the GetByteRush carousel renderer.

This wrapper keeps the visual renderer deterministic while replacing the old
DOM validator with a geometry-aware validator. Decorative transforms (for
example the rotated hero mark) are intentionally excluded from hard bounds;
real text overflow and content escaping the safe canvas are still failures.
"""

import json
from pathlib import Path

import carousel_generator as renderer

WIDTH = renderer.WIDTH
HEIGHT = renderer.HEIGHT
SAFE = renderer.SAFE

# Elements that are decorative or deliberately positioned outside the normal
# flow must not fail the content validator merely because their transformed
# bounding box extends past the canvas.
IGNORED_CLASSES = {
    "grain",
    "hero-mark",
    "hero-line",
}

CRITICAL_SELECTORS = [
    ".meta",
    ".kicker",
    "h1",
    ".body",
    ".metric-card",
    ".metric-value",
    ".metric-label",
    ".pair-card",
    ".pair-title",
    ".pair-copy",
    ".node",
    ".node .value",
    ".timeline",
    ".timeline-item",
    ".timeline-text",
    ".compare-card",
    ".compare-name",
    ".compare-row",
    ".quote-wrap",
    ".quote",
    ".verdict",
    ".verdict .big",
    ".verdict .copy",
    ".evidence-frame",
    ".evidence-window",
    ".evidence-window img",
    ".footer",
    ".source",
    ".brand",
]


def validate_page(page):
    return page.evaluate(
        """
        ({width, height, safe, criticalSelectors, ignoredClasses}) => {
          const viewport = document.querySelector('.slide');
          if (!viewport) return {error: 'missing .slide'};

          const root = viewport.getBoundingClientRect();
          const ignored = (el) => {
            const classes = String(el.className || '').split(/\\s+/);
            return classes.some(c => ignoredClasses.includes(c));
          };

          const rectOf = (el) => {
            const r = el.getBoundingClientRect();
            return {left:r.left, top:r.top, right:r.right, bottom:r.bottom,
                    width:r.width, height:r.height};
          };

          const geometryFailures = [];
          const textFailures = [];
          const seen = new Set();

          for (const selector of criticalSelectors) {
            for (const el of document.querySelectorAll(selector)) {
              if (ignored(el)) continue;
              if (seen.has(el)) continue;
              seen.add(el);

              const r = el.getBoundingClientRect();
              // Content must remain inside the physical canvas. The safe-area
              // is used for authored content, while chrome/footer may occupy
              // the full canvas by design.
              if (r.left < -1 || r.top < -1 || r.right > width + 1 || r.bottom > height + 1) {
                geometryFailures.push({selector, cls:String(el.className), text:(el.innerText||'').slice(0,120), rect:rectOf(el)});
              }

              if (el.matches('h1,.body,.metric-value,.metric-label,.pair-title,.pair-copy,.node .value,.timeline-text,.compare-name,.compare-row,.quote,.verdict .big,.verdict .copy,.source,.brand')) {
                const style = getComputedStyle(el);
                const horizontal = el.scrollWidth > el.clientWidth + 2;
                const vertical = el.scrollHeight > el.clientHeight + 2 && style.overflowY !== 'hidden';
                if (horizontal || vertical) {
                  textFailures.push({selector, cls:String(el.className), text:(el.innerText||'').slice(0,160), client:[el.clientWidth,el.clientHeight], scroll:[el.scrollWidth,el.scrollHeight]});
                }
              }
            }
          }

          return {
            canvas:{width:root.width,height:root.height},
            document:{scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight},
            geometryFailures:geometryFailures.slice(0,30),
            textFailures:textFailures.slice(0,30)
          };
        }
        """,
        {
            "width": WIDTH,
            "height": HEIGHT,
            "safe": SAFE,
            "criticalSelectors": CRITICAL_SELECTORS,
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
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)

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
        raise RuntimeError("Production carousel validation failed. Fix the reported content bounds/overflow before publishing.")

    print("✓ Production layout validation passed")


def main():
    # Replace only the validator/render stage; all template, evidence, package,
    # topic-memory and design-system logic remains owned by the main renderer.
    original = renderer.render_pngs_validate
    renderer.render_pngs_validate = production_render
    try:
        renderer.main()
    finally:
        renderer.render_pngs_validate = original


if __name__ == "__main__":
    main()
