#!/usr/bin/env python3
"""Render-only utility.

Reads data/selected_story.json and renders it without calling Gemini.
"""
import json
from pathlib import Path

import carousel_generator

INPUT = Path("data/selected_story.json")

if __name__ == "__main__":
    if not INPUT.exists():
        raise SystemExit("Missing data/selected_story.json")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    if not data.get("selected"):
        raise SystemExit("No selected story")
    carousel_generator.main()
