/**
 * GetByteRush Telegram webhook relay + content-schedule cron trigger.
 *
 * Two independent jobs in one Worker:
 *
 * 1. fetch() — Telegram callback -> this Worker -> answerCallbackQuery
 *    (stop the button spinner immediately) -> forward the raw update to
 *    GitHub as a repository_dispatch event. GitHub Actions owns every
 *    decision from there — this file contains no business logic: it
 *    does not parse callback_data into an action/content_id, does not
 *    know about content states, does not render, does not call Gemini.
 *
 * 2. scheduled() — GitHub Actions' own `schedule:` cron trigger proved
 *    unreliable for this project (confirmed: on the day the 5-slot
 *    content schedule shipped, GitHub's scheduler fired zero of the 5
 *    crons — every run that day was manual). Cloudflare's Cron Triggers
 *    are reliable to the minute, so they now own the 5 daily
 *    content-slot times instead, firing daily-carousel.yml directly via
 *    GitHub's workflow_dispatch API with the right `slot` input — same
 *    remedy already applied to Telegram approvals in job 1 above.
 *
 * Secrets (never in this file, never in wrangler.toml — set via
 * `wrangler secret put`):
 *   TELEGRAM_BOT_TOKEN     - to call answerCallbackQuery
 *   TELEGRAM_WEBHOOK_SECRET - must match Telegram's X-Telegram-Bot-Api-Secret-Token
 *                              header (set via setWebhook's secret_token param)
 *   GITHUB_DISPATCH_TOKEN  - fine-grained PAT, Contents + Actions: Read
 *                              and write, scoped to this one repo, used
 *                              for POST /repos/{repo}/dispatches
 *                              (job 1) and POST .../actions/workflows/
 *                              {id}/dispatches (job 2)
 */

// Keep in sync with scripts/content_slots.py's SLOTS[*].cron_utc — this
// is the one place outside that file the schedule is duplicated,
// because Cloudflare cron triggers can't import Python. If you change a
// slot time, update both.
const SLOT_CRONS = {
  '45 1 * * *': 'morning',
  '15 5 * * *': 'midmorning',
  '15 8 * * *': 'afternoon',
  '15 12 * * *': 'evening',
  '45 14 * * *': 'night',
};

export default {
  async scheduled(event, env, ctx) {
    const slot = SLOT_CRONS[event.cron];
    if (!slot) {
      console.log(`scheduled(): unrecognized cron '${event.cron}', ignoring`);
      return;
    }

    const resp = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/actions/workflows/daily-carousel.yml/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'User-Agent': 'getbyterush-telegram-webhook',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: 'main', inputs: { slot } }),
      }
    );
    const body = await resp.text();
    console.log(`scheduled(): slot=${slot} cron=${event.cron} workflow_dispatch status=${resp.status} body=${body}`);
    if (!resp.ok) {
      // Cloudflare retries a failed scheduled() invocation automatically
      // (with backoff) if it throws — surface the failure that way
      // rather than swallowing it, so a real outage isn't silent.
      throw new Error(`workflow_dispatch failed for slot ${slot}: ${resp.status} ${body}`);
    }
  },

  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('ok', { status: 200 });
    }

    const secretHeader = request.headers.get('X-Telegram-Bot-Api-Secret-Token');
    if (!env.TELEGRAM_WEBHOOK_SECRET || secretHeader !== env.TELEGRAM_WEBHOOK_SECRET) {
      return new Response('unauthorized', { status: 401 });
    }

    let update;
    try {
      update = await request.json();
    } catch (err) {
      return new Response('bad request', { status: 400 });
    }

    if (update.callback_query) {
      try {
        await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/answerCallbackQuery`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ callback_query_id: update.callback_query.id }),
        });
      } catch (err) {
        // Non-fatal: GitHub Actions still processes the update below;
        // worst case the button's loading spinner takes longer to clear.
      }
    }

    if (!update.callback_query && !update.message) {
      return new Response('ok, ignored (no callback_query or message)', { status: 200 });
    }

    try {
      const dispatchResp = await fetch(
        `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/dispatches`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
            Accept: 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'getbyterush-telegram-webhook',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            event_type: 'telegram-update',
            client_payload: { update },
          }),
        }
      );
      const dispatchBody = await dispatchResp.text();
      console.log(`github dispatch status=${dispatchResp.status} body=${dispatchBody}`);
      return new Response(`ok, github dispatch status ${dispatchResp.status}: ${dispatchBody}`, { status: 200 });
    } catch (err) {
      console.log(`github dispatch threw: ${err.message}`);
      return new Response(`ok, github dispatch failed: ${err.message}`, { status: 200 });
    }
  },
};
