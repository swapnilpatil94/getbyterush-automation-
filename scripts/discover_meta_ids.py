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
import urllib.error
import urllib.parse
import urllib.request

GRAPH_VERSION = "v21.0"


def _get(host, path, params):
    url = f"https://{host}/{GRAPH_VERSION}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Graph API error on {host}/{path}: {e.code} {body}")


def _probe_hosts(token):
    """The 'IGAA...'-prefixed token from Meta's newer Instagram API with
    Instagram Login belongs to graph.instagram.com, not the older
    graph.facebook.com Graph API this script (and instagram_publish.py)
    were originally written against — confirmed live after three
    identical 'Cannot parse access token' failures against
    graph.facebook.com with freshly re-set tokens ruled out a paste
    error."""
    for host in ("graph.facebook.com", "graph.instagram.com"):
        url = f"https://{host}/{GRAPH_VERSION}/me?" + urllib.parse.urlencode(
            {"fields": "id,username,account_type", "access_token": token}
        )
        try:
            with urllib.request.urlopen(url) as resp:
                print(f"  {host}: OK -> {resp.read().decode()}")
        except urllib.error.HTTPError as e:
            print(f"  {host}: {e.code} {e.read().decode('utf-8', errors='replace')[:300]}")
    print()


def main():
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        raise SystemExit("Missing INSTAGRAM_ACCESS_TOKEN")

    print("Probing both possible Graph API hosts for this token:")
    _probe_hosts(token)

    me = _get("graph.facebook.com", "me", {"fields": "id,name", "access_token": token})
    print(f"Token belongs to: {me.get('name')} (user id {me.get('id')})")
    print()

    accounts = _get("graph.facebook.com", "me/accounts", {
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
