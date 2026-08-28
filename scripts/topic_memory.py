#!/usr/bin/env python3
"""GetByteRush topic memory and generated-output cleanup.

The memory layer runs BEFORE Gemini so recently published stories are removed
from the candidate pool without spending another Gemini call on them.
It compares both the selected editorial title and the original source title,
plus the canonical source URL and token overlap, so one event cannot easily
return under a rewritten headline.
"""

import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CANDIDATES_PATH = Path("data/candidates.json")
SELECTED_PATH = Path("data/selected_story.json")
MEMORY_PATH = Path("state/topic_memory.json")
OUTPUT_ROOT = Path("output/posts")
TOPIC_COOLDOWN_DAYS = 7
MEMORY_RETENTION_DAYS = 30
OUTPUT_RETENTION_DAYS = 7


def now():
    return datetime.now(timezone.utc)


def parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except Exception:
        return None


def normalize(value):
    value = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", value).strip()


def tokens(value):
    return {x for x in normalize(value).split() if len(x) > 2}


def load_memory():
    if not MEMORY_PATH.exists():
        return {"version": 2, "topics": []}
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("topics"), list):
            data["version"] = 2
            return data
    except Exception:
        pass
    return {"version": 2, "topics": []}


def save_memory(memory):
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(memory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def identity(story):
    source = story.get("source_story") if isinstance(story.get("source_story"), dict) else {}
    title = str(story.get("title") or story.get("story_title") or "").strip()
    source_title = str(source.get("title") or story.get("source_title") or "").strip()
    url = str(story.get("url") or source.get("url") or "").strip()
    return {"title": title, "source_title": source_title, "url": url}


def title_match(a, b):
    candidates_a = [normalize(a.get("title")), normalize(a.get("source_title"))]
    candidates_b = [normalize(b.get("title")), normalize(b.get("source_title"))]

    for left in candidates_a:
        if not left:
            continue
        for right in candidates_b:
            if not right:
                continue
            if left == right:
                return True
            aa, bb = tokens(left), tokens(right)
            if len(aa) >= 4 and len(bb) >= 4:
                overlap = len(aa & bb) / min(len(aa), len(bb))
                if overlap >= 0.80:
                    return True
    return False


def same_topic(story, entry):
    current = identity(story)
    remembered = identity(entry)

    if current["url"] and current["url"] == remembered["url"]:
        return True

    return title_match(current, remembered)


def prune(memory):
    cutoff = now() - timedelta(days=MEMORY_RETENTION_DAYS)
    kept = []
    for entry in memory.get("topics", []):
        recorded = parse_dt(entry.get("recorded_at"))
        if recorded and recorded >= cutoff:
            kept.append(entry)
    kept.sort(key=lambda e: e.get("recorded_at", ""), reverse=True)
    memory["topics"] = kept
    memory["version"] = 2
    return memory


def prepare():
    if not CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"Missing {CANDIDATES_PATH}")

    data = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    stories = data.get("stories", []) if isinstance(data, dict) else []
    memory = prune(load_memory())
    cutoff = now() - timedelta(days=TOPIC_COOLDOWN_DAYS)
    recent = [
        entry
        for entry in memory["topics"]
        if parse_dt(entry.get("recorded_at")) and parse_dt(entry.get("recorded_at")) >= cutoff
    ]

    kept = []
    blocked = []
    for story in stories:
        match = next((entry for entry in recent if same_topic(story, entry)), None)
        if match:
            blocked.append(story)
        else:
            kept.append(story)

    data["stories"] = kept
    data["topic_memory"] = {
        "cooldown_days": TOPIC_COOLDOWN_DAYS,
        "blocked_count": len(blocked),
        "remaining_count": len(kept),
    }
    CANDIDATES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    save_memory(memory)

    print("GETBYTERUSH TOPIC MEMORY")
    print(f"Candidates before: {len(stories)}")
    print(f"Blocked recent:   {len(blocked)}")
    print(f"Candidates after:  {len(kept)}")
    print(f"Cooldown:          {TOPIC_COOLDOWN_DAYS} days")

    if not kept:
        raise RuntimeError("Topic memory removed every candidate; nothing safe to publish.")


def record():
    if not SELECTED_PATH.exists():
        return

    selected = json.loads(SELECTED_PATH.read_text(encoding="utf-8"))
    if not selected.get("selected"):
        return

    source = selected.get("source_story") or {}
    title = str(selected.get("story_title") or "").strip()
    source_title = str(source.get("title") or "").strip()
    url = str(source.get("url") or selected.get("url") or "").strip()
    source_name = str(source.get("source") or selected.get("source") or "").strip()

    memory = prune(load_memory())
    new_identity = {
        "title": title,
        "source_title": source_title,
        "url": url,
    }
    memory["topics"] = [entry for entry in memory["topics"] if not same_topic(new_identity, entry)]
    memory["topics"].insert(0, {
        "title": title,
        "source_title": source_title,
        "url": url,
        "source": source_name,
        "normalized_title": normalize(title),
        "normalized_source_title": normalize(source_title),
        "tokens": sorted(tokens(title)),
        "source_tokens": sorted(tokens(source_title)),
        "recorded_at": now().isoformat(),
    })
    save_memory(prune(memory))
    print(f"Recorded topic: {title}")
    if source_title:
        print(f"Source title:    {source_title}")


def cleanup():
    if not OUTPUT_ROOT.exists():
        return

    cutoff = now() - timedelta(days=OUTPUT_RETENTION_DAYS)
    removed = 0
    for path in OUTPUT_ROOT.iterdir():
        if not path.is_dir():
            continue
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if modified < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except OSError:
            pass
    print(f"Old output packages removed: {removed}")


def main():
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "prepare"
    if command == "prepare":
        prepare()
    elif command == "record":
        record()
    elif command == "cleanup":
        cleanup()
    else:
        raise SystemExit("Usage: topic_memory.py [prepare|record|cleanup]")


if __name__ == "__main__":
    main()
