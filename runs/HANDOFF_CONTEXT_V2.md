# Computer Fund — PROD MIGRATION HANDOFF (V2)

_Committed as the first durable write of the prod-born thread, per the V2 handoff instruction.
The prior thread (session 174426aa, staging URL staging.perplexity.ai/computer/tasks/1de87c54-6201-46ec-a8ac-5490b3c94b33)
hit a wedged E2B sandbox (instance 019f0ba7, ~6 "failed to provision" failures, host e2b.staging.p.perplexity.ai;
diagnostic 174426aa). The repo is source of truth; nothing was lost. This prod thread re-homes the heartbeat._

## 0. Why this thread exists
The staging thread's execution sandbox wedged. A prod-born thread runs its sandbox + crons on prod infra.
Re-home the heartbeat here and resume.

## 1. Boot sequence
- load skills: computer-fund-operating-doctrine (id ebc09692), autoresearch, finance/finance-markets, task-scheduling.
- Clone + orient: `gh repo clone salvatorepplx/computer-fund`. HEAD at/after 9d18c1b. Read STATE.md
  (verify header HEAD vs git log), runs/HANDOFF_CONTEXT.md, CHARTER.md, CONSTITUTION.md, corpus/lessons.md,
  runs/SELF_AUDIT.md, runs/QUEUE.json.
- Reconcile via live commands: `gh pr list --state open`; `python evals/leadlag_real.py TICKER:NVDA`.

## 2. Re-home the heartbeat (the staging crons must not double-fire the dead/old sandbox)
Recreate all three via pplx-tool schedule_cron in THIS prod thread:
- capture `*/10 * * * *`
- watch `*/15 * * * *` (programmatic trigger scripts/cron_triggers/watch_cron_trigger.sh)
- self-audit `29 * * * *`
Exact task prompts live in runs/CRONS.md — reuse them. Then delete the prior crons
(80400d62 capture, 2dff0abe watch, 98c3d3f3 self-audit).

### RECONCILIATION FINDING (prod thread, 2026-06-27 21:0x PDT) — IMPORTANT
At handoff-execution time, the three crons 80400d62 / 2dff0abe / 98c3d3f3 were NOT stranded —
they surfaced in this prod session's cross-session cron list and were FIRING SUCCESSFULLY
(capture+watch last_run 8:23-8:24 PM PDT, self-audit 8:29 PM PDT; run_counts 7/7/3; future
next_run times set). They are owned by session 174426aa (the "staging" thread). Per Sal's
explicit instruction, the prod thread still re-creates the heartbeat here (owned by this thread)
and deletes the old three to consolidate ownership in prod.

## 3. The TWO live blockers (highest priority after PR drain)

### Blocker A — RDDT PROPOSED artifact unverified + malformed
runs/PROPOSED/battle-RDDT-leadlag-2026-06-28.json: EDGE, best_lag=2, corr=0.6522, circular=false,
conviction 0.49.
- created_at (2026-06-28T03:25:22.183347+00:00) fails the ISO8601-UTC validator (the one red eval,
  eval_proposed_artifact_validator). Root cause: execution/alpha_pipeline.py `_now()` emits
  isoformat() with microseconds and +00:00 offset. Fix to emit ...Z without microseconds; patch
  the artifact; confirm the eval passes.
- The permutation p-value is NOT in the artifact and is unverified. Trade gate = EDGE AND
  non-circular AND permutation p<=0.10. Run evals/leadlag_permutation.py TICKER:RDDT. If p>0.10,
  withdraw to runs/KILLED/ with a corpse note — do NOT arm.
- SUSPICION (chip on shoulder): this EDGE appeared right after scorer-bias fixes (#46/#47) changed
  the signal mid-thesis. A fresh edge after a signal change is a bug suspect. Compare score
  distribution before/after those commits. (See corpus/lessons.md 2026-06-28 over-bullish regex finding.)
- NOTE: STATE.md (auto-generated) caches perm=EDGE_SURVIVES_NULL p=0.0345 sig=True for RDDT. Do NOT
  trust the cache; trust a fresh live permutation run.

### Blocker B — NO trade executor (the bigger structural gap)
Pipeline writes PROPOSED but there is no PROPOSED->ARMED->place entrypoint. Build
scripts/promote_and_place.py: validated PROPOSED -> Charter review gates (live quote, account
696264779 safety via assert_account_allowed, Phase-0 sizing caps, kill-switch) -> write runs/ARMED/
-> place via the Robinhood connector (programmatic-tool-calling surface). Account allowlist
696264779 ONLY; Roth/margin abort. No human per-trade confirm — the review gates ARE the safety.

## 4. Open PR queue to drain (Obligation A)
At handoff: #48 (gate proposals on cross-sectional breadth, draft), #49 (production AI-code
discipline), #50 (production-quality commenter RFC), #51 (AGI production standards inventory),
#52 (diagnostic feedback loop RFC), #54 (record TSLA permutation-noise corpse, draft). Read each
diff, verify rails (propose-only must not touch execution/ / state/ / ARMED / order paths; gating
evals must not hard-assert against the live series), merge or request-changes.

## 5. Owed coordination with Teammate (Slack #sal-teammate, C0BCXKG835M, thread ts 1782466134.541989)
- It needs the expected account/settlement-data shape + fail-closed semantics for settlement-aware
  buying power, and whether Computer owns that implementation. Answer it.
- It posted queue-reconciliation notes (its offline leadlag_real probes disagree with runs/QUEUE.json
  — Computer owns queue state). Reconcile and confirm.
- It's drafting an open-web tool-split RFC (PR #44 landed the HPR stub). Constraints: capability to
  LEARN is wide for both via curl/gh/pip reading the open web (sandbox CAN reach); authority to ACT +
  own the observed signal series is Computer-only. Dispose its RFC PR when it lands.
- STRUCTURAL FIX: add a "Teammate-blocked-on-Computer" disposition axis to scripts/self_audit.py and
  the watch cron prompt that scans #sal-teammate for "blocked pending Computer" notes and treats them
  as P1 — same way pr_queue_drain treats open PRs. This is the gap that let Teammate sit blocked.

## 6. Architecture question (Sal raised it) — via PSI, read-only
Does ppl-ai/agi expose a computer/asi CLI or programmatic agent-spawn entrypoint invokable from the
sandbox? Goal: replace the fragile N-cold-boot-cron heartbeat with one durable driver that does cheap
deterministic work (capture, permutation, commit) directly in Python and invokes a Computer-agent run
only for judgment steps (verdict disposition, ARMED review). Dispatch once compute is healthy.

## 7. State of the world (grounded at handoff)
Repo HEAD 9d18c1b. NVDA n_spaced ~30, EDGE, non-circular, fails permutation (p~0.13-0.19) -> 0
eligible. RDDT proposal written (Blocker A). RDDT/TSLA preliminary, SNDK no-edge. CRM/PATH newly
wired, no rows yet. No trade ever placed. Risk Phase 0. Seed sentiment-leadlag thesis is honestly
dying on the permutation null — the machine working. Signal-quality finding (regex scorer over-bullish;
llm.extract upgrade spiked in runs/spikes/) is the next evolution.

## The LAW (never flexes)
Account allowlist 696264779; review-before-place; Phase-0 sizing; kill-switch; options-L2-only;
no look-ahead; post-trade transparency. confirm_action ONLY for trade placement + destructive ops.
Act, don't ask. Drain the queue every tick. Never end with an unfinished chain. Honest KILL is a win.
