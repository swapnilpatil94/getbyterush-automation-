import json
import os
import subprocess
import urllib.parse
import urllib.request


BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])

OFFSET_FILE = "state/telegram_offset.txt"

GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]


def telegram_request(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    if payload:
        data = urllib.parse.urlencode(payload).encode("utf-8")
    else:
        data = None

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
    )

    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def read_offset():
    if not os.path.exists(OFFSET_FILE):
        return 0

    with open(OFFSET_FILE, "r") as file:
        value = file.read().strip()

    return int(value) if value else 0


def write_offset(offset):
    os.makedirs("state", exist_ok=True)

    with open(OFFSET_FILE, "w") as file:
        file.write(str(offset))


def trigger_workflow(post_id, decision):
    workflow_file = "approval-result-test.yml"

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/actions/workflows/"
        f"{workflow_file}/dispatches"
    )

    payload = {
        "ref": "main",
        "inputs": {
            "post_id": post_id,
            "decision": decision,
        },
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
    )

    request.add_header(
        "Authorization",
        f"Bearer {GITHUB_TOKEN}",
    )

    request.add_header(
        "Accept",
        "application/vnd.github+json",
    )

    request.add_header(
        "X-GitHub-Api-Version",
        "2022-11-28",
    )

    request.add_header(
        "Content-Type",
        "application/json",
    )

    with urllib.request.urlopen(request) as response:
        print(
            f"GitHub workflow triggered: "
            f"{post_id} / {decision}"
        )


def answer_callback(callback_query_id, text):
    telegram_request(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_query_id,
            "text": text,
        },
    )


def edit_message(chat_id, message_id, text):
    telegram_request(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        },
    )


def main():
    offset = read_offset()

    print(f"Checking Telegram updates from offset {offset}")

    response = telegram_request(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": json.dumps(
                ["callback_query"]
            ),
        },
    )

    updates = response.get("result", [])

    if not updates:
        print("No new Telegram updates.")
        return

    highest_update_id = offset

    for update in updates:

        update_id = update["update_id"]

        highest_update_id = max(
            highest_update_id,
            update_id + 1,
        )

        callback = update.get("callback_query")

        if not callback:
            continue

        callback_data = callback.get("data", "")

        callback_chat_id = str(
            callback["message"]["chat"]["id"]
        )

        callback_user_id = str(
            callback["from"]["id"]
        )

        print(
            f"Callback received: "
            f"{callback_data}"
        )

        # SECURITY CHECK
        # Only accept callbacks from your configured chat.
        if callback_chat_id != CHAT_ID:
            print("Ignoring callback from unknown chat.")
            continue

        if ":" not in callback_data:
            print("Ignoring malformed callback.")
            continue

        decision, post_id = callback_data.split(
            ":",
            1,
        )

        if decision not in {
            "approve",
            "reject",
        }:
            print(
                f"Ignoring unsupported decision: "
                f"{decision}"
            )
            continue

        print(
            f"Decision: {decision} "
            f"for post: {post_id}"
        )

        if decision == "approve":

            answer_callback(
                callback["id"],
                "✅ Approved. Starting GitHub workflow...",
            )

            trigger_workflow(
                post_id,
                "approved",
            )

            edit_message(
                callback_chat_id,
                callback["message"]["message_id"],
                (
                    "✅ GETBYTERUSH POST APPROVED\n\n"
                    f"Post: {post_id}\n\n"
                    "GitHub publishing workflow started."
                ),
            )

        elif decision == "reject":

            answer_callback(
                callback["id"],
                "❌ Post rejected.",
            )

            edit_message(
                callback_chat_id,
                callback["message"]["message_id"],
                (
                    "❌ GETBYTERUSH POST REJECTED\n\n"
                    f"Post: {post_id}\n\n"
                    "Nothing was published."
                ),
            )

    write_offset(highest_update_id)

    print(
        f"Saved Telegram offset: "
        f"{highest_update_id}"
    )


if __name__ == "__main__":
    main()