import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# Topics that are highly relevant to GetByteRush.
HIGH_VALUE_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "agent",
    "agents",
    "model",
    "gemini",
    "gpt",
    "claude",
    "openai",
    "anthropic",
    "meta ai",
    "microsoft",
    "nvidia",
    "apple",
    "google",
    "robot",
    "robotics",
    "chip",
    "gpu",
    "cybersecurity",
    "security",
    "hack",
    "breach",
    "privacy",
    "browser",
    "search",
    "internet",
    "developer",
    "github",
    "software",
    "startup",
    "acquisition",
    "layoff",
    "funding",
    "revenue",
    "enterprise",
    "automation",
    "mcp",
    "open source",
]


# Topics that are generally weak for the daily radar.
LOW_VALUE_KEYWORDS = [
    "home decor",
    "dinner party",
    "back to school",
    "football club",
    "holiday",
    "gift guide",
    "recipes",
    "fashion",
    "shopping tips",
    "travel tips",
]


def parse_date(value):
    if not value:
        return None

    try:
        return parsedate_to_datetime(value).astimezone(
            timezone.utc
        )
    except Exception:
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return None


def relevance_score(story):
    text = " ".join([
        story.get("title", ""),
        story.get("description", "")
    ]).lower()

    score = 0

    for keyword in HIGH_VALUE_KEYWORDS:
        if keyword in text:
            score += 2

    for keyword in LOW_VALUE_KEYWORDS:
        if keyword in text:
            score -= 5

    return score


def freshness_score(story):
    published = parse_date(
        story.get("published", "")
    )

    if not published:
        return 0

    now = datetime.now(timezone.utc)

    age_hours = (
        now - published
    ).total_seconds() / 3600

    if age_hours <= 6:
        return 10

    if age_hours <= 24:
        return 8

    if age_hours <= 72:
        return 5

    if age_hours <= 168:
        return 2

    return 0


def should_keep(story):
    relevance = relevance_score(story)
    freshness = freshness_score(story)

    # Strong relevance + recent
    if relevance >= 4 and freshness >= 5:
        return True

    # Extremely relevant even if date parsing failed
    if relevance >= 8:
        return True

    return False


def main():

    with open(
        "data/raw_stories.json",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    candidates = []

    for story in data["stories"]:

        relevance = relevance_score(story)
        freshness = freshness_score(story)

        story["pre_filter_score"] = (
            relevance + freshness
        )

        story["relevance_score"] = relevance
        story["freshness_score"] = freshness

        if should_keep(story):
            candidates.append(story)

    candidates.sort(
        key=lambda x: x["pre_filter_score"],
        reverse=True
    )

    result = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "count": len(candidates),

        "stories": candidates
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

    print("")
    print("=" * 70)
    print("GETBYTERUSH PRE-FILTER")
    print("=" * 70)

    print(
        f"Raw stories: {len(data['stories'])}"
    )

    print(
        f"Candidates: {len(candidates)}"
    )

    print("")

    for i, story in enumerate(
        candidates[:30],
        1
    ):

        print(
            f"{i}. {story['title']}"
        )

        print(
            f"   relevance="
            f"{story['relevance_score']} "
            f"freshness="
            f"{story['freshness_score']}"
        )

        print(
            f"   {story['source']}"
        )

        print("")


if __name__ == "__main__":
    main()