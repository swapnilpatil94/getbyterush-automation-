import json
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


def fetch_feed(feed):
    request = urllib.request.Request(
        feed["url"],
        headers={
            "User-Agent": "GetByteRush-News-Radar/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read()

        root = ET.fromstring(data)

        stories = []

        # RSS
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")

            if title:
                stories.append({
                    "source": feed["name"],
                    "title": clean(title),
                    "url": link,
                    "description": clean(description),
                    "published": pub_date
                })

        # Atom
        if not stories:
            namespaces = {
                "atom": "http://www.w3.org/2005/Atom"
            }

            for entry in root.findall("atom:entry", namespaces):
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
                    link = link_element.attrib.get("href", "")

                if title:
                    stories.append({
                        "source": feed["name"],
                        "title": clean(title),
                        "url": link,
                        "description": clean(summary),
                        "published": published
                    })

        return stories

    except Exception as error:
        print(f"WARNING: {feed['name']} failed: {error}")
        return []


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


def main():
    all_stories = []

    for feed in FEEDS:
        print(f"Fetching: {feed['name']}")

        stories = fetch_feed(feed)

        all_stories.extend(stories)

    # Remove duplicate URLs
    unique = {}

    for story in all_stories:
        key = story["url"] or story["title"].lower()

        if key not in unique:
            unique[key] = story

    stories = list(unique.values())

    result = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "count": len(stories),
        "stories": stories
    }

    with open(
        "data/raw_stories.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"\nCollected {len(stories)} stories."
    )


if __name__ == "__main__":
    main()