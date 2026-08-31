#!/usr/bin/env python3
"""Deterministic SEO metadata — zero Gemini calls, reuses editorial output
that already exists (headline, hashtags, kicker, source entities) rather
than asking Gemini for a new field set. Phase 10's constraint is absolute:
no new Gemini calls anywhere in this architecture, so this is regex/
heuristic extraction over text Gemini already generated, not a new prompt.
"""
import re

_STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on', 'for',
    'and', 'or', 'but', 'with', 'this', 'that', 'it', 'its', 'as', 'at', 'by',
    'from', 'be', 'has', 'have', 'had', 'just', 'now', 'new', 'more', 'than',
}


def _clean_words(text):
    return re.findall(r"[A-Za-z][A-Za-z0-9']*", str(text or ''))


def _entities(headline, source_story):
    """Capitalized multi-word or known-brand tokens — the same signal a
    human skimming the headline would call out as 'the companies/products
    this is about', not a fabricated NLP entity model."""
    ents = []
    text = f"{headline} {(source_story or {}).get('title', '')}"
    for m in re.finditer(r'\b([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*){0,2})\b', text):
        tok = m.group(1).strip()
        if tok.upper() in ('THE', 'THIS', 'THAT') or len(tok) < 2:
            continue
        if tok not in ents:
            ents.append(tok)
    return ents[:6]


def derive(story):
    """story: the full editorial JSON (post.json shape). Returns
    {primary_keyword, secondary_keywords, search_phrases, entities}."""
    headline = story.get('slides', [{}])[0].get('headline', '') if story.get('slides') else ''
    title = story.get('story_title', '') or headline
    hashtags = [h.lstrip('#') for h in (story.get('hashtags') or [])]
    source_story = story.get('source_story') or {}

    entities = _entities(title, source_story)

    words = [w for w in _clean_words(title) if w.lower() not in _STOPWORDS]
    primary_keyword = entities[0] if entities else (' '.join(words[:3]) or 'technology')

    secondary = []
    for tag in hashtags:
        if tag and tag.lower() not in primary_keyword.lower() and tag not in secondary:
            secondary.append(tag)
    for ent in entities[1:]:
        if ent not in secondary:
            secondary.append(ent)
    secondary = secondary[:8]

    search_phrases = []
    if entities:
        search_phrases.append(f"what is {entities[0]}")
        if len(entities) > 1:
            search_phrases.append(f"{entities[0]} vs {entities[1]}")
    for kw in secondary[:2]:
        phrase = f"{primary_keyword} {kw}".strip()
        if phrase not in search_phrases:
            search_phrases.append(phrase)
    search_phrases = search_phrases[:5]

    return {
        'primary_keyword': primary_keyword,
        'secondary_keywords': secondary,
        'search_phrases': search_phrases,
        'entities': entities,
    }
