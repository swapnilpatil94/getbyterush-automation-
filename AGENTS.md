# GetByteRush Automation — Project Instructions

## 1. PROJECT

Repository:
getbyterush-automation-

Brand:
GetByteRush

Instagram:
@getbyterush

Purpose:

Build a fully automated, low/no-cost Instagram technology media
publishing system.

The system researches fresh technology/AI developments, selects
high-potential stories, creates original Instagram carousel content,
renders HTML/CSS to PNG, prepares captions/hashtags/alt text/comments,
sends the completed post to Telegram for human approval, and after
approval prepares/publishes it to Instagram.

The project should work primarily through GitHub Actions.

Do NOT assume a paid server.

Prefer free/open-source services wherever practical.

---

# 2. BRAND POSITIONING

GetByteRush covers:

AI + Technology + Internet

The editorial promise is:

TESTED
EXPLAINED
REAL

The account should NOT become a generic AI-news repost account.

We want:

- interesting technology
- consequential AI developments
- new model releases
- AI agents
- AI replacing/augmenting real work
- major product launches
- important technology shifts
- business stories involving AI
- real experiments
- useful new tools
- major security/technology developments
- model comparisons
- practical technology changes
- "what this means for you" stories
- official product announcements
- screenshots/evidence from official sources
- major technology news roundups

Avoid:

- generic AI tips
- recycled "10 ChatGPT prompts"
- meaningless minor updates
- low-impact product announcements
- generic motivational content
- clickbait unsupported by evidence
- fabricated statistics
- fabricated screenshots
- fabricated quotes

---

# 3. CORE CONTENT PHILOSOPHY

The biggest current problem is NOT simply finding news.

The content must have:

HOOK
→ CURIOSITY
→ STORY
→ TENSION
→ REVEAL
→ CONSEQUENCE
→ INSIGHT

A carousel must make the user WANT to swipe.

Do NOT write slides as independent news summaries.

The carousel should feel like a short story.

Example structure:

Slide 1:
Something changed.

Slide 2:
Here is what people initially thought.

Slide 3:
Here is what actually happened.

Slide 4:
The surprising evidence.

Slide 5:
The consequence.

Slide 6:
Why this matters.

Slide 7:
The bigger picture.

Slide 8:
GetByteRush takeaway.

Every slide should create a reason to continue.

---

# 4. INSTAGRAM GROWTH GOAL

The goal is not simply to publish.

The goal is:

- reach new people
- maximize shares
- maximize saves
- maximize completion/swipe-through rate
- generate comments
- generate profile visits
- generate follows
- build recognizable GetByteRush identity

Prioritize content with:

1. Curiosity
2. Emotional reaction
3. Novelty
4. Consequence
5. Practical usefulness
6. Shareability
7. Saveability
8. Visual potential
9. Discussion potential
10. Brand fit

Do NOT optimize purely for news freshness.

A boring new announcement is worse than a slightly older but extremely consequential story.

---

# 5. STORY TYPES

Use different editorial formats depending on the story.

Do NOT force every story into one template.

Supported formats should include:

## BREAKING NEWS

Fast:
What happened
→ Why it matters
→ What changes now

## MODEL UPDATE

New model
→ benchmark/evidence
→ comparison
→ real capability
→ practical impact

## AI AGENT

What agent does
→ what humans previously did
→ evidence/demo
→ limitations
→ business/work impact

## AI REPLACES WORK

Old workflow
→ AI workflow
→ actual example
→ productivity/economic effect
→ what humans still do

## PRODUCT LAUNCH

What launched
→ actual feature
→ screenshot
→ before/after
→ who benefits
→ hidden catch

## BUSINESS STORY

Company decision
→ motivation
→ evidence
→ consequence
→ bigger trend

## SECURITY

Threat
→ how it worked
→ who was affected
→ evidence
→ what users should know

## EXPERIMENT

Claim
→ test
→ result
→ surprising finding
→ takeaway

## COMPARISON

A vs B
→ meaningful differences
→ evidence
→ use cases
→ winner by scenario

## 24-HOUR ROUNDUP

5–10 important technology developments.

This should NOT simply be a list.

Rank the stories and make each one visually distinct.

---

# 6. RESEARCH

Research the freshest information available.

Priority sources:

1. Official company announcements
2. Official product/model pages
3. Official documentation
4. Official research papers
5. Reuters
6. AP
7. Major reputable technology publications
8. Other reliable primary/secondary sources

Official sources should be preferred whenever possible.

Examples:

OpenAI
Google
Anthropic
Meta
Microsoft
NVIDIA
Apple
Amazon
xAI
Mistral
Perplexity
Cloudflare
etc.

Do not treat company marketing claims as independent facts.

Clearly label:

- company claim
- benchmark
- independent evidence
- reported information

---

# 7. NEWS RADAR

The current radar collects too many stories.

Previously it produced:

Raw stories: ~1187

The pre-filter initially became too aggressive.

The system was changed to allow more candidates.

Current objective:

Do NOT throw away potentially interesting stories too early.

Use multiple stages:

RAW
→ CLEAN
→ FRESHNESS
→ RELEVANCE
→ IMPACT
→ VIRAL POTENTIAL
→ EDITORIAL SELECTION

The final editorial selector should decide.

Do not let an early numeric threshold eliminate everything interesting.

Freshness should be important, but not the only factor.

---

# 8. EDITORIAL SCORING

Evaluate stories using something similar to:

- freshness
- relevance
- impact
- curiosity
- surprise
- shareability
- saveability
- visual potential
- discussion potential
- practical value
- source quality
- brand fit

A story can win even if its raw relevance score is moderate
if it has extremely high curiosity/impact/shareability.

---

# 9. EVIDENCE

Evidence is extremely important.

Whenever appropriate:

- capture official product pages
- capture official announcement screenshots
- capture model pages
- capture benchmark pages
- capture documentation
- capture relevant source material

Never fabricate evidence.

If evidence cannot be captured:

DO NOT invent it.

The carousel may instead explain the information textually
and clearly cite the source.

Evidence rendering must never crash the entire pipeline.

---

# 10. CURRENT RENDERING BUG

There was a production error:

ValueError:
relative path can't be expressed as a file URI

The problem came from:

evidence_path.as_uri()

when evidence_path was relative.

The correct implementation must resolve the path first:

evidence_file = Path(evidence_path).resolve()

then:

evidence_file.as_uri()

Also make evidence rendering fail gracefully.

Missing evidence should not crash carousel generation.

---

# 11. CAROUSEL DESIGN

Instagram carousel:

1080 × 1350

Format:

4:5

Design identity:

Premium editorial technology publication.

Palette:

- warm cream
- deep forest green
- near black
- restrained gold

Visual characteristics:

- oversized typography
- strong whitespace
- editorial layouts
- asymmetric/Bento layouts
- technical monospace annotations
- information pills
- large numerical hooks
- visual hierarchy
- occasional neo-brutalist elements
- screenshots where useful

Do NOT make every slide visually identical.

Use different template families according to story type.

---

# 12. FIRST SLIDE

The first slide is critical.

It must answer:

"Why should I swipe?"

Avoid:

"OpenAI just announced X"

Prefer:

"OpenAI just changed who can build software."

or:

"AI just started doing the job humans thought it couldn't."

or:

"30× more work per watt."

Then create curiosity without lying.

The first slide should usually contain:

- strong hook
- minimal text
- visual tension
- large typography
- clear GetByteRush identity

---

# 13. SWIPE MECHANISM

Every slide must have a reason to continue.

Examples:

Slide 1:
"But something went wrong."

Slide 2:
"That wasn't the real surprise."

Slide 3:
"Then the numbers changed."

Slide 4:
"But there was a catch."

Slide 5:
"This is where it gets interesting."

Slide 6:
"Here's what nobody noticed."

Slide 7:
"So what actually changes?"

Do not literally add "swipe reason" text to the visual unless editorially appropriate.

It is an internal storytelling mechanism.

---

# 14. COPY

Keep slide copy concise.

One major idea per slide.

Avoid paragraphs.

Use:

short sentences
large numbers
strong contrast
clear explanations

The reader should understand the slide in approximately 1–3 seconds.

---

# 15. CAPTION

Caption should:

- add context rather than repeat slides
- explain why the story matters
- encourage discussion
- include source attribution
- avoid spammy engagement bait

---

# 16. HASHTAGS

Do not stuff hashtags.

Use a focused mix of:

broad technology
AI
specific topic
specific company/product
audience intent

Example:

#AI
#ArtificialIntelligence
#Technology
#FutureOfWork
#AITools
#TechNews
#AIAgents
#GetByteRush

Adjust hashtags per story.

---

# 17. ALT TEXT

Generate useful Instagram accessibility alt text.

Describe:

- number of slides
- major visual information
- key facts
- charts
- screenshots
- important text

Do not keyword stuff.

---

# 18. TELEGRAM APPROVAL

The project already has Telegram integration.

The intended workflow:

GitHub Action
↓
Research
↓
Editorial selection
↓
Carousel generation
↓
HTML
↓
PNG
↓
Caption
↓
Hashtags
↓
Alt text
↓
Pinned comment
↓
Telegram approval card
↓
Human approves
↓
Publishing workflow

Approval must be human-controlled.

Do not automatically publish without explicit approval.

---

# 19. GITHUB ACTIONS

GitHub Actions is currently the execution environment.

Keep storage under control.

Generated images/assets can be deleted after a reasonable retention period.

Do not allow repository size to grow indefinitely.

Prefer artifacts/releases/external temporary storage where appropriate.

---

# 20. GEMINI

Gemini API is currently connected and tested.

A previous Gemini test passed:

GETBYTERUSH GEMINI TEST PASSED

Do not hard-code obsolete model names.

The previous model:

models/gemini-2.5-flash

returned:

404 NOT_FOUND

because the environment instructed us to use:

models/gemini-3.6-flash

Always inspect current configuration before changing models.

Keep API keys in GitHub Secrets.

NEVER commit API keys.

---

# 21. IMPORTANT DEVELOPMENT RULE

The user strongly prefers COMPLETE FILES.

When proposing a code change:

DO NOT give only a patch/diff unless explicitly requested.

Prefer:

"Replace this entire file with the following."

Provide the full file.

Before modifying code:

1. Inspect the repository.
2. Inspect existing architecture.
3. Preserve working functionality.
4. Avoid rewriting unrelated systems.
5. Test the complete flow.

---

# 22. CURRENT OBJECTIVE

The immediate priority is NOT adding more features.

The priority is:

MAKE ONE CAROUSEL PERFECTLY.

The complete pipeline must successfully:

1. Find a strong story.
2. Select it.
3. Generate a compelling story-driven carousel.
4. Generate 5–8 slides.
5. Render HTML.
6. Render PNG.
7. Capture evidence when available.
8. Generate caption.
9. Generate hashtags.
10. Generate alt text.
11. Generate pinned comment.
12. Package the post.
13. Send it to Telegram.
14. Allow approval.
15. Preserve all assets required for publishing.

Only after one complete carousel works reliably should more complexity be added.

---

# 23. DO NOT DO THIS

Do not:

- blindly increase story count
- generate generic AI news
- optimize only for freshness
- create slides that read like a press release
- fabricate screenshots
- fabricate statistics
- fabricate quotes
- break working Telegram functionality
- break Gemini integration
- create unnecessary paid dependencies
- add unnecessary infrastructure
- return partial code when a full file is requested
- change unrelated files without inspecting them

---

# 24. DEVELOPMENT STYLE

Be practical.

When debugging:

Explain the root cause in 1–3 sentences.

Then inspect the actual code.

Then provide the complete corrected file.

Then provide exact commands/actions to test.

Prioritize working software over theoretical architecture.

---

# 25. SUCCESS CRITERIA

A successful GetByteRush post should make someone think:

"I didn't know this."

then:

"Wait, what happened?"

then:

"Oh — that's actually important."

then:

"I should send this to someone."

or:

"I need to save this."

That is the target.

The objective is not to be another technology news account.

The objective is to become:

THE TECHNOLOGY ACCOUNT PEOPLE CHECK
TO UNDERSTAND WHAT JUST CHANGED.