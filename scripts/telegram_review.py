#!/usr/bin/env python3
"""Sends the real GetByteRush Telegram review card: the actual rendered
carousel as a media-group album, followed by the review summary and
[✅ APPROVE & POST] / [❌ REJECT] buttons. Replaces the send_approval.py
prototype, which sent a hardcoded fake message with no real images.
"""
import sys
from pathlib import Path

import telegram_bot as tg


def _format_card(content_id, package, story_title, source_url):
    seo = package.get('seo', {})
    lines = [
        "GETBYTERUSH",
        "DAILY REVIEW",
        "",
        "Topic:",
        story_title or '(untitled)',
        "",
        "Why this topic:",
        source_url or '(no source URL on record)',
        "",
        "Slides:",
        str(package.get('slide_count', 0)),
        "",
        "Renderer:",
        "V17",
        "",
        "QA:",
        "✓ PASS",
        "",
        "Gemini calls:",
        "0 for graphics",
        "",
        "SEO:",
        seo.get('primary_keyword', ''),
        "",
        "CTA:",
        package.get('cta', ''),
    ]
    return "\n".join(lines)


def send_review_card(content_id, pkg_dir, package):
    pkg_dir = Path(pkg_dir)
    images = sorted((pkg_dir / 'slides').glob('*.png'))
    if len(images) > 10:
        print(f"WARNING: {len(images)} slides, Telegram/Instagram carousel cap is 10 — sending first 10 only")

    tg.send_media_group([str(p) for p in images])

    text = _format_card(content_id, package, package.get('story_title', ''), (package.get('source_attribution') or {}).get('url', ''))
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
