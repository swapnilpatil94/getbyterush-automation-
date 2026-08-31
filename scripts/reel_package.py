#!/usr/bin/env python3
"""Future-ready Reel content model — schema only, NOT wired into any
automated publishing path. Phase 9 explicitly says do not auto-publish
Reels yet; this exists so that when a human decides to build the Reel
pipeline, the shape of a "Reel package" is already defined and testable,
rather than invented from scratch under deadline. Zero Gemini calls: this
derives a package skeleton from an existing approved editorial story
(reuses its facts/evidence), it does not generate new script content.

Narrative shape (per the spec): HOOK -> TEST -> REAL DEMONSTRATION ->
UNEXPECTED RESULT -> EXPLANATION -> PRACTICAL TAKEAWAY -> CTA.
"""
import json
import sys
from pathlib import Path

REEL_SCHEMA_FIELDS = [
    "topic", "hook", "script", "shot_list", "screen_recording_instructions",
    "camera_instructions", "on_screen_text", "evidence", "cta", "caption", "seo",
]


def build_from_story(story):
    """Builds a REEL PACKAGE SKELETON — the narrative beats and shot list
    are structural placeholders keyed to the real editorial facts (headline/
    body/source per slide), not fabricated dialogue. A human (or, later, a
    dedicated Reel-script generation step) fills in the actual words."""
    slides = story.get("slides") or []
    hook_slide = slides[0] if slides else {}
    source = story.get("source_story") or {}

    beats = ["HOOK", "TEST", "REAL DEMONSTRATION", "UNEXPECTED RESULT", "EXPLANATION", "PRACTICAL TAKEAWAY", "CTA"]
    shot_list = []
    for i, beat in enumerate(beats):
        slide = slides[i] if i < len(slides) else {}
        shot_list.append({
            "beat": beat,
            "source_fact": slide.get("headline", "") or slide.get("body", ""),
            "visual": "screen recording / real demonstration — see module docstring; avoid generic stock footage",
        })

    import seo_metadata
    seo = seo_metadata.derive(story)

    return {
        "topic": story.get("story_title", ""),
        "hook": hook_slide.get("headline", ""),
        "script": "DRAFT — fill per beat from shot_list[].source_fact; do not fabricate dialogue not grounded in the source facts.",
        "shot_list": shot_list,
        "screen_recording_instructions": "Record the actual product/website/app referenced in source_attribution.url wherever the beat needs a real demonstration.",
        "camera_instructions": "Hands/device interaction preferred over talking-head; keep GetByteRush on-screen identity consistent with the carousel brand (cream/forest/near-black/gold).",
        "on_screen_text": [s.get("headline", "") for s in slides if s.get("headline")],
        "evidence": story.get("sources", []),
        "cta": story.get("share_trigger") or story.get("save_reason") or "",
        "caption": story.get("caption", ""),
        "seo": seo,
        "source_attribution": {"title": source.get("title", ""), "source": source.get("source", ""), "url": source.get("url", "")},
        "status": "SKELETON_ONLY — not wired into any publishing automation",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: reel_package.py <path-to-story.json>")
        raise SystemExit(1)
    story = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    pkg = build_from_story(story)
    print(json.dumps(pkg, indent=2, ensure_ascii=False))
