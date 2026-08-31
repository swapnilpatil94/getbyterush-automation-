#!/usr/bin/env python3
"""Minimal Telegram Bot API client — stdlib only (matches the existing
telegram_listener.py/send_approval.py style, no new dependency). Shared
by telegram_review.py and telegram_review_listener.py so there is exactly
one HTTP/multipart implementation, not one per script.
"""
import json
import mimetypes
import os
import urllib.parse
import urllib.request
import uuid

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))


def _base_url(method):
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


def call(method, payload=None):
    """application/x-www-form-urlencoded POST — for text/keyboard/callback
    methods that carry no binary file data."""
    data = urllib.parse.urlencode(payload or {}).encode("utf-8")
    req = urllib.request.Request(_base_url(method), data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_multipart(method, fields, files):
    """fields: {name: str}. files: {name: (filename, bytes)}. Needed for
    sendMediaGroup, which uploads local PNGs rather than URLs."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (fields or {}).items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(str(value).encode("utf-8"))
        parts.append(b"\r\n")
    for name, (filename, content) in (files or {}).items():
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
        parts.append(content)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(_base_url(method), data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_message(text, reply_markup=None):
    payload = {"chat_id": CHAT_ID, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    return call("sendMessage", payload)


def send_media_group(image_paths, caption=""):
    """image_paths: list of local file paths, max 10 (Telegram's own
    sendMediaGroup limit — matches Instagram's carousel limit)."""
    image_paths = image_paths[:10]
    media = []
    files = {}
    for i, path in enumerate(image_paths):
        key = f"photo{i}"
        item = {"type": "photo", "media": f"attach://{key}"}
        if i == 0 and caption:
            item["caption"] = caption
        media.append(item)
        with open(path, "rb") as fh:
            files[key] = (os.path.basename(path), fh.read())
    return call_multipart("sendMediaGroup", {"chat_id": CHAT_ID, "media": json.dumps(media)}, files)


def answer_callback(callback_query_id, text=""):
    return call("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})


def edit_message_text(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    return call("editMessageText", payload)


def edit_message_reply_markup(chat_id, message_id, reply_markup):
    return call("editMessageReplyMarkup", {
        "chat_id": chat_id, "message_id": message_id, "reply_markup": json.dumps(reply_markup),
    })
