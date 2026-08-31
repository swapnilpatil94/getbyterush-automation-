#!/usr/bin/env python3
"""Objective, automated QA for one rendered package — the same checks
verify-v17-fixtures.yml runs in CI, factored out so the real production
pipeline runs the identical logic instead of a second copy that could
drift. Deterministic, zero API calls: PNG dimensions/signature, HTML
internal-label leaks, renderer tag, gemini_calls, slide count.

This is Tier 1 (objective) QA only — see design/design-principles.md and
the V17 production report for why creativity/memorability/scroll-stop are
explicitly NOT checked here and require the Telegram human review instead.
"""
import json
import re
from pathlib import Path

_LEAK_RE = re.compile(
    r'\b(?:visual[_ ]concept|visual[_ ]direction|callout graphic|design direction|'
    r'layout instruction|composition_family|graphics_director|grammar:|primitive:)\b',
    re.I,
)
EXPECTED_RENDERER_TAG = 'getbyterush-pinterest-editorial-v17'


def _jpeg_dimensions(raw):
    """Minimal, pure-stdlib JPEG SOF parser — no new dependency for one
    dimension check. Returns (width, height) or None if not a valid JPEG."""
    if raw[:2] != b'\xff\xd8':
        return None
    i = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while i + 4 <= len(raw):
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker in (0xD8, 0xD9):  # SOI / EOI
            i += 2
            continue
        if 0xD0 <= marker <= 0xD7:  # RST markers carry no length
            i += 2
            continue
        seg_len = int.from_bytes(raw[i + 2:i + 4], 'big')
        if marker in sof_markers:
            h = int.from_bytes(raw[i + 5:i + 7], 'big')
            w = int.from_bytes(raw[i + 7:i + 9], 'big')
            return w, h
        i += 2 + seg_len
    return None


def check_package(pkg_dir, expected_slides=None):
    """Returns (passed: bool, failures: list[str])."""
    pkg_dir = Path(pkg_dir)
    failures = []

    post_path = pkg_dir / 'post.json'
    if not post_path.exists():
        return False, [f'{pkg_dir}: missing post.json']
    post = json.loads(post_path.read_text(encoding='utf-8'))

    if expected_slides is None:
        expected_slides = len(post.get('slides') or [])

    slides = sorted((pkg_dir / 'slides').glob('*.jpg'))
    if len(slides) != expected_slides:
        failures.append(f'{pkg_dir}: expected {expected_slides} slides, found {len(slides)}')

    for f in slides:
        raw = f.read_bytes()
        dims = _jpeg_dimensions(raw) if len(raw) >= 4 else None
        if dims is None:
            failures.append(f'{f}: invalid JPEG signature')
            continue
        w, h = dims
        if (w, h) != (1080, 1350):
            failures.append(f'{f}: {w}x{h}, expected 1080x1350')

    for f in sorted((pkg_dir / 'html').glob('*.html')):
        text = f.read_text(encoding='utf-8')
        visible = re.sub(r'<style\b[^>]*>.*?</style>', ' ', text, flags=re.I | re.S)
        visible = re.sub(r'<script\b[^>]*>.*?</script>', ' ', visible, flags=re.I | re.S)
        visible = re.sub(r'<[^>]+>', ' ', visible)
        m = _LEAK_RE.search(visible)
        if m:
            failures.append(f'{f}: internal-label leak {m.group(0)!r}')

    if post.get('renderer') != EXPECTED_RENDERER_TAG:
        failures.append(f'{pkg_dir}: wrong renderer tag {post.get("renderer")!r}')
    if post.get('gemini_calls') != 0:
        failures.append(f'{pkg_dir}: gemini_calls={post.get("gemini_calls")!r}, expected 0')

    return not failures, failures


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('usage: qa_check.py <rendered-package-dir>')
        raise SystemExit(1)
    ok, fails = check_package(sys.argv[1])
    print('QA_PASS' if ok else 'QA_FAIL')
    for f in fails:
        print(' -', f)
    raise SystemExit(0 if ok else 1)
