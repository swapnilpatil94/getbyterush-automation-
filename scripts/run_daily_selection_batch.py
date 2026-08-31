#!/usr/bin/env python3
"""GetByteRush content-generation orchestrator.

Two modes, sharing the same per-candidate pipeline:

- Full batch (`run()`): daily_selection.run() picks up to ~5 candidates
  at once (used for manual/backfill runs).
- Slotted (`run_slot(name)`): daily_selection.run_slot(name) picks the
  single best candidate for one named time-of-day slot (see
  content_slots.py) — this is what the five scheduled workflow triggers
  use, so each post is selected and generated close to its own target
  posting time instead of all ~5 bursting out together each morning.

Either way, each selected candidate goes through the same UNCHANGED
chain, one at a time:

    editorial_engine.py (ONE Gemini call, single-candidate input)
    -> topic_memory.py record
    -> run_daily_carousel.py (Graphics Director V17 -> render -> QA ->
       publishing package -> Telegram review card)

Nothing here modifies the editorial prompt, V17, or the Telegram
approval gate — this script only feeds them one pre-selected candidate
at a time instead of the whole pool, by writing data/candidates.json as
a single-item list before each editorial_engine.py invocation (exactly
the same input shape editorial_engine.py already expects). Gemini call
count == number of candidates actually attempted, never more.

A failure on one candidate (editorial validation exhausted its retries,
or the renderer/QA fails) is recorded in the daily content plan; a full
batch run continues to the next candidate rather than aborting the day.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import candidate_pool as cp
import daily_selection

CANDIDATES_PATH = Path("data/candidates.json")
SELECTED_STORY_PATH = Path("data/selected_story.json")
PLAN_PATH = Path("data/daily_content_plan.json")

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd, **kwargs):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, **kwargs)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def _load_plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _save_plan(plan):
    PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _update_post(plan, content_id, **fields):
    for post in plan["posts"]:
        if post["content_id"] == content_id:
            post.update(fields)
            break
    _save_plan(plan)


def _write_single_candidate(story):
    payload = {
        "generated_at": "",
        "count": 1,
        "stories": [{k: v for k, v in story.items() if k not in ("content_id", "selection_meta")}],
    }
    CANDIDATES_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _generate_one(pool_content_id, story, plan):
    """Runs the editorial -> V17 -> QA -> Telegram chain for one
    pre-selected candidate. Returns (gemini_calls_attempted, plan)."""
    _write_single_candidate(story)

    editorial = _run([sys.executable, "scripts/editorial_engine.py"])
    if editorial.returncode != 0:
        _update_post(plan, pool_content_id, editorial_status="FAILED")
        # Gemini rejected it (e.g. scored below editorial_engine.py's own
        # production threshold even after its internal repair retry) —
        # don't let the next slot immediately re-pick and re-spend a
        # Gemini call on the same likely-rejected candidate today.
        cp.mark_editorial_rejected([pool_content_id])
        print(f"EDITORIAL_FAILED for {pool_content_id}.")
        return 1, _load_plan()

    selected = json.loads(SELECTED_STORY_PATH.read_text(encoding="utf-8"))
    if not selected.get("selected"):
        _update_post(plan, pool_content_id, editorial_status="REJECTED_BY_EDITORIAL")
        cp.mark_editorial_rejected([pool_content_id])
        print(f"Editorial engine did not select {pool_content_id} despite being pre-picked.")
        return 1, _load_plan()

    # Carry the deterministic selection metadata through so the Telegram
    # card (built downstream in run_daily_carousel.py) can show
    # POST #N/CATEGORY or the slot label, WHY SELECTED, QUALITY SCORE —
    # without touching the editorial prompt or its JSON schema.
    selected["selection_meta"] = story["selection_meta"]
    SELECTED_STORY_PATH.write_text(json.dumps(selected, indent=2, ensure_ascii=False), encoding="utf-8")
    _update_post(plan, pool_content_id, editorial_status="GENERATED")

    _run([sys.executable, "scripts/topic_memory.py", "record"])

    carousel_env = dict(os.environ)
    carousel_env["PYTHONPATH"] = "scripts"
    carousel = _run([sys.executable, "scripts/run_daily_carousel.py"], env=carousel_env)

    content_state_id = ""
    for line in carousel.stdout.splitlines():
        if line.startswith("CONTENT_ID="):
            content_state_id = line.split("=", 1)[1].strip()

    if carousel.returncode != 0:
        _update_post(plan, pool_content_id, render_status="FAILED", content_state_id=content_state_id)
        print(f"RENDER_OR_QA_FAILED for {pool_content_id}.")
        return 1, _load_plan()

    _update_post(
        plan, pool_content_id,
        render_status="QA_PASSED",
        telegram_status="SENT",
        content_state_id=content_state_id,
    )
    # Only now — a real post reached Telegram review — is this pool
    # entry retired from future selection. A candidate that failed
    # earlier (editorial/render) was never marked SELECTED, so it can be
    # picked up again on a later run/slot.
    cp.mark_selected([pool_content_id])
    return 1, _load_plan()


def run():
    """Full batch: up to ~5 candidates in one run (manual/backfill use)."""
    plan = daily_selection.run()
    if plan["no_quality_post"]:
        print("NO_QUALITY_POST — 0 candidates cleared the quality gate today. Nothing sent to Telegram.")
        return plan

    stories_by_content_id = {
        s["content_id"]: s
        for s in json.loads(daily_selection.SELECTED_STORIES_PATH.read_text(encoding="utf-8"))["stories"]
    }

    gemini_calls = 0
    for post in plan["posts"]:
        pool_content_id = post["content_id"]
        story = stories_by_content_id[pool_content_id]
        print("=" * 70)
        print(f"POST #{post['rank']}/{plan['selected_count']} [{post['category']}] score={post['score']}")
        print(f"Topic: {post['topic']}")
        print("=" * 70)
        calls, plan = _generate_one(pool_content_id, story, plan)
        gemini_calls += calls

    print("=" * 70)
    print("GETBYTERUSH DAILY BATCH COMPLETE")
    print("=" * 70)
    print(f"Gemini calls this run: {gemini_calls} (== candidates attempted, target was {plan['target']})")
    for post in plan["posts"]:
        print(f"  #{post['rank']} {post['content_id']} editorial={post['editorial_status']} render={post['render_status']} telegram={post['telegram_status']}")

    return plan


def run_slot(slot_name):
    """One slot: at most one candidate, selected only from that slot's
    allowed categories (or any category for the category-agnostic
    slots). See content_slots.py for the schedule."""
    plan, chosen = daily_selection.run_slot(slot_name)
    if chosen is None:
        print(f"NO_QUALITY_POST for slot '{slot_name}' — nothing in its categories cleared the quality gate. Nothing sent to Telegram.")
        return plan

    story = json.loads(daily_selection.SELECTED_STORIES_PATH.read_text(encoding="utf-8"))["stories"][0]
    post = plan["posts"][-1]  # the one run_slot() just appended
    print("=" * 70)
    print(f"SLOT '{slot_name}' [{post['category']}] score={post['score']}")
    print(f"Topic: {post['topic']}")
    print("=" * 70)
    gemini_calls, plan = _generate_one(post["content_id"], story, plan)

    print("=" * 70)
    print(f"GETBYTERUSH SLOT '{slot_name}' COMPLETE")
    print("=" * 70)
    print(f"Gemini calls this run: {gemini_calls}")
    print(f"  {post['content_id']} editorial={post['editorial_status']} render={post['render_status']} telegram={post['telegram_status']}")
    return plan


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--slot":
        run_slot(sys.argv[2])
    else:
        run()
