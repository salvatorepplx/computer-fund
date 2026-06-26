"""Promote historical-sweep BH-survivors to SEEDED theses for the iterator.

Reads every sweep_results.json under runs/SWEEPS/, finds BH-survivors that haven't
already been turned into a thesis, scaffolds a thesis directory with a real
hypothesis structure based on the survivor's event/ticker/window, and adds STATUS.

This closes the pipeline gap: sweeps produce leads, leads become theses, theses get
deep-iterated.

Usage:
    python sweep_to_thesis.py            # scan + promote any new survivors
    python sweep_to_thesis.py --dry      # show what would be promoted
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone, date

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"; SWEEPS = RUNS / "SWEEPS"
sys.path.insert(0, str(ROOT/"scripts"))
from reasoning_log import log as rlog

def _slugify(ticker, event_calendar, window_pre, window_post):
    cal = Path(event_calendar).stem
    return f"swept_{ticker.lower()}_{cal}_tminus{window_pre}_tplus{window_post}".replace("-","_")

def scan_survivors():
    """Yield (ticker, calendar, window, metrics, source_path) for every BH-pass row."""
    if not SWEEPS.exists(): return
    for sdir in sorted(SWEEPS.iterdir()):
        result_path = sdir / "sweep_results.json"
        if not result_path.exists(): continue
        try: d = json.loads(result_path.read_text())
        except Exception: continue
        cal = d.get("event_calendar","unknown")
        wp, wpos = d.get("window",[1,5])
        for t, m in d.get("aggregate", {}).items():
            if m.get("bh_pass"):
                yield {"ticker": t, "event_calendar": cal, "window_pre": wp,
                       "window_post": wpos, "metrics": m, "source": str(result_path)}

def already_promoted(slug):
    return (RUNS / slug).exists()

def promote(survivor: dict, dry=False):
    s = survivor
    slug = _slugify(s["ticker"], s["event_calendar"], s["window_pre"], s["window_post"])
    if already_promoted(slug):
        return {"already_promoted": slug}
    if dry: return {"would_promote": slug, "survivor": s}

    tdir = RUNS / slug; tdir.mkdir(parents=True)
    (tdir / "STATUS").write_text("SEEDED")

    direction = "long" if s["metrics"]["mean"] > 0 else "short"
    cal_name = Path(s["event_calendar"]).stem
    thesis_md = f"""# Promoted from historical sweep · {slug}

**Created**: {date.today().isoformat()}
**Source**: {s['source']}
**Status**: SEEDED

## Origin
Historical sweep across {cal_name} events found {s['ticker']} as a BH-corrected survivor:
- Mean event-window return: **{s['metrics']['mean']:.4f}** ({direction})
- t-stat: **{s['metrics']['t_stat']}**, BH q-value: **{s['metrics']['bh_q']}**
- Hit rate: **{s['metrics']['hit_rate']}**, n_events: **{s['metrics']['n']}**
- Window: T−{s['window_pre']} to T+{s['window_post']}

## Hypothesis tuple (for deep_iterate)
- **signal**: `price_momentum`
- **universe**: `singleton_{s['ticker'].lower()}`
- **horizon**: `{s['window_post']}d`
- **structure**: `{direction}_only`

## Notes
This thesis represents a HISTORICAL event-window pattern, not a continuously-applicable
signal. The deep_iterate runner may give it a low Sharpe because the pattern only
fires on event days. A more accurate test would be event-conditional entry/exit
restricted to the {cal_name} window — which deep_iterate doesn't yet implement.

For now, this serves as a placeholder that records the discovery and can be
hand-promoted to a fuller event-conditional study later.
"""
    (tdir / "thesis.md").write_text(thesis_md)
    prs_dir = tdir / "prs"; prs_dir.mkdir()
    (prs_dir / "PR-001.md").write_text(f"""# PR-001: {slug} · seeded from sweep

**Date**: {date.today().isoformat()}
**Source**: {s['source']}

This is the seed PR. The actual iteration will happen via deep_iterate.py.

## Survivor metrics (input)
{json.dumps(s['metrics'], indent=2)}
""")
    rlog("sweep_to_thesis", "decision",
         f"promoted {s['ticker']} on {cal_name} → SEEDED thesis {slug}",
         f"t={s['metrics']['t_stat']} q={s['metrics']['bh_q']} hit={s['metrics']['hit_rate']}",
         "deep_iterate cron should pick this up next firing.")
    return {"promoted": slug, "survivor": s}

def main():
    p = argparse.ArgumentParser(); p.add_argument("--dry", action="store_true")
    a = p.parse_args()
    survivors = list(scan_survivors())
    # Dedup: same ticker × calendar × window
    seen = set(); unique = []
    for s in survivors:
        key = (s["ticker"], s["event_calendar"], s["window_pre"], s["window_post"])
        if key in seen: continue
        seen.add(key); unique.append(s)
    results = [promote(s, a.dry) for s in unique]
    print(json.dumps({"scanned": len(survivors), "unique": len(unique),
                      "results": results}, indent=2, default=str))

if __name__ == "__main__": main()
