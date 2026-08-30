#!/usr/bin/env python3
"""Render every fixture in this directory through V16 and report the
composition family each slide selected, so generalization can be checked
without opening every PNG by hand first."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[1]
OUT = Path('/tmp/gbr-fixtures-out')

sys.path.insert(0, str(ROOT / 'scripts'))
import carousel_art_renderer_v16 as v16  # noqa: E402


def report_selection(name, data):
    total = len(data['slides'])
    rows = []
    for i, s in enumerate(data['slides']):
        role = v16.select_role(s, i, total)
        rows.append(f"  {i+1:02d} vt={s.get('visual_type') or '-':12s} -> {role}")
    print(f"{name} ({total} slides):")
    print('\n'.join(rows))


async def render_one(path):
    env = dict(os.environ)
    env['GBR_INPUT'] = str(path)
    env['GBR_OUT'] = str(OUT)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(ROOT / 'scripts/carousel_art_renderer_v16.py'),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(ROOT),
    )
    out, _ = await proc.communicate()
    return proc.returncode, out.decode()


async def main():
    fixtures = sorted(FIXTURES.glob('*.json'))
    for f in fixtures:
        data = json.loads(f.read_text())
        report_selection(f.stem, data)
        code, out = await render_one(f)
        status = 'OK' if code == 0 else 'FAIL'
        last_line = out.strip().splitlines()[-1] if out.strip() else ''
        print(f'  render: {status} | {last_line}')
        print()


if __name__ == '__main__':
    asyncio.run(main())
