#!/usr/bin/env python3
"""GetByteRush art-directed editorial poster layer.

This wrapper deliberately leaves the editorial/Gemini generator untouched. It overrides
only the visual role mapping, composition and CSS used by carousel_generator.main().
"""
import html
import carousel_generator as renderer

W, H = 1080, 1350
CREAM = "#F2EBDD"
INK = "#0B0D0C"
FOREST = "#12382E"
RED = "#B70C07"
GOLD = "#C8A45A"
LIME = "#B7E32B"


def E(v):
    return html.escape(renderer.clean(v), quote=True)


def punch(v, words=8, chars=72):
    return renderer.punch(v, words, chars)


def support(v, chars=120):
    return renderer.support(v, chars)


def role(slide, i, total):
    explicit = renderer.first(slide.get("role"), slide.get("scene_role")).lower().replace(" ", "_")
    mapping = {
        "interrupt": "hook",
        "open_loop": "open_loop",
        "proof": "evidence",
        "escalation": "reveal",
        "pattern_interrupt": "interrupt",
        "implication": "architecture",
        "payoff": "payoff",
    }
    if explicit in mapping:
        return mapping[explicit]
    return renderer.role(slide, i, total)


def css(p):
    return f"""
@page{{size:{W}px {H}px;margin:0}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:Inter,Arial,Helvetica,sans-serif;background:{CREAM};color:{INK}}}
.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{CREAM};color:{INK}}}
.top,.foot{{position:absolute;left:54px;right:54px;z-index:50;display:flex;justify-content:space-between;align-items:center;font:800 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.6px;text-transform:uppercase}}
.top{{top:30px}}.foot{{bottom:27px;opacity:.58}}
.page{{border:1px solid currentColor;padding:7px 9px}}
.kicker,.micro{{font:900 10px/1.15 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.7px;text-transform:uppercase}}
.kicker{{color:{RED}}}.micro{{opacity:.68}}
.hero{{position:absolute;left:54px;right:54px;top:120px;z-index:10}}
.hero h1{{margin:13px 0 0;max-width:900px;font-size:74px;line-height:.84;letter-spacing:-4px;font-weight:950}}
.hero .sub{{margin:18px 0 0;max-width:680px;font-size:18px;line-height:1.18;opacity:.68}}
.hero-tight{{top:126px}}

.hook-canvas{{position:absolute;inset:0;background:{CREAM}}}
.hook-red{{position:absolute;left:54px;top:292px;width:670px;height:840px;background:{RED};color:{CREAM};padding:38px 34px;overflow:hidden}}
.hook-red:before{{content:"";position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent 0 47px,rgba(242,235,221,.07) 48px),repeating-linear-gradient(90deg,transparent 0 47px,rgba(242,235,221,.07) 48px)}}
.hook-red .inner{{position:relative;z-index:2}}
.hook-red .eyebrow{{font:900 11px/1 ui-monospace,monospace;letter-spacing:2px}}
.hook-red strong{{display:block;margin-top:48px;max-width:570px;font-size:78px;line-height:.82;letter-spacing:-5px;font-weight:950}}
.hook-red .bottom{{position:absolute;left:34px;right:34px;bottom:30px;border-top:1px solid rgba(242,235,221,.55);padding-top:13px;font:800 9px/1.2 ui-monospace,monospace;letter-spacing:1.1px}}
.hook-black{{position:absolute;right:54px;top:292px;width:250px;height:840px;background:{INK};color:{CREAM};padding:25px;overflow:hidden}}
.hook-black:after{{content:"15×";position:absolute;right:-24px;bottom:65px;font:950 150px/.7 Arial,sans-serif;letter-spacing:-12px;color:{RED};transform:rotate(-90deg);opacity:.95}}
.hook-black p{{position:absolute;left:25px;right:25px;bottom:32px;font-size:17px;line-height:1.03;font-weight:900}}

.open-canvas{{position:absolute;left:54px;right:54px;top:330px;bottom:105px}}
.open-left{{position:absolute;left:0;top:0;width:58%;height:100%;border:2px solid {INK};padding:30px;overflow:hidden}}
.open-left:before{{content:"CONTEXT";position:absolute;right:-6px;bottom:-35px;font:950 180px/.7 Arial;letter-spacing:-12px;opacity:.045}}
.open-left .bigline{{font-size:55px;line-height:.86;letter-spacing:-3px;font-weight:950;max-width:500px}}
.open-left .arrow{{position:absolute;right:42px;bottom:42px;font:950 120px/.6 Arial;color:{RED}}}
.open-right{{position:absolute;right:0;top:45px;width:38%;height:92%;background:{FOREST};color:{CREAM};padding:30px;overflow:hidden}}
.open-right:before{{content:"01";position:absolute;right:10px;top:0;font:950 120px/.8 ui-monospace,monospace;opacity:.1}}
.open-right .label{{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.4px}}
.open-right strong{{display:block;margin-top:72px;font-size:48px;line-height:.86;letter-spacing:-2.5px;font-weight:950}}
.open-right p{{margin-top:22px;font-size:15px;line-height:1.2;opacity:.72}}

.evidence-canvas{{position:absolute;left:54px;right:54px;top:320px;bottom:102px}}
.evidence-frame{{position:absolute;left:0;right:115px;top:0;height:690px;background:white;border:2px solid {INK};padding:10px;overflow:hidden;box-shadow:20px 20px 0 {RED}}}
.evidence-frame img{{width:100%;height:100%;display:block;object-fit:contain;background:white}}
.evidence-tag{{position:absolute;left:18px;top:18px;background:{RED};color:{CREAM};padding:9px 12px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.2px;z-index:3}}
.evidence-side{{position:absolute;right:0;top:75px;width:100px;font:900 9px/1.2 ui-monospace,monospace;letter-spacing:1px;text-transform:uppercase;writing-mode:vertical-rl;transform:rotate(180deg)}}
.evidence-note{{position:absolute;left:0;bottom:0;max-width:690px;font-size:19px;line-height:1.05;font-weight:900}}

.reveal-canvas{{position:absolute;inset:0;background:{INK};color:{CREAM};overflow:hidden}}
.reveal-canvas:before{{content:"30×";position:absolute;right:-15px;top:250px;font:950 330px/.65 Arial;letter-spacing:-24px;color:{LIME};opacity:.9}}
.reveal-inner{{position:absolute;left:54px;right:54px;top:270px;z-index:2}}
.reveal-inner .eyebrow{{font:900 11px/1 ui-monospace,monospace;letter-spacing:2px;color:{LIME}}}
.reveal-inner strong{{display:block;margin-top:40px;max-width:670px;font-size:100px;line-height:.78;letter-spacing:-6px;font-weight:950}}
.reveal-inner p{{margin-top:34px;max-width:560px;font-size:18px;line-height:1.18;opacity:.68}}
.reveal-corner{{position:absolute;left:54px;bottom:70px;border-top:2px solid {LIME};width:210px;padding-top:10px;font:800 10px/1.2 ui-monospace,monospace;letter-spacing:1px}}

.interrupt-canvas{{position:absolute;inset:0;background:{RED};color:{CREAM};overflow:hidden}}
.interrupt-canvas:before{{content:"35×";position:absolute;right:-35px;bottom:85px;font:950 330px/.65 Arial;letter-spacing:-25px;color:{INK};opacity:.22}}
.interrupt-grid{{position:absolute;left:54px;right:54px;top:155px;bottom:70px;border-top:2px solid rgba(242,235,221,.55);border-bottom:2px solid rgba(242,235,221,.55)}}
.interrupt-grid .count{{position:absolute;top:20px;right:0;font:900 11px/1 ui-monospace,monospace;letter-spacing:1.5px}}
.interrupt-grid strong{{position:absolute;left:0;top:150px;max-width:820px;font-size:110px;line-height:.76;letter-spacing:-7px;font-weight:950}}
.interrupt-grid p{{position:absolute;left:0;bottom:18px;max-width:520px;font-size:17px;line-height:1.18;opacity:.76}}

.arch-canvas{{position:absolute;left:54px;right:54px;top:315px;bottom:105px}}
.arch-line{{position:absolute;left:0;right:0;top:180px;height:2px;background:{INK};opacity:.35}}
.arch-node{{position:absolute;width:250px;min-height:190px;padding:22px;background:{CREAM};border:2px solid {INK}}}
.arch-node.dark{{background:{FOREST};color:{CREAM};border-color:{FOREST}}}
.arch-node.red{{background:{RED};color:{CREAM};border-color:{RED}}}
.arch-node.n1{{left:0;top:0}}.arch-node.n2{{left:305px;top:135px}}.arch-node.n3{{right:0;top:0}}
.arch-node .label{{font:900 9px/1 ui-monospace,monospace;letter-spacing:1.3px;text-transform:uppercase;opacity:.7}}
.arch-node strong{{display:block;margin-top:34px;font-size:31px;line-height:.9;letter-spacing:-1.5px;font-weight:950}}
.arch-arrow{{position:absolute;font:950 70px/.5 Arial;color:{RED}}}
.arch-arrow.a1{{left:247px;top:110px}}.arch-arrow.a2{{right:240px;top:110px}}
.arch-note{{position:absolute;left:0;bottom:0;max-width:720px;font-size:17px;line-height:1.18;opacity:.7}}

.payoff-canvas{{position:absolute;left:54px;right:54px;top:300px;bottom:100px;background:{INK};color:{CREAM};padding:54px;overflow:hidden}}
.payoff-canvas:before{{content:"→";position:absolute;right:-30px;bottom:-80px;font:950 300px/.6 Arial;color:{RED};opacity:.85}}
.payoff-canvas .eyebrow{{font:900 11px/1 ui-monospace,monospace;letter-spacing:2px;color:{LIME}}}
.payoff-canvas strong{{display:block;margin-top:46px;max-width:800px;font-size:86px;line-height:.79;letter-spacing:-5px;font-weight:950}}
.payoff-canvas p{{margin-top:26px;max-width:650px;font-size:18px;line-height:1.18;opacity:.7}}
.payoff-sign{{position:absolute;left:54px;bottom:32px;font:900 9px/1 ui-monospace,monospace;letter-spacing:1.5px;color:{GOLD}}}
"""


def html_for(slide, story, p, evidence_uri, i, total):
    r = role(slide, i, total)
    headline, body = renderer.content(slide)
    label = renderer.first(slide.get("kicker"), r.replace("_", " "), "GETBYTERUSH")
    source_label, _ = renderer.source(story, slide)

    if r == "hook":
        return f'''<div class="hook-canvas"><div class="hook-red"><div class="inner"><div class="eyebrow">01 / {E(label)}</div><strong>{E(punch(headline,7,54))}</strong></div><div class="bottom">{E(source_label)} · GETBYTERUSH</div></div><div class="hook-black"><div class="micro">TECH • AI • INTERNET</div><p>{E(support(body,78))}</p></div></div>'''

    if r == "open_loop":
        return f'''<div class="hero hero-tight"><div class="kicker">{E(label)}</div><h1>{E(punch(headline,8,72))}</h1></div><div class="open-canvas"><div class="open-left"><div class="micro">THE BOTTLENECK</div><div class="bigline">{E(punch(body,9,75))}</div><div class="arrow">↗</div></div><div class="open-right"><div class="label">02 / WHY IT MATTERS</div><strong>{E(punch(headline,7,48))}</strong><p>{E(support(body,105))}</p></div></div>'''

    if r == "evidence":
        visual = f'<div class="evidence-frame"><span class="evidence-tag">VERIFIED / SOURCE</span><img src="{evidence_uri}" alt="Verified source evidence"></div>' if evidence_uri else '<div class="evidence-frame"><div style="padding:45px;font-size:36px;font-weight:900">Evidence unavailable</div></div>'
        return f'''<div class="hero hero-tight"><div class="kicker">{E(label)}</div><h1>{E(punch(headline,8,72))}</h1></div><div class="evidence-canvas">{visual}<div class="evidence-side">{E(source_label)} · {i:02d}/{total:02d}</div><div class="evidence-note">{E(punch(body,10,110))}</div></div>'''

    if r == "reveal":
        return f'''<div class="reveal-canvas"><div class="reveal-inner"><div class="eyebrow">04 / {E(label)}</div><strong>{E(punch(headline,7,62))}</strong><p>{E(support(body,135))}</p></div><div class="reveal-corner">MEASURED RESULT<br>{E(source_label)}</div></div>'''

    if r == "interrupt":
        return f'''<div class="interrupt-canvas"><div class="interrupt-grid"><div class="count">05 / PATTERN INTERRUPT</div><strong>{E(punch(headline,7,66))}</strong><p>{E(support(body,125))}</p></div></div>'''

    if r == "architecture":
        return f'''<div class="hero hero-tight"><div class="kicker">{E(label)}</div><h1>{E(punch(headline,8,72))}</h1></div><div class="arch-canvas"><div class="arch-line"></div><div class="arch-node n1"><div class="label">CONTEXT</div><strong>Long context</strong></div><div class="arch-arrow a1">→</div><div class="arch-node n2 dark"><div class="label">CACHE / LINK</div><strong>NVLink + KV-cache</strong></div><div class="arch-arrow a2">→</div><div class="arch-node n3 red"><div class="label">ACTIVE WORK</div><strong>Reasoning stays fast</strong></div><div class="arch-note">{E(support(body,145))}</div></div>'''

    if r == "payoff":
        return f'''<div class="hero hero-tight"><div class="kicker">{E(label)}</div><h1>{E(punch(headline,8,72))}</h1></div><div class="payoff-canvas"><div class="eyebrow">07 / THE BOTTOM LINE</div><strong>{E(punch(headline,8,68))}</strong><p>{E(support(body,145))}</p><div class="payoff-sign">GETBYTERUSH / TESTED • EXPLAINED • REAL</div></div>'''

    return f'''<div class="hero"><div class="kicker">{E(label)}</div><h1>{E(punch(headline,8,72))}</h1><p class="sub">{E(support(body,140))}</p></div>'''


renderer.role = role
renderer.css = css
renderer.html_for = html_for

if __name__ == "__main__":
    renderer.main()
