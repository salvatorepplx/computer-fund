#!/bin/bash
# Watch-tick programmatic trigger. Clone/sync the repo, then delegate to the repo's
# scripts/watch_trigger.sh which exits 0 only on real new activity (Slack @computer/handoff
# newer than last_seen, OR a new open PR / new master commit). Exit 1 = skip, 2 = error.
set -uo pipefail
WS=/home/user/workspace
if [ -d "$WS/computer-fund/.git" ]; then
  cd "$WS/computer-fund" && git fetch origin --quiet && git reset --hard origin/master --quiet 2>/dev/null
else
  cd "$WS" && gh repo clone salvatorepplx/computer-fund -- --quiet 2>/dev/null || exit 2
  cd "$WS/computer-fund"
fi
[ -f scripts/watch_trigger.sh ] || exit 1
# Fail-safe: any error inside the trigger -> exit 1 (skip this tick cheaply), never exit 2,
# so a transient Slack/gh cred blip does not mark the cron failed. Real new activity -> exit 0.
bash scripts/watch_trigger.sh; rc=$?
if [ "$rc" = "0" ]; then exit 0; else exit 1; fi
