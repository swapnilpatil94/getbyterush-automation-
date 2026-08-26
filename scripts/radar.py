import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


FEEDS = [
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/"
    },
    {
        "name": "OpenAI News",
        "url": "https://openai.com/news/rss.xml"
    },
    {
        "name": "Microsoft AI",
        "url": "https://blogs.microsoft.com/ai/feed/"
    },
    {
        "name": "Meta AI",
        "url": "https://ai.meta.com/blog/rss/"
    },
    {
        "name": "NVIDIA Blog",
        "url": "https://blogs.nvidia.com/feed/"
    },
]


def clean(text):
    """
    Remove HTML and normalize whitespace.
    """

    text = text or ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_date(element):
    """
    Extract publication/update date from RSS or Atom entries.

    Supports:
    - pubDate
    - published
    - updated
    - date
    - namespaced versions
    """

    possible_tags = [
        "pubDate",
        "published",
        "updated",
        "date",
    ]

    # Standard RSS / Atom
    for tag in possible_tags:

        child = element.find(tag)

        if child is not None and child.text:

            return child.text.strip()

    # Namespaced / Dublin Core / other feed formats
    for child in list(element):

        tag = child.tag.lower()

        if any(
            keyword in tag
            for keyword in [
                "pubdate",
                "published",
                "updated",
                "date",
            ]
        ):

            if child.text:

                return child.text.strip()

    return ""


def fetch_feed(feed):

    print(
        f"Fetching: {feed['name']}"
    )

    request = urllib.request.Request(
        feed["url"],
        headers={
            "User-Agent":
                "GetByteRush-News-Radar/1.0"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            data = response.read()

        root = ET.fromstring(data)

        stories = []

        # ============================================================
        # RSS
        # ============================================================

        for item in root.findall(
            ".//item"
        ):

            title = item.findtext(
                "title",
                ""
            )

            link = item.findtext(
                "link",
                ""
            )

            description = item.findtext(
                "description",
                ""
            )

            published = extract_date(
                item
            )

            if title:

                stories.append(
                    {
                        "source":
                            feed["name"],

                        "title":
                            clean(title),

                        "url":
                            link.strip(),

                        "description":
                            clean(description),

                        "published":
                            published
                    }
                )

        # ============================================================
        # ATOM
        # ============================================================

        if not stories:

            namespaces = {
                "atom":
                    "http://www.w3.org/2005/Atom"
            }

            for entry in root.findall(
                "atom:entry",
                namespaces
            ):

                title = entry.findtext(
                    "atom:title",
                    "",
                    namespaces
                )

                summary = entry.findtext(
                    "atom:summary",
                    "",
                    namespaces
                )

                published = extract_date(
                    entry
                )

                link_element = entry.find(
                    "atom:link",
                    namespaces
                )

                link = ""

                if link_element is not None:

                    link = link_element.attrib.get(
                        "href",
                        ""
                    )

                if title:

                    stories.append(
                        {
                            "source":
                                feed["name"],

                            "title":
                                clean(title),

                            "url":
                                link.strip(),

                            "description":
                                clean(summary),

                            "published":
                                published
                        }
                    )

        print(
            f"  ✓ {len(stories)} stories"
        )

        return stories

    except Exception as error:

        print(
            f"  ⚠ Skipping "
            f"{feed['name']}: {error}"
        )

        return []


def deduplicate(stories):

    unique = {}

    for story in stories:

        url = story.get(
            "url",
            ""
        ).strip()

        title = story.get(
            "title",
            ""
        ).strip().lower()

        key = url or title

        if not key:
            continue

        if key not in unique:

            unique[key] = story

    return list(
        unique.values()
    )


def parse_date(value):

    if not value:

        return None

    # RSS dates
    try:

        return parsedate_to_datetime(
            value
        ).astimezone(
            timezone.utc
        )

    except Exception:
        pass

    # ISO dates
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
        pass

    return None


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

    # Ignore future/malformed dates
    if age_hours < -1:

        return 0

    # ============================================================
    # FRESHNESS SCALE
    # ============================================================

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

    return 0


def main():

    print("")
    print("=" * 70)
    print("GETBYTERUSH NEWS RADAR")
    print("=" * 70)
    print("")

    all_stories = []

    # ============================================================
    # FETCH
    # ============================================================

    for feed in FEEDS:

        stories = fetch_feed(
            feed
        )

        all_stories.extend(
            stories
        )

    # ============================================================
    # DEDUPLICATE
    # ============================================================

    stories = deduplicate(
        all_stories
    )

    print("")
    print(
        f"Total unique stories: "
        f"{len(stories)}"
    )

    # ============================================================
    # CREATE DATA DIRECTORY
    # ============================================================

    os.makedirs(
        "data",
        exist_ok=True
    )

    # ============================================================
    # ADD FRESHNESS INFORMATION
    # ============================================================

    for story in stories:

        story[
            "freshness_score"
        ] = freshness_score(
            story
        )

    # ============================================================
    # SAVE RAW STORIES
    # ============================================================

    result = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(stories),

        "stories":
            stories
    }

    output_path = (
        "data/raw_stories.json"
    )

    with open(
        output_path,
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
    print(
        f"Saved: {output_path}"
    )

    # ============================================================
    # SHOW RECENT STORIES
    # ============================================================

    recent = [
        story
        for story in stories
        if story.get(
            "freshness_score",
            0
        ) > 0
    ]

    recent.sort(
        key=lambda story:
            story.get(
                "freshness_score",
                0
            ),
        reverse=True
    )

    print("")
    print("=" * 70)
    print("RECENT STORIES")
    print("=" * 70)
    print("")

    print(
        f"Stories in last 72h: "
        f"{len(recent)}"
    )

    print("")

    for index, story in enumerate(
        recent[:30],
        1
    ):

        print(
            f"{index}. "
            f"{story['title']}"
        )

        print(
            f"   Source: "
            f"{story['source']}"
        )

        print(
            f"   Published: "
            f"{story.get('published', 'N/A')}"
        )

        print(
            f"   Freshness: "
            f"{story.get('freshness_score', 0)}"
        )

        print(
            f"   URL: "
            f"{story['url']}"
        )

        print("")


if __name__ == "__main__":

    main()