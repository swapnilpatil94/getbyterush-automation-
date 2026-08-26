import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


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


def fetch_feed(feed):
    print(f"Fetching: {feed['name']}")

    request = urllib.request.Request(
        feed["url"],
        headers={
            "User-Agent": "GetByteRush-News-Radar/1.0"
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

        # --------------------------------
        # RSS
        # --------------------------------

        for item in root.findall(".//item"):

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

            pub_date = item.findtext(
                "pubDate",
                ""
            )

            if title:

                stories.append({
                    "source": feed["name"],
                    "title": clean(title),
                    "url": link,
                    "description": clean(description),
                    "published": pub_date
                })

        # --------------------------------
        # Atom
        # --------------------------------

        if not stories:

            namespaces = {
                "atom": "http://www.w3.org/2005/Atom"
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

                published = entry.findtext(
                    "atom:published",
                    "",
                    namespaces
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

                    stories.append({
                        "source": feed["name"],
                        "title": clean(title),
                        "url": link,
                        "description": clean(summary),
                        "published": published
                    })

        print(
            f"  ✓ {len(stories)} stories"
        )

        return stories

    except Exception as error:

        print(
            f"  ⚠ Skipping {feed['name']}: "
            f"{error}"
        )

        return []


def deduplicate(stories):

    unique = {}

    for story in stories:

        url = story.get("url", "").strip()

        title = story.get(
            "title",
            ""
        ).strip().lower()

        key = url or title

        if not key:
            continue

        if key not in unique:

            unique[key] = story

    return list(unique.values())


def main():

    print("")
    print("=" * 70)
    print("GETBYTERUSH NEWS RADAR")
    print("=" * 70)
    print("")

    all_stories = []

    # --------------------------------
    # Fetch sources
    # --------------------------------

    for feed in FEEDS:

        stories = fetch_feed(feed)

        all_stories.extend(
            stories
        )

    # --------------------------------
    # Deduplicate
    # --------------------------------

    stories = deduplicate(
        all_stories
    )

    print("")
    print(
        f"Total unique stories: "
        f"{len(stories)}"
    )

    # --------------------------------
    # Create output directory
    # --------------------------------

    os.makedirs(
        "data",
        exist_ok=True
    )

    # --------------------------------
    # Save results
    # --------------------------------

    result = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "count": len(stories),

        "stories": stories
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

    # --------------------------------
    # Preview
    # --------------------------------

    print("")
    print("=" * 70)
    print("TOP RAW STORIES")
    print("=" * 70)
    print("")

    for index, story in enumerate(
        stories[:20],
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
            f"   URL: "
            f"{story['url']}"
        )

        print("")


if __name__ == "__main__":

    main()