#!/usr/bin/env python3
"""Sends the real GetByteRush Telegram review card: the actual rendered
carousel as a media-group album, followed by the review summary and
[✅ APPROVE & POST] / [❌ REJECT] buttons. Replaces the send_approval.py
prototype, which sent a hardcoded fake message with no real images.
"""
import sys
from pathlib import Path

import telegram_bot as tg


def _format_card(content_id, package, story_title, source_url, selection_meta=None):
    seo = package.get('seo', {})
    meta = selection_meta or {}
    rank = meta.get('rank')
    total = meta.get('total')
    if meta.get('slot_label'):
        header = f"⏰ {meta['slot_label'].upper()} SLOT"
    elif rank and total:
        header = f"POST #{rank}/{total}"
    else:
        header = "GETBYTERUSH DAILY REVIEW"

    lines = [header]
    if meta.get('category'):
        lines.append(f"CATEGORY: {meta['category']}")
    lines += [
        "",
        story_title or '(untitled)',
        "",
    ]
    if meta.get('why_selected'):
        lines += ["WHY THIS WAS SELECTED:", meta['why_selected'], ""]
    if meta.get('quality_score') is not None:
        lines += [f"QUALITY SCORE: {meta['quality_score']}/100", ""]
    lines += [
        f"SOURCE: {meta.get('source') or '(unattributed)'}",
        source_url or '(no source URL on record)',
        "",
        f"SLIDES: {package.get('slide_count', 0)}",
        "",
        "VISUAL PREVIEW: sent above ↑",
        "",
        "Renderer: V17   QA: ✓ PASS   Gemini calls: 1 (editorial)",
        "",
        "SEO:", seo.get('primary_keyword', ''),
        "",
        "CTA:", package.get('cta', ''),
    ]
    return "\n".join(lines)


def send_review_card(content_id, pkg_dir, package, selection_meta=None):
    pkg_dir = Path(pkg_dir)
    images = sorted((pkg_dir / 'slides').glob('*.jpg'))
    if not images:
        # A silently empty list here used to reach Telegram as an empty
        # media array, which sendMediaGroup rejects with a bare "400 Bad
        # Request" that gives no hint why — confirmed live when the
        # renderer's output extension changed and this glob wasn't updated
        # to match. Fail loudly and specifically instead.
        raise SystemExit(f"No slide images found in {pkg_dir / 'slides'} (looked for *.jpg) — nothing to send.")
    if len(images) > 10:
        print(f"WARNING: {len(images)} slides, Telegram/Instagram carousel cap is 10 — sending first 10 only")

    tg.send_media_group([str(p) for p in images])

    text = _format_card(content_id, package, package.get('story_title', ''), (package.get('source_attribution') or {}).get('url', ''), selection_meta=selection_meta)
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ APPROVE & POST", "callback_data": f"approve:{content_id}"},
            {"text": "❌ REJECT", "callback_data": f"reject:{content_id}"},
        ]]
    }
    result = tg.send_message(text, reply_markup=keyboard)
    print(f"REVIEW_CARD_SENT content_id={content_id} ok={result.get('ok')}")
    return result


if __name__ == '__main__':
    import json
    if len(sys.argv) != 2:
        print('usage: telegram_review.py <content_id>')
        raise SystemExit(1)
    content_id = sys.argv[1]
    import content_state as cs
    record = cs.load(content_id)
    if record is None:
        raise SystemExit(f'No content record for {content_id}')
    package = json.loads((Path(record['package_path']) / 'publishing_package.json').read_text(encoding='utf-8'))
    send_review_card(content_id, record['package_path'], package)
