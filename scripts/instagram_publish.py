#!/usr/bin/env python3
"""Instagram Graph API publisher — carousel container-based publishing.

Verified against Meta's official Instagram Platform docs (Content
Publishing + IG User/media reference) before writing this:
  https://developers.facebook.com/docs/instagram-platform/content-publishing/
  https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/

Flow: one child container per image (is_carousel_item=true, image_url) ->
one parent container (media_type=CAROUSEL, children=[...], caption,
alt_text) -> media_publish(creation_id=parent).

image_url MUST be a public URL — the Graph API fetches it itself, it does
not accept file uploads. This uses the raw.githubusercontent.com URL of
the already-committed slide PNG (the repo is public, and the render step
already commits output/posts/ to main), so no new image-hosting
infrastructure is needed.

alt_text: Meta's own parameter description says "for a single image or
image media in a carousel" (arguably per-child support) while the caption
parameter is explicitly "not supported on images or videos in carousels"
(clearly parent-only). Because this phrasing is genuinely ambiguous and
I have no live credentials to test against, this module ATTEMPTS alt_text
on each child container as a best effort, and ALWAYS also sets it on the
parent container (documented-safe placement) — so accessibility text
reaches Instagram in at least one guaranteed spot even if the per-child
attempt is silently ignored by the API. This is reported, not assumed, in
the production report; it needs a real publish to confirm either way.

Hard gate: only runs after content_state says APPROVED, and refuses to
publish anything already PUBLISHED (idempotent — Phase 6's absolute rule).
Zero Gemini calls.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import content_state as cs

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def _env(name, *alt_names):
    for n in (name, *alt_names):
        v = os.environ.get(n)
        if v:
            return v
    return None


def _graph_post(path, payload):
    url = f"{GRAPH_BASE}/{path}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph API error on {path}: {e.code} {body}")


def _graph_get(path, params):
    url = f"{GRAPH_BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _public_image_url(repo, local_path):
    # output/posts/... path relative to repo root, already committed to main.
    rel = os.path.relpath(local_path, start=os.getcwd()).replace(os.sep, "/")
    return f"https://raw.githubusercontent.com/{repo}/main/{rel}"


def _wait_until_finished(container_id, access_token, timeout_s=120):
    waited = 0
    while waited < timeout_s:
        status = _graph_get(container_id, {"fields": "status_code", "access_token": access_token})
        code = status.get("status_code")
        if code == "FINISHED":
            return True
        if code == "ERROR":
            raise RuntimeError(f"Container {container_id} failed: {status}")
        time.sleep(3)
        waited += 3
    raise TimeoutError(f"Container {container_id} did not finish within {timeout_s}s (status polling)")


def publish(content_id):
    if cs.is_published(content_id):
        print(f"ALREADY_PUBLISHED={content_id} — doing nothing.")
        return {"already_published": True}

    record = cs.load(content_id)
    if record is None:
        raise SystemExit(f"No content record for {content_id}")
    if record["status"] != "APPROVED":
        raise SystemExit(f"Refusing to publish: status is {record['status']!r}, not APPROVED.")

    access_token = _env("INSTAGRAM_ACCESS_TOKEN")
    ig_user_id = _env("INSTAGRAM_ACCOUNT_ID", "IG_USER_ID")
    missing = [n for n, v in (("INSTAGRAM_ACCESS_TOKEN", access_token), ("INSTAGRAM_ACCOUNT_ID", ig_user_id)) if not v]
    if missing:
        cs.transition(content_id, "FAILED", note=f"missing credentials: {', '.join(missing)}")
        raise SystemExit(f"MISSING_CREDENTIALS={','.join(missing)} — cannot publish. See production report for setup steps.")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY not set — cannot build public image URLs.")

    from pathlib import Path
    package = json.loads((Path(record["package_path"]) / "publishing_package.json").read_text(encoding="utf-8"))
    images = package["images"]
    alt_texts = package.get("alt_text_per_slide", [])
    caption = package.get("caption", "")
    overall_alt = package.get("alt_text_overall", "")

    cs.transition(content_id, "PUBLISHING", note="Instagram Graph API")

    try:
        child_ids = []
        for i, img in enumerate(images[:10]):
            public_url = _public_image_url(repo, img)
            payload = {"image_url": public_url, "is_carousel_item": "true", "access_token": access_token}
            if i < len(alt_texts):
                payload["alt_text"] = alt_texts[i][:1000]  # best-effort per-child, see module docstring
            resp = _graph_post(ig_user_id + "/media", payload)
            if "id" not in resp:
                raise RuntimeError(f"Child container {i} failed: {resp}")
            _wait_until_finished(resp["id"], access_token)
            child_ids.append(resp["id"])

        parent_payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "alt_text": (overall_alt or (alt_texts[0] if alt_texts else ""))[:1000],
            "access_token": access_token,
        }
        parent = _graph_post(ig_user_id + "/media", parent_payload)
        if "id" not in parent:
            raise RuntimeError(f"Parent carousel container failed: {parent}")
        _wait_until_finished(parent["id"], access_token)

        published = _graph_post(ig_user_id + "/media_publish", {"creation_id": parent["id"], "access_token": access_token})
        if "id" not in published:
            raise RuntimeError(f"media_publish failed: {published}")

        cs.mark_published(content_id, ig_media_id=published["id"])
        print(f"PUBLISHED={content_id} ig_media_id={published['id']}")
        return {"ig_media_id": published["id"]}

    except Exception as exc:
        cs.transition(content_id, "FAILED", note=str(exc)[:500])
        print(f"PUBLISH_FAILED={content_id}: {exc}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: instagram_publish.py <content_id>")
        raise SystemExit(1)
    publish(sys.argv[1])
