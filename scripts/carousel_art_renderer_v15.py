#!/usr/bin/env python3
"""GetByteRush V15: final art-direction density pass over V14.
Keeps the editorial/Gemini output unchanged; only adjusts the renderer composition.
"""
import asyncio
import carousel_art_renderer_v14 as v14

# Preserve V14 before replacing the module-global function. This avoids
# the recursive self-call that broke the first V15 Action run.
_BASE_ART = v14.art


def art(role):
    base = _BASE_ART(role)
    if role == 'interrupt':
        return base + '''<div style="position:absolute;left:52px;right:52px;bottom:86px;height:300px;overflow:hidden;pointer-events:none;z-index:3">
          <div style="position:absolute;left:-10px;bottom:-105px;font:950 360px/.72 Arial,sans-serif;letter-spacing:-24px;color:rgba(9,11,10,.12)">35X</div>
          <div style="position:absolute;left:0;top:18px;width:420px;height:2px;background:#090B0A;opacity:.7"></div>
          <div style="position:absolute;left:0;top:42px;font:900 10px ui-monospace,monospace;letter-spacing:2px;color:#090B0A">SCALE / COST / THROUGHPUT</div>
          <div style="position:absolute;right:0;bottom:12px;width:230px;height:76px;border:2px solid #090B0A;transform:rotate(-2deg);background:rgba(242,235,221,.10)">
            <div style="padding:14px;font:950 14px/1 Arial,sans-serif;letter-spacing:-.3px">THE SIGNAL<br><span style="font:800 9px ui-monospace,monospace;letter-spacing:1.2px">AGENTIC LOAD IS THE STORY</span></div>
          </div>
        </div>'''
    return base


# v14.main resolves `art` from v14.main.__globals__, so inject the V15
# wrapper there without replacing v14.art itself.
v14.main.__globals__['art'] = art


if __name__ == '__main__':
    asyncio.run(v14.main())
