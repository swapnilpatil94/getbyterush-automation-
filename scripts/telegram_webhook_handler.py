#!/usr/bin/env python3
"""Entry point for telegram-webhook-dispatch.yml (triggered by
repository_dispatch, event_type=telegram-update). The Cloudflare Worker
already answered the callback_query (if any) to stop the button's loading
spinner and forwarded the raw Telegram update as client_payload.update —
this script just hands it to the same processing logic
telegram_review_listener.py's polling path already used.
"""
import json
import os

import telegram_review_listener as listener


def main():
    raw = os.environ.get("TELEGRAM_UPDATE_JSON", "")
    if not raw:
        raise SystemExit("TELEGRAM_UPDATE_JSON is empty — nothing to process.")
    update = json.loads(raw)
    print(f"Processing update_id={update.get('update_id')}")
    listener.process_update(update)
    print("Done.")


if __name__ == "__main__":
    main()
