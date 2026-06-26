#!/bin/bash
# Smart trigger for the Computer Fund watch. Fires (exit 0) only on REAL new activity:
#   (a) a new Slack message in #sal-teammate newer than last_seen, that mentions Computer
#       or is a handoff (not Computer's own message, not a join notice), OR
#   (b) a new GitHub event: an open PR not yet recorded, or a new commit on origin/master.
# Otherwise exit 1 (skip the LLM wake cheaply). Exit 2 on error.
# This lets the cron poll frequently at near-zero cost on empty ticks.
set -uo pipefail

CHANNEL="C0BCXKG835M"
COMPUTER_UID="U08C9BB5A2G"
ROOT="/home/user/workspace/computer_fund"
SEEN_FILE="$ROOT/state/last_seen_ts.txt"
GH_STATE="$ROOT/state/gh_last_seen.txt"   # stores: "<latest_master_sha>|<sorted open PR numbers>"
mkdir -p "$ROOT/state"
LAST_SEEN=$(cat "$SEEN_FILE" 2>/dev/null || echo "0")

fire=1  # default skip

# ---- (a) Slack check ----
SLACK=$(external-tool call "{\"source_id\":\"slack_direct\",\"tool_name\":\"slack_read_channel\",\"arguments\":{\"channel_id\":\"$CHANNEL\",\"limit\":15,\"response_format\":\"detailed\"}}" 2>/dev/null)
if [ -n "$SLACK" ]; then
  slack_fire=$(printf '%s' "$SLACK" | python3 - "$LAST_SEEN" "$COMPUTER_UID" <<'PY' 2>/dev/null
import json, sys, re
last_seen=float(sys.argv[1] or 0); cu=sys.argv[2].lower()
try: text=json.load(sys.stdin).get("messages","")
except Exception: print("err"); sys.exit(0)
parts=re.split(r"(=== Message from .*? ===)", text)
fire=False
for i in range(1,len(parts),2):
    h=parts[i]; b=parts[i+1] if i+1<len(parts) else ""; blk=h+"\n"+b; low=blk.lower()
    m=re.search(r"Message TS:\s*(\d{10}\.\d{3,6})", blk)
    if not m: continue
    if float(m.group(1))<=last_seen: continue
    am=re.search(r"\((u[0-9a-z]+)\)", h.lower()); au=am.group(1) if am else ""
    if "has joined" in low: continue
    if au==cu: continue
    if (cu in low) or ("@computer" in b.lower()) or ("propose" in low) or ("armed" in low):
        fire=True
print("fire" if fire else "skip")
PY
)
  [ "$slack_fire" = "fire" ] && fire=0
fi

# ---- (b) GitHub check ----
cd "$ROOT" 2>/dev/null || true
git fetch -q origin 2>/dev/null
MASTER_SHA=$(git rev-parse origin/master 2>/dev/null || echo "nosha")
OPEN_PRS=$(gh pr list --repo salvatorepplx/computer-fund --state open --json number 2>/dev/null | python3 -c "import json,sys;
try: print(','.join(str(p['number']) for p in sorted(json.load(sys.stdin), key=lambda x:x['number'])))
except Exception: print('')" 2>/dev/null)
GH_NOW="${MASTER_SHA}|${OPEN_PRS}"
GH_PREV=$(cat "$GH_STATE" 2>/dev/null || echo "")
if [ "$GH_NOW" != "$GH_PREV" ]; then
  fire=0
  echo "$GH_NOW" > "$GH_STATE"
fi

exit $fire
