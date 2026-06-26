#!/bin/bash
# Trigger check for "Watch #sal-teammate for @computer".
# Exit 0 -> fire LLM tick (new message addressed to Computer, not from Computer).
# Exit 1 -> skip (nothing new for Computer).
# Exit 2 -> error (so setup testing flags it).
set -uo pipefail

CHANNEL="C0BCXKG835M"
COMPUTER_UID="U08C9BB5A2G"
SEEN_FILE="/home/user/workspace/computer_fund/state/last_seen_ts.txt"
mkdir -p "$(dirname "$SEEN_FILE")"
[ -f "$SEEN_FILE" ] || echo "0" > "$SEEN_FILE"
LAST_SEEN=$(cat "$SEEN_FILE" 2>/dev/null || echo "0")

DATA=$(external-tool call "{\"source_id\":\"slack_direct\",\"tool_name\":\"slack_read_channel\",\"arguments\":{\"channel_id\":\"$CHANNEL\",\"limit\":20,\"response_format\":\"detailed\"}}") || exit 2

printf '%s' "$DATA" | python3 - "$LAST_SEEN" "$COMPUTER_UID" <<'PY'
import json, sys, re
last_seen = float(sys.argv[1] or 0)
computer_uid = sys.argv[2].lower()
try:
    text = json.load(sys.stdin).get("messages", "")
except Exception:
    sys.exit(2)

# Messages are delimited by headers: "=== Message from <author> (<UID>) at <time> ==="
# Split keeping each header with its body.
parts = re.split(r"(=== Message from .*? ===)", text)
# parts = [preamble, header1, body1, header2, body2, ...]
fire = False
for i in range(1, len(parts), 2):
    header = parts[i]
    body = parts[i + 1] if i + 1 < len(parts) else ""
    block = header + "\n" + body
    m = re.search(r"Message TS:\s*(\d{10}\.\d{3,6})", block)
    if not m:
        continue
    ts = float(m.group(1))
    if ts <= last_seen:
        continue
    low = block.lower()
    # author UID is the (Uxxxx) in the header
    am = re.search(r"\((u[0-9a-z]+)\)", header.lower())
    author_uid = am.group(1) if am else ""
    is_join = "has joined the channel" in low
    authored_by_computer = (author_uid == computer_uid)
    addresses_computer = (computer_uid in low) or ("@computer" in body.lower())
    if (not is_join) and (not authored_by_computer) and addresses_computer:
        fire = True

sys.exit(0 if fire else 1)
PY
exit $?
