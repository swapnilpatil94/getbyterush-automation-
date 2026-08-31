#!/usr/bin/env python3
"""GetByteRush V17 — grammar-variant visual primitives.

Every function draws one composition variant of one of the eight visual
grammars (see visual_grammars.py for selection, design/design-principles.md
for the philosophy). Pure functions: typed values in, an HTML/SVG fragment
out — same discipline as visual_primitives.py, which this module imports
for shared low-level constants and for variants that were already correct
(comparison two-panel, real-screenshot evidence, pull quote, the 2-point
timeline, the calm payoff bookend) and don't need reinventing.

The one rule every function here is built around: the graphic must carry
meaning with the headline removed. A dot field where 73 of 100 cells are
filled says "73%" before anyone reads a caption; a chain that visibly
widens says "this grows" before anyone reads a word.
"""
import re
import html as _html

import visual_primitives as vp

W, H, M = vp.W, vp.H, vp.M
CREAM, INK = vp.CREAM, vp.INK
esc = vp.esc


# ---------------------------------------------------------------------------
# 1. CONFRONTATION — myth struck through, fact revealed. Generalized from
# the slide-1-only hook_myth: `scale` softens type size for interior use,
# where the slide isn't carrying the whole "STOP" burden alone.
# ---------------------------------------------------------------------------
def confrontation(kicker, myth_text, fact_text, body, accent, fg, source_label, top=170, scale=1.0):
    myth_size = round((44 if len(myth_text) > 34 else 56) * scale)
    fact_size = round((64 if len(fact_text) > 26 else 84) * scale)
    strike_top = round(myth_size * 0.56)
    src_line = (f'<div style="position:absolute;left:{M}px;bottom:118px;font:600 10px/1 \'IBM Plex Mono\';'
                f'letter-spacing:.1em;opacity:.6" class="mono">{esc(source_label)}</div>') if source_label else ''
    return f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:{top}px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{esc(kicker)}</div>
      <div style="position:relative;margin-top:26px;display:inline-block">
        <div class="serif" style="font:700 {myth_size}px/.94 'Fraunces';color:{fg};opacity:.42;text-wrap:balance">{esc(myth_text)}</div>
        <div style="position:absolute;left:-8px;right:-8px;top:{strike_top}px;height:4px;background:{accent};transform:rotate(-2deg)"></div>
      </div>
      <div class="serif" style="margin-top:24px;font:900 {fact_size}px/.9 'Fraunces';letter-spacing:-.025em;color:{accent};text-wrap:balance">{esc(fact_text)}</div>
      {f'<div style="margin-top:26px;max-width:520px;font:600 17px/1.32 Archivo;opacity:.8">{esc(body)}</div>' if body else ''}
    </div>
    {src_line}'''


# ---------------------------------------------------------------------------
# 2. PROPORTIONAL FIELD — a percentage becomes a literal population.
# ---------------------------------------------------------------------------
def proportional_field(pct, label_hi, label_lo, accent, fg, top=380, cols=12, gap=10):
    size = (W - 2 * M - (cols - 1) * gap) / cols
    n_fill = round(pct)
    cells = ''
    for i in range(100):
        r, c = divmod(i, cols)
        x = round(c * (size + gap))
        y = round(r * (size + gap))
        filled = i < n_fill
        cells += (f'<rect x="{x}" y="{y}" width="{size:.1f}" height="{size:.1f}" '
                  f'fill="{accent if filled else "none"}" stroke="{accent if filled else fg}" '
                  f'stroke-opacity="{1 if filled else 0.2}" stroke-width="1.5"/>')
    rows = -(-100 // cols)
    grid_w, grid_h = cols * size + (cols - 1) * gap, rows * size + (rows - 1) * gap
    return f'''
    <svg viewBox="0 0 {grid_w:.0f} {grid_h:.0f}" width="{grid_w:.0f}" height="{grid_h:.0f}" style="position:absolute;left:{M}px;top:{top}px">{cells}</svg>
    <div style="position:absolute;left:{M}px;top:{top + grid_h + 40:.0f}px;display:flex;gap:40px">
      <div><div class="serif" style="font:900 40px/1 'Fraunces';color:{accent}">{pct}%</div>
        <div class="mono" style="margin-top:8px;font:600 9px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.65;color:{fg}">{esc(label_hi)}</div></div>
      <div><div class="serif" style="font:900 40px/1 'Fraunces';color:{fg};opacity:.32">{100-pct}%</div>
        <div class="mono" style="margin-top:8px;font:600 9px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.4;color:{fg}">{esc(label_lo)}</div></div>
    </div>'''


def bar_split(pct, label_hi, label_lo, accent, fg, top=680, bar_h=220):
    full_w = W - 2 * M
    fill_w = round(full_w * pct / 100)
    num_fg = INK if accent in (vp.CREAM,) else CREAM
    return f'''
    <div style="position:absolute;left:{M}px;top:{top}px;width:{full_w}px;height:{bar_h}px;background:{fg}14;border:1px solid {fg}22">
      <div style="position:absolute;left:0;top:0;height:100%;width:{fill_w}px;background:{accent};display:flex;align-items:center;padding-left:26px">
        <span class="serif" style="font:900 44px/1 'Fraunces';color:{num_fg}">{pct}%</span>
      </div>
    </div>
    <div style="position:absolute;left:{M}px;top:{top + bar_h + 22}px;font:700 12px/1 'Archivo';letter-spacing:.02em;color:{accent}">{esc(label_hi)}</div>
    <div style="position:absolute;right:{M}px;top:{top + bar_h + 22}px;font:600 12px/1 'Archivo';opacity:.5;color:{fg}">{esc(label_lo)}</div>'''


# ---------------------------------------------------------------------------
# 3. ACCUMULATION TRAIL — a resource that thins out (or grows) stage by
# stage, drawn as shrinking (or growing) weighted blocks in a row.
# ---------------------------------------------------------------------------
def accumulation_trail(start_value, stages, accent, fg, top=620, h=240):
    weights = [1.0]
    for _ in stages:
        weights.append(weights[-1] * 0.66)
    full_w, gap = W - 2 * M, 14
    total_w = sum(weights)
    x = 0
    blocks, labels = '', ''
    n = len(weights)
    for i, w in enumerate(weights):
        bw = max(56, round(full_w * (w / total_w) * 0.9))
        label = start_value if i == 0 else stages[i - 1]
        if i == n - 1:
            blocks += f'<div style="position:absolute;left:{x}px;top:0;width:{bw}px;height:{h}px;border:2px dashed {accent};opacity:.55"></div>'
        else:
            op = 1.0 if i == 0 else round(max(0.3, 0.85 - i * 0.15), 2)
            blocks += f'<div style="position:absolute;left:{x}px;top:0;width:{bw}px;height:{h}px;background:{accent};opacity:{op}"></div>'
        labels += (f'<div class="mono" style="position:absolute;left:{x}px;top:{h+18}px;width:{bw+40}px;'
                   f'font:600 9px/1.2 \'IBM Plex Mono\';letter-spacing:.08em;opacity:.65;color:{fg}">{esc(str(label)).upper()}</div>')
        x += bw + gap
    return f'<div style="position:absolute;left:{M}px;top:{top}px;height:{h}px">{blocks}{labels}</div>'


# ---------------------------------------------------------------------------
# 4. ASYMMETRIC COMPARISON — matrix variant (2-3 measurable rows). The
# two-panel variant reuses visual_primitives.comparison_split unchanged.
# ---------------------------------------------------------------------------
def comparison_matrix(a_label, b_label, rows, accent, fg, top=420):
    col_w = (W - 2 * M - 60) // 2
    n = len(rows)
    row_h = min(230, max(150, 620 // n))
    header = f'''
    <div style="position:absolute;left:{M}px;top:{top-64}px;width:{col_w}px" class="mono">
      <div style="font:700 11px/1 'IBM Plex Mono';letter-spacing:.14em;color:{fg};opacity:.55">{esc(str(a_label).upper())}</div>
    </div>
    <div style="position:absolute;right:{M}px;top:{top-64}px;width:{col_w}px;text-align:right" class="mono">
      <div style="font:700 11px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">{esc(str(b_label).upper())}</div>
    </div>
    <div style="position:absolute;left:50%;top:{top-64}px;width:1px;height:{n*row_h+40}px;background:{fg}1f;transform:translateX(-50%)"></div>'''
    rows_html = ''
    y = top
    for label, a_val, b_val in rows:
        rows_html += f'''
        <div style="position:absolute;left:{M}px;top:{y}px;width:{col_w}px;border-top:1px solid {fg}22;padding-top:16px">
          <div class="mono" style="font:600 9px/1 'IBM Plex Mono';letter-spacing:.12em;opacity:.45;color:{fg}">{esc(label)}</div>
          <div class="serif" style="margin-top:10px;font:700 27px/1.15 'Fraunces';color:{fg};text-wrap:balance">{esc(a_val)}</div>
        </div>
        <div style="position:absolute;right:{M}px;top:{y}px;width:{col_w}px;text-align:right;border-top:1px solid {accent}55;padding-top:16px">
          <div class="mono" style="font:600 9px/1 'IBM Plex Mono';letter-spacing:.12em;opacity:.7;color:{accent}">{esc(label)}</div>
          <div class="serif" style="margin-top:10px;font:900 27px/1.15 'Fraunces';color:{accent};text-wrap:balance">{esc(b_val)}</div>
        </div>'''
        y += row_h
    return header + rows_html


# ---------------------------------------------------------------------------
# 5. CHRONOLOGICAL SEQUENCE — variable-count multi-point variant; marker
# size grows toward the most recent point (recency emphasis, not a fabricated
# magnitude claim). The 2-point variant reuses visual_primitives.timeline.
# ---------------------------------------------------------------------------
def chronological_multi(points, accent, fg, top=560):
    n = max(1, len(points))
    track_w = W - 2 * M - 40
    step = track_w / max(1, n - 1) if n > 1 else 0
    dots, labels = '', ''
    for j, year in enumerate(points):
        r = 6 + round(10 * (j / (n - 1))) if n > 1 else 10
        x = round(j * step)
        dots += f'<circle cx="{x}" cy="30" r="{r}" fill="{accent if j == n-1 else "none"}" stroke="{accent}" stroke-width="2"/>'
        align = 'left' if j < n - 1 else 'right'
        offset = f'left:{max(0, x-90)}px' if j < n - 1 else 'right:0px'
        labels += f'''<div style="position:absolute;{offset};top:66px;width:180px;text-align:{align}">
          <div class="mono" style="font:700 13px/1 'IBM Plex Mono';letter-spacing:.04em;color:{accent}">{esc(year)}</div>
        </div>'''
    return f'''
    <svg viewBox="0 0 {track_w} 60" width="{track_w}" height="60" style="position:absolute;left:{M}px;top:{top}px;overflow:visible">
      <line x1="0" y1="30" x2="{track_w}" y2="30" stroke="{accent}" stroke-width="2" opacity=".4"/>
      {dots}
    </svg>
    <div style="position:absolute;left:{M}px;top:{top}px;width:{W-2*M}px">{labels}</div>'''


# ---------------------------------------------------------------------------
# 6. SEQUENTIAL SYSTEM — chain (vertical, weight-encoded) and layered-stack
# (horizontal, architecture-flavored) variants.
# ---------------------------------------------------------------------------
def chain_vertical(steps, weights, accent, fg, top=460):
    n = len(steps)
    row_h = min(132, max(88, 720 // n))
    rows = ''
    for i, (label, w) in enumerate(zip(steps, weights)):
        y = top + i * row_h
        bar_w = round(36 + 280 * w)
        rows += f'''
        <div style="position:absolute;left:{M}px;top:{y}px;display:flex;align-items:center;gap:20px">
          <div style="width:11px;height:11px;border-radius:50%;background:{accent};flex:none"></div>
          <div style="height:7px;width:{bar_w}px;background:{accent};opacity:{round(0.32+0.55*w,2)};flex:none"></div>
          <div class="serif" style="font:700 {round(20+11*w)}px/1.1 'Fraunces';color:{fg};text-wrap:balance">{esc(label)}</div>
        </div>'''
        if i < n - 1:
            rows += f'<div style="position:absolute;left:{M+5}px;top:{y+15}px;width:2px;height:{row_h-20}px;background:{fg};opacity:.22"></div>'
    return rows


_LAYER_ALPHA = ['0A', '12', '1A', '22', '2A']


def layered_stack(steps, accent, fg, top=420, gap=16):
    full_w = W - 2 * M
    n = len(steps)
    layer_h = min(132, max(80, (700 - gap * (n - 1)) // n))
    bands = ''
    for i, label in enumerate(steps):
        y = top + i * (layer_h + gap)
        alpha = _LAYER_ALPHA[min(i, len(_LAYER_ALPHA) - 1)]
        bands += f'''
        <div style="position:absolute;left:{M}px;top:{y}px;width:{full_w}px;height:{layer_h}px;background:{fg}{alpha};border-left:4px solid {accent};display:flex;align-items:center;padding-left:28px">
          <div class="mono" style="font:600 10px/1 'IBM Plex Mono';letter-spacing:.12em;opacity:.5;color:{fg};margin-right:22px">{i+1:02d}</div>
          <div class="serif" style="font:700 26px/1.1 'Fraunces';color:{fg};text-wrap:balance">{esc(label)}</div>
        </div>'''
    total_h = len(steps) * (layer_h + gap) - gap
    bands += f'<div style="position:absolute;left:{M+40}px;top:{top}px;width:2px;height:{total_h}px;background:{accent};opacity:.5"></div>'
    return bands


# ---------------------------------------------------------------------------
# 7. EVIDENCE BOARD — pinned real facts (stat / date / source / note) when
# there's investigative texture but no capturable screenshot.
# ---------------------------------------------------------------------------
_CHIP_ROTATIONS = [-3, 2.2, -1.6, 3.1]
_CHIP_KIND_LABEL = {'stat': 'DATA POINT', 'date': 'TIMESTAMP', 'tag': 'SOURCE', 'note': 'CONTEXT'}


def evidence_board(chips, accent, fg, bg, top=380):
    n = len(chips)
    # Fewer real facts means each one earns more presence rather than
    # leaving the rest of the canvas empty — scale card and type size down
    # as chip count grows, up as it shrinks (confirmed necessary by direct
    # render: 2 chips at the "many chips" size left ~700px of dead canvas).
    scale = {1: 1.5, 2: 1.35, 3: 1.05}.get(n, 1.0)
    row_h = round(200 * scale)
    html_out, x, y = '', M, top
    for i, (kind, label) in enumerate(chips):
        rot = _CHIP_ROTATIONS[i % len(_CHIP_ROTATIONS)]
        w = round((420 if kind == 'note' else 250) * scale)
        if x + w > W - M:
            x, y = M, y + row_h
        size = round((44 if kind in ('stat', 'date') else 21) * scale)
        html_out += f'''
        <div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;background:{bg};border:1px solid {fg}2a;box-shadow:{round(6*scale)}px {round(8*scale)}px 0 {accent}22;transform:rotate({rot}deg);padding:{round(22*scale)}px {round(24*scale)}px">
          <div class="mono" style="font:700 {max(8.5,9*scale):.1f}px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">{_CHIP_KIND_LABEL.get(kind, kind.upper())}</div>
          <div class="serif" style="margin-top:{round(12*scale)}px;font:900 {size}px/1.1 'Fraunces';color:{fg};text-wrap:balance">{esc(label)}</div>
        </div>'''
        x += w + 24
    return html_out


# ---------------------------------------------------------------------------
# 8. SINGULAR OBJECT — a metric grounded by a literal unit-count texture
# (its own magnitude drawn as repeated marks, not decoration) when a real
# number exists; a plain isolated word/statement otherwise, per
# design-principles.md's existing `statement` primitive (reused as-is).
# ---------------------------------------------------------------------------
def metric_texture(value, accent, fg, top=200):
    m = re.match(r'([\d.]+)', value)
    n_units = min(40, max(3, round(float(m.group(1))))) if m else None
    size = 640 if len(value) <= 3 else 480
    hero = f'<div style="position:absolute;left:0;right:0;top:{top}px;text-align:center;color:{accent}"><div class="serif" style="font:900 {size}px/.74 \'Fraunces\';letter-spacing:-.06em">{esc(value)}</div></div>'
    if not n_units:
        return hero
    cols, cell, gap = 10, 15, 10
    rows_used = -(-n_units // cols)
    ticks = ''
    for i in range(n_units):
        r, c = divmod(i, cols)
        ticks += f'<rect x="{c*(cell+gap)}" y="{r*(cell+gap)}" width="{cell}" height="{cell}" fill="{accent}" opacity=".85"/>'
    field_w, field_h = cols * (cell + gap) - gap, rows_used * (cell + gap) - gap
    return hero + f'<svg viewBox="0 0 {field_w} {field_h}" width="{field_w}" height="{field_h}" style="position:absolute;right:{M}px;bottom:230px;opacity:.9">{ticks}</svg>'
