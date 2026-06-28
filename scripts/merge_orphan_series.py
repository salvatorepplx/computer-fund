"""One-shot: merge orphan lowercase series files into canonical TICKER_* files,
dedup by event_id, sort by ts, fix the embedded entity field, remove orphans."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SD = ROOT / "runs" / "sentiment" / "series"

PAIRS = [("nvda", "TICKER:NVDA"), ("rddt", "TICKER:RDDT"), ("tsla", "TICKER:TSLA")]

for low, canon in PAIRS:
    orphan = SD / f"{low}.jsonl"
    target = SD / f"{canon.replace(':', '_')}.jsonl"
    if not orphan.exists():
        continue
    rows = []
    seen = set()
    for path in (target, orphan):  # target first preserves order, orphan adds new
        if path.exists():
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                eid = r.get("event_id")
                if eid in seen:
                    continue
                seen.add(eid)
                r["entity"] = canon  # fix lowercase entity field on orphan rows
                rows.append(r)
    rows.sort(key=lambda r: r.get("ts", ""))
    with target.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    orphan.unlink()
    print(f"{canon}: merged -> {len(rows)} pts (orphan {low}.jsonl removed)")

print("done")
