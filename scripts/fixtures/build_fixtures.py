#!/usr/bin/env python3
"""Renderer-only test fixtures for V16 — NOT touched by the editorial
pipeline. These exercise the composition system across content types the
production story (NVIDIA/AI hardware) never reaches: consumer product,
cybersecurity, social platforms, model comparison, business impact, and
human-behavior stories. Same JSON schema the editorial engine produces;
no Gemini call involved.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def pkg(title, source_title, source_name, source_url, caption, slides, arc):
    return {
        'selected': True, 'rank': 1, 'format': 'standard', 'story_title': title,
        'why_this_story': 'fixture', 'viral_angle': 'fixture', 'story_sentence': title,
        'story_arc': arc, 'score': 90,
        'design': {'template': 'editorial', 'slide_count': len(slides)},
        'source_story': {'title': source_title, 'source': source_name, 'url': source_url},
        'slides': slides, 'caption': caption, 'share_trigger': 'fixture',
        'save_reason': 'fixture', 'pinned_comment': 'fixture',
        'alt_text': f'{len(slides)}-slide carousel: {title}',
        'hashtags': ['#Tech', '#GetByteRush'], 'fact_check': [], 'sources': [source_url],
        'visual_production_notes': 'fixture', 'generated_at': '2026-08-30T00:00:00Z',
        'model': 'fixture', 'candidate_count': 1,
    }


def slide(n, role, kicker, headline, body, visual_type, bg, accent, context='', implication='', source_label='SOURCE', asset_url=''):
    return {
        'number': n, 'role': role, 'kicker': kicker, 'headline': headline, 'body': body,
        'visual_type': visual_type, 'asset_url': asset_url, 'asset_requirement': '',
        'source_label': source_label, 'background_mode': bg, 'accent_color': accent,
        'context': context, 'implication': implication, 'swipe_reason': '', 'psychological_goal': '',
    }


# ---------------------------------------------------------------------------
# B: Consumer tech / product — iPhone Air launch
# ---------------------------------------------------------------------------
consumer_product = pkg(
    'Apple iPhone Air: The Thinnest iPhone Ever',
    'Introducing iPhone Air', 'Apple Newsroom', 'https://apple.com/newsroom/iphone-air',
    'Apple just redefined how thin a flagship phone can be.',
    [
        slide(1, 'interrupt', 'GETBYTERUSH / HARDWARE', '40% THINNER THAN EVER.',
              "Apple's new iPhone Air drops the design language that's defined the lineup for a decade.",
              'metric', 'black', '#B7E32B'),
        slide(2, 'proof', 'FIRST LOOK', 'THE BODY IS THE HEADLINE.',
              'A single-piece titanium frame houses a battery that curves around the camera bump for the first time.',
              'product', 'cream', '#12352B', source_label='APPLE NEWSROOM', asset_url='https://apple.com/newsroom/iphone-air'),
        slide(3, 'open_loop', 'THE TRADE-OFF', 'IPHONE AIR VS IPHONE 16 PRO.',
              'Thinner doesn’t mean weaker — but it does mean choices.', 'comparison', 'cream', '#B70C07',
              context='Single rear camera, no telephoto', implication='Triple camera system, 5x optical zoom'),
        slide(4, 'escalation', 'BY THE NUMBERS', 'THE SPEC SHEET NOBODY EXPECTED.',
              'The Air is 40% thinner than the Pro, charges 2x faster on the new brick, and holds 3x better thermal headroom under load.',
              'data', 'black', '#B7E32B'),
        slide(5, 'implication', 'HOW THEY DID IT', 'THE BATTERY WRAPS THE CHIP.',
              'A new battery topology was required to hit the thickness target.', 'diagram', 'cream', '#12352B',
              context='Flat battery cell, fixed capacity', implication='Contoured cell, capacity gained back'),
        slide(6, 'pattern_interrupt', 'THE VERDICT', 'THIS IS WHAT "FLAGSHIP" USED TO MEAN.',
              'A design team spent three years arguing over half a millimeter.', 'quote', 'black', '#C9A45C'),
        slide(7, 'payoff', 'THE BOTTOM LINE', 'THIN IS THE NEW FAST.',
              'Every iPhone generation picks one axis to obsess over. This year, it was thickness.',
              'final', 'cream', '#C9A45C'),
    ],
    'Hook → Reveal → Trade-off → Proof → Mechanism → Reaction → Payoff',
)

# ---------------------------------------------------------------------------
# D + F: Cybersecurity / privacy breach, with a mechanism explanation
# ---------------------------------------------------------------------------
security_breach = pkg(
    '22 Million Records Exposed in Credential-Stuffing Breach',
    'Security Incident Disclosure: Unauthorized Access Report', 'CyberScoop',
    'https://cyberscoop.com/incident-report', 'A breach that started with one reused password.',
    [
        slide(1, 'interrupt', 'GETBYTERUSH / SECURITY', '22 MILLION RECORDS EXPOSED.',
              'A single leaked password from a 2019 breach was still valid on this platform in 2026.', 'metric',
              'black', '#B70C07'),
        slide(2, 'proof', 'THE DISCLOSURE', 'THE NOTICE NOBODY WANTED TO SEND.',
              'The company confirmed unauthorized access to its user database on August 14th.', 'evidence',
              'cream', '#12352B', source_label='INCIDENT REPORT', asset_url='https://cyberscoop.com/incident-report'),
        slide(3, 'open_loop', 'HOW IT WORKED', 'ONE OLD PASSWORD, ONE OPEN DOOR.',
              'Attackers didn’t break in — they logged in, using credentials leaked years earlier.',
              'diagram', 'cream', '#12352B', context='2019 breach dumps credential lists',
              implication='2026 platform, same reused password'),
        slide(4, 'escalation', 'THE SCALE', '80% NEVER CHANGED THEIR PASSWORD.',
              'Post-incident analysis found 80% of affected accounts reused the exact same password, a 3x jump in phishing attempts followed within 48 hours, and only 15% had two-factor authentication enabled.',
              'data', 'black', '#B70C07'),
        slide(5, 'implication', 'THE FIX THAT EXISTED', 'ENCRYPTED VS PLAINTEXT STORAGE.',
              'The difference between a leak and a non-event.', 'comparison', 'cream', '#B70C07',
              context='Plaintext password table, instantly usable', implication='Salted hash, computationally useless'),
        slide(6, 'pattern_interrupt', 'THE NUMBER THAT MATTERS', '340% MORE IDENTITY THEFT CLAIMS.',
              'That’s the year-over-year increase filed with the FTC tied to credential-stuffing attacks.',
              'reveal', 'black', '#B7E32B'),
        slide(7, 'implication', 'THE EXPERT VIEW', '"PASSWORDS DON’T EXPIRE. BREACHES DON’T EITHER."',
              'Security researchers have been saying this for a decade.', 'quote', 'black', '#C9A45C'),
        slide(8, 'payoff', 'THE BOTTOM LINE', 'YOUR OLDEST PASSWORD IS YOUR WEAKEST LINK.',
              'A password manager doesn’t just create strong passwords — it makes sure you never reuse one.',
              'final', 'cream', '#C9A45C'),
    ],
    'Hook → Disclosure → Mechanism → Scale → Fix → Reveal → Insight → Payoff',
)

# ---------------------------------------------------------------------------
# C + E: Internet / social media — algorithm & attention
# ---------------------------------------------------------------------------
social_media = pkg(
    'Inside the For You Page: What Changed in 2026',
    'Platform Engineering Blog: Ranking Update Notes', 'Platform Engineering Blog',
    'https://blog.platform.example/ranking-update',
    'The feed that knows you better than your friends do.',
    [
        slide(1, 'interrupt', 'GETBYTERUSH / INTERNET', '3X MORE SCROLLING.',
              'The average session length on short-form video jumped again this year, and nobody agreed to it.',
              'metric', 'black', '#B7E32B'),
        slide(2, 'escalation', 'THE ENGAGEMENT SHIFT', 'THE NUMBERS BEHIND THE FEED.',
              'Short-form consumption is up 40% year over year, users spend 2.5x longer on video than on photos, and article reads on the same platforms dropped 18%.',
              'data', 'black', '#B7E32B'),
        slide(3, 'open_loop', 'THE MECHANISM', 'WATCH TIME BEATS EVERYTHING.',
              'One signal quietly outweighs every other ranking factor.', 'diagram', 'cream', '#12352B',
              context='Likes, comments, shares — explicit signals', implication='Rewatch rate — implicit, dominant'),
        slide(4, 'implication', 'THE OLD WAY', 'FOR YOU PAGE VS FOLLOWING FEED.',
              'One is ranked by a model. The other is ranked by you.', 'comparison', 'cream', '#B70C07',
              context='Following: chronological, your choices', implication='For You: predicted, the model’s choices'),
        slide(5, 'pattern_interrupt', 'THE INSIGHT', '"THE FEED ISN’T SHOWING YOU WHAT YOU LIKE. IT’S SHOWING YOU WHAT YOU WATCH."',
              'That distinction is the entire attention economy.', 'quote', 'black', '#C9A45C'),
        slide(6, 'payoff', 'THE BOTTOM LINE', 'YOU’RE NOT THE CUSTOMER. YOUR ATTENTION IS THE PRODUCT.',
              'Every ranking change this year optimized for one thing: time on platform.', 'final', 'cream', '#C9A45C'),
    ],
    'Hook → Data → Mechanism → Comparison → Insight → Payoff',
)

# ---------------------------------------------------------------------------
# A + G: AI model comparison — heavy comparison testing
# ---------------------------------------------------------------------------
ai_comparison = pkg(
    'GPT-5 vs Claude Opus vs Gemini: The Real Benchmark',
    'Independent Reasoning Benchmark Results Q3 2026', 'SemiAnalysis',
    'https://semianalysis.com/reasoning-benchmark-q3',
    'We ran all three on the same 500 problems. Here’s what actually won.',
    [
        slide(1, 'interrupt', 'GETBYTERUSH / AI', '92% ACCURACY. ONE CLEAR WINNER.',
              'Three frontier models, one benchmark, and a result none of the labs published themselves.',
              'metric', 'black', '#B7E32B'),
        slide(2, 'open_loop', 'WHY IT MATTERS', 'EVERYONE PICKS A MODEL BY VIBES.',
              'No one runs the actual numbers before choosing which AI to build on.', 'typography', 'black', '#C9A45C'),
        slide(3, 'open_loop', 'THE MATCHUP', 'REASONING: GPT-5 VS CLAUDE OPUS.',
              'Both claim the reasoning crown. Only one holds it under pressure.', 'comparison', 'cream', '#B70C07',
              context='GPT-5: faster on short chains', implication='Claude Opus: more consistent on long chains'),
        slide(4, 'escalation', 'THE TRADE-OFF', 'SPEED VS ACCURACY.',
              'The fastest model isn’t the most reliable one — and vice versa.', 'comparison', 'cream',
              '#12352B', context='Gemini: 1.8s average response', implication='Claude Opus: 4.2s, fewer retries needed'),
        slide(5, 'proof', 'THE METHODOLOGY', 'HOW THE BENCHMARK WAS RUN.',
              'Every model saw the identical 500-problem set, blind-scored by three independent graders.',
              'evidence', 'cream', '#12352B', source_label='SEMIANALYSIS',
              asset_url='https://semianalysis.com/reasoning-benchmark-q3'),
        slide(6, 'implication', 'THE COST GAP', 'THE PRICE NOBODY TALKS ABOUT.',
              'Claude Opus costs 3x more per token than Gemini, but needs 40% fewer retries to reach a correct answer, closing the real-world gap to just 15% more expensive.',
              'data', 'black', '#B7E32B'),
        slide(7, 'open_loop', 'UNDER THE HOOD', 'WHY THE ARCHITECTURES DIVERGE.',
              'Each lab made a different bet on how reasoning should work internally.', 'diagram', 'cream',
              '#12352B', context='Chain-of-thought, single forward pass', implication='Tree search, multiple candidate paths'),
        slide(8, 'pattern_interrupt', 'THE CAVEAT', '"BENCHMARKS MEASURE BENCHMARKS. NOT YOUR WORKLOAD."',
              'The model that wins this test may not win yours.', 'quote', 'black', '#C9A45C'),
        slide(9, 'payoff', 'THE BOTTOM LINE', 'PICK THE MODEL FOR THE JOB, NOT THE LEADERBOARD.',
              'Reasoning-heavy work still favors Claude Opus. Everything else favors whatever’s cheapest.',
              'final', 'cream', '#C9A45C'),
    ],
    'Hook → Why it matters → Comparison → Comparison → Proof → Cost → Mechanism → Caveat → Payoff',
)

# ---------------------------------------------------------------------------
# I + H: Business impact / breaking news — short, 5 slides
# ---------------------------------------------------------------------------
business_impact = pkg(
    'Klarna Cut 700 Support Roles With One AI Deployment',
    'Klarna Q3 Investor Update: AI Assistant Performance', 'Klarna Press Room',
    'https://klarna.com/press/ai-assistant-q3', 'The most-cited AI layoff case study just got an update.',
    [
        slide(1, 'interrupt', 'GETBYTERUSH / BUSINESS', '700 JOBS. ONE ALGORITHM.',
              'Klarna’s AI assistant now handles the workload of 700 full-time agents.', 'metric', 'black',
              '#B7E32B'),
        slide(2, 'proof', 'THE ANNOUNCEMENT', 'THE UPDATE THAT CONFIRMED IT WASN’T A FLUKE.',
              'A year after the first headlines, Klarna published performance numbers instead of predictions.',
              'evidence', 'cream', '#12352B', source_label='KLARNA PRESS ROOM',
              asset_url='https://klarna.com/press/ai-assistant-q3'),
        slide(3, 'escalation', 'THE PERFORMANCE DATA', 'THE NUMBERS BEHIND THE CUT.',
              'Support costs dropped 27%, resolution time fell 3x, and customer satisfaction held at 65% — within two points of the human baseline.',
              'data', 'black', '#B7E32B'),
        slide(4, 'implication', 'THE SHIFT', 'BEFORE AI VS AFTER AI.',
              'The support org didn’t shrink evenly — it inverted.', 'comparison', 'cream', '#B70C07',
              context='700 agents, 11-minute average resolution', implication='AI assistant, 2-minute average resolution'),
        slide(5, 'payoff', 'THE BOTTOM LINE', 'THE CASE STUDY EVERY CFO IS READING.',
              'Klarna didn’t automate support. It replaced the org chart.', 'final', 'cream', '#C9A45C'),
    ],
    'Hook → Proof → Data → Shift → Payoff',
)

# ---------------------------------------------------------------------------
# J: Human psychology / tech behavior
# ---------------------------------------------------------------------------
psychology = pkg(
    'Your Brain on Notifications: What the Research Actually Shows',
    'Journal of Behavioral Neuroscience: Digital Interruption Study', 'Journal of Behavioral Neuroscience',
    'https://jbn-journal.example/digital-interruption-2026', 'The dopamine story is real, but it’s not the whole story.',
    [
        slide(1, 'interrupt', 'GETBYTERUSH / PSYCHOLOGY', '3X MORE PHONE CHECKS PER HOUR.',
              'A decade of notification design has quietly rewired how often we look up.', 'metric', 'black',
              '#B7E32B'),
        slide(2, 'open_loop', 'THE MECHANISM', 'THE LOOP THAT KEEPS YOU CHECKING.',
              'It isn’t reward that drives the habit — it’s uncertainty.', 'diagram', 'cream',
              '#12352B', context='Predictable reward, habit fades fast', implication='Random reward, habit compounds'),
        slide(3, 'escalation', 'THE MEASURED EFFECT', 'WHAT INTERRUPTION ACTUALLY DOES.',
              'Study participants showed a 200% spike in cortisol after unexpected notifications, 47% shorter sustained attention spans over a week, and 3x more phone checks per hour by day five.',
              'data', 'black', '#B7E32B'),
        slide(4, 'implication', 'THE CONTRAST', 'FOCUSED BRAIN VS DISTRACTED BRAIN.',
              'The same task, two very different cognitive states.', 'comparison', 'cream', '#B70C07',
              context='Focused: single task, low cortisol', implication='Distracted: task-switching, elevated cortisol'),
        slide(5, 'proof', 'THE STUDY', 'WHERE THIS DATA CAME FROM.',
              'Forty participants, six weeks, continuous cortisol and attention tracking.', 'evidence', 'cream',
              '#12352B', source_label='JOURNAL OF BEHAVIORAL NEUROSCIENCE',
              asset_url='https://jbn-journal.example/digital-interruption-2026'),
        slide(6, 'pattern_interrupt', 'THE REFRAME', '"IT’S NOT ADDICTION. IT’S A WELL-DESIGNED HABIT LOOP."',
              'The distinction matters for how you actually fix it.', 'quote', 'black', '#C9A45C'),
        slide(7, 'payoff', 'THE BOTTOM LINE', 'THE FIX ISN’T WILLPOWER. IT’S FRICTION.',
              'Every notification you don’t disable is a decision someone else made for your attention.',
              'final', 'cream', '#C9A45C'),
    ],
    'Hook → Mechanism → Data → Contrast → Proof → Reframe → Payoff',
)

FIXTURES = {
    'consumer_product': consumer_product,
    'security_breach': security_breach,
    'social_media': social_media,
    'ai_comparison': ai_comparison,
    'business_impact': business_impact,
    'psychology': psychology,
}

if __name__ == '__main__':
    for name, data in FIXTURES.items():
        (OUT / f'{name}.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'{name}: {len(data["slides"])} slides -> {OUT / f"{name}.json"}')
