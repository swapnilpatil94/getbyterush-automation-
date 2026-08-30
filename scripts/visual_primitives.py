#!/usr/bin/env python3
"""GetByteRush visual primitives — the composable vocabulary the renderer
executes. Every function here is pure: explicit typed parameters in, an HTML
fragment string out. Nothing reads `slide`/`story`/editorial JSON directly —
that's the Graphics Director's job (scripts/graphics_director.py). This
separation is the actual point of the architecture: primitives are "how to
draw a bar chart," the director is "should this be a bar chart."

Ten primitives: two structural bookends (hook, payoff) plus eight
content-driven ones, matching design/design-principles.md's content-to-
treatment table.
"""
import html as _html

W, H = 1080, 1350
M = 64  # safe margin

CREAM = '#F3EBDD'
INK = '#0B0D0C'


def esc(v):
    return _html.escape(str(v or ''), quote=True)


def header_block(kicker, headline, hsize, accent, fg, body='', top=140, max_w=900, body_max_w=600):
    """Kicker + display headline + optional support body. Reused by every
    content-driven primitive so typography stays identical regardless of
    which hero visual follows it — the one piece of every slide that never
    varies in treatment, only in content."""
    body_html = (
        f'<div style="margin-top:20px;max-width:{body_max_w}px;font:600 17px/1.32 \'Archivo\';opacity:.8">{esc(body)}</div>'
        if body else ''
    )
    return f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:{top}px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{esc(kicker)}</div>
      <div class="serif" style="margin-top:18px;font:900 {hsize}px/.94 'Fraunces';letter-spacing:-.03em;max-width:{max_w}px;text-wrap:balance">{esc(headline)}</div>
      {body_html}
    </div>'''


def hook(kicker, headline, hsize, body, accent, fg, mark_value, mark_size, source_label):
    """Structural bookend, slide 1 only. Asymmetric: header pinned left,
    a numeral (or an arrow when no metric exists in the content) bleeds off
    the right edge — the incomplete-numeral curiosity move from
    design-principles.md."""
    mark = (
        f'<div class="serif" style="position:absolute;right:-70px;top:600px;font:900 {mark_size}px/.7 \'Fraunces\';letter-spacing:-.05em;color:{accent}">{esc(mark_value)}</div>'
        if mark_value else
        f'<div class="serif" style="position:absolute;right:-40px;top:640px;font:900 {round(mark_size*0.82)}px/.7 \'Fraunces\';color:{accent}">&rarr;</div>'
    )
    return f'''
    <div style="position:absolute;left:{M}px;right:340px;top:150px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{esc(kicker)}</div>
      <div class="serif" style="margin-top:26px;font:900 {hsize}px/.86 'Fraunces';letter-spacing:-.035em;text-wrap:balance">{esc(headline)}</div>
      <div style="margin-top:34px;max-width:440px;font:600 19px/1.32 'Archivo';opacity:.86">{esc(body)}</div>
    </div>
    {mark}
    <div style="position:absolute;left:{M}px;bottom:118px;font:600 10px/1 'IBM Plex Mono';letter-spacing:.1em;opacity:.6" class="mono">{esc(source_label)}</div>'''


def payoff(kicker, headline, hsize, body, accent, fg, cta):
    """Structural bookend, last slide only. Calm, not loud — per
    design-principles.md, a carousel ending at maximum intensity has
    nowhere to land. The brand signature is the one place branding asserts
    itself at scale rather than staying in the masthead thread."""
    return f'''
    <div style="position:absolute;left:{M}px;right:{M}px;top:190px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{esc(kicker)}</div>
      <div class="serif" style="margin-top:24px;font:900 {hsize}px/.94 'Fraunces';letter-spacing:-.03em;max-width:840px;text-wrap:balance">{esc(headline)}</div>
      <div style="margin-top:28px;max-width:600px;font:600 18px/1.36 'Archivo';opacity:.8">{esc(body)}</div>
    </div>
    <div class="serif" style="position:absolute;right:-40px;top:560px;font:900 460px/.7 'Fraunces';color:{fg};opacity:.06">&rarr;</div>
    <div style="position:absolute;left:{M}px;top:900px;color:{fg}">
      <div class="serif" style="font:600 64px/1 'Fraunces';font-style:italic;color:{accent}">getByteRush<span style="color:{fg}">.</span></div>
      <div class="mono" style="margin-top:18px;font:600 11px/1.3 'IBM Plex Mono';letter-spacing:.06em;opacity:.6;text-transform:none">{esc(cta)}</div>
    </div>'''


def giant_metric(value, is_word, accent, top=160):
    """One standout number (or, when no clean metric exists, an oversized
    word from the headline) dominates the canvas. See
    design-principles.md's table: the isolation *is* the encoding."""
    size = 460 if is_word else (700 if len(value) <= 3 else 560)
    return f'''
    <div style="position:absolute;left:0;right:0;top:{top}px;text-align:center;color:{accent};overflow:visible">
      <div class="serif" style="font:900 {size}px/.74 'Fraunces';letter-spacing:-.06em;text-transform:uppercase">{esc(value)}</div>
    </div>'''


def data_bars(items, accent, fg, top=560):
    """Two or more comparable numbers become proportional horizontal bars,
    not bare numerals side by side — magnitude is what a bar encodes and a
    numeral doesn't. `items`: [(label, display_value, magnitude 0..1), ...],
    already sorted by the director; magnitude drives bar width directly."""
    bar_max_w = W - 2*M
    rows = ''
    y = 0
    for label, val, magnitude in items:
        # magnitude=None means the director found the numbers didn't share
        # a unit (e.g. "80%" and "3x") — sizing a bar by raw digits across
        # different units would assert a false comparison, so every bar
        # gets the same short, non-comparative mark instead of a
        # proportional width.
        bw = (max(24, round(bar_max_w * max(0.0, min(1.0, magnitude))))
              if magnitude is not None else 90)
        rows += f'''
        <div style="position:absolute;left:0;top:{y}px;width:{W-2*M}px">
          <div class="mono" style="font:600 10px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">{esc(label)}</div>
          <div style="position:relative;margin-top:10px;height:34px">
            <div style="position:absolute;left:0;top:0;height:100%;width:{bw}px;background:{accent}"></div>
          </div>
          <div class="serif" style="margin-top:10px;font:900 34px/.9 'Fraunces';letter-spacing:-.02em;color:{fg}">{esc(val)}</div>
        </div>'''
        y += 150
    return f'<div style="position:absolute;left:{M}px;top:{top}px;width:{W-2*M}px">{rows}</div>'


def comparison_split(a_label, a_val, b_label, b_val, accent, fg, bg, top=430, card_h=560):
    """Two competing options as spatial contrast: one neutral panel, one
    accent-colored panel. The color asymmetry visually weights one side —
    a legitimate editorial technique, not decoration."""
    gap = 16
    half = (W - 2*M - gap) // 2
    return f'''
    <div style="position:absolute;left:{M}px;top:{top}px;width:{half}px;min-height:{card_h}px;background:{INK};color:{CREAM};padding:30px">
      <div class="mono" style="font:700 10px/1 'IBM Plex Mono';letter-spacing:.16em;opacity:.6">{esc(str(a_label).upper())}</div>
      <div class="serif" style="margin-top:22px;font:700 30px/1.18 'Fraunces';text-wrap:balance">{esc(a_val)}</div>
    </div>
    <div style="position:absolute;right:{M}px;top:{top}px;width:{half}px;min-height:{card_h}px;background:{accent};color:{CREAM};padding:30px">
      <div class="mono" style="font:700 10px/1 'IBM Plex Mono';letter-spacing:.16em;opacity:.75">{esc(str(b_label).upper())}</div>
      <div class="serif" style="margin-top:22px;font:700 30px/1.18 'Fraunces';text-wrap:balance">{esc(b_val)}</div>
    </div>
    <div style="position:absolute;left:50%;top:{top - 26}px;transform:translateX(-50%);width:52px;height:52px;border-radius:50%;background:{fg};color:{bg};display:flex;align-items:center;justify-content:center;font:900 12px/1 'IBM Plex Mono';letter-spacing:.04em">VS</div>'''


def before_after(before_label, before_val, after_label, after_val, accent, fg, bg, top=430, card_h=560):
    """The SAME subject in two states — deliberately distinct grammar from
    comparison_split: one shared frame with a center divide and a directional
    arrow, not two independent panels, so it reads as transformation rather
    than as two competing options."""
    gap = 2
    half = (W - 2*M - gap) // 2
    return f'''
    <div style="position:absolute;left:{M}px;top:{top}px;width:{half}px;min-height:{card_h}px;background:{fg}14;border:1px solid {fg}33;padding:30px">
      <div class="mono" style="font:700 10px/1 'IBM Plex Mono';letter-spacing:.16em;opacity:.55;color:{fg}">{esc(str(before_label).upper())}</div>
      <div class="serif" style="margin-top:22px;font:700 28px/1.18 'Fraunces';text-wrap:balance;color:{fg};opacity:.7">{esc(before_val)}</div>
    </div>
    <div style="position:absolute;right:{M}px;top:{top}px;width:{half}px;min-height:{card_h}px;background:{accent};color:{CREAM};padding:30px">
      <div class="mono" style="font:700 10px/1 'IBM Plex Mono';letter-spacing:.16em;opacity:.75">{esc(str(after_label).upper())}</div>
      <div class="serif" style="margin-top:22px;font:700 30px/1.18 'Fraunces';text-wrap:balance">{esc(after_val)}</div>
    </div>
    <div style="position:absolute;left:50%;top:{top + card_h//2 - 22}px;transform:translateX(-50%);width:44px;height:44px;border-radius:50%;background:{bg};border:2px solid {accent};color:{accent};display:flex;align-items:center;justify-content:center;font:900 18px/1 'IBM Plex Mono'">&rarr;</div>'''


def timeline(points, accent, fg, top=560):
    """A sequence of ordered/dated events becomes a line with markers —
    chronology shown, not narrated. `points`: [(marker, label), ...],
    3-5 items, first point hollow through to the last filled (progression)."""
    n = max(1, len(points))
    track_w = W - 2*M - 40
    step = track_w / max(1, n - 1) if n > 1 else 0
    dots = ''.join(
        f'<circle cx="{round(j*step)}" cy="20" r="{9 if j == n-1 else 6}" fill="{accent if j == n-1 else "none"}" stroke="{accent}" stroke-width="2"/>'
        for j in range(n)
    )
    labels = ''
    for j, (marker, label) in enumerate(points):
        x = round(j * step)
        align = 'left' if j < n - 1 else 'right'
        offset = f'left:{max(0, x-140)}px' if j < n - 1 else f'right:0px'
        labels += f'''<div style="position:absolute;{offset};top:52px;width:280px;text-align:{align}">
          <div class="mono" style="font:600 9px/1 'IBM Plex Mono';letter-spacing:.12em;color:{accent}">{esc(marker)}</div>
          <div class="serif" style="margin-top:8px;font:700 22px/1.15 'Fraunces';color:{fg}">{esc(label)}</div>
        </div>'''
    return f'''
    <svg viewBox="0 0 {track_w} 40" width="{track_w}" height="40" style="position:absolute;left:{M}px;top:{top}px;overflow:visible">
      <line x1="0" y1="20" x2="{track_w}" y2="20" stroke="{accent}" stroke-width="2" opacity=".45"/>
      {dots}
    </svg>
    <div style="position:absolute;left:{M}px;top:{top}px;width:{W-2*M}px">{labels}</div>'''


def process_flow(frm, to, accent, fg, bg, top=460):
    """A mechanism with a clear start/end state: two labeled points and a
    connecting directional arrow — causality shown as a line, not spelled
    out in a sentence."""
    lane_w = (W - 2*M - 112) // 2
    return f'''
    <div style="position:absolute;left:{M}px;top:{top}px;width:{lane_w}px;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">01 / From</div>
      <div class="serif" style="margin-top:14px;font:700 32px/1.1 'Fraunces';text-wrap:balance">{esc(frm)}</div>
    </div>
    <div style="position:absolute;right:{M}px;top:{top}px;width:{lane_w}px;text-align:right;color:{fg}">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">02 / To</div>
      <div class="serif" style="margin-top:14px;font:700 32px/1.1 'Fraunces';text-wrap:balance">{esc(to)}</div>
    </div>
    <svg viewBox="0 0 {W-2*M} 40" width="{W-2*M}" height="40" style="position:absolute;left:{M}px;top:{top+200}px">
      <line x1="0" y1="20" x2="{W-2*M-40}" y2="20" stroke="{accent}" stroke-width="2" opacity=".5"/>
      <polygon points="{W-2*M-40},10 {W-2*M},20 {W-2*M-40},30" fill="{accent}" opacity=".85"/>
      <circle cx="0" cy="20" r="7" fill="{bg}" stroke="{accent}" stroke-width="2"/>
    </svg>
    <div class="serif" style="position:absolute;right:-30px;top:{top+270}px;font:900 340px/.7 'Fraunces';color:{accent};opacity:.07">&rarr;</div>'''


def annotated_screenshot(image_url, accent, badge_text, annotation_label=None, top=320, frame_h=660):
    """A real captured screenshot in an editorial frame. When the director
    supplies a short annotation label (something specific worth pointing
    at), adds a leader-line + circle marker; otherwise stays a plain framed
    citation — an annotation only when one is justified, per
    design-principles.md, not on every evidence slide by default."""
    marker = ''
    if annotation_label:
        marker = f'''
        <div style="position:absolute;left:60%;top:38%;width:18px;height:18px;border:2px solid {accent};border-radius:50%;background:{CREAM}66"></div>
        <div style="position:absolute;left:calc(60% + 20px);top:calc(38% + 8px);width:110px;height:1px;background:{accent}"></div>
        <div class="mono" style="position:absolute;left:calc(60% + 26px);top:calc(38% + 14px);background:{INK};color:{CREAM};padding:6px 10px;font:700 9px/1.2 'IBM Plex Mono';letter-spacing:.08em;max-width:220px">{esc(annotation_label)}</div>'''
    return f'''
    <div style="position:absolute;left:{M}px;top:{top}px;width:820px;height:{frame_h}px;background:#fff;border:1px solid rgba(11,13,12,.14);box-shadow:16px 20px 0 {accent}22;transform:rotate(-.5deg);overflow:hidden">
      <img src="{image_url}" style="width:100%;height:100%;object-fit:contain;display:block;filter:grayscale(.8) contrast(1.1)">
      <div style="position:absolute;inset:0;background:{accent};mix-blend-mode:multiply;opacity:.3;pointer-events:none"></div>
      {marker}
    </div>
    <div class="mono" style="position:absolute;left:{M+24}px;top:{top-22}px;background:{accent};color:{CREAM};padding:8px 12px;font:700 9px/1 'IBM Plex Mono';letter-spacing:.12em">{esc(badge_text)}</div>'''


def citation_card(source_name, quote_text, source_url_text, accent, top=320, frame_h=660):
    """Evidence fallback when no screenshot was captured: the real
    source_story title, never fabricated placeholder text."""
    return f'''
    <div style="position:absolute;left:{M}px;top:{top}px;width:820px;height:{frame_h}px;background:{INK};color:{CREAM};padding:48px">
      <div class="mono" style="font:600 10px/1 'IBM Plex Mono';letter-spacing:.16em;color:{accent}">{esc(source_name)}</div>
      <div class="serif" style="margin-top:40px;font:600 38px/1.24 'Fraunces';font-style:italic;max-width:700px">&ldquo;{esc(quote_text)}&rdquo;</div>
      <div class="mono" style="position:absolute;left:48px;right:48px;bottom:40px;border-top:1px solid rgba(243,235,221,.25);padding-top:14px;font:500 11px/1.3 'IBM Plex Mono';opacity:.7;word-break:break-all">{esc(source_url_text)}</div>
    </div>'''


def visual_quote(kicker, quote_text, source_name, accent, fg):
    """A quotable line gets citation-styled framing — attribution matters
    for credibility, per design-principles.md; italic text alone reads as
    unsourced. Vertically centered across the full canvas, the same
    proven pattern as `statement` — a top-pinned kicker with the quote
    fixed below it left roughly 600px of dead space whenever the quote
    itself was short, confirmed by direct render, not assumed."""
    return f'''
    <div style="position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;color:{fg};padding:0 {M}px">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.18em;color:{accent}">{esc(kicker)}</div>
      <div class="serif" style="margin-top:28px;font:600 46px/1.16 'Fraunces';font-style:italic;letter-spacing:-.01em;max-width:880px;text-wrap:balance">&ldquo;{esc(quote_text)}&rdquo;</div>
      <div class="mono" style="margin-top:30px;font:700 10px/1 'IBM Plex Mono';letter-spacing:.14em;color:{accent}">— {esc(source_name).upper()}</div>
    </div>'''


def statement(kicker, headline, hsize, body, accent, fg):
    """Full-bleed, centered, calm — the carousel's deliberate reset beat,
    not a fallback. See design-principles.md: a real design choice, used
    when it earns its place."""
    return f'''
    <div style="position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:{fg};padding:0 {M}px">
      <div class="mono" style="font:600 11px/1 'IBM Plex Mono';letter-spacing:.2em;color:{accent}">{esc(kicker)}</div>
      <div style="margin-top:30px;width:120px;height:2px;background:{accent}"></div>
      <div class="serif" style="margin-top:34px;font:900 {hsize}px/.94 'Fraunces';letter-spacing:-.03em;max-width:820px;text-wrap:balance">{esc(headline)}</div>
      <div style="margin-top:30px;width:120px;height:2px;background:{accent}"></div>
      <div style="margin-top:34px;max-width:520px;font:600 18px/1.36 'Archivo';opacity:.75">{esc(body)}</div>
    </div>'''
