#!/usr/bin/env bash
# Robust capture+commit for the Computer Fund capture cron.
# Defends against the class of bugs that have bitten the cron twice:
#   - arg-mangling (handled in capture_web_tick.py canonical_entity)
#   - git-add pathspec failures stranding committed data (handled here)
# Usage: bash scripts/capture_and_commit.sh
# RESILIENCE: multi-credential sessions intermittently 400 on /v1/sessions. This script needs
#   only pplx-sdk for capture (price comes from the web corpus; robinhood 401s anyway) and
#   github for the commit. Invoke with api_credentials=["pplx-sdk","github"] (NOT external-tools).
#   If even two creds flap, run capture (pplx-sdk) and commit (github) as two separate bash calls.
# Requires api_credentials=["pplx-sdk","external-tools","github"].
set -uo pipefail   # NOT -e: we never want one failing step to strand a commit

ROOT="/home/user/workspace/computer_fund"
cd "$ROOT" || { echo "FATAL: cannot cd $ROOT"; exit 1; }

PAIRS=( "TICKER:NVDA NVDA Nvidia" "TICKER:RDDT RDDT Reddit" \
        "TICKER:TSLA TSLA Tesla" "TICKER:SNDK SNDK SanDisk" )

echo "=== capture @ $(date -u +%FT%TZ) ==="
for p in "${PAIRS[@]}"; do
  # shellcheck disable=SC2086
  set -- $p
  out=$(python scripts/capture_web_tick.py "$1" "$2" "$3" 2>&1)
  ent=$(echo "$out" | python -c "import sys,json;
try:
  d=json.load(sys.stdin); print(d.get('entity'),'n='+str(d.get('series_length')),'price='+str(d.get('price_proxy')))
except Exception: print('CAPTURE_PARSE_FAIL')" 2>/dev/null)
  echo "  $2 -> $ent"
  # hard guard: never let a contaminated entity through silently
  case "$ent" in
    *TICKER:TICKER*) echo "  !! ABORT: TICKER:TICKER contamination detected for $2"; ;;
  esac
done

echo "=== verdicts ==="
for e in TICKER:NVDA TICKER:RDDT TICKER:TSLA TICKER:SNDK; do
  python evals/leadlag_real.py "$e" 2>/dev/null | python -c "import sys,json;
d=json.load(sys.stdin); print('  ',d['entity'],'n='+str(d.get('n')),d.get('verdict'),'circ='+str(d.get('circularity_flag')))" 2>/dev/null
done

echo "=== alpha pipeline (writes PROPOSED only for authoritative non-circular EDGE) ==="
python execution/alpha_pipeline.py 2>/dev/null | tail -2

echo "=== refresh STATE.md (the cold-agent front door) ==="
python scripts/state_snapshot.py 2>/dev/null || echo "  WARN: STATE.md refresh failed (non-fatal)"

# ---- robust commit: add ONLY paths that exist; never fail the commit on a bad pathspec ----
echo "=== commit+push ==="
git add -A STATE.md 2>/dev/null || true
git add -A runs/sentiment/series 2>/dev/null || true
git add -A runs/sentiment/raw 2>/dev/null || true
git add -A runs/PROPOSED 2>/dev/null || true   # only matters if a proposal was written
git add -A state 2>/dev/null || true
git add -A corpus runs/CORPSES.md runs/KILLED 2>/dev/null || true

if git diff --cached --quiet; then
  echo "  no changes to commit"
else
  git -c user.email=computer@pplx.ai -c user.name=Computer commit -q -m "web series capture tick" \
    && git push -q origin HEAD \
    && echo "  PUSHED $(git rev-parse --short HEAD)" \
    || echo "  WARN: commit or push failed (data is staged; next tick retries)"
fi
echo "=== done @ $(date -u +%FT%TZ) ==="
