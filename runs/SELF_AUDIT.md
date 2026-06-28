# Computer Fund — SELF-AUDIT (every axis under scrutiny)
_Generated 2026-06-28T02:32:44.309353+00:00. RSI mandate: no axis sits unimproved._

| axis | health | note |
|---|---|---|
| sim | 0.7 | sim PARKED by decision (RETIRED.md): off critical path, re-activate only if a future thesis needs it |
| graph | 0.7 | graph PARKED by decision (RETIRED.md): off critical path, re-activate only if a future thesis needs it |
| cron_tasks | 0.7 | cron task prompts now self-orienting (read STATE.md/lessons first, act-not-log); watch cron prompt not yet upgraded to same standard |
| signal | 0.8 | web_sentiment present=True tested=True; single source (no cross-source corroboration yet) |
| lessons | 0.8 | lessons.md age=0.0h; capturing bug-classes + findings |
| universe | 0.83 | 6 configured names; 6 wired series files; 4 observed series with rows (120 rows total); pending/no rows: CRM, PATH |
| capture_infra | 0.85 | hardened single wrapper=True; transient 400/502 still skips ticks (no in-script session retry possible) |
| state_memory | 0.85 | STATE.md age=0.2h (front door); Computer memory holds governance+technical_state+lessons |
| meta_improvement | 0.85 | self-audit exists=True, scheduled hourly (cron 253ff74b), all cron prompts self-orienting+never-idle |
| verdict | 0.9 | lead-lag + permutation null present=True; de-burst+circularity+p-value gates live |
| pipeline | 0.9 | alpha_pipeline present+tested=True (e2e dryrun 18/18) |
| safety | 0.95 | safety rails present+tested=True; allowlist/sizing/kill verified to fire |
| pr_queue_drain | 0.95 | queue drained: 0 actionable PRs open |
| pr_queue | 1.0 | Teammate PR queue DRAINED (0 non-draft open PRs) |

## Weakest axis -> forcing function
**sim** (health 0.7): sim PARKED by decision (RETIRED.md): off critical path, re-activate only if a future thesis needs it
Next improvement must target this axis (or justify in writing why another axis is higher-leverage).
