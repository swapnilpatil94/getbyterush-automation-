import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# ============================================================
# GETBYTERUSH EDITORIAL PRE-FILTER
#
# Purpose:
#   Remove obvious low-value stories before Gemini evaluates
#   the candidates for actual Instagram potential.
#
# Important:
#   This is NOT the final viral-content scorer.
#
#   Pipeline:
#
#   RSS / Atom feeds
#          ↓
#   radar.py
#          ↓
#   freshness + relevance
#          ↓
#   THIS FILE
#          ↓
#   Gemini editorial judge
#          ↓
#   story / carousel / post
#
# ============================================================


# ============================================================
# HIGH-VALUE TOPICS
# ============================================================

HIGH_VALUE_KEYWORDS = [

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
    "foundation model",
    "reasoning model",
    "multimodal",
    "generative ai",

    # Major AI companies
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

    # AI infrastructure
    "gpu",
    "chip",
    "semiconductor",
    "inference",
    "training",
    "datacenter",
    "data center",
    "compute",
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
    "github",
    "open source",
    "startup",
    "app",
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
    "surveillance",

    # Business
    "acquisition",
    "acquired",
    "funding",
    "investment",
    "revenue",
    "valuation",
    "layoff",
    "laid off",
    "employees",
    "enterprise",
    "workforce",
    "productivity",

    # Consumer tech
    "iphone",
    "android",
    "pixel",
    "apple",
    "samsung",
    "meta",
    "instagram",
    "whatsapp",
    "youtube",
    "tiktok",
    "amazon",
    "google search",
]


# ============================================================
# HIGH-IMPACT TERMS
#
# These indicate a story may have consequences beyond a
# routine product announcement.
# ============================================================

HIGH_IMPACT_KEYWORDS = [

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
    "most powerful",
    "breakthrough",
    "breakthroughs",
    "new model",
    "new ai",
    "new agent",
    "autonomous",
    "agentic",
    "acquisition",
    "acquired",
    "raises",
    "funding",
    "valuation",
    "revenue",
    "profit",
    "loss",
    "regulation",
    "lawsuit",
    "court",
    "government",
    "investigation",
    "copyright",
    "copyright lawsuit",
    "open source",
    "open-sourced",
    "production",
    "deployment",
    "real-world",
    "real world",
]


# ============================================================
# CURIOSITY SIGNALS
#
# These are useful because the eventual Instagram story needs
# a reason for someone to stop scrolling.
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
    "what happened",
    "changed",
    "changes",
    "turning point",
    "problem",
    "failed",
    "failure",
    "didn't",
    "couldn't",
    "instead",
    "but",
    "however",
    "warning",
    "risk",
    "danger",
    "strange",
    "weird",
    "unexpectedly",
]


# ============================================================
# WEAK / LOW-VALUE TOPICS
#
# These should normally be excluded unless there is a very
# strong secondary signal.
# ============================================================

LOW_VALUE_KEYWORDS = [

    "home decor",
    "dinner party",
    "back to school",
    "football club",
    "holiday",
    "gift guide",
    "recipes",
    "recipe",
    "fashion",
    "shopping tips",
    "travel tips",
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
# ROUTINE ANNOUNCEMENT SIGNALS
#
# Not automatically bad.
#
# But a simple "new feature available" story should require
# stronger impact / usefulness before reaching Gemini.
# ============================================================

ROUTINE_TERMS = [

    "tips",
    "ways to",
    "how to",
    "level up",
    "upgrade your",
    "celebrating",
    "recap",
    "guide",
    "announcement",
    "introducing",
    "learn more",
]


# ============================================================
# SOURCE PRIORITY
#
# First-party sources are useful for verification.
# But first-party does NOT automatically mean interesting.
# ============================================================

PRIMARY_SOURCES = {

    "OpenAI News",
    "Google AI Blog",
    "Microsoft AI",
    "Meta AI",
    "NVIDIA Blog",
}


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(value):

    if not value:
        return None

    value = str(value).strip()

    # RSS date
    try:

        return parsedate_to_datetime(
            value
        ).astimezone(
            timezone.utc
        )

    except Exception:
        pass

    # ISO date
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
# TEXT NORMALIZATION
# ============================================================

def story_text(story):

    return " ".join(
        [
            story.get("title", ""),
            story.get("description", ""),
        ]
    ).lower()


# ============================================================
# WORD / PHRASE MATCHING
# ============================================================

def count_matches(text, keywords):

    score = 0

    for keyword in keywords:

        if keyword in text:

            score += 1

    return score


# ============================================================
# FRESHNESS
#
# Daily GetByteRush content should heavily favor recent stories.
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

    # Future/malformed date
    if age_hours < -1:

        return 0

    # Last 6 hours
    if age_hours <= 6:

        return 10

    # 6–12 hours
    if age_hours <= 12:

        return 9

    # 12–24 hours
    if age_hours <= 24:

        return 8

    # 24–48 hours
    if age_hours <= 48:

        return 6

    # 48–72 hours
    if age_hours <= 72:

        return 5

    # 3–7 days
    if age_hours <= 168:

        return 2

    return 0


# ============================================================
# RELEVANCE
# ============================================================

def relevance_score(story):

    text = story_text(
        story
    )

    high_value = count_matches(
        text,
        HIGH_VALUE_KEYWORDS
    )

    high_impact = count_matches(
        text,
        HIGH_IMPACT_KEYWORDS
    )

    curiosity = count_matches(
        text,
        CURIOSITY_KEYWORDS
    )

    low_value = count_matches(
        text,
        LOW_VALUE_KEYWORDS
    )

    routine = count_matches(
        text,
        ROUTINE_TERMS
    )

    # --------------------------------------------------------
    # Base relevance
    # --------------------------------------------------------

    score = 0

    # Technology relevance
    score += min(
        high_value * 2,
        12
    )

    # Consequence / impact
    score += min(
        high_impact * 3,
        15
    )

    # Curiosity
    score += min(
        curiosity * 2,
        8
    )

    # Routine announcement penalty
    score -= min(
        routine * 1,
        5
    )

    # Low-value penalty
    score -= min(
        low_value * 6,
        18
    )

    return max(
        score,
        0
    )


# ============================================================
# IMPACT SCORE
#
# Separate from generic relevance.
# ============================================================

def impact_score(story):

    text = story_text(
        story
    )

    score = 0

    impact_matches = count_matches(
        text,
        HIGH_IMPACT_KEYWORDS
    )

    curiosity_matches = count_matches(
        text,
        CURIOSITY_KEYWORDS
    )

    score += min(
        impact_matches * 3,
        18
    )

    score += min(
        curiosity_matches * 2,
        8
    )

    # Numbers often make stories easier to communicate visually.
    if re.search(
        r"\b\d+(?:\.\d+)?%|\$\d+|\b\d+x\b|\b\d+\s*(?:million|billion|trillion)\b",
        text,
        re.IGNORECASE
    ):

        score += 4

    # Comparison language is useful for carousel storytelling.
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

        score += 3

    return score


# ============================================================
# STORY TYPE
# ============================================================

def classify_story(story):

    text = story_text(
        story
    )

    # AI model / capability
    if any(
        term in text
        for term in [
            "new model",
            "new ai model",
            "language model",
            "reasoning model",
            "foundation model",
            "gpt",
            "gemini",
            "claude",
        ]
    ):

        return "MODEL_UPDATE"

    # Agents
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

    # Security
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

    # Business
    if any(
        term in text
        for term in [
            "layoff",
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

    # Product / platform
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

    # Research / breakthrough
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

    return "TECH_NEWS"


# ============================================================
# HARD FILTER
#
# This is deliberately conservative.
#
# We do NOT want:
#
# 1187 stories
# ↓
# 234 weak stories
#
# We want a manageable pool for Gemini.
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

    text = story_text(
        story
    )

    low_value_count = count_matches(
        text,
        LOW_VALUE_KEYWORDS
    )

    # --------------------------------------------------------
    # Rule 1:
    # Very weak stories are rejected.
    # --------------------------------------------------------

    if relevance <= 2:

        return False

    # --------------------------------------------------------
    # Rule 2:
    # Strong low-value content is rejected.
    # --------------------------------------------------------

    if low_value_count >= 2:

        return False

    # --------------------------------------------------------
    # Rule 3:
    # Fresh stories are preferred.
    #
    # Anything from the last 72h with reasonable relevance
    # should reach Gemini.
    # --------------------------------------------------------

    if freshness >= 5 and relevance >= 5:

        return True

    # --------------------------------------------------------
    # Rule 4:
    # Extremely impactful stories can survive slightly weaker
    # relevance.
    # --------------------------------------------------------

    if freshness >= 5 and impact >= 10:

        return True

    # --------------------------------------------------------
    # Rule 5:
    # Undated stories are NOT allowed simply because they contain
    # words like GPT/OpenAI/AI.
    #
    # They need a very strong impact signal.
    # --------------------------------------------------------

    if freshness == 0 and impact >= 16:

        return True

    # --------------------------------------------------------
    # Rule 6:
    # 3–7 day stories can survive only when they are unusually
    # important.
    # --------------------------------------------------------

    if freshness == 2 and impact >= 14:

        return True

    return False


# ============================================================
# LOAD DATA
# ============================================================

def load_stories():

    with open(
        "data/raw_stories.json",
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )

    return data


# ============================================================
# SAVE DATA
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

    data = load_stories()

    stories = data.get(
        "stories",
        []
    )

    candidates = []

    # ========================================================
    # SCORE EVERYTHING
    # ========================================================

    for story in stories:

        relevance = relevance_score(
            story
        )

        freshness = freshness_score(
            story
        )

        impact = impact_score(
            story
        )

        story_type = classify_story(
            story
        )

        # ----------------------------------------------------
        # Combined pre-filter score
        #
        # Freshness is deliberately weighted heavily.
        # ----------------------------------------------------

        pre_filter_score = (
            relevance
            + impact
            + freshness * 2
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
        ] = pre_filter_score

        if should_keep(
            story
        ):

            candidates.append(
                story
            )

    # ========================================================
    # SORT
    # ========================================================

    candidates.sort(
        key=lambda story: (
            story.get(
                "pre_filter_score",
                0
            ),
            story.get(
                "freshness_score",
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
    # DEDUPLICATE SIMILAR TITLES
    #
    # Prevent 5 versions of the same announcement from flooding
    # the Gemini pool.
    # ========================================================

    final_candidates = []

    seen_titles = []

    for story in candidates:

        title = story.get(
            "title",
            ""
        ).lower()

        # Normalize title
        normalized = re.sub(
            r"[^a-z0-9 ]",
            " ",
            title
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized
        ).strip()

        duplicate = False

        for previous in seen_titles:

            # Exact normalized title
            if normalized == previous:

                duplicate = True

                break

            # Simple word-overlap similarity
            current_words = set(
                normalized.split()
            )

            previous_words = set(
                previous.split()
            )

            if not current_words:

                continue

            overlap = (
                len(
                    current_words
                    & previous_words
                )
                /
                max(
                    len(
                        current_words
                        | previous_words
                    ),
                    1
                )
            )

            if overlap >= 0.78:

                duplicate = True

                break

        if duplicate:

            continue

        seen_titles.append(
            normalized
        )

        final_candidates.append(
            story
        )

    candidates = final_candidates

    # ========================================================
    # LIMIT
    #
    # Gemini does NOT need 234 stories.
    #
    # Give it a high-quality pool.
    # ========================================================

    candidates = candidates[:80]

    save_candidates(
        candidates
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print("")
    print("=" * 70)
    print("GETBYTERUSH PRE-FILTER")
    print("=" * 70)
    print("")

    print(
        f"Raw stories: "
        f"{len(stories)}"
    )

    print(
        f"Candidates: "
        f"{len(candidates)}"
    )

    print("")

    # --------------------------------------------------------
    # Recent candidate count
    # --------------------------------------------------------

    recent_count = sum(
        1
        for story in candidates
        if story.get(
            "freshness_score",
            0
        ) >= 5
    )

    print(
        f"Fresh candidates (<72h): "
        f"{recent_count}"
    )

    print("")

    # ========================================================
    # PRINT TOP CANDIDATES
    # ========================================================

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


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()