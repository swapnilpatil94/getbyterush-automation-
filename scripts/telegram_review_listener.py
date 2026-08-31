#!/usr/bin/env python3
"""GetByteRush Telegram review listener — replaces telegram_listener.py.

Polls getUpdates for callback_query (button presses) and plain text
messages (optional rejection notes), drives content_state transitions,
and dispatches the follow-up GitHub Actions workflow for each outcome:
publish-instagram.yml on approval, regenerate-visual.yml on VISUAL/
DIFFERENT_APPROACH rejection, refetch-evidence.yml on EVIDENCE rejection.
TOPIC and CONTENT rejections need no follow-up workflow — the state
transition alone is enough (topic_memory already blocks the topic; content
has no automated remediation and goes straight to HOLD_FOR_HUMAN_REVIEW).

Zero Gemini calls anywhere in this file.
"""
import json
import os
from pathlib import Path

import content_state as cs
import github_dispatch
import telegram_bot as tg

OFFSET_FILE = Path("state/telegram_offset.txt")
PENDING_NOTE_FILE = Path("state/pipeline/pending_note.json")

CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))

REASON_LABELS = {
    "v": ("visual", "🎨 VISUALS"),
    "t": ("topic", "🧠 TOPIC"),
    "c": ("content", "✍️ CONTENT"),
    "e": ("evidence", "🖼️ EVIDENCE"),
    "d": ("different_approach", "🔄 DIFFERENT APPROACH"),
}


def read_offset():
    if not OFFSET_FILE.exists():
        return 0
    value = OFFSET_FILE.read_text().strip()
    return int(value) if value else 0


def write_offset(offset):
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))


def load_pending():
    if not PENDING_NOTE_FILE.exists():
        return None
    try:
        return json.loads(PENDING_NOTE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_pending(pending):
    PENDING_NOTE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if pending is None:
        if PENDING_NOTE_FILE.exists():
            PENDING_NOTE_FILE.unlink()
        return
    PENDING_NOTE_FILE.write_text(json.dumps(pending), encoding="utf-8")


def _dispatch_for(next_action, content_id):
    if next_action == "regenerate_visual":
        github_dispatch.trigger("regenerate-visual.yml", {"content_id": content_id})
    elif next_action == "refetch_evidence":
        github_dispatch.trigger("refetch-evidence.yml", {"content_id": content_id})
    # 'next_topic' and 'hold' need no follow-up workflow.


def _finalize_rejection(chat_id, message_id, content_id, category, note):
    record, next_action = cs.record_rejection(content_id, category, note)
    _dispatch_for(next_action, content_id)

    status = record["status"]
    lines = [f"❌ GETBYTERUSH POST REJECTED", "", f"Post: {content_id}", f"Reason: {category}"]
    if note:
        lines.append(f"Note: {note}")
    lines.append("")
    if status == "HOLD_FOR_HUMAN_REVIEW":
        lines.append("⏸ HOLD FOR HUMAN REVIEW — automated attempts exhausted or no automated fix exists.")
    elif next_action == "regenerate_visual":
        lines.append(f"Regenerating a materially different visual (attempt {record['attempts'].get(category, record['attempts'].get('visual'))}/{cs.MAX_REGENERATION_ATTEMPTS})...")
    elif next_action == "refetch_evidence":
        lines.append("Refetching evidence and re-rendering...")
    elif next_action == "next_topic":
        lines.append("Topic blocked. The next daily run will select a different candidate.")
    tg.edit_message_text(chat_id, message_id, "\n".join(lines))


def handle_callback(callback):
    data = callback.get("data", "")
    chat_id = str(callback["message"]["chat"]["id"])
    message_id = callback["message"]["message_id"]

    if chat_id != CHAT_ID:
        print("Ignoring callback from unknown chat.")
        return
    if ":" not in data:
        print("Ignoring malformed callback.")
        return

    action, _, rest = data.partition(":")

    if action == "approve":
        content_id = rest
        if cs.is_published(content_id):
            tg.answer_callback(callback["id"], "Already published — no action taken.")
            return
        record = cs.load(content_id)
        if record is None or record["status"] in ("REJECTED_TOPIC", "REJECTED_CONTENT", "HOLD_FOR_HUMAN_REVIEW"):
            tg.answer_callback(callback["id"], "This post is not in an approvable state.")
            return
        cs.transition(content_id, "APPROVED", note="approved via Telegram")
        github_dispatch.trigger("publish-instagram.yml", {"content_id": content_id})
        tg.answer_callback(callback["id"], "✅ Approved. Publishing workflow started...")
        tg.edit_message_text(chat_id, message_id, f"✅ GETBYTERUSH POST APPROVED\n\nPost: {content_id}\n\nPublishing workflow started — will only post after it confirms success.")
        return

    if action == "reject":
        content_id = rest
        tg.answer_callback(callback["id"], "What needs fixing?")
        keyboard = {"inline_keyboard": [
            [{"text": label, "callback_data": f"rr:{code}:{content_id}"}] for code, (_, label) in REASON_LABELS.items()
        ]}
        tg.edit_message_text(chat_id, message_id, f"WHAT NEEDS FIXING?\n\nPost: {content_id}", reply_markup=keyboard)
        return

    if action == "rr":
        code, _, content_id = rest.partition(":")
        category = REASON_LABELS.get(code, (None, None))[0]
        if category is None:
            tg.answer_callback(callback["id"], "Unrecognized reason.")
            return
        tg.answer_callback(callback["id"], "Add an optional note, or skip.")
        save_pending({"content_id": content_id, "category": category, "chat_id": chat_id, "message_id": message_id})
        keyboard = {"inline_keyboard": [[{"text": "⏭ Skip note", "callback_data": f"skip_note:{content_id}"}]]}
        tg.edit_message_text(chat_id, message_id, f"Add a note (optional) — just reply with a message.\nOr tap Skip.\n\nPost: {content_id}\nReason: {category}", reply_markup=keyboard)
        return

    if action == "skip_note":
        content_id = rest
        pending = load_pending()
        if not pending or pending.get("content_id") != content_id:
            tg.answer_callback(callback["id"], "Nothing pending.")
            return
        tg.answer_callback(callback["id"], "Rejected.")
        _finalize_rejection(chat_id, message_id, content_id, pending["category"], "")
        save_pending(None)
        return

    print(f"Ignoring unsupported action: {action}")


def handle_text_message(message):
    chat_id = str(message["chat"]["id"])
    if chat_id != CHAT_ID:
        return
    text = message.get("text", "").strip()
    if not text:
        return
    pending = load_pending()
    if not pending or pending.get("chat_id") != chat_id:
        return  # not a note reply we're waiting on
    _finalize_rejection(chat_id, pending["message_id"], pending["content_id"], pending["category"], text)
    save_pending(None)


def main():
    offset = read_offset()
    print(f"Checking Telegram updates from offset {offset}")
    response = tg.call("getUpdates", {
        "offset": offset, "timeout": 0,
        "allowed_updates": json.dumps(["callback_query", "message"]),
    })
    updates = response.get("result", [])
    if not updates:
        print("No new Telegram updates.")
        return

    highest = offset
    for update in updates:
        highest = max(highest, update["update_id"] + 1)
        if update.get("callback_query"):
            handle_callback(update["callback_query"])
        elif update.get("message"):
            handle_text_message(update["message"])

    write_offset(highest)
    print(f"Saved Telegram offset: {highest}")


if __name__ == "__main__":
    main()
