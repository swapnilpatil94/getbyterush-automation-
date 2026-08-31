#!/usr/bin/env python3
"""Assembles the Instagram publishing package from a V17-rendered post
package (post.json + design_spec.json + slides/*.jpg). Zero Gemini calls —
reuses the editorial JSON's own caption/hashtags/alt_text/pinned_comment
and adds SEO fields via seo_metadata.py (deterministic) and per-slide alt
text via plain-language description of what each grammar actually draws
(never internal names like "grammar"/"V17"/"primitive"/"JSON").
"""
import json
import sys
from pathlib import Path

import graphics_director as gd
import seo_metadata

# Plain-language description of what each grammar visually draws — used
# only to enrich alt text, never the grammar/variant name itself, which
# would leak an internal implementation detail into public accessibility
# text.
_GRAMMAR_ALT_HINT = {
    'confrontation': 'a common misconception struck through, with the correct answer stated below it',
    'proportional_field': 'a grid of cells showing the proportion as filled versus empty cells',
    'accumulation_trail': 'a row of blocks that shrink to show a resource being spent down',
    'comparison': 'a side-by-side comparison',
    'chronological_sequence': 'a timeline with dated points',
    'sequential_system': 'a diagram of connected steps',
    'evidence_board': 'pinned reference facts',
    'evidence_screenshot': 'a captured screenshot of the source with a caption',
    'quote': 'a pulled quote',
    'singular_object': 'one large highlighted number or word',
    'payoff': 'a closing statement with the GetByteRush signature',
}


def _slide_alt_text(i, slide, spec):
    headline = str(slide.get('headline') or '').strip()
    body = str(slide.get('body') or '').strip()
    hint = _GRAMMAR_ALT_HINT.get((spec or {}).get('grammar', ''), '')
    parts = [p for p in (headline, body) if p]
    text = '. '.join(parts)
    if hint:
        text = f"{text} — shown as {hint}." if text else hint.capitalize() + '.'
    return f"Slide {i}: {text}".strip()


def build(pkg_dir):
    pkg_dir = Path(pkg_dir)
    story = json.loads((pkg_dir / 'post.json').read_text(encoding='utf-8'))
    spec = json.loads((pkg_dir / 'design_spec.json').read_text(encoding='utf-8'))
    slide_specs = spec.get('slides', [])
    slides = story.get('slides', [])

    images = sorted((pkg_dir / 'slides').glob('*.jpg'))
    alt_texts = [
        _slide_alt_text(i + 1, slides[i] if i < len(slides) else {}, slide_specs[i] if i < len(slide_specs) else {})
        for i in range(len(images))
    ]

    seo = seo_metadata.derive(story)
    source_story = story.get('source_story') or {}

    raw_caption = story.get('caption', '')
    hashtags = story.get('hashtags', []) or []
    hashtag_line = ' '.join(f'#{h.lstrip("#")}' for h in hashtags)
    # Instagram has no separate hashtags field on either publishing path —
    # they only take effect as clickable tags when they're literally part
    # of the caption text. Confirmed missing on the first real post: the
    # caption alone was sent, hashtags were built and stored in the
    # package but never appended anywhere before reaching Instagram.
    caption_for_publish = f'{raw_caption}\n\n{hashtag_line}'.strip() if hashtag_line else raw_caption

    package = {
        'content_id': story.get('content_id', ''),
        'story_title': story.get('story_title', ''),
        'renderer': story.get('renderer', ''),
        'gemini_calls': story.get('gemini_calls', 0),
        'images': [str(p) for p in images],
        'slide_count': len(images),
        'caption': raw_caption,
        'caption_for_publish': caption_for_publish,
        'pinned_comment': story.get('pinned_comment', ''),
        'alt_text_overall': story.get('alt_text', ''),
        'alt_text_per_slide': alt_texts,
        'hashtags': story.get('hashtags', []),
        'cta': gd.cta_line(story),
        'seo': seo,
        'source_attribution': {
            'title': source_story.get('title', ''),
            'source': source_story.get('source', ''),
            'url': source_story.get('url', ''),
            'sources': story.get('sources', []),
            'fact_check': story.get('fact_check', []),
        },
    }
    (pkg_dir / 'publishing_package.json').write_text(
        json.dumps(package, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    return package


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: publishing_package.py <rendered-package-dir>')
        raise SystemExit(1)
    pkg = build(sys.argv[1])
    print(f"PACKAGE_BUILT={pkg['content_id']}")
    print(f"SLIDES={pkg['slide_count']}")
    print(f"PRIMARY_KEYWORD={pkg['seo']['primary_keyword']}")
