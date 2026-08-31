#!/usr/bin/env python3
"""GetByteRush daily batch orchestrator.

Runs daily_selection.py to deterministically pick up to ~5 candidates,
then for EACH selected candidate — one at a time, sequentially — runs
the unchanged existing chain:

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
or the renderer/QA fails) is recorded in the daily content plan and the
batch continues to the next candidate rather than aborting the whole day.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import daily_selection

CANDIDATES_PATH = Path("data/candidates.json")
SELECTED_STORY_PATH = Path("data/selected_story.json")
SELECTED_STORIES_PATH = Path("data/selected_stories.json")
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


def run():
    plan = daily_selection.run()
    if plan["no_quality_post"]:
        print("NO_QUALITY_POST — 0 candidates cleared the quality gate today. Nothing sent to Telegram.")
        return plan

    stories_by_content_id = {
        s["content_id"]: s
        for s in json.loads(SELECTED_STORIES_PATH.read_text(encoding="utf-8"))["stories"]
    }

    gemini_calls = 0
    for post in plan["posts"]:
        pool_content_id = post["content_id"]
        story = stories_by_content_id[pool_content_id]
        print("=" * 70)
        print(f"POST #{post['rank']}/{plan['selected_count']} [{post['category']}] score={post['score']}")
        print(f"Topic: {post['topic']}")
        print("=" * 70)

        _write_single_candidate(story)

        editorial = _run([sys.executable, "scripts/editorial_engine.py"])
        gemini_calls += 1  # attempted regardless of success — this is what "counted" means
        if editorial.returncode != 0:
            _update_post(plan, pool_content_id, editorial_status="FAILED")
            print(f"EDITORIAL_FAILED for {pool_content_id} — skipping to next candidate.")
            continue

        selected = json.loads(SELECTED_STORY_PATH.read_text(encoding="utf-8"))
        if not selected.get("selected"):
            _update_post(plan, pool_content_id, editorial_status="REJECTED_BY_EDITORIAL")
            print(f"Editorial engine did not select {pool_content_id} despite being pre-picked — skipping.")
            continue

        # Carry the deterministic selection metadata through so the
        # Telegram card (built downstream in run_daily_carousel.py) can
        # show POST #N/CATEGORY/WHY SELECTED/QUALITY SCORE without
        # touching the editorial prompt or its JSON schema.
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
            print(f"RENDER_OR_QA_FAILED for {pool_content_id} — skipping to next candidate.")
            continue

        _update_post(
            plan, pool_content_id,
            render_status="QA_PASSED",
            telegram_status="SENT",
            content_state_id=content_state_id,
        )

    plan = _load_plan()
    print("=" * 70)
    print("GETBYTERUSH DAILY BATCH COMPLETE")
    print("=" * 70)
    print(f"Gemini calls this run: {gemini_calls} (== candidates attempted, target was {plan['target']})")
    for post in plan["posts"]:
        print(f"  #{post['rank']} {post['content_id']} editorial={post['editorial_status']} render={post['render_status']} telegram={post['telegram_status']}")

    return plan


if __name__ == "__main__":
    run()
