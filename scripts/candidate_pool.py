#!/usr/bin/env python3
"""GetByteRush persistent candidate pool.

research.yml runs every 4-6h and each run's filter_stories.py output
(data/candidates.json) is a fresh, REPLACED snapshot — it does not
accumulate across runs. This module is the accumulation layer: it merges
each run's fresh candidates into a persistent, deduplicated pool
(data/candidate_pool.json) that daily_selection.py later scores and
selects from. Reuses topic_memory.py's own title/url matching for dedup
identity rather than re-implementing it, per the instruction not to
duplicate existing dedup logic.

Zero Gemini calls.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import quality_scoring as qs
import topic_memory as tm

POOL_PATH = Path("data/candidate_pool.json")

POOL_RETENTION_DAYS = 14
EVERGREEN_RETENTION_DAYS = 45

# Pool-level lifecycle. Distinct from content_state.py's per-rendered-post
# states — a pool entry becomes SELECTED the day it's chosen by
# daily_selection.py, independent of whether it later gets approved,
# rejected, or published downstream (content_state owns that).
STATUS_POOLED = "POOLED"
STATUS_SELECTED = "SELECTED"
STATUS_EXPIRED = "EXPIRED"
STATUS_EDITORIAL_REJECTED = "EDITORIAL_REJECTED"


def _now():
    return datetime.now(timezone.utc)


def _stable_id(story):
    identity = tm.normalize(story.get("url") or story.get("title") or "")
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
    return f"cand-{digest}"


def load_pool():
    if not POOL_PATH.exists():
        return {"version": 1, "updated_at": "", "candidates": []}
    try:
        data = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("candidates"), list):
            return data
    except Exception:
        pass
    return {"version": 1, "updated_at": "", "candidates": []}


def save_pool(pool):
    POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    pool["updated_at"] = _now().isoformat()
    pool["count"] = len(pool["candidates"])
    POOL_PATH.write_text(json.dumps(pool, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _entry_from_story(story, content_id):
    scored = qs.score_candidate(story, now=_now())
    return {
        "content_id": content_id,
        "topic": story.get("title", ""),
        "title": story.get("title", ""),
        "summary": story.get("description", ""),
        "content_type": scored["content_type"],
        "source": story.get("source", ""),
        "source_url": story.get("url", ""),
        "published_at": story.get("published", ""),
        "discovered_at": _now().isoformat(),
        "evidence_available": scored["evidence_available"],
        "evergreen": scored["evergreen"],
        "timeliness": scored["timeliness"],
        "novelty": scored["novelty"],
        "visual_potential": scored["visual_potential"],
        "curiosity_score": scored["curiosity_score"],
        "save_score": scored["save_score"],
        "share_score": scored["share_score"],
        "information_value": scored["information_value"],
        "credibility": scored["credibility"],
        "experiment_possible": scored["experiment_possible"],
        "reel_readiness": {
            "screen_recording_possible": scored["screen_recording_possible"],
            "product_demo_possible": scored["product_demo_possible"],
            "mobile_demo_possible": scored["mobile_demo_possible"],
            "website_demo_possible": scored["website_demo_possible"],
            "visual_demo_possible": scored["visual_demo_possible"],
        },
        "status": STATUS_POOLED,
        "score": scored["score"],
        "raw": story,
    }


def prune(pool):
    now = _now()
    kept = []
    for entry in pool["candidates"]:
        discovered = tm.parse_dt(entry.get("discovered_at"))
        if discovered is None:
            continue  # malformed entry — drop rather than keep unbounded junk
        retention = EVERGREEN_RETENTION_DAYS if entry.get("evergreen") else POOL_RETENTION_DAYS
        if now - discovered > timedelta(days=retention):
            continue
        kept.append(entry)
    pool["candidates"] = kept
    return pool


def merge_new_candidates(new_stories):
    """Adds this run's freshly-filtered stories into the persistent pool,
    skipping anything that already matches an existing pool entry (by
    stable id, falling back to topic_memory's fuzzy title/url match so a
    slightly-reworded re-fetch of the same story doesn't duplicate)."""
    pool = prune(load_pool())
    existing_ids = {e["content_id"] for e in pool["candidates"]}
    added, skipped = 0, 0

    for story in new_stories:
        content_id = _stable_id(story)
        if content_id in existing_ids:
            skipped += 1
            continue
        duplicate = next(
            (e for e in pool["candidates"] if tm.same_topic(story, e.get("raw", e))),
            None,
        )
        if duplicate:
            skipped += 1
            continue
        pool["candidates"].append(_entry_from_story(story, content_id))
        existing_ids.add(content_id)
        added += 1

    save_pool(pool)
    print(f"POOL_MERGE added={added} skipped_duplicates={skipped} pool_size={len(pool['candidates'])}")
    return pool


def mark_selected(content_ids):
    pool = load_pool()
    ids = set(content_ids)
    for entry in pool["candidates"]:
        if entry["content_id"] in ids:
            entry["status"] = STATUS_SELECTED
            entry["selected_at"] = _now().isoformat()
    save_pool(pool)


def mark_editorial_rejected(content_ids):
    """A candidate Gemini itself rejected (validation failure, or scored
    below editorial_engine.py's own production threshold) shouldn't be
    immediately re-picked by the next slot/run — its deterministic
    pre-filter score said it looked fine, but Gemini's deeper read (full
    source text, real narrative judgment) disagreed, which is real
    signal. Distinct from STATUS_SELECTED so it's clear in the pool why
    this entry stopped being offered."""
    pool = load_pool()
    ids = set(content_ids)
    for entry in pool["candidates"]:
        if entry["content_id"] in ids:
            entry["status"] = STATUS_EDITORIAL_REJECTED
            entry["rejected_at"] = _now().isoformat()
    save_pool(pool)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        candidates_path = Path("data/candidates.json")
        if not candidates_path.exists():
            raise SystemExit("Missing data/candidates.json — run filter_stories.py first.")
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
        merge_new_candidates(data.get("stories", []))
    else:
        pool = load_pool()
        print(f"Pool size: {len(pool['candidates'])}")
        for e in pool["candidates"][:20]:
            print(f" - [{e['content_type']:<28}] score={e['score']:<3} {e['title']}")
