#!/usr/bin/env python3
"""Minimal Telegram Bot API client — stdlib only (matches the existing
telegram_listener.py/send_approval.py style, no new dependency). Shared
by telegram_review.py and telegram_review_listener.py so there is exactly
one HTTP/multipart implementation, not one per script.
"""
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))


def _base_url(method):
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


def call(method, payload=None):
    """application/x-www-form-urlencoded POST — for text/keyboard/callback
    methods that carry no binary file data.

    Telegram returns HTTP 4xx (not just ok:false in a 200) for entirely
    expected, recoverable rejections — e.g. answering a callback_query
    that the Cloudflare Worker already answered to stop the button's
    spinner, or editing a message with text it already has. urlopen()
    raises HTTPError on those, which used to crash this script after the
    real work (state transition, follow-up workflow dispatch) had already
    happened — confirmed live: an APPROVE tap successfully transitioned
    content_state and dispatched publish-instagram.yml, then crashed on
    the second answerCallbackQuery before the "commit state" step ran, so
    the approval was silently lost. Telegram's error responses are still
    JSON with the same {"ok": false, "description": ...} shape success
    responses have, so degrading to that instead of raising keeps every
    caller's existing `response.get("ok")` handling correct without
    needing a try/except at every call site."""
    data = urllib.parse.urlencode(payload or {}).encode("utf-8")
    req = urllib.request.Request(_base_url(method), data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            body = json.loads(err.read().decode("utf-8"))
        except Exception:
            body = {}
        print(f"Telegram {method} returned HTTP {err.code}: {body.get('description', err.reason)}")
        return {"ok": False, "error_code": err.code, "description": body.get("description", str(err.reason))}


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
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            body_resp = json.loads(err.read().decode("utf-8"))
        except Exception:
            body_resp = {}
        print(f"Telegram {method} returned HTTP {err.code}: {body_resp.get('description', err.reason)}")
        return {"ok": False, "error_code": err.code, "description": body_resp.get("description", str(err.reason))}


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
