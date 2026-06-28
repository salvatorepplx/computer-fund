#!/bin/bash
set -euo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/watch_trigger.sh"
COMPUTER_UID="U08C9BB5A2G"

json_for_messages() {
  python3 - "$1" <<'PY'
import json
import sys
print(json.dumps({"messages": sys.argv[1]}))
PY
}

assert_parse() {
  local name="$1"
  local expected="$2"
  local last_seen="$3"
  local messages="$4"
  local actual
  actual=$(json_for_messages "$messages" | bash "$SCRIPT" --parse-slack "$last_seen" "$COMPUTER_UID")
  if [ "$actual" != "$expected" ]; then
    printf 'FAIL %s: expected %s, got %s\n' "$name" "$expected" "$actual" >&2
    exit 1
  fi
  printf 'ok %s -> %s\n' "$name" "$actual"
}

qualifying_message=$'=== Message from Sal (U123ABC) ===\nMessage TS: 1782467000.123456\n@computer please review this proposal\n'
old_qualifying_message=$'=== Message from Sal (U123ABC) ===\nMessage TS: 1782466000.123456\n@computer please review this proposal\n'
computer_own_message=$'=== Message from Computer (U08C9BB5A2G) ===\nMessage TS: 1782467000.123456\n@computer armed update\n'
join_notice=$'=== Message from New User (U999ABC) ===\nMessage TS: 1782467000.123456\nNew User has joined the channel and says @computer\n'

assert_parse "new qualifying mention fires" "fire" "1782466000.000000" "$qualifying_message"
assert_parse "old qualifying mention skips" "skip" "1782467000.123456" "$old_qualifying_message"
assert_parse "computer own message skips" "skip" "1782466000.000000" "$computer_own_message"
assert_parse "join notice skips" "skip" "1782466000.000000" "$join_notice"
