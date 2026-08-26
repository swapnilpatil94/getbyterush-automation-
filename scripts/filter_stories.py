import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# ============================================================
# GETBYTERUSH PRE-FILTER
#
# Purpose:
#   Clean the RSS radar output before Gemini editorial scoring.
#
# IMPORTANT:
#   This is NOT the viral-content selector.
#   It should be permissive.
#
#   Radar:
#       ~1187 stories
#
#   Pre-filter:
#       ideally ~30–100 candidates
#
#   Gemini:
#       decides what is actually worth posting
# ============================================================


# ============================================================
# TECHNOLOGY / AI RELEVANCE
# ============================================================

RELEVANCE_KEYWORDS = [

    # AI
    "ai",
    "artificial intelligence",
    "agent",
    "agents",
    "agentic",
    "ai agent",
    "ai agents",
    "model",
    "models",
    "reasoning",
    "multimodal",
    "generative ai",

    # Major companies / products
    "openai",
    "chatgpt",
    "gpt",
    "anthropic",
    "claude",
    "google",
    "gemini",
    "deepmind",
    "meta ai",
    "microsoft",
    "copilot",
    "nvidia",
    "xai",
    "perplexity",
    "mistral",
    "cohere",

    # Infrastructure
    "gpu",
    "chip",
    "chips",
    "semiconductor",
    "inference",
    "training",
    "compute",
    "datacenter",
    "data center",
    "cloud",
    "mcp",
    "model context protocol",

    # Technology
    "robot",
    "robotics",
    "humanoid",
    "autonomous",
    "self-driving",
    "browser",
    "search",
    "internet",
    "software",
    "developer",
    "developers",
    "github",
    "open source",
    "startup",
    "platform",

    # Security
    "cybersecurity",
    "cyber security",
    "security",
    "hack",
    "hacked",
    "breach",
    "vulnerability",
    "exploit",
    "malware",
    "ransomware",
    "privacy",

    # Business / work
    "acquisition",
    "acquired",
    "funding",
    "investment",
    "revenue",
    "valuation",
    "layoff",
    "layoffs",
    "laid off",
    "employees",
    "workforce",
    "productivity",
    "enterprise",

    # Consumer technology
    "iphone",
    "android",
    "pixel",
    "apple",
    "samsung",
    "instagram",
    "whatsapp",
    "youtube",
    "tiktok",
    "amazon",
]


# ============================================================
# IMPACT SIGNALS
# ============================================================

IMPACT_KEYWORDS = [

    "replaces",
    "replace",
    "replacement",
    "jobs",
    "job cuts",
    "layoffs",
    "laid off",
    "cuts",
    "shutdown",
    "banned",
    "ban",
    "blocked",
    "breach",
    "hacked",
    "hack",
    "attack",
    "vulnerability",
    "exploit",
    "security flaw",
    "privacy",
    "surveillance",
    "record",
    "first",
    "first-ever",
    "largest",
    "biggest",
    "breakthrough",
    "new model",
    "new ai",
    "new agent",
    "autonomous",
    "acquisition",
    "acquired",
    "funding",
    "valuation",
    "revenue",
    "regulation",
    "lawsuit",
    "court",
    "government",
    "investigation",
    "copyright",
    "open source",
    "production",
    "deployment",
    "real-world",
    "real world",
]


# ============================================================
# CURIOSITY SIGNALS
# ============================================================

CURIOSITY_KEYWORDS = [

    "secret",
    "surprise",
    "unexpected",
    "quietly",
    "silently",
    "inside",
    "behind",
    "reveals",
    "revealed",
    "why",
    "how",
    "changed",
    "changes",
    "turning point",
    "problem",
    "failed",
    "failure",
    "warning",
    "risk",
    "danger",
    "strange",
    "weird",
    "instead",
    "however",
    "but",
]


# ============================================================
# OBVIOUS LOW-VALUE CONTENT
#
# Only use these as a strong negative signal.
# Do NOT over-filter normal technology announcements.
# ============================================================

LOW_VALUE_KEYWORDS = [

    "home decor",
    "dinner party",
    "football club",
    "holiday",
    "gift guide",
    "recipes",
    "recipe",
    "fashion",
    "shopping tips",
    "vacation tips",
    "decor",
    "meal planning",
    "party ideas",
    "study tips",
    "lifestyle tips",
    "how to decorate",
    "how to host",
]


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(value):

    if not value:
        return None

    value = str(value).strip()

    try:
        return parsedate_to_datetime(
            value
        ).astimezone(
            timezone.utc
        )

    except Exception:
        pass

    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        ).astimezone(
            timezone.utc
        )

    except Exception:
        return None


# ============================================================
# TEXT
# ============================================================

def get_text(story):

    return " ".join(
        [
            story.get("title", ""),
            story.get("description", ""),
        ]
    ).lower()


# ============================================================
# MATCHING
# ============================================================

def count_matches(
    text,
    keywords
):

    return sum(
        1
        for keyword in keywords
        if keyword in text
    )


# ============================================================
# FRESHNESS
# ============================================================

def freshness_score(story):

    published = parse_date(
        story.get(
            "published",
            ""
        )
    )

    if not published:
        return 0

    now = datetime.now(
        timezone.utc
    )

    age_hours = (
        now - published
    ).total_seconds() / 3600

    if age_hours < -1:
        return 0

    if age_hours <= 6:
        return 10

    if age_hours <= 12:
        return 9

    if age_hours <= 24:
        return 8

    if age_hours <= 48:
        return 6

    if age_hours <= 72:
        return 5

    if age_hours <= 168:
        return 2

    return 0


# ============================================================
# RELEVANCE
#
# Deliberately generous.
# ============================================================

def relevance_score(story):

    text = get_text(
        story
    )

    relevance_matches = count_matches(
        text,
        RELEVANCE_KEYWORDS
    )

    impact_matches = count_matches(
        text,
        IMPACT_KEYWORDS
    )

    curiosity_matches = count_matches(
        text,
        CURIOSITY_KEYWORDS
    )

    low_value_matches = count_matches(
        text,
        LOW_VALUE_KEYWORDS
    )

    score = 0

    # Main technology relevance
    score += min(
        relevance_matches * 2,
        16
    )

    # Impact
    score += min(
        impact_matches * 2,
        8
    )

    # Curiosity
    score += min(
        curiosity_matches,
        5
    )

    # Obvious lifestyle/noise
    score -= min(
        low_value_matches * 5,
        15
    )

    return max(
        score,
        0
    )


# ============================================================
# IMPACT
# ============================================================

def impact_score(story):

    text = get_text(
        story
    )

    matches = count_matches(
        text,
        IMPACT_KEYWORDS
    )

    curiosity = count_matches(
        text,
        CURIOSITY_KEYWORDS
    )

    score = min(
        matches * 3,
        18
    )

    score += min(
        curiosity * 2,
        6
    )

    # Numbers create good visual possibilities.
    if re.search(
        r"\b\d+(?:\.\d+)?%"
        r"|\$\d+(?:\.\d+)?"
        r"|\b\d+x\b"
        r"|\b\d+\s*(?:million|billion|trillion)\b",
        text,
        re.IGNORECASE
    ):
        score += 3

    # Comparisons
    if any(
        phrase in text
        for phrase in [
            "vs",
            "versus",
            "compared with",
            "compared to",
            "faster than",
            "larger than",
            "smaller than",
            "more than",
            "less than",
        ]
    ):
        score += 2

    return score


# ============================================================
# STORY TYPE
# ============================================================

def classify_story(story):

    text = get_text(
        story
    )

    if any(
        term in text
        for term in [
            "new model",
            "ai model",
            "reasoning model",
            "foundation model",
            "language model",
            "gpt",
            "gemini",
            "claude",
        ]
    ):
        return "MODEL_UPDATE"

    if any(
        term in text
        for term in [
            "ai agent",
            "ai agents",
            "agentic",
            "managed agents",
            "autonomous agent",
        ]
    ):
        return "AI_AGENTS"

    if any(
        term in text
        for term in [
            "breach",
            "hack",
            "hacked",
            "vulnerability",
            "exploit",
            "cybersecurity",
            "ransomware",
            "malware",
        ]
    ):
        return "SECURITY"

    if any(
        term in text
        for term in [
            "layoff",
            "layoffs",
            "laid off",
            "acquisition",
            "acquired",
            "funding",
            "valuation",
            "revenue",
            "employees",
            "workforce",
        ]
    ):
        return "BUSINESS"

    if any(
        term in text
        for term in [
            "research",
            "study",
            "breakthrough",
            "demonstrates",
            "demonstrated",
            "experiment",
        ]
    ):
        return "RESEARCH"

    if any(
        term in text
        for term in [
            "launch",
            "launched",
            "introducing",
            "available",
            "rollout",
            "update",
            "feature",
            "platform",
        ]
    ):
        return "PRODUCT_UPDATE"

    return "TECH_NEWS"


# ============================================================
# KEEP / DROP
#
# This is intentionally permissive.
# ============================================================

def should_keep(story):

    relevance = relevance_score(
        story
    )

    freshness = freshness_score(
        story
    )

    impact = impact_score(
        story
    )

    text = get_text(
        story
    )

    low_value = count_matches(
        text,
        LOW_VALUE_KEYWORDS
    )

    # --------------------------------------------------------
    # Obvious junk
    # --------------------------------------------------------

    if low_value >= 2:
        return False

    # --------------------------------------------------------
    # Recent + relevant
    #
    # This is the main path.
    # --------------------------------------------------------

    if freshness >= 5 and relevance >= 4:
        return True

    # --------------------------------------------------------
    # Very fresh stories get a lower relevance threshold.
    # --------------------------------------------------------

    if freshness >= 8 and relevance >= 2:
        return True

    # --------------------------------------------------------
    # Older but genuinely important stories.
    # --------------------------------------------------------

    if freshness == 2 and impact >= 8:
        return True

    # --------------------------------------------------------
    # Undated stories:
    # keep only when they have substantial relevance.
    # --------------------------------------------------------

    if freshness == 0 and relevance >= 10:
        return True

    return False


# ============================================================
# LOAD
# ============================================================

def load_stories():

    path = "data/raw_stories.json"

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"Missing {path}. "
            "Run radar.py first."
        )

    with open(
        path,
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )

    return data.get(
        "stories",
        []
    )


# ============================================================
# SAVE
# ============================================================

def save_candidates(
    candidates
):

    result = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(candidates),

        "stories":
            candidates,
    }

    with open(
        "data/candidates.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# MAIN
# ============================================================

def main():

    stories = load_stories()

    candidates = []

    # ========================================================
    # SCORE + FILTER
    # ========================================================

    for story in stories:

        relevance = relevance_score(
            story
        )

        impact = impact_score(
            story
        )

        freshness = freshness_score(
            story
        )

        story_type = classify_story(
            story
        )

        # Freshness matters, but does not dominate.
        combined_score = (
            relevance
            + impact
            + freshness
        )

        story[
            "relevance_score"
        ] = relevance

        story[
            "impact_score"
        ] = impact

        story[
            "freshness_score"
        ] = freshness

        story[
            "story_type"
        ] = story_type

        story[
            "pre_filter_score"
        ] = combined_score

        if should_keep(story):

            candidates.append(
                story
            )

    # ========================================================
    # SORT
    # ========================================================

    candidates.sort(
        key=lambda story: (
            story.get(
                "freshness_score",
                0
            ),
            story.get(
                "pre_filter_score",
                0
            ),
            story.get(
                "impact_score",
                0
            ),
        ),
        reverse=True
    )

    # ========================================================
    # DEDUPLICATE EXACT TITLES
    # ========================================================

    seen = set()

    unique_candidates = []

    for story in candidates:

        title = story.get(
            "title",
            ""
        ).strip().lower()

        normalized = re.sub(
            r"\s+",
            " ",
            title
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        unique_candidates.append(
            story
        )

    candidates = unique_candidates

    # ========================================================
    # LIMIT TO A HEALTHY GEMINI INPUT
    # ========================================================

    candidates = candidates[:80]

    save_candidates(
        candidates
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print("")
    print("=" * 70)
    print("GETBYTERUSH PRE-FILTER")
    print("=" * 70)
    print("")

    print(
        f"Raw stories: {len(stories)}"
    )

    print(
        f"Candidates: {len(candidates)}"
    )

    fresh = sum(
        1
        for story in candidates
        if story.get(
            "freshness_score",
            0
        ) >= 5
    )

    print(
        f"Fresh candidates (<72h): {fresh}"
    )

    print("")

    for index, story in enumerate(
        candidates[:30],
        1
    ):

        print(
            f"{index}. "
            f"{story.get('title', '')}"
        )

        print(
            f"   Source: "
            f"{story.get('source', '')}"
        )

        print(
            f"   Type: "
            f"{story.get('story_type', '')}"
        )

        print(
            f"   Relevance: "
            f"{story.get('relevance_score', 0)}"
        )

        print(
            f"   Impact: "
            f"{story.get('impact_score', 0)}"
        )

        print(
            f"   Freshness: "
            f"{story.get('freshness_score', 0)}"
        )

        print(
            f"   Pre-filter: "
            f"{story.get('pre_filter_score', 0)}"
        )

        print(
            f"   URL: "
            f"{story.get('url', '')}"
        )

        print("")


if __name__ == "__main__":

    main()