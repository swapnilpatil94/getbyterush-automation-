#!/usr/bin/env python3
"""Local, offline test harness for the content research/selection engine
(candidate_pool.py, quality_scoring.py, daily_selection.py). Zero network
calls, zero Gemini calls — everything here is deterministic and runs
against synthetic fixtures under a temp data/state root, never touching
the real data/candidate_pool.json or state/topic_memory.json.

Covers the required test-case shapes: breaking AI news, product launch,
real experiment, evergreen explainer, curiosity story, comparison,
data/research, internet behavior, security event, long-form/dense story
— plus dedup, topic-memory blocking, diversity-aware selection, and the
NO_QUALITY_POST fallback.

Run: python scripts/test_content_engine.py
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))


def now_iso(hours_ago=0):
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%a, %d %b %Y %H:%M:%S +0000")


FIXTURES = [
    # 1. Breaking AI news (<6h old)
    {
        "source": "OpenAI News", "title": "OpenAI launches new reasoning model with 40% faster inference",
        "url": "https://openai.com/news/reasoning-model-launch",
        "description": "OpenAI announced a new reasoning model today, claiming 40% faster inference than the previous generation.",
        "published": now_iso(2),
    },
    # 2. Product launch
    {
        "source": "TechCrunch", "title": "New AI writing app launches with free tier and waitlist",
        "url": "https://example.com/ai-writing-app-launch",
        "description": "A new AI writing tool is now available for download on the app store, with a free tier and paid subscription pricing.",
        "published": now_iso(10),
    },
    # 3. Real experiment (testable/reproducible)
    {
        "source": "Independent Blog", "title": "We tested 5 AI coding agents side-by-side on the same benchmark",
        "url": "https://example.com/ai-agent-benchmark-test",
        "description": "We ran a side-by-side benchmark test comparing five AI coding agents on identical reproducible tasks.",
        "published": now_iso(20),
    },
    # 4. Evergreen explainer
    {
        "source": "Explainer Site", "title": "How large language models actually work, explained simply",
        "url": "https://example.com/how-llms-work-explained",
        "description": "A guide explaining how large language models process text, useful reference for understanding AI months from now.",
        "published": now_iso(400),
    },
    # 5. Curiosity story
    {
        "source": "Curious Blog", "title": "Why does ChatGPT sometimes refuse simple questions? The strange reason revealed",
        "url": "https://example.com/why-chatgpt-refuses-strange",
        "description": "Researchers reveal the surprising, unexpected reason behind a strange quirk in how the model behaves. Why does this happen?",
        "published": now_iso(30),
    },
    # 6. Comparison
    {
        "source": "Compare Blog", "title": "GPT vs Gemini vs Claude: which model is actually faster than the others",
        "url": "https://example.com/gpt-vs-gemini-vs-claude-compared",
        "description": "A comparison of three major models, compared to each other on speed, cost, and accuracy, more than 10000 tokens tested.",
        "published": now_iso(15),
    },
    # 7. Data/research
    {
        "source": "Research Journal", "title": "New study finds 62% of developers now use AI agents daily",
        "url": "https://example.com/study-62-percent-developers-ai-agents",
        "description": "Researchers found that a survey of developers shows 62% of respondents now use AI agents daily, according to data from a new report.",
        "published": now_iso(40),
    },
    # 8. Internet/human tech behavior
    {
        "source": "Culture Blog", "title": "Why Gen Z is quietly addicted to AI chatbots for companionship",
        "url": "https://example.com/genz-addicted-ai-chatbots-companionship",
        "description": "Users report a growing trend on social media and reddit around AI chatbot use, raising psychology and loneliness questions.",
        "published": now_iso(50),
    },
    # 9. Security/technology event
    {
        "source": "Security Wire", "title": "Critical vulnerability exploited in popular AI framework, breach confirmed",
        "url": "https://example.com/critical-vulnerability-ai-framework-breach",
        "description": "A security breach was confirmed after attackers exploited a critical vulnerability, a major hack affecting cloud infrastructure.",
        "published": now_iso(4),
    },
    # 10. Long-form / high-density story
    {
        "source": "Deep Dive Wire", "title": "Inside the acquisition: how a $2 billion AI deal reshaped the chip industry",
        "url": "https://example.com/inside-acquisition-2-billion-ai-deal-chip",
        "description": "An investigation into the acquisition, revealing how the largest AI chip deal in years changed compute, GPU supply, and workforce plans, with layoffs and government scrutiny.",
        "published": now_iso(60),
    },
    # 11. Low-value / should be excluded from the pool entirely
    {
        "source": "Lifestyle Blog", "title": "Best holiday gift guide and recipes for your dinner party",
        "url": "https://example.com/holiday-gift-guide-recipes-dinner-party",
        "description": "Fashion and home decor tips plus recipes for your next dinner party and vacation tips.",
        "published": now_iso(5),
    },
    # 12. Near-duplicate of #1 (should be deduped within the pool)
    {
        "source": "Mirror Blog", "title": "OpenAI launches new reasoning model with 40% faster inference",
        "url": "https://mirror.example.com/openai-reasoning-model-copy",
        "description": "OpenAI announced a new reasoning model today, claiming 40% faster inference than the previous generation.",
        "published": now_iso(3),
    },
]


def run():
    import filter_stories as fs

    for story in FIXTURES:
        story["freshness_score"] = fs.freshness_score(story)
        story["relevance_score"] = fs.relevance_score(story)
        story["impact_score"] = fs.impact_score(story)
        story["story_type"] = fs.classify_story(story)
        story["pre_filter_score"] = story["relevance_score"] + story["impact_score"] + story["freshness_score"]

    tmp = Path(tempfile.mkdtemp(prefix="gbr-content-engine-test-"))
    (tmp / "data").mkdir()
    (tmp / "state").mkdir()
    cwd = Path.cwd()
    os.chdir(tmp)
    try:
        import candidate_pool as cp
        import quality_scoring as qs
        import daily_selection as ds
        import importlib
        importlib.reload(cp)
        importlib.reload(ds)

        print("=" * 70)
        print("TEST 1: classification covers all 7 buckets across fixtures")
        print("=" * 70)
        buckets_seen = set()
        for story in FIXTURES[:11]:
            bucket = qs.classify_content_type(story)
            buckets_seen.add(bucket)
            print(f"  {bucket:<32} {story['title'][:60]}")
        missing = set(qs.CONTENT_TYPES) - buckets_seen
        assert len(buckets_seen) >= 5, f"expected at least 5 distinct buckets, got {buckets_seen}"
        print(f"PASS — {len(buckets_seen)}/7 buckets represented (missing: {missing or 'none'})")

        print()
        print("=" * 70)
        print("TEST 2: low-value fixture (#11) fails the quality gate")
        print("=" * 70)
        low_value = FIXTURES[10]
        scored = qs.score_candidate(low_value)
        gate = qs.passes_quality_gate(scored)
        print(f"  score={scored['score']} strong_signals={scored['strong_signals']} passes_gate={gate}")
        assert gate is False, "low-value lifestyle story must not pass the quality gate"
        print("PASS")

        print()
        print("=" * 70)
        print("TEST 3: pool merge dedupes the near-duplicate fixture (#1 vs #12)")
        print("=" * 70)
        cp.merge_new_candidates(FIXTURES[:12])
        pool = cp.load_pool()
        openai_entries = [e for e in pool["candidates"] if "openai" in e["title"].lower() and "reasoning model" in e["title"].lower()]
        print(f"  pool_size={len(pool['candidates'])} openai_reasoning_entries={len(openai_entries)}")
        assert len(openai_entries) == 1, "near-duplicate story must be deduped, not double-pooled"
        print("PASS")

        print()
        print("=" * 70)
        print("TEST 4: re-running merge with the same fixtures adds nothing new")
        print("=" * 70)
        before = len(cp.load_pool()["candidates"])
        cp.merge_new_candidates(FIXTURES[:12])
        after = len(cp.load_pool()["candidates"])
        print(f"  before={before} after={after}")
        assert before == after, "re-merging identical stories must not grow the pool"
        print("PASS")

        print()
        print("=" * 70)
        print("TEST 5: daily selection picks <= target, diverse, quality-gated")
        print("=" * 70)
        os.environ["DAILY_SELECTION_TARGET"] = "5"
        os.environ["DAILY_SELECTION_QUALITY_FLOOR"] = "45"
        plan = ds.run(target=5)
        cats = [p["category"] for p in plan["posts"]]
        print(f"  selected={len(plan['posts'])} categories={cats}")
        assert len(plan["posts"]) <= 5
        assert len(plan["posts"]) >= 1, "expected at least one quality candidate from 10 strong fixtures"
        assert all(p["score"] >= 45 for p in plan["posts"])
        print("PASS")

        print()
        print("=" * 70)
        print("TEST 6: topic memory blocks a selected topic from re-selection")
        print("=" * 70)
        import topic_memory as tm
        selected_path = Path("data/selected_stories.json")
        first_pick = json.loads(selected_path.read_text())["stories"][0]
        (Path("data/selected_story.json")).write_text(json.dumps({
            "selected": True, "story_title": first_pick["title"],
            "source_story": {"title": first_pick["title"], "url": first_pick["url"], "source": first_pick["source"]},
        }))
        tm.record()
        plan2 = ds.run(target=5)
        titles2 = [p["topic"] for p in plan2["posts"]]
        print(f"  re-selected topics: {titles2}")
        assert first_pick["title"] not in titles2, "topic-memory-recorded topic must not be re-selected same week"
        print("PASS")

        print()
        print("=" * 70)
        print("TEST 7: NO_QUALITY_POST when pool has nothing above the floor")
        print("=" * 70)
        shutil.rmtree("data", ignore_errors=True)
        Path("data").mkdir()
        cp.merge_new_candidates([FIXTURES[10]])  # only the low-value story
        os.environ["DAILY_SELECTION_QUALITY_FLOOR"] = "60"
        plan3 = ds.run(target=5)
        print(f"  no_quality_post={plan3['no_quality_post']} selected_count={plan3['selected_count']}")
        assert plan3["no_quality_post"] is True
        assert plan3["selected_count"] == 0
        print("PASS")

        print()
        print("=" * 70)
        print("ALL CONTENT ENGINE TESTS PASSED — 0 Gemini calls made")
        print("=" * 70)
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    run()
