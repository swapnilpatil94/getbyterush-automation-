#!/usr/bin/env bash
# Run this yourself, in your own terminal (not via chat). It:
#   1. Prompts for your Telegram bot token (masked input, never echoed,
#      never sent anywhere but api.telegram.org and used locally).
#   2. Generates a fresh random webhook secret and sets it as the
#      Cloudflare Worker's TELEGRAM_WEBHOOK_SECRET (overwrites the
#      placeholder one set during initial deploy).
#   3. Registers that Worker URL + secret with Telegram's setWebhook.
# Prints only Telegram's JSON confirmation — never the token or secret.
set -euo pipefail

WORKER_URL="https://getbyterush-telegram-webhook.getbyterushpost.workers.dev"

read -r -s -p "Telegram bot token (input hidden): " BOT_TOKEN
echo
if [ -z "$BOT_TOKEN" ]; then
  echo "No token entered, aborting."
  exit 1
fi

WEBHOOK_SECRET=$(openssl rand -hex 32)

echo "Updating Cloudflare Worker secret..."
echo "$WEBHOOK_SECRET" | npx --yes wrangler secret put TELEGRAM_WEBHOOK_SECRET

echo "Registering webhook with Telegram..."
curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${WORKER_URL}" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d "allowed_updates=[\"callback_query\",\"message\"]"
echo

unset BOT_TOKEN
unset WEBHOOK_SECRET
