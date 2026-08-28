#!/usr/bin/env python3
"""GetByteRush topic memory and generated-output cleanup."""

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
        return {"version": 1, "topics": []}
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and isinstance(data.get("topics"), list) else {"version": 1, "topics": []}
    except Exception:
        return {"version": 1, "topics": []}


def save_memory(memory):
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(memory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def identity(story):
    return {
        "title": str(story.get("title") or story.get("story_title") or "").strip(),
        "url": str(story.get("url") or "").strip(),
        "source": str(story.get("source") or "").strip(),
    }


def same_topic(story, entry):
    a = identity(story)
    if a["url"] and a["url"] == str(entry.get("url") or "").strip():
        return True
    at = normalize(a["title"])
    bt = normalize(entry.get("title"))
    if at and bt and at == bt:
        return True
    aa, bb = tokens(at), set(entry.get("tokens") or tokens(bt))
    if len(aa) >= 4 and len(bb) >= 4 and len(aa & bb) / min(len(aa), len(bb)) >= 0.80:
        return True
    return False


def prune(memory):
    cutoff = now() - timedelta(days=MEMORY_RETENTION_DAYS)
    memory["topics"] = [e for e in memory.get("topics", []) if parse_dt(e.get("recorded_at")) and parse_dt(e.get("recorded_at")) >= cutoff]
    memory["topics"].sort(key=lambda e: e.get("recorded_at", ""), reverse=True)
    memory["version"] = 1
    return memory


def prepare():
    if not CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"Missing {CANDIDATES_PATH}")
    data = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    stories = data.get("stories", []) if isinstance(data, dict) else []
    memory = prune(load_memory())
    cutoff = now() - timedelta(days=TOPIC_COOLDOWN_DAYS)
    recent = [e for e in memory["topics"] if parse_dt(e.get("recorded_at")) and parse_dt(e.get("recorded_at")) >= cutoff]
    kept = []
    blocked = []
    for story in stories:
        match = next((e for e in recent if same_topic(story, e)), None)
        if match:
            blocked.append(story)
        else:
            kept.append(story)
    data["stories"] = kept
    data["topic_memory"] = {"cooldown_days": TOPIC_COOLDOWN_DAYS, "blocked_count": len(blocked), "remaining_count": len(kept)}
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
    title = str(selected.get("story_title") or source.get("title") or "").strip()
    url = str(source.get("url") or selected.get("url") or "").strip()
    source_name = str(source.get("source") or selected.get("source") or "").strip()
    memory = prune(load_memory())
    memory["topics"] = [e for e in memory["topics"] if not same_topic({"title": title, "url": url}, e)]
    memory["topics"].insert(0, {
        "title": title,
        "url": url,
        "source": source_name,
        "normalized_title": normalize(title),
        "tokens": sorted(tokens(title)),
        "recorded_at": now().isoformat(),
    })
    save_memory(prune(memory))
    print(f"Recorded topic: {title}")


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
