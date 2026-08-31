#!/usr/bin/env python3
"""Re-render a rejected carousel through V17 with a materially different
composition per slide — the VISUAL and DIFFERENT_APPROACH rejection paths
from the Telegram review flow. Zero Gemini calls: the editorial JSON is
reused unchanged, only the Graphics Director's grammar selection is
steered away from whatever it picked last time (visual_grammars.select's
`avoid` parameter, added specifically for this).

Usage: regenerate_visual.py <content_id>
Reads state/pipeline/<content_id>.json for the story and the
already-tried grammars, re-renders, updates the record's avoid_grammars
so a third attempt avoids both prior treatments, and leaves the record in
QA_PASSED (caller sends the new Telegram review card) or HOLD_FOR_HUMAN_REVIEW
if content_state already capped the attempts.
"""
import json
import os
import sys
from pathlib import Path

import content_state as cs
import graphics_director_v17 as gd17
import publishing_package


def _avoid_from_record(record):
    stored = record.get('avoid_grammars_by_slide') or {}
    return {int(k): [tuple(x) for x in v] for k, v in stored.items()}


def _update_avoid(record, specs):
    stored = record.get('avoid_grammars_by_slide') or {}
    for i, spec in enumerate(specs):
        key = str(i)
        entry = stored.setdefault(key, [])
        pair = [spec['grammar'], spec['variant']]
        if pair not in entry:
            entry.append(pair)
    record['avoid_grammars_by_slide'] = stored
    return record


def main():
    if len(sys.argv) != 2:
        print('usage: regenerate_visual.py <content_id>')
        raise SystemExit(1)
    content_id = sys.argv[1]
    record = cs.load(content_id)
    if record is None:
        raise SystemExit(f'No content record for {content_id}')
    if record['status'] == 'HOLD_FOR_HUMAN_REVIEW':
        print(f'HOLD_FOR_HUMAN_REVIEW={content_id} — max regeneration attempts already reached, not re-rendering')
        return

    story_path = Path(record['story_path'])
    story = json.loads(story_path.read_text(encoding='utf-8'))

    # GBR_INPUT/GBR_OUT must be set BEFORE carousel_art_renderer_v17 is
    # imported — its DATA/OUT globals are resolved once at import time,
    # not read fresh inside main().
    tmp_input = Path(f'/tmp/regen-{content_id}.json')
    tmp_input.write_text(json.dumps(story, ensure_ascii=False), encoding='utf-8')
    os.environ['GBR_INPUT'] = str(tmp_input)
    os.environ['GBR_OUT'] = str(Path('output/posts').resolve())
    import carousel_art_renderer_v17 as v17

    avoid = _avoid_from_record(record)
    evidence_urls = {i: v17.source_url(story, s) for i, s in enumerate(story.get('slides') or []) if v17.source_url(story, s)}
    carousel = gd17.direct(story, evidence_urls, avoid_grammars=avoid)
    specs = carousel['slides']
    record = _update_avoid(record, specs)

    import asyncio
    asyncio.run(v17.main())

    packages = sorted(Path('output/posts').glob('*/*'), key=lambda p: p.stat().st_mtime)
    pkg_dir = packages[-1]
    publishing_package.build(pkg_dir)

    record['package_path'] = str(pkg_dir)
    cs.save(record)
    cs.transition(content_id, 'QA_PASSED', note=f'regenerated, attempts={record["attempts"]}')
    print(f'REGENERATED={content_id}')
    print(f'PACKAGE={pkg_dir}')
    print('GRAMMARS=', [f"{s['grammar']}:{s['variant']}" for s in specs])


if __name__ == '__main__':
    main()
