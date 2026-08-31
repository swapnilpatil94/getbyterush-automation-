#!/usr/bin/env python3
"""Daily carousel generation — the EDITORIAL -> GRAPHICS DIRECTOR V17 ->
RENDER -> QA -> PUBLISHING PACKAGE -> TELEGRAM REVIEW stretch of the
production architecture. Assumes data/selected_story.json already exists
(radar -> filter -> topic_memory -> editorial_engine ran earlier in the
same workflow, unchanged from before this script existed). Zero Gemini
calls in this script itself — editorial_engine.py's one call already
happened before this runs.

Creates one content_state record, renders through V17, runs Tier-1 QA,
builds the publishing package, and sends the real Telegram review card.
Leaves the record in AWAITING_TELEGRAM_APPROVAL — nothing here ever
calls Instagram.
"""
import json
import os
import sys
from pathlib import Path

SELECTED = Path('data/selected_story.json')
PIPELINE_DIR = Path('data/pipeline')


def main():
    if not SELECTED.exists():
        raise SystemExit('data/selected_story.json not found — editorial_engine must run first')
    story = json.loads(SELECTED.read_text(encoding='utf-8'))
    if not story.get('selected') or not story.get('slides'):
        raise SystemExit('selected_story.json is not a valid, selected editorial package')

    import content_state as cs
    source_url = (story.get('source_story') or {}).get('url', '')
    record = cs.create(story.get('story_title', ''), source_url)
    content_id = record['content_id']
    story['content_id'] = content_id

    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    story_path = PIPELINE_DIR / f'{content_id}.json'
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
    record['story_path'] = str(story_path)
    cs.save(record)

    cs.transition(content_id, 'SHORTLISTED', note='selected by editorial_engine + topic_memory')
    cs.transition(content_id, 'EDITORIAL_READY')
    cs.transition(content_id, 'RENDERING')

    # GBR_INPUT/GBR_OUT must be set before carousel_art_renderer_v17 is
    # imported — its DATA/OUT globals resolve once at import time.
    os.environ['GBR_INPUT'] = str(story_path)
    os.environ['GBR_OUT'] = str(Path('output/posts').resolve())
    import asyncio
    import carousel_art_renderer_v17 as v17
    asyncio.run(v17.main())

    packages = sorted(Path('output/posts').glob('*/*'), key=lambda p: p.stat().st_mtime)
    if not packages:
        cs.transition(content_id, 'FAILED', note='renderer produced no package')
        raise SystemExit('V17 render produced no output package')
    pkg_dir = packages[-1]
    record = cs.load(content_id)
    record['package_path'] = str(pkg_dir)
    cs.save(record)

    import qa_check
    ok, failures = qa_check.check_package(pkg_dir, expected_slides=len(story['slides']))
    if not ok:
        cs.transition(content_id, 'FAILED', note='; '.join(failures)[:500])
        print('QA_FAIL')
        for f in failures:
            print(' -', f)
        raise SystemExit(1)
    cs.transition(content_id, 'QA_PASSED', note='V17, gemini_calls=0')
    print('QA_PASS')

    import publishing_package
    package = publishing_package.build(pkg_dir)

    import telegram_review
    telegram_review.send_review_card(content_id, pkg_dir, package)
    cs.transition(content_id, 'AWAITING_TELEGRAM_APPROVAL')

    print(f'CONTENT_ID={content_id}')
    print(f'PACKAGE={pkg_dir}')
    print(f'GEMINI_CALLS_THIS_SCRIPT=0')


if __name__ == '__main__':
    main()
