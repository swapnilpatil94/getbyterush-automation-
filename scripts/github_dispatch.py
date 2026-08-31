#!/usr/bin/env python3
"""Trigger a workflow_dispatch on another workflow file — the built-in
GITHUB_TOKEN passed into telegram-listener.yml already has `actions: write`
for exactly this. Factored out of the old telegram_listener.py so both the
review listener and any future caller share one implementation.
"""
import json
import os
import urllib.request


def trigger(workflow_file, inputs, ref="main"):
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
    payload = json.dumps({"ref": ref, "inputs": inputs}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        ok = 200 <= resp.status < 300
        print(f"Dispatched {workflow_file} inputs={inputs} status={resp.status}")
        return ok
