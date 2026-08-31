#!/usr/bin/env python3
"""Instagram publishing via a Make.com scenario webhook — a workaround for
the Meta Developer app setup currently blocking instagram_publish.py's
direct Graph API path. Both paths coexist; nothing here replaces or
disables instagram_publish.py.

Payload shape matches the user's own working Make.com scenario:
  {"caption": "...", "images": ["<public url>", ...]}
Image URLs use the already-committed raw.githubusercontent.com path
(repo is public, output/posts/ is already committed), same approach as
the Graph API path — no new image hosting needed.

Honesty constraint: a Make.com webhook is fire-and-forget. A 200/Accepted
response means Make.com's scenario STARTED, not that Instagram actually
received the post — Make.com runs the scenario asynchronously and can
still fail on its end (bad URL, Instagram API error, rate limit) without
this script ever knowing. So this does NOT call content_state.mark_published()
on a 200 — it transitions to PUBLISHING with a note that it's unconfirmed,
and leaves final confirmation to a human checking Instagram directly (or
a future webhook-callback mechanism, not built here). Never claims a
publish happened that wasn't actually verified.

Same hard gates as instagram_publish.py: only runs if content_state says
APPROVED, refuses if already PUBLISHED.
"""
import json
import os
import sys
import urllib.error
import urllib.request

import content_state as cs


def publish(content_id):
    if cs.is_published(content_id):
        print(f"ALREADY_PUBLISHED={content_id} — doing nothing.")
        return {"already_published": True}

    record = cs.load(content_id)
    if record is None:
        raise SystemExit(f"No content record for {content_id}")
    if record["status"] != "APPROVED":
        raise SystemExit(f"Refusing to publish: status is {record['status']!r}, not APPROVED.")

    webhook_url = os.environ.get("MAKE_COM_WEBHOOK_URL")
    if not webhook_url:
        cs.transition(content_id, "FAILED", note="missing credential: MAKE_COM_WEBHOOK_URL")
        raise SystemExit("MISSING_CREDENTIALS=MAKE_COM_WEBHOOK_URL — cannot publish.")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY not set — cannot build public image URLs.")

    from pathlib import Path
    package = json.loads((Path(record["package_path"]) / "publishing_package.json").read_text(encoding="utf-8"))

    def public_url(local_path):
        rel = os.path.relpath(local_path, start=os.getcwd()).replace(os.sep, "/")
        return f"https://raw.githubusercontent.com/{repo}/main/{rel}"

    # Make.com's native "Instagram for Business — Create a carousel post"
    # module requires each Files item as an object with exactly these
    # three keys (confirmed via Make.com's own community docs after a
    # live "Array of objects expected in parameter 'files'" validation
    # error) — a plain array of URL strings, which is what this sent
    # before, isn't a shape that module accepts at all.
    payload = {
        "caption": package.get("caption", ""),
        "images": [
            {"media_type": "IMAGE", "image_url": public_url(p), "video_url": ""}
            for p in package["images"][:10]
        ],
    }

    cs.transition(content_id, "PUBLISHING", note="Make.com webhook")

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"Make.com webhook responded {resp.status}: {body}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        cs.transition(content_id, "FAILED", note=f"Make.com webhook HTTP {e.code}: {body[:300]}")
        print(f"PUBLISH_FAILED={content_id}: HTTP {e.code}: {body}")
        raise SystemExit(1)
    except Exception as exc:
        cs.transition(content_id, "FAILED", note=str(exc)[:500])
        print(f"PUBLISH_FAILED={content_id}: {exc}")
        raise

    record = cs.load(content_id)
    record["publish"] = {"make_com_accepted": True, "note": "accepted by Make.com — NOT confirmed published, verify on Instagram"}
    cs.save(record)
    print(f"ACCEPTED_BY_MAKE_COM={content_id}")
    print("Status left as PUBLISHING — this only confirms Make.com accepted the request, not that Instagram received the post. Verify manually.")
    return {"accepted": True}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: make_com_publish.py <content_id>")
        raise SystemExit(1)
    publish(sys.argv[1])
