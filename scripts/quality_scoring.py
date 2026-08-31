#!/usr/bin/env python3
"""GetByteRush deterministic quality scoring + content-type classification.

Zero Gemini calls. Consolidates rather than duplicates: the underlying
relevance/impact/freshness/curiosity signals are the same keyword-based
scores filter_stories.py already computes (imported, not re-derived).
This module's job is to (a) classify a story into one of the seven
content-mix buckets and (b) turn those signals into the 100-point
rubric used by daily_selection.py to rank and gate candidates.

Rubric (0-100):
  HOOK / SCROLL STOP     0-20   from impact_score (big numbers, drama)
  CURIOSITY              0-15   from curiosity keyword density
  INFORMATION VALUE      0-15   from relevance keyword density
  SAVE POTENTIAL         0-10   evergreen/how-to/reference value
  SHARE POTENTIAL        0-10   surprise + human-interest value
  NOVELTY                0-10   first/new/breakthrough language
  VISUAL POTENTIAL       0-10   numbers, comparisons, experiment-ability
  EVIDENCE / CREDIBILITY 0-5    source reputation + evidence presence
  TIMELINESS             0-5    freshness (evergreen gets a flat credit)
"""
import re
from datetime import datetime, timezone

import filter_stories as fs

CONTENT_TYPES = [
    "LAST_24H",
    "EXPERIMENT",
    "CURIOSITY",
    "EVERGREEN_VALUE",
    "INTERNET_HUMAN_TECH_BEHAVIOR",
    "DATA_RESEARCH",
    "PRODUCT_TOOL",
]

# Keyword sets not already covered by filter_stories.py — additive, not a
# replacement for its RELEVANCE/IMPACT/CURIOSITY/LOW_VALUE lists.
EXPERIMENT_KEYWORDS = [
    "we tested", "we tried", "hands-on", "hands on", "i tried", "we ran",
    "benchmarked", "benchmark test", "side-by-side", "side by side",
    "reproduc", "put it to the test", "real-world test", "stress test",
    "tried it for", "tested it", "we compared",
]

INTERNET_HUMAN_KEYWORDS = [
    "users report", "users say", "people are", "why do people", "reddit",
    "viral", "backlash", "community", "psychology", "habit", "addiction",
    "screen time", "trend", "trending", "social media", "influencer",
    "gen z", "burnout", "loneliness", "attention span", "doomscroll",
]

DATA_RESEARCH_KEYWORDS = [
    "study", "survey", "report finds", "dataset", "researchers found",
    "percent of", "% of", "according to data", "statistics", "analysis shows",
    "sample size", "peer-reviewed", "meta-analysis",
]

PRODUCT_TOOL_KEYWORDS = [
    "available now", "download", "pricing", "free tier", "subscription",
    "app store", "play store", "extension", "plugin", "sign up", "waitlist",
    "how to use", "getting started",
]

NOVELTY_KEYWORDS = [
    "first", "first-ever", "unprecedented", "breakthrough", "never before",
    "new record", "world's first", "debut",
]

_KNOWN_PRIMARY_SOURCES = {
    "google ai blog", "openai news", "microsoft ai", "meta ai", "nvidia blog",
}


def _text(story):
    return " ".join([story.get("title", ""), story.get("description", "")]).lower()


def _count(text, keywords):
    return sum(1 for kw in keywords if kw in text)


def classify_content_type(story):
    """First-match-wins heuristic across the 7 content-mix buckets."""
    text = _text(story)
    freshness = story.get("freshness_score", fs.freshness_score(story))
    story_type = story.get("story_type") or fs.classify_story(story)

    if _count(text, EXPERIMENT_KEYWORDS) >= 1:
        return "EXPERIMENT"
    if freshness >= 8:
        return "LAST_24H"
    if story_type == "RESEARCH" or _count(text, DATA_RESEARCH_KEYWORDS) >= 1:
        return "DATA_RESEARCH"
    if _count(text, INTERNET_HUMAN_KEYWORDS) >= 1:
        return "INTERNET_HUMAN_TECH_BEHAVIOR"
    curiosity_hits = _count(text, fs.CURIOSITY_KEYWORDS)
    if curiosity_hits >= 3:
        return "CURIOSITY"
    if story_type == "PRODUCT_UPDATE" or _count(text, PRODUCT_TOOL_KEYWORDS) >= 1:
        return "PRODUCT_TOOL"
    return "EVERGREEN_VALUE"


def score_candidate(story, now=None):
    """Returns the full rubric breakdown + total, plus the pool-metadata
    boolean/numeric fields the brief requires (evidence_available,
    evergreen, experiment_possible, etc). Freshness/timeliness are
    recomputed live against `now` rather than trusting a stale stored
    value, since pool candidates may be scored days after discovery."""
    now = now or datetime.now(timezone.utc)
    text = _text(story)

    relevance_matches = _count(text, fs.RELEVANCE_KEYWORDS)
    impact_matches = _count(text, fs.IMPACT_KEYWORDS)
    curiosity_matches = _count(text, fs.CURIOSITY_KEYWORDS)
    low_value_matches = _count(text, fs.LOW_VALUE_KEYWORDS)

    freshness_raw = fs.freshness_score(story)  # 0-10 scale, live recompute
    impact_raw = fs.impact_score(story)  # roughly 0-29 scale
    novelty_matches = _count(text, NOVELTY_KEYWORDS)

    bucket = classify_content_type(story)
    is_evergreen = bucket == "EVERGREEN_VALUE"
    is_experiment = bucket == "EXPERIMENT" or _count(text, EXPERIMENT_KEYWORDS) >= 1

    source = str(story.get("source", "")).strip().lower()
    credible_source = source in _KNOWN_PRIMARY_SOURCES
    has_url = bool(story.get("url"))
    has_description = len(story.get("description", "")) >= 60

    # ---- rubric sub-scores ----
    # Real RSS titles/descriptions are short and plainly worded — they
    # rarely hit filter_stories' dramatic IMPACT_KEYWORDS ("breach",
    # "banned", "first") even when the story is genuinely significant.
    # Hook/information-value lean primarily on relevance + freshness
    # (reliably present for anything that already passed
    # filter_stories.should_keep()), with impact/curiosity keywords as a
    # bonus on top rather than the sole signal.
    hook = min(20, relevance_matches * 2 + min(6, impact_matches * 2) + (6 if freshness_raw >= 8 else 3 if freshness_raw >= 5 else 0))
    curiosity_score = min(15, curiosity_matches * 4)
    information_value = min(15, relevance_matches * 2 + min(5, impact_matches))

    save_score = 6 if bucket in ("EVERGREEN_VALUE", "DATA_RESEARCH", "PRODUCT_TOOL") else 4
    if any(p in text for p in ("how to", "guide", "explained", "everything you need")):
        save_score = min(10, save_score + 3)
    if relevance_matches >= 3:
        save_score = min(10, save_score + 1)

    share_score = min(10, 3 + impact_matches * 2 + min(3, curiosity_matches))
    if bucket == "INTERNET_HUMAN_TECH_BEHAVIOR":
        share_score = min(10, share_score + 3)

    novelty = min(10, novelty_matches * 4 + (2 if freshness_raw >= 9 else 0))

    visual_potential = 3
    if re.search(r"\b\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?|\b\d+x\b", text, re.IGNORECASE):
        visual_potential += 3
    if "vs" in text or "versus" in text or "compared" in text:
        visual_potential += 2
    if is_experiment:
        visual_potential += 2
    visual_potential = min(10, visual_potential)

    credibility = 5 if credible_source else (3 if has_url and has_description else 1)
    evidence_available = credibility >= 3

    timeliness = 3 if is_evergreen else min(5, round(freshness_raw / 2))

    total = (
        hook + curiosity_score + information_value + save_score + share_score
        + novelty + visual_potential + credibility + timeliness
    )
    if is_experiment:
        # Testable/reproducible content is explicitly called out as
        # especially valuable (it can later become a faceless Reel), and
        # keyword density alone tends to undersell it since "we tested"
        # phrasing doesn't overlap much with the relevance/impact lists.
        total += 8
    total = max(0, min(100, total - min(low_value_matches * 5, 20)))

    strong_signals = []
    if curiosity_score >= 10:
        strong_signals.append("HIGHLY_CURIOUS")
    elif curiosity_score >= 6:
        strong_signals.append("SURPRISING")
    elif hook >= 14 or impact_matches >= 2:
        # A high hook score or multiple impact-keyword hits (breach,
        # layoffs, acquisition, regulation...) marks a genuinely
        # important/urgent story even without curiosity-style phrasing.
        strong_signals.append("SURPRISING")
    if save_score >= 7:
        strong_signals.append("USEFUL")
    if novelty >= 6 or (bucket == "LAST_24H" and freshness_raw >= 9):
        strong_signals.append("NEW")
    if evidence_available and credibility >= 3:
        strong_signals.append("PROVABLE")
    if is_experiment:
        strong_signals.append("DEMONSTRABLE")
    if is_evergreen and information_value >= 6:
        strong_signals.append("EXPLAINABLE")

    return {
        "content_type": bucket,
        "score": total,
        "breakdown": {
            "hook": hook,
            "curiosity": curiosity_score,
            "information_value": information_value,
            "save_potential": save_score,
            "share_potential": share_score,
            "novelty": novelty,
            "visual_potential": visual_potential,
            "evidence_credibility": credibility,
            "timeliness": timeliness,
        },
        "evidence_available": evidence_available,
        "evergreen": is_evergreen,
        "experiment_possible": is_experiment,
        "timeliness": timeliness,
        "novelty": novelty,
        "visual_potential": visual_potential,
        "curiosity_score": curiosity_score,
        "save_score": save_score,
        "share_score": share_score,
        "information_value": information_value,
        "credibility": credibility,
        "strong_signals": strong_signals,
        "low_value_matches": low_value_matches,
    }


def passes_quality_gate(scored, floor=60):
    """Strong candidates need a decent total AND at least one of the
    named strong signals (SURPRISING/USEFUL/NEW/PROVABLE/DEMONSTRABLE/
    EXPLAINABLE/HIGHLY_CURIOUS) — a high score alone from generic
    keyword density isn't enough."""
    if scored["low_value_matches"] >= 2:
        return False
    if scored["score"] < floor:
        return False
    return len(scored["strong_signals"]) >= 1
