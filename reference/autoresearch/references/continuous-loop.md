# Continuous Autoresearch Loop

The skill runs as a stateless, memory-backed loop. Thread length doesn't matter — every tick reads state from disk + long-term memory and decides one action.

## State Layout (all on disk + memory)

```
autoresearch/
├── runs/
│   ├── <thesis_id>/
│   │   ├── thesis.md            # one-paragraph framing
│   │   ├── CHANGELOG.md         # one-line per PR
│   │   ├── STATUS               # single word: SEEDED|ARMED|MERGED|ITERATING|KILLED|PAUSED
│   │   ├── prs/PR-NNN.md        # full PR history
│   │   ├── paper_book.csv       # entries (truth)
│   │   ├── paper_pnl.csv        # daily MTM
│   │   └── data/, results/
│   ├── PORTFOLIO.md             # live roll-up
│   ├── CORPSES.md               # killed-thesis log
│   ├── BACKLOG.md               # candidate theses queue
│   └── QUEUE.json               # next-action queue (priority-sorted)
└── corpus/
    ├── catalysts.md             # upcoming dated catalysts (CPI, FOMC, earnings)
    ├── universe.md              # tracked tickers/markets
    └── lessons.md               # cross-thesis learnings (informs new seeds)
```

Long-term memory complements files:
- `memory_update`: every MERGE, KILL, and high-signal lesson. Format: "Remember that autoresearch merged/killed thesis <id>: <one-liner>, key reason <X>."
- `memory_search`: every tick reads memory for related prior work before iterating.

## Pick-Next-Action Algorithm

On each tick (hourly cron), the orchestrator picks ONE action by priority:

1. **KILL-SWITCH check** (always first). Run `paper_engine.py kill_check`. If any thesis breached, write KILL PR and stop.
2. **Stale ARMED thesis** (≥ 5 trading days since last PR, not MERGED yet) → spawn iteration N+1.
3. **MERGED thesis weekly re-falsification** (≥ 5 trading days since last falsification) → spawn re-falsification.
4. **BACKLOG seeding** (if < 3 active theses) → run thesis_seeder to discover a new candidate from corpus/catalysts.
5. **Fresh paper marking** (if no other action) → MTM all positions, update PORTFOLIO.md, exit silently.

Each tick does exactly ONE of the above and exits. This keeps each cron run cheap and bounded.

## Memory-Backed Continuity

Every tick begins with:
1. `memory_search` queries: `["What thesis_ids has autoresearch merged or killed?", "What recent market catalysts has the user flagged?", "What features or factors are known to have look-ahead leaks in autoresearch?"]`
2. Read `corpus/lessons.md` for cross-thesis patterns.
3. Read `runs/QUEUE.json` for current queue.

Every tick ends (on action completion) with:
1. Append to `CHANGELOG.md` of the affected thesis.
2. If MERGE / KILL / armed new thesis: `memory_update` with the one-liner.
3. Re-sort `QUEUE.json` based on next priorities.

## Frequency

- **Hourly during market hours (9-16 ET weekdays)**: research loop ticks. Each tick does at most one PR iteration or one seeding. Limits to ~7 actions/day during market hours.
- **4:15 PM ET weekdays**: paper-trade MTM + portfolio digest. Sends in-app notification ONLY if portfolio delta is meaningful (>1% book P&L change OR any kill switch tripped OR new MERGE).
- **9:00 AM ET weekdays**: catalyst scan + thesis seeding. Reads upcoming catalysts (earnings, CPI, FOMC) and queues thesis candidates for the day.

## Thesis Seeder (new module)

`scripts/seed_thesis.py` runs as the BACKLOG action. It:
1. Reads `corpus/catalysts.md` for upcoming events (earnings, macro prints, expiries).
2. Reads memory for tickers/themes the user has shown interest in.
3. Drafts 1-3 candidate thesis seeds in `runs/BACKLOG.md`.
4. The top seed by edge-confidence becomes a new `runs/<thesis_id>/` directory next tick.

## Action Budget per Tick

To keep cost predictable each cron run is allowed at most:
- 1 backtest run (≤ 2 min wall-clock)
- 1 reviewer subagent spawn
- 5 data fetches
- 1 paper_engine command

If the planned action exceeds this, split across multiple ticks via QUEUE.json.
