#!/usr/bin/env python3
"""GetByteRush content state machine.

One explicit, persistent record per content_id — never inferred from
filenames or directory layout. Every transition is idempotent: calling
transition() with a state the record is already in is a no-op that
returns the existing record unchanged, so a retried GitHub Actions step
can never double-apply a state change or double-publish.

Storage: one JSON file per content_id under state/pipeline/<content_id>.json,
plus state/pipeline/index.json (content_id -> current status) for fast
listing without reading every file. Both are meant to be committed by the
calling workflow, same as state/topic_memory.json already is.
"""
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATES = [
    "DISCOVERED", "SHORTLISTED", "EDITORIAL_READY", "RENDERING", "QA_PASSED",
    "AWAITING_TELEGRAM_APPROVAL", "REJECTED_VISUAL", "REJECTED_TOPIC",
    "REJECTED_CONTENT", "REJECTED_EVIDENCE", "REJECTED_DIFFERENT_APPROACH",
    "APPROVED", "PUBLISHING", "PUBLISHED", "FAILED", "HOLD_FOR_HUMAN_REVIEW",
]

# States a rejection can legally move OUT of — guards against transitioning
# a record that's already terminal (PUBLISHED, FAILED) or mid-flight in a
# way a stale/duplicate Telegram callback shouldn't be able to touch.
_TERMINAL = {"PUBLISHED", "FAILED", "HOLD_FOR_HUMAN_REVIEW"}
_REJECTION_STATES = {
    "visual": "REJECTED_VISUAL", "topic": "REJECTED_TOPIC",
    "content": "REJECTED_CONTENT", "evidence": "REJECTED_EVIDENCE",
    "different_approach": "REJECTED_DIFFERENT_APPROACH",
}
MAX_REGENERATION_ATTEMPTS = 3

ROOT = Path("state/pipeline")
INDEX_PATH = ROOT / "index.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_content_id(story_title):
    # Kept short deliberately: Telegram inline-keyboard callback_data is
    # capped at 64 bytes, and callbacks are "<action>:<content_id>" — a
    # long slug here left no room for the action prefix once rejection
    # reason codes were added (confirmed by computing worst case:
    # "rr:v:" + a 48-char-slug id blew past 64 bytes).
    slug = re.sub(r"[^a-z0-9]+", "-", str(story_title or "post").lower()).strip("-")[:20]
    stamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    return f"{stamp}-{slug}-{uuid.uuid4().hex[:6]}"


def _path(content_id):
    return ROOT / f"{content_id}.json"


def _load_index():
    if not INDEX_PATH.exists():
        return {}
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_index(index):
    ROOT.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def load(content_id):
    p = _path(content_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save(record):
    ROOT.mkdir(parents=True, exist_ok=True)
    content_id = record["content_id"]
    _path(content_id).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    index = _load_index()
    index[content_id] = {"status": record["status"], "updated_at": record["updated_at"], "story_title": record.get("story_title", "")}
    _save_index(index)
    return record


def create(story_title, source_url=""):
    content_id = new_content_id(story_title)
    record = {
        "content_id": content_id,
        "story_title": story_title,
        "source_url": source_url,
        "status": "DISCOVERED",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "history": [{"status": "DISCOVERED", "at": now_iso(), "note": ""}],
        "attempts": {"visual": 0, "different_approach": 0},
        "avoid_grammars": [],
        "rejections": [],
        "package_path": "",
        "publish": {},
    }
    return save(record)


def transition(content_id, new_status, note=""):
    """Idempotent: if the record is already in new_status, returns it
    unchanged rather than appending a duplicate history entry — this is
    what makes a retried workflow step safe to re-run."""
    if new_status not in STATES:
        raise ValueError(f"Unknown state: {new_status}")
    record = load(content_id)
    if record is None:
        raise KeyError(f"No content record for {content_id}")
    if record["status"] == new_status:
        return record
    record["status"] = new_status
    record["updated_at"] = now_iso()
    record["history"].append({"status": new_status, "at": now_iso(), "note": note})
    return save(record)


def record_rejection(content_id, category, note=""):
    """category: one of visual|topic|content|evidence|different_approach.
    Returns (record, next_action) where next_action is one of
    'regenerate_visual' | 'hold' | 'next_topic' | 'refetch_evidence' —
    the caller (telegram_review_listener.py) dispatches on this rather
    than re-deriving the rejection-category rules itself."""
    if category not in _REJECTION_STATES:
        raise ValueError(f"Unknown rejection category: {category}")
    record = load(content_id)
    if record is None:
        raise KeyError(f"No content record for {content_id}")
    if record["status"] in _TERMINAL:
        return record, "hold"  # already terminal — a late/duplicate reject is a no-op

    record["rejections"].append({"category": category, "note": note, "at": now_iso()})
    new_status = _REJECTION_STATES[category]
    record["status"] = new_status
    record["updated_at"] = now_iso()
    record["history"].append({"status": new_status, "at": now_iso(), "note": note})

    if category in ("visual", "different_approach"):
        record["attempts"][category] = record["attempts"].get(category, 0) + 1
        if record["attempts"][category] > MAX_REGENERATION_ATTEMPTS:
            record["status"] = "HOLD_FOR_HUMAN_REVIEW"
            record["history"].append({"status": "HOLD_FOR_HUMAN_REVIEW", "at": now_iso(), "note": f"max {MAX_REGENERATION_ATTEMPTS} {category} attempts reached"})
            save(record)
            return record, "hold"
        save(record)
        return record, "regenerate_visual"

    if category == "topic":
        save(record)
        return record, "next_topic"

    if category == "evidence":
        save(record)
        return record, "refetch_evidence"

    # content: no deterministic, zero-Gemini-call way to "fix" copy —
    # honest boundary, not a fake auto-repair loop. See PHASE3-CONTENT
    # note in the final report.
    record["status"] = "HOLD_FOR_HUMAN_REVIEW"
    record["history"].append({"status": "HOLD_FOR_HUMAN_REVIEW", "at": now_iso(), "note": "content rejection has no automated remediation"})
    save(record)
    return record, "hold"


def is_published(content_id):
    record = load(content_id)
    return bool(record and record["status"] == "PUBLISHED")


def mark_published(content_id, ig_media_id=""):
    """The idempotency gate Phase 6 requires: if already PUBLISHED, callers
    must check is_published() BEFORE attempting to publish at all — this
    function only records the result of a publish that already happened."""
    record = transition(content_id, "PUBLISHED", note=f"ig_media_id={ig_media_id}")
    record["publish"] = {"ig_media_id": ig_media_id, "published_at": now_iso()}
    return save(record)


def list_by_status(status):
    index = _load_index()
    return [cid for cid, meta in index.items() if meta.get("status") == status]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: content_state.py <content_id>")
        raise SystemExit(1)
    rec = load(sys.argv[1])
    print(json.dumps(rec, indent=2, ensure_ascii=False) if rec else "not found")
