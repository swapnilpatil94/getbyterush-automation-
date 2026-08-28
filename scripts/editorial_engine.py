#!/usr/bin/env python3
"""GetByteRush Editorial Engine.

The editorial engine decides WHAT to publish and HOW the story should be
structured. The carousel renderer owns the final visual design.

Important production rule: factual claims must be traceable to the supplied
source material. The engine must never manufacture a benchmark, quote,
statistic, screenshot, motive, experiment or causal claim.
"""

import json
import os
import re
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
DESIGN_PATH = Path("design/getbyterush-carousel-design-system.md")
SCORING_PATH = Path("prompts/story-scoring.md")


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
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)

    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def fetch_source(url):
    if not url:
        return ""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GetByteRush-EditorialResearch/2.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return ""
            raw = response.read(1_000_000)

        parser = TextExtractor()
        parser.feed(raw.decode("utf-8", errors="ignore"))
        return parser.text()[:14000]
    except Exception as exc:
        print(f"  WARNING: evidence fetch failed: {url} -> {exc}")
        return ""


def load_candidates():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing {INPUT_PATH}. Run radar.py and filter_stories.py first.")
    with INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("stories", [])


def select_research_set(stories):
    """Keep enough diversity for Gemini without creating a huge prompt."""
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
        if seen_types.get(story_type, 0) >= 8:
            continue

        selected.append(story)
        seen_urls.add(url)
        seen_types[story_type] = seen_types.get(story_type, 0) + 1

        if len(selected) >= 30:
            break

    return selected


def build_prompt(stories, repair_feedback=""):
    evidence_blocks = []

    for i, story in enumerate(stories, 1):
        source_text = fetch_source(story.get("url", ""))
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
                "source_page_text": source_text,
            }
        )

    editorial_system = DESIGN_PATH.read_text(encoding="utf-8")
    story_scoring = SCORING_PATH.read_text(encoding="utf-8")

    repair = ""
    if repair_feedback:
        repair = f"""
A previous draft failed the production validator.
Repair ONLY these issues while preserving the verified story:
{repair_feedback}
"""

    return f"""
You are the Chief Editor and Story Producer for getByteRush.

BRAND:
TECH • AI • INTERNET
TESTED • EXPLAINED • REAL

You are producing ONE real Instagram carousel from the current news radar.
The locked design system below is authoritative.

EDITORIAL / DESIGN SYSTEM:
{editorial_system}

STORY SCORING:
{story_scoring}

{repair}

================ FACTUAL INTEGRITY ================

This is a publication system, not a creative-writing task.

1. Treat supplied source_page_text as the primary factual evidence.
2. A company statement is a company statement. Do not silently turn it into an independent fact.
3. Preserve qualifiers exactly: "up to", "may", "plans to", "announced", "according to", etc.
4. NEVER convert "frees up to 25% more area" into "wastes 25% of the chip".
5. NEVER infer a company's motive unless the source explicitly states it.
6. NEVER invent a benchmark, number, quote, date, product capability, customer, partnership, screenshot or result.
7. NEVER invent an experiment. If GetByteRush did not actually run it, do not write "we tested it".
8. If the source does not support a claim, remove the claim rather than filling the gap.
9. For interpretation, label it as analysis/implication. Do not present it as source fact.
10. For speculation, label it SPECULATION and only use it if it adds real value.
11. Every numeric claim in a slide must be traceable to one of the supplied source URLs.
12. Every quote must be directly supported by the supplied source text.
13. Use one primary source whenever it is sufficient. Add secondary sources only when they materially improve verification.
14. The carousel may be dramatic, but the wording must remain factually defensible.

================ STORY QUALITY ================

Do not optimize for volume.
Select the strongest evidence-backed story, not merely the newest headline.

The story must contain a genuine narrative:
HOOK → OPEN LOOP → PROOF → ESCALATION → REVEAL → IMPLICATION → PAYOFF

The first slide should create an information gap without lying.
Every slide must make the next slide feel necessary.
Do not repeat the same fact across slides.
Do not write slides as press-release summaries.
Do not use generic conclusions such as "AI is changing everything".

Prefer:
- surprising architecture changes
- real product changes
- model releases with evidence
- AI agents doing real work
- AI replacing/augmenting real workflows
- business decisions caused by technology
- important security developments
- useful tools with a real reason to care
- comparisons with measurable differences
- official screenshots/evidence

Reject stories that are merely minor announcements unless the consequence is unusually important.

================ DESIGN DECISION ================

Choose exactly one template from:
THE STORY
THE EXPERIMENT
THE SHOCK NUMBER
THE BREAKDOWN
THE CONTRADICTION
THE RECEIPTS
THE TIMELINE
THE COMPARISON
THE WTF
THE DATA STORY

Choose one emotional mode from:
STORY, URGENCY, EXPERIMENT, MONEY, EXPLAINER, CONTRADICTION, INVESTIGATION, TIMELINE, COMPARISON, MYSTERY, DATA.

Choose one primary psychological trigger from:
CURIOSITY, SURPRISE, TENSION, DISCOVERY, UNDERSTANDING, COMPETITION, INVESTIGATION, SCALE, UTILITY.

Choose an accent_color ONLY from this canonical palette:
#12352B, #E53935, #2D8C7A, #B7E32B, #527A91, #F26A21, #426A78, #3159C9, #C7F000, #C9A75D, #B99A5B, #7457FF, #4B78A8, #BFDCCF, #D7D9D5

Do not invent arbitrary neon colours, gradients or brand palettes.
The renderer will reject arbitrary accents.

================ SLIDES ================

Produce 6–8 slides for a normal story. Use 7 when possible.

SLIDE 1 — INTERRUPT
- 3–8 word hook preferred.
- A question, contradiction, huge number or surprising change.
- Minimal supporting text.

SLIDE 2 — OPEN LOOP
- Explain enough to validate the hook.
- Leave the central answer unresolved.

SLIDE 3 — PROOF
- Show an official screenshot, source, metric, diagram or directly supported evidence.
- If a screenshot is requested, asset_url MUST be a real supplied source URL.

SLIDE 4 — ESCALATION / REVEAL
- Introduce the surprising consequence or central reveal.

SLIDE 5 — PATTERN INTERRUPT
- Visually different but factually connected.
- Use a huge number, quote, black interruption, diagram or evidence frame when appropriate.

SLIDE 6 — IMPLICATION
- Answer "So what?" for a normal person, builder, business or industry.
- Clearly distinguish analysis from source fact.

SLIDE 7 — PAYOFF
- One memorable conclusion.
- No generic follow CTA.

SLIDE 8 only when genuinely useful.

COPY LIMITS:
- headline <= 100 characters; target <= 70.
- body <= 320 characters.
- One major idea per slide.
- No paragraph walls.

VISUAL LIMITS:
Allowed visual_type:
screenshot, metric, comparison, timeline, diagram, quote, evidence, typography, final

For every slide provide:
- role
- background_mode: cream OR black
- accent_color from canonical palette
- visual_type
- visual_concept
- source_label
- asset_url when an actual source page is needed
- swipe_reason
- psychological_goal

Do not use filler like "SCENARIO A", "THE DETAIL", "THE ANSWER" unless it is intentionally part of the editorial design and does not replace actual information.

OUTPUT ONLY JSON matching this schema:

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
  "design": {{
    "template": "story|experiment|shock-number|breakdown|contradiction|receipts|timeline|comparison|wtf|data-story",
    "emotional_mode": "story|urgency|experiment|money|explainer|contradiction|investigation|timeline|comparison|mystery|data",
    "primary_psychology": "curiosity|surprise|tension|discovery|understanding|competition|investigation|scale|utility",
    "background_mode": "cream|black",
    "accent_color": "#12352B",
    "visual_strategy": "...",
    "retention_strategy": "...",
    "slide_count": 7
  }},
  "source_story": {{
    "title": "...",
    "source": "...",
    "url": "..."
  }},
  "slides": [
    {{
      "number": 1,
      "role": "interrupt|open_loop|proof|escalation|pattern_interrupt|reveal|implication|payoff",
      "kicker": "...",
      "headline": "...",
      "body": "...",
      "visual_type": "screenshot|metric|comparison|timeline|diagram|quote|evidence|typography|final",
      "visual_concept": "...",
      "asset_url": "...",
      "asset_requirement": "...",
      "source_label": "...",
      "background_mode": "cream|black",
      "accent_color": "#12352B",
      "context": "...",
      "implication": "...",
      "swipe_reason": "...",
      "psychological_goal": "..."
    }}
  ],
  "caption": "...",
  "share_trigger": "...",
  "save_reason": "...",
  "pinned_comment": "...",
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
    {{"name": "...", "url": "..."}}
  ],
  "visual_production_notes": "..."
}}

CANDIDATES:
{json.dumps(evidence_blocks, ensure_ascii=False, indent=2)}
"""


def call_gemini(prompt):
    if not API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) GitHub secret.")

    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.35,
            response_mime_type="application/json",
        ),
    )

    value = (response.text or "").strip()
    if not value:
        raise RuntimeError("Gemini returned an empty response.")
    return json.loads(value)


def validate(result):
    if not isinstance(result, dict):
        raise ValueError("Gemini response is not an object.")
    if not result.get("selected"):
        return

    slides = result.get("slides", [])
    if not 5 <= len(slides) <= 9:
        raise ValueError("Selected story must contain 5–9 slides.")

    score = result.get("score", {})
    if score.get("total", 0) < 75:
        raise ValueError(f"Selected story scored below production threshold: {score.get('total')}")

    for key in ["story_title", "viral_angle", "story_arc", "caption", "alt_text", "hashtags", "fact_check", "sources", "design"]:
        if not result.get(key):
            raise ValueError(f"Missing required field: {key}")

    design = result["design"]
    if design.get("template") not in set(TEMPLATE for TEMPLATE in ["story", "experiment", "shock-number", "breakdown", "contradiction", "receipts", "timeline", "comparison", "wtf", "data-story"]):
        raise ValueError("Invalid design.template")
    if str(design.get("accent_color", "")).upper() not in {
        "#12352B", "#E53935", "#2D8C7A", "#B7E32B", "#527A91", "#F26A21",
        "#426A78", "#3159C9", "#C7F000", "#C9A75D", "#B99A5B", "#7457FF",
        "#4B78A8", "#BFDCCF", "#D7D9D5",
    }:
        raise ValueError("Invalid design accent_color")

    for slide in slides:
        number = slide.get("number")
        headline = str(slide.get("headline") or "").strip()
        body = str(slide.get("body") or "").strip()
        for key in ["number", "role", "headline", "visual_type", "visual_concept", "swipe_reason", "psychological_goal"]:
            if not slide.get(key):
                raise ValueError(f"Slide {number} missing {key}")
        if len(headline) > 120:
            raise ValueError(f"Slide {number} headline is too long ({len(headline)} chars)")
        if len(body) > 360:
            raise ValueError(f"Slide {number} body is too long ({len(body)} chars)")
        if slide.get("visual_type") in {"screenshot", "evidence"} and not slide.get("asset_url"):
            raise ValueError(f"Slide {number} requires asset_url for {slide.get('visual_type')}")
        if str(slide.get("accent_color", "")).upper() not in {
            "#12352B", "#E53935", "#2D8C7A", "#B7E32B", "#527A91", "#F26A21",
            "#426A78", "#3159C9", "#C7F000", "#C9A75D", "#B99A5B", "#7457FF",
            "#4B78A8", "#BFDCCF", "#D7D9D5",
        }:
            raise ValueError(f"Slide {number} has invalid accent_color")

    for fact in result.get("fact_check", []):
        if fact.get("classification") == "FACT" and not fact.get("source_url"):
            raise ValueError("Every FACT needs a source_url")


def main():
    print("=" * 70)
    print("GETBYTERUSH EDITORIAL ENGINE V2")
    print("=" * 70)

    stories = load_candidates()
    if not stories:
        raise RuntimeError("No candidates found.")

    research_set = select_research_set(stories)
    print(f"Candidates available: {len(stories)}")
    print(f"Candidates sent to Gemini: {len(research_set)}")
    print(f"Gemini model: {MODEL}")

    prompt = build_prompt(research_set)
    result = None
    last_error = ""

    for attempt in range(2):
        try:
            result = call_gemini(prompt)
            validate(result)
            break
        except Exception as exc:
            last_error = str(exc)
            if attempt == 1:
                raise
            print(f"WARNING: editorial validation failed: {exc}")
            print("Retrying once with a focused repair request...")
            time.sleep(2)
            prompt = build_prompt(research_set, repair_feedback=last_error)

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

    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    SELECTED_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("=" * 70)
    print("EDITORIAL RESULT")
    print("=" * 70)

    if result.get("selected"):
        print(f"SELECTED: {result['story_title']}")
        print(f"FORMAT:   {result['format']}")
        print(f"TEMPLATE: {result['design']['template']}")
        print(f"THEME:    {result['design']['emotional_mode']}")
        print(f"SCORE:    {result['score']['total']}/100")
        print(f"SLIDES:   {len(result['slides'])}")
        print(f"OUTPUT:   {SELECTED_PATH}")
    else:
        print("NO STORY PASSED THE QUALITY GATE.")
        print("Nothing will be sent to Telegram.")


if __name__ == "__main__":
    main()
