#!/usr/bin/env python3
"""Read-only Telegram diagnostic — calls getUpdates with the CURRENT
stored offset and prints whatever is pending, but does not advance the
offset and does not call telegram_review_listener's handlers. Safe to run
against a real pending approval: no state transition, no workflow
dispatch, no answerCallbackQuery, no editMessageText. Exists solely to
answer "did Telegram actually receive the button tap" without risking
acting on it while diagnosing.
"""
import json

import telegram_bot as tg
import telegram_review_listener as listener


def main():
    offset = listener.read_offset()
    print(f"Stored offset: {offset}")
    response = tg.call("getUpdates", {
        "offset": offset, "timeout": 0,
        "allowed_updates": json.dumps(["callback_query", "message"]),
    })
    print(f"getUpdates ok={response.get('ok')}")
    updates = response.get("result", [])
    print(f"Pending updates: {len(updates)}")
    for u in updates:
        print("---")
        print(json.dumps(u, indent=2, ensure_ascii=False))
    if not updates:
        print("Nothing pending at this offset — Telegram has nothing queued for this bot right now.")


if __name__ == "__main__":
    main()
