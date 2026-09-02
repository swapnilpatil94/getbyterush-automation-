#!/usr/bin/env python3
"""One-off discovery helper — NOT part of the production pipeline.

Uses INSTAGRAM_ACCESS_TOKEN (already a GitHub secret) to ask the Graph
API which Facebook Pages this token can manage, and which Instagram
Business Account is linked to each. Prints only non-secret identifiers
(Page ID, Page name, IG Business Account ID, IG username) — never prints
any access token, including the per-Page token Meta returns in the same
response.

Run via workflow_dispatch only; delete once IDs are confirmed and set as
INSTAGRAM_ACCOUNT_ID / FACEBOOK_PAGE_ID secrets.
"""
import json
import os
import urllib.parse
import urllib.request

GRAPH_VERSION = "v21.0"


def _get(path, params):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        raise SystemExit("Missing INSTAGRAM_ACCESS_TOKEN")

    me = _get("me", {"fields": "id,name", "access_token": token})
    print(f"Token belongs to: {me.get('name')} (user id {me.get('id')})")
    print()

    accounts = _get("me/accounts", {
        "fields": "id,name,instagram_business_account{id,username}",
        "access_token": token,
    })

    pages = accounts.get("data", [])
    if not pages:
        print("No Facebook Pages found for this token. Check that the token has")
        print("pages_show_list / pages_read_engagement permissions and that your")
        print("Facebook user is an admin of the target Page.")
        return

    print(f"Found {len(pages)} Page(s) this token can manage:")
    print()
    for page in pages:
        ig = page.get("instagram_business_account") or {}
        print(f"  PAGE_NAME       = {page.get('name')}")
        print(f"  FACEBOOK_PAGE_ID = {page.get('id')}")
        if ig:
            print(f"  INSTAGRAM_ACCOUNT_ID = {ig.get('id')}  (@{ig.get('username')})")
        else:
            print("  INSTAGRAM_ACCOUNT_ID = (none linked — connect an IG Business account to this Page)")
        print()


if __name__ == "__main__":
    main()
