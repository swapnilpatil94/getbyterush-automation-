#!/usr/bin/env python3
"""
GetByteRush Editorial Engine

Input:
    data/candidates.json

Output:
    data/editorial_queue.json
    data/selected_story.json

The engine:
1. Loads the permissive pre-filter candidates.
2. Fetches evidence from the supplied source URLs.
3. Gives Gemini a structured editorial brief.
4. Forces a real story arc, curiosity chain and quality gate.
5. Returns ONE strongest story for the first production run.
6. Never invents experiments, evidence, numbers or screenshots.
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from google import genai
from google.genai import types


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

INPUT_PATH = Path("data/candidates.json")
QUEUE_PATH = Path("data/editorial_queue.json")
SELECTED_PATH = Path("data/selected_story.json")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0
        self.skip_tags = {"script", "style", "noscript", "svg"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)

    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def fetch_source(url):
    if not url:
        return ""

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "GetByteRush-EditorialResearch/1.0"
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return ""

            raw = response.read(1_000_000)

        parser = TextExtractor()
        parser.feed(raw.decode("utf-8", errors="ignore"))
        text = parser.text()

        # Keep enough context for Gemini without exploding the prompt.
        return text[:12000]

    except Exception as exc:
        print(f"  ⚠ Evidence fetch failed: {url} -> {exc}")
        return ""


def load_candidates():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing {INPUT_PATH}. Run radar.py and filter_stories.py first."
        )

    with INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    return data.get("stories", [])


def select_research_set(stories):
    """
    Keep the input broad enough for Gemini to discover a non-obvious winner,
    while avoiding an unnecessarily huge prompt.
    """

    stories = sorted(
        stories,
        key=lambda s: (
            s.get("freshness_score", 0),
            s.get("pre_filter_score", 0),
            s.get("impact_score", 0),
        ),
        reverse=True,
    )

    selected = []
    seen_urls = set()
    seen_types = {}

    for story in stories:
        url = story.get("url", "")
        story_type = story.get("story_type", "TECH_NEWS")

        if url in seen_urls:
            continue

        # Avoid giving one feed/type all the oxygen.
        if seen_types.get(story_type, 0) >= 8:
            continue

        selected.append(story)
        seen_urls.add(url)
        seen_types[story_type] = seen_types.get(story_type, 0) + 1

        if len(selected) >= 30:
            break

    return selected


def build_prompt(stories):
    evidence_blocks = []

    for i, story in enumerate(stories, 1):
        evidence = fetch_source(story.get("url", ""))
        evidence_blocks.append(
            {
                "candidate_id": i,
                "source": story.get("source"),
                "title": story.get("title"),
                "url": story.get("url"),
                "description": story.get("description", ""),
                "published": story.get("published", ""),
                "story_type": story.get("story_type", "TECH_NEWS"),
                "freshness_score": story.get("freshness_score", 0),
                "pre_filter_score": story.get("pre_filter_score", 0),
                "impact_score": story.get("impact_score", 0),
                "source_page_text": evidence,
            }
        )

    editorial_system = Path("prompts/editorial-system.md").read_text(
        encoding="utf-8"
    )

    story_scoring = Path("prompts/story-scoring.md").read_text(
        encoding="utf-8"
    )

    return f"""
You are the Chief Editor and Story Producer for getByteRush.

BRAND:
TECH • AI • INTERNET
TESTED • EXPLAINED • REAL

You are producing the FIRST REAL GetByteRush carousel from the current news radar.

The existing editorial system is authoritative. Follow it closely.

EDITORIAL SYSTEM:
{editorial_system}

SCORING SYSTEM:
{story_scoring}

IMPORTANT:
- Do not optimize for volume.
- Select ONE story only for this production run.
- A technically important but boring announcement loses to a smaller story with a powerful, evidence-backed narrative.
- Do not invent facts.
- Do not invent experiments.
- Do not imply GetByteRush tested something unless the supplied evidence explicitly shows a real test we can reproduce.
- Do not turn a company's marketing claim into an independent fact.
- Clearly distinguish FACT, INTERPRETATION and SPECULATION.
- Prefer primary source evidence.
- If the supplied evidence is insufficient, reject the candidate.
- The first slide must create a question, not summarize the answer.
- Every slide must have a concrete reason to swipe.
- The carousel must have a beginning, tension, reveal, consequence and payoff.
- Avoid generic AI news language.
- Avoid generic "AI is changing..." conclusions.
- Avoid empty engagement bait.
- Prefer real screenshots, official pages, documentation, numbers, comparisons, timelines and evidence.
- If a source page is unavailable, do not fabricate its contents.

STORY SELECTION:
Generate an internal shortlist of at least 10 candidates.
Score them on:
freshness, importance, curiosity, surprise, story tension, shareability,
saveability, visual potential, discussion and brand fit.

Then apply the final quality gate:
Would I stop?
Would I swipe?
Would I finish?
Would I send it?
Would I save it?
Would I follow?
Is there a real story?
Is there a reveal?
Is there something visually demonstrable?
Is it genuinely useful, surprising or important?

If no candidate passes strongly, return selected=false.

SLIDE REQUIREMENTS:
- 5 to 8 slides.
- 1080x1350.
- Mobile first.
- Slide 1: strongest unanswered question.
- Slide 2: setup.
- Slide 3: tension/evidence.
- Slide 4: reveal.
- Slide 5: why it matters.
- Slide 6: deeper twist when supported.
- Slide 7: payoff.
- Slide 8 only when genuinely useful.
- Every slide needs a swipe_reason.
- Never reveal the whole story early.
- Keep body copy short.

VISUAL REQUIREMENTS:
Use real evidence whenever possible.
Allowed visual types:
screenshot, metric, comparison, timeline, diagram, quote, evidence, typography, final.
For screenshot/evidence, specify the exact source URL and what should be captured.
Never request an image that does not exist in the supplied evidence.

OUTPUT ONLY JSON matching this exact conceptual schema:

{{
  "selected": true,
  "rank": 1,
  "format": "breaking_news|daily_24_hours|model_drop|model_comparison|experiment|product_story|business_story|ai_agent_story|internet_mystery|deep_dive|explainer|tool_discovery|data_story|timeline|failure_story|what_happens_next",
  "story_title": "...",
  "why_this_story": "...",
  "viral_angle": "...",
  "story_sentence": "Everyone thinks X, but ...",
  "story_arc": "Hook → Setup → Tension → Reveal → Consequence → Payoff",
  "score": {{
    "freshness": 0,
    "importance": 0,
    "curiosity": 0,
    "surprise": 0,
    "story_tension": 0,
    "shareability": 0,
    "saveability": 0,
    "visual_potential": 0,
    "discussion": 0,
    "brand_fit": 0,
    "total": 0
  }},
  "source_story": {{
    "title": "...",
    "source": "...",
    "url": "..."
  }},
  "slides": [
    {{
      "number": 1,
      "kicker": "...",
      "headline": "...",
      "body": "...",
      "visual_type": "screenshot|metric|comparison|timeline|diagram|quote|evidence|typography|final",
      "visual_concept": "...",
      "asset_url": "...",
      "asset_requirement": "...",
      "source_label": "...",
      "swipe_reason": "..."
    }}
  ],
  "caption": "...",
  "share_trigger": "...",
  "save_reason": "...",
  "pinned_comment": "...",
  "follow_cta": "...",
  "alt_text": "...",
  "hashtags": ["..."],
  "fact_check": [
    {{
      "claim": "...",
      "classification": "FACT|INTERPRETATION|SPECULATION",
      "source_url": "...",
      "source_name": "..."
    }}
  ],
  "sources": [
    {{
      "name": "...",
      "url": "..."
    }}
  ],
  "visual_production_notes": "..."
}}

CANDIDATES:
{json.dumps(evidence_blocks, ensure_ascii=False, indent=2)}
"""


def call_gemini(prompt):
    if not API_KEY:
        raise RuntimeError(
            "Missing GEMINI_API_KEY (or GOOGLE_API_KEY) GitHub secret."
        )

    client = genai.Client(api_key=API_KEY)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.65,
            response_mime_type="application/json",
        ),
    )

    text = (response.text or "").strip()

    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    return json.loads(text)


def validate(result):
    if not isinstance(result, dict):
        raise ValueError("Gemini response is not an object.")

    if not result.get("selected"):
        return

    slides = result.get("slides", [])

    if not 5 <= len(slides) <= 8:
        raise ValueError("Selected story must contain 5–8 slides.")

    score = result.get("score", {})
    if score.get("total", 0) < 75:
        raise ValueError(
            f"Selected story scored below production threshold: {score.get('total')}"
        )

    required = [
        "story_title",
        "viral_angle",
        "story_arc",
        "caption",
        "alt_text",
        "hashtags",
        "fact_check",
        "sources",
    ]

    for key in required:
        if not result.get(key):
            raise ValueError(f"Missing required field: {key}")

    for slide in slides:
        for key in ["number", "headline", "body", "swipe_reason"]:
            if not slide.get(key):
                raise ValueError(
                    f"Slide {slide.get('number')} missing {key}"
                )


def main():
    print("=" * 70)
    print("GETBYTERUSH EDITORIAL ENGINE")
    print("=" * 70)

    stories = load_candidates()

    if not stories:
        raise RuntimeError("No candidates found.")

    research_set = select_research_set(stories)

    print(f"Candidates available: {len(stories)}")
    print(f"Candidates sent to Gemini: {len(research_set)}")
    print(f"Gemini model: {MODEL}")

    prompt = build_prompt(research_set)

    for attempt in range(2):
        try:
            result = call_gemini(prompt)
            validate(result)
            break
        except Exception as exc:
            if attempt == 1:
                raise
            print(f"⚠ Editorial attempt failed: {exc}")
            print("Retrying once...")
            time.sleep(2)

    generated_at = datetime.now(timezone.utc).isoformat()

    result["generated_at"] = generated_at
    result["model"] = MODEL
    result["candidate_count"] = len(stories)

    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)

    queue = {
        "generated_at": generated_at,
        "model": MODEL,
        "count": 1 if result.get("selected") else 0,
        "stories": [result] if result.get("selected") else [],
    }

    QUEUE_PATH.write_text(
        json.dumps(queue, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    SELECTED_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("=" * 70)
    print("EDITORIAL RESULT")
    print("=" * 70)

    if result.get("selected"):
        print(f"SELECTED: {result['story_title']}")
        print(f"FORMAT:   {result['format']}")
        print(f"SCORE:    {result['score']['total']}/100")
        print(f"SLIDES:   {len(result['slides'])}")
        print(f"OUTPUT:   {SELECTED_PATH}")
    else:
        print("NO STORY PASSED THE QUALITY GATE.")
        print("Nothing will be sent to Telegram.")


if __name__ == "__main__":
    main()
