# Computer Fund — live scheduled tasks (heartbeat)

Recreated 2026-06-28 after the original three crons were lost when the source session's sandbox died.
A cold thread should verify these still exist via `pplx-tool schedule_cron {"action":"list"}`.

- **80400d62 — capture tick** — `*/10 * * * *` (every 10 min). Runs the capture+commit, drains the
  PR queue first (Obligation A), acts on authoritative verdicts. Always-fire programmatic trigger
  (`scripts/cron_triggers/capture_trigger.sh`, exit 0) only unlocks sub-hourly cadence.
- **2dff0abe — watch tick** — `*/15 * * * *` (every 15 min). Programmatic trigger
  (`scripts/cron_triggers/watch_cron_trigger.sh`) fires only on real new activity (Slack @computer /
  ARMED handoff newer than last_seen, OR new open PR / new master commit). Drains PR queue, acts on
  bus messages, else improves the weakest axis.
- **98c3d3f3 — self-audit** — `29 * * * *` (hourly at :29). Runs scripts/self_audit.py (now includes
  the pr_queue_drain axis), writes SELF_AUDIT.md + QUEUE.json, makes one weakest-axis improvement.

All three cron task prompts load `computer-fund-operating-doctrine` first and treat an un-drained
Teammate PR queue as a P1. Cron edits: `pplx-tool schedule_cron` with
api_credentials=["pplx-tool:schedule_cron"].
