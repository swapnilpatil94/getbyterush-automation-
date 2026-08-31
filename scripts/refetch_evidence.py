#!/usr/bin/env python3
"""EVIDENCE rejection path: re-render the same editorial content through
V17 unchanged (same grammar selection — the problem was the captured
screenshot, not the composition). The renderer's own evidence capture
step re-navigates and re-screenshots the source URL fresh on every run,
so simply re-invoking it IS "replace/refetch evidence where possible" —
no new code path needed for the actual refetch, only for wiring it into
the state machine. Zero Gemini calls.
"""
import json
import sys
from pathlib import Path

import content_state as cs


def main():
    if len(sys.argv) != 2:
        print('usage: refetch_evidence.py <content_id>')
        raise SystemExit(1)
    content_id = sys.argv[1]
    record = cs.load(content_id)
    if record is None:
        raise SystemExit(f'No content record for {content_id}')

    story_path = Path(record['story_path'])
    story = json.loads(story_path.read_text(encoding='utf-8'))

    import os
    os.environ['GBR_INPUT'] = str(story_path)
    os.environ['GBR_OUT'] = str(Path('output/posts').resolve())
    import asyncio
    import carousel_art_renderer_v17 as v17
    asyncio.run(v17.main())

    packages = sorted(Path('output/posts').glob('*/*'), key=lambda p: p.stat().st_mtime)
    pkg_dir = packages[-1]

    import qa_check
    ok, failures = qa_check.check_package(pkg_dir, expected_slides=len(story['slides']))
    if not ok:
        cs.transition(content_id, 'FAILED', note='; '.join(failures)[:500])
        print('QA_FAIL')
        for f in failures:
            print(' -', f)
        raise SystemExit(1)

    import publishing_package
    publishing_package.build(pkg_dir)

    record = cs.load(content_id)
    record['package_path'] = str(pkg_dir)
    cs.save(record)
    cs.transition(content_id, 'QA_PASSED', note='evidence refetched')
    print(f'REFETCHED={content_id}')
    print(f'PACKAGE={pkg_dir}')


if __name__ == '__main__':
    main()
