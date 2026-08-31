# Archived workflows

Not scanned by GitHub Actions (only `.github/workflows/` is auto-discovered),
kept for history/reference rather than deleted, per the production
architecture cleanup that replaced them:

- `editorial.yml` — old scheduled pipeline; called `carousel_production.py`
  (`carousel_generator.py`), a pre-V9 renderer, not V16 or V17. Replaced by
  `research.yml` (discovery, every 6h) + `daily-carousel.yml` (selection
  through Telegram review, once/day, V17).
- `render-existing.yml`, `render-pinterest-v7.yml` — two separate workflows
  both re-rendering `data/selected_story.json` via V16 on the same
  schedule, coordinated only by a shared concurrency group so they
  wouldn't race each other. Superseded by `daily-carousel.yml` rendering
  once, through V17, as part of the same run that generated the content.
- `getbyterush-radar.yml` — manual radar+filter debug tool; superseded by
  `research.yml`, which does the same thing on a schedule and commits the
  result.
- `telegram-test.yml`, `telegram-approval-test.yml`,
  `approval-result-test.yml` — connectivity/prototype stubs (the approval
  card was hardcoded fake content, not the real pipeline). Superseded by
  the real `telegram-listener.yml` + `scripts/telegram_review.py` +
  `scripts/telegram_review_listener.py`.

`oneoff-render-verify.yml` was deleted outright rather than archived here —
its own last step was `git rm` on itself; it was designed to delete itself
after one run and had already served its purpose.

`gemini-test.yml`, `verify-v16-fixtures.yml`, and `verify-v17-fixtures.yml`
were NOT archived — they're still-useful manual diagnostic/verification
tools, not superseded by anything in this cleanup.
