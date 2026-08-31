#!/usr/bin/env bash
# Shared "stage, commit, push with retry" used by every workflow that
# commits generated state back to main. The getbyterush-production
# concurrency group serializes most of these, but a push can still race
# against something outside that group (a manual run, a stray dispatch,
# GitHub's own queueing edge cases) — confirmed live: regenerate-visual.yml
# hit a non-fast-forward rejection despite the shared concurrency group,
# because it dispatches its own follow-up run *before* its own commit
# step executes, so two jobs can legitimately have overlapping git
# lifetimes even when serialized by GitHub's scheduler. Rather than only
# patching that one call site, every commit step now retries through this
# script, since the same race is possible anywhere two of these workflows
# commit close together.
#
# Usage: git_commit_push.sh "<commit message>" <path> [<path> ...]
set -euo pipefail

MESSAGE="$1"
shift
PATHS=("$@")

git config user.name "GetByteRush Bot"
git config user.email "getbyterush-bot@users.noreply.github.com"

git add "${PATHS[@]}"
if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "$MESSAGE"

MAX_ATTEMPTS=5
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if git push origin HEAD:main; then
    echo "Pushed on attempt $attempt."
    exit 0
  fi
  echo "Push attempt $attempt/$MAX_ATTEMPTS rejected (likely non-fast-forward) — rebasing onto latest main and retrying..."
  git fetch origin main
  git rebase origin/main
  sleep $((attempt))
done

echo "ERROR: failed to push after $MAX_ATTEMPTS attempts."
exit 1
