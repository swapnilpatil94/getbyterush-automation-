#!/usr/bin/env python3
"""GetByteRush daily selection — picks ~5 strongest candidates from the
persistent pool for today's carousels. Fully deterministic (zero Gemini
calls). This is the layer that turns "5 posts/day" into a quality floor
rather than a quota: if fewer than TARGET candidates clear the quality
gate, fewer are selected; if none do, the day is NO_QUALITY_POST.

Order of operations: load pool -> drop expired/duplicate/topic-blocked ->
score -> quality gate -> diversity-aware greedy selection -> write the
auditable daily content plan.
"""
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import candidate_pool as cp
import content_slots
import quality_scoring as qs
import topic_memory as tm

PLAN_PATH = Path("data/daily_content_plan.json")
SELECTED_STORIES_PATH = Path("data/selected_stories.json")

DEFAULT_TARGET = int(os.environ.get("DAILY_SELECTION_TARGET", "5"))
QUALITY_FLOOR = int(os.environ.get("DAILY_SELECTION_QUALITY_FLOOR", "50"))


def _topic_blocked(entry, recent_memory):
    return any(tm.same_topic(entry.get("raw", entry), mem) for mem in recent_memory)


def _recent_memory_entries():
    memory = tm.prune(tm.load_memory())
    cutoff = datetime.now(timezone.utc) - timedelta(days=tm.TOPIC_COOLDOWN_DAYS)
    return [
        e for e in memory["topics"]
        if tm.parse_dt(e.get("recorded_at")) and tm.parse_dt(e.get("recorded_at")) >= cutoff
    ]


def _reason(scored):
    signals = ", ".join(scored["strong_signals"]) or "baseline quality signals"
    return f"{scored['content_type']} — {signals} (score {scored['score']}/100)"


def eligible_candidates(pool_entries, recent_memory):
    eligible = []
    seen_within_pool = []
    for entry in pool_entries:
        if entry.get("status") == cp.STATUS_SELECTED:
            continue
        if _topic_blocked(entry, recent_memory):
            continue
        # within-pool dedup: two pool entries that slipped in as near-
        # duplicates (e.g. merged before topic_memory recorded either)
        if any(tm.same_topic(entry.get("raw", entry), s.get("raw", s)) for s in seen_within_pool):
            continue
        scored = qs.score_candidate(entry.get("raw", entry))
        if not qs.passes_quality_gate(scored, floor=QUALITY_FLOOR):
            continue
        merged = dict(entry)
        merged.update(scored)
        eligible.append(merged)
        seen_within_pool.append(entry)
    return eligible


def select_diverse(eligible, target):
    """Quality beats artificial balance: rank by score first. A soft
    per-bucket cap only kicks in to break up an otherwise homogeneous top
    list — it never blocks a bucket that is genuinely carrying the day
    (e.g. 3 exceptional experiments + nothing else strong enough)."""
    ranked = sorted(eligible, key=lambda c: c["score"], reverse=True)
    if len(ranked) <= target:
        return ranked

    soft_cap = max(2, math.ceil(target * 0.6))
    selected, per_bucket = [], {}
    leftover = []

    for cand in ranked:
        bucket = cand["content_type"]
        if len(selected) >= target:
            break
        if per_bucket.get(bucket, 0) < soft_cap:
            selected.append(cand)
            per_bucket[bucket] = per_bucket.get(bucket, 0) + 1
        else:
            leftover.append(cand)

    for cand in leftover:
        if len(selected) >= target:
            break
        selected.append(cand)

    return selected


def build_plan(selected, target):
    date = datetime.now(timezone.utc).date().isoformat()
    posts = []
    for rank, cand in enumerate(selected, 1):
        posts.append({
            "rank": rank,
            "content_id": cand["content_id"],
            "topic": cand["topic"],
            "category": cand["content_type"],
            "score": cand["score"],
            "reason": _reason(cand),
            "source": cand["source"],
            "source_url": cand["source_url"],
            "editorial_status": "PENDING",
            "render_status": "PENDING",
            "telegram_status": "PENDING",
            "publish_status": "PENDING",
        })
    return {
        "date": date,
        "target": target,
        "selected_count": len(posts),
        "quality_floor": QUALITY_FLOOR,
        "no_quality_post": len(posts) == 0,
        "posts": posts,
    }


def run(target=None):
    target = target if target is not None else DEFAULT_TARGET
    pool = cp.prune(cp.load_pool())
    recent_memory = _recent_memory_entries()

    eligible = eligible_candidates(pool["candidates"], recent_memory)
    selected = select_diverse(eligible, target)

    plan = build_plan(selected, target)
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Each selected story goes to editorial_engine.py one at a time, so
    # its own candidates.json input format is reused unchanged — every
    # entry here is a single "stories": [...] item, tagged with the
    # selection metadata the Telegram card needs later.
    selected_stories = []
    for post, cand in zip(plan["posts"], selected):
        raw = dict(cand["raw"])
        raw["content_id"] = cand["content_id"]
        raw["selection_meta"] = {
            "rank": post["rank"],
            "total": plan["selected_count"],
            "category": post["category"],
            "quality_score": post["score"],
            "why_selected": post["reason"],
            "source": post["source"],
        }
        selected_stories.append(raw)
    SELECTED_STORIES_PATH.write_text(
        json.dumps({"date": plan["date"], "stories": selected_stories}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Pool status is NOT marked SELECTED here — a candidate that later
    # fails editorial validation or rendering never got a real post or a
    # topic_memory block, and shouldn't be silently locked out of every
    # future selection. run_daily_selection_batch.py marks it via
    # candidate_pool.mark_selected() only once it actually succeeds.

    print("=" * 70)
    print("GETBYTERUSH DAILY SELECTION")
    print("=" * 70)
    print(f"Pool size (after prune): {len(pool['candidates'])}")
    print(f"Eligible after dedup/topic-memory/quality-gate: {len(eligible)}")
    print(f"Target: {target}  Quality floor: {QUALITY_FLOOR}")
    if not selected:
        print("NO_QUALITY_POST — nothing cleared the quality gate today.")
    for post in plan["posts"]:
        print(f"  #{post['rank']} [{post['category']}] score={post['score']} — {post['topic']}")
        print(f"      reason: {post['reason']}")

    return plan


def _load_today_plan():
    """The slotted schedule runs as five separate workflow invocations
    across the day (see content_slots.py), each contributing one post to
    the SAME day's plan — so this appends to today's plan file rather
    than overwriting it. A stale plan from a previous date is discarded
    (each day starts fresh)."""
    today = datetime.now(timezone.utc).date().isoformat()
    if PLAN_PATH.exists():
        try:
            plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
            if plan.get("date") == today:
                plan.setdefault("posts", [])
                plan.setdefault("slots", {})
                return plan
        except Exception:
            pass
    return {"date": today, "mode": "slotted", "quality_floor": QUALITY_FLOOR, "posts": [], "slots": {}}


def _save_plan(plan):
    plan["selected_count"] = len(plan["posts"])
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_slot(slot_name):
    """Selects the single best remaining candidate for one named slot
    (see content_slots.SLOTS) rather than a batch of ~5. Same dedup /
    topic-memory / quality-gate pipeline as run(); only the final
    selection step differs (top-1 within the slot's allowed categories,
    or top-1 overall for the category-agnostic 'night' slot). Zero
    Gemini calls — this only decides WHICH candidate, if any."""
    if slot_name not in content_slots.SLOTS:
        raise ValueError(f"Unknown slot: {slot_name}")
    slot = content_slots.SLOTS[slot_name]

    pool = cp.prune(cp.load_pool())
    recent_memory = _recent_memory_entries()
    eligible = eligible_candidates(pool["candidates"], recent_memory)
    if slot["categories"]:
        eligible = [c for c in eligible if c["content_type"] in slot["categories"]]
    eligible.sort(key=lambda c: c["score"], reverse=True)

    plan = _load_today_plan()

    print("=" * 70)
    print(f"GETBYTERUSH SLOT SELECTION — {slot_name} ({slot['label']})")
    print("=" * 70)
    print(f"Pool size (after prune): {len(pool['candidates'])}")
    print(f"Eligible in slot categories {slot['categories'] or 'ANY'}: {len(eligible)}")

    if not eligible:
        plan["slots"][slot_name] = {"status": "NO_QUALITY_POST", "label": slot["label"], "categories": slot["categories"]}
        _save_plan(plan)
        print(f"NO_QUALITY_POST — nothing in this slot's categories cleared the quality gate.")
        return plan, None

    chosen = eligible[0]
    rank = len(plan["posts"]) + 1
    post = {
        "rank": rank,
        "slot": slot_name,
        "content_id": chosen["content_id"],
        "topic": chosen["topic"],
        "category": chosen["content_type"],
        "score": chosen["score"],
        "reason": _reason(chosen),
        "source": chosen["source"],
        "source_url": chosen["source_url"],
        "editorial_status": "PENDING",
        "render_status": "PENDING",
        "telegram_status": "PENDING",
        "publish_status": "PENDING",
    }
    plan["posts"].append(post)
    plan["slots"][slot_name] = {"status": "SELECTED", "content_id": chosen["content_id"], "label": slot["label"]}
    _save_plan(plan)

    raw = dict(chosen["raw"])
    raw["content_id"] = chosen["content_id"]
    raw["selection_meta"] = {
        "rank": post["rank"],
        "total": None,  # unknown until the day's slots finish — the per-slot card shows the slot label instead
        "slot": slot_name,
        "slot_label": slot["label"],
        "category": post["category"],
        "quality_score": post["score"],
        "why_selected": post["reason"],
        "source": post["source"],
    }
    SELECTED_STORIES_PATH.write_text(
        json.dumps({"date": plan["date"], "stories": [raw]}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"SELECTED [{post['category']}] score={post['score']} — {post['topic']}")
    print(f"  reason: {post['reason']}")
    return plan, chosen


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--slot":
        run_slot(sys.argv[2])
    else:
        run()
