# Cron Topology — current working schedule

> Provisional. The meta-orchestrator may propose changes to any of these.

## Active recurring tasks (7)

| # | Name | Cron (UTC) | Mode | What it does |
|---|------|------------|------|----|
| 1 | hourly explorer (cheap) | `35 * * * *` | cheap | KILL_CHECK or EXPLORE or MTM_ONLY — no subagent spawning |
| 2 | hourly iterator (heavy) | `6 * * * *` | heavy | drain SEEDED queue → ITERATE → ARM/KILL. Lock-protected |
| 3 | overnight historical sweep | `41 2,4,6,8,10 * * 2-6` | heavy | full historical replay across past events; markets closed |
| 4 | weekend deep mining | `57 */2 * * 0,6` | heavy | factor-zoo replication, cross-sectional sweep, or adversarial critic |
| 5 | daily mini meta-eval | `31 3 * * 2-6` | cheap | refresh evals, drain notification queue, day-over-day drift check |
| 6 | EOD MTM + digest | `15 20 * * 1-5` | cheap | mark-to-market + portfolio summary + coalesced digest |
| 7 | weekly meta-eval + self-improve | `20 0 * * 1` | heavy | full eval suite + meta-orchestrator deep reasoning + HPR draft |

Approximate weekly throughput:
- ~168 cheap explorer ticks → up to 168 new hypotheses scaffolded
- ~168 iterator ticks → drain the queue; capped by subagent throughput
- ~25 overnight sweep ticks → historical replays
- ~24 weekend deep-mining ticks → anomaly replications + critiques
- 5 daily meta-evals, 1 weekly deep meta-eval
- 5 EOD MTMs

Subagent throughput is the practical bottleneck. Each heavy iterator tick that triggers a subagent may take 2–10 minutes; ~6/hour is achievable.

## Concurrency model

- Cheap explorer never spawns subagents → safe at any frequency
- Heavy iterator locks the thesis it works on via `runs/<id>/.lock` (stale after 10min) → never two iterators on same thesis
- Overnight + weekend + weekly are non-overlapping in time
- All crons are idempotent: re-firing a no-op cron does nothing

## Notification budget

`scripts/notify_budget.py` enforces:
- critical (KILL switch, new MERGE, eval regression >25%) → always fires
- high (new ARMED, killed thesis, HPR proposed) → max 6/day
- low → queued, drained into the daily 8pm PT digest

## When to change this

Add a cron if:
- A new artifact type emerges that needs its own cadence
- The hot/deep meta-orchestrator pattern proves out at another layer

Remove a cron if:
- Two crons reliably do the same thing at different cadences (consolidate)
- A cron has fired 50+ times without producing material output

Renew this file whenever the schedule changes.

---

## Open questions

- 1-hour cron minimum is a platform constraint. The session-resident continuous explorer (`scripts/continuous.py`, see below) bypasses this when needed.
- Is `35` (explorer) vs `6` (iterator) the right offset, or should iterator fire shortly after explorer to drain its output?
- Should the overnight schedule shift across the week to avoid blocking out the same overnight hours every day?
- The weekend deep-mining rotation (factor-zoo / cross-sectional / critic) is hand-coded — should it be priority-driven?
