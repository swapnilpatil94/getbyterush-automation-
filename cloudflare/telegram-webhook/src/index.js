/**
 * GetByteRush Telegram webhook relay.
 *
 * Telegram callback -> this Worker -> answerCallbackQuery (stop the button
 * spinner immediately) -> forward the raw update to GitHub as a
 * repository_dispatch event. GitHub Actions owns every decision from
 * there — this file contains no business logic: it does not parse
 * callback_data into an action/content_id, does not know about content
 * states, does not render, does not call Gemini.
 *
 * Secrets (never in this file, never in wrangler.toml — set via
 * `wrangler secret put`):
 *   TELEGRAM_BOT_TOKEN     - to call answerCallbackQuery
 *   TELEGRAM_WEBHOOK_SECRET - must match Telegram's X-Telegram-Bot-Api-Secret-Token
 *                              header (set via setWebhook's secret_token param)
 *   GITHUB_DISPATCH_TOKEN  - fine-grained PAT, Contents: Read and write only,
 *                              scoped to this one repo, used solely for
 *                              POST /repos/{repo}/dispatches
 */
export default {
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
      return new Response(`ok, github dispatch status ${dispatchResp.status}`, { status: 200 });
    } catch (err) {
      return new Response(`ok, github dispatch failed: ${err.message}`, { status: 200 });
    }
  },
};
