# Cross-thesis Lessons

Append every confirmed pattern. Seeder reads this before proposing new theses.

## L-001 (2026-05-18) — Macro features fail at daily horizon on single names
From prior backtest_v2/ work: VIX, EPU, yield-change features carry near-zero IC on RDDT daily moves. Stop using them as primary signals for tactical names. They may still gate regime overlays.

## L-002 (2026-05-18) — Attention proxies beat sentiment proxies
Google Trends volume and stock-own-volume z-scores beat Fear & Greed and AAII bull/bear for daily prediction on social-platform names. Prioritize attention-construction features over polled-sentiment features.

## L-003 (2026-05-18) — Idiosyncratic catalysts dominate
On RDDT, 13 RDDT_IDIO events drove the entire +0.07 IC of M3. Future theses should pre-flag events and run conditional-on-event backtests, not always-on regressions.

## L-004 (open) — Earnings drift not yet isolated
Need a clean test of whether RDDT alpha is just post-earnings drift in disguise. Iteration 1 of event_conditional_rddt will resolve.

## L-005 (2026-05-18) — Attention spikes on RDDT predict INTRADAY FADES, not rallies
Iteration 1 of event_conditional_rddt killed: long-side on (event_window ∨ vol_z>2 + basket positive) produces Sharpe -3.13 OOS. Same signal short-side has 67% hit rate, -2.5% mean open-to-close. **Update prior L-002**: attention proxies on RDDT are sign-flipped for next-day longs — they identify exhaustion tops, not entry points. Implication: future "high-attention" theses on retail names should pre-register direction explicitly and not assume momentum continuation.

## L-006 (2026-05-18) — Pre-registered conviction bar worked
The 6/10 ARMING gate prevented opening a paper position that would have lost 44% on $50K of paper capital. Net saved: ~$22,000 of paper P&L vs an unguarded approach. Keep the gate strict.

## L-007 (2026-05-18) — Meta-orchestrator must distinguish PR-file existence from PR-iteration completion
HPR-001 reasoning pass caught that 3 of 5 PR-001.md files were scaffolder stubs (placeholders intact), miscounted as failed iterations. E-CAP-03 and E-REG-02 both fired falsely. Fixed via template-stub filter in run_evals.py. Generalizable principle: every eval must distinguish "artifact present" from "artifact populated with real reasoning." Audit all future evals against this distinction.

## L-008 (2026-05-18) — Cron task descriptions must reference real CLI commands
First heavy iterator cron firing failed with "orchestrator.py does not support 'iterate'" because the task description assumed a CLI verb that didn't exist. Generalizable principle: any cron task description should be written as if a fresh agent will execute it with zero context — every command must be copy-pasteable and exist in the codebase at the time the cron fires. Built scripts/iterate.py as a thin convenience wrapper (prepare → subagent does work → finalize) so future iteration crons have a single unambiguous entry point. Also caught by the system as designed: the cron escalated rather than silently failing, which let the user surface it.

## L-009 (2026-05-18) — Convenience wrappers > inline procedural cron prose
The iterator cron description is now ~50 lines of prose explaining what to do. A better long-term pattern: every recurring task should be backed by a CLI command that captures the whole procedure (or at minimum, scaffolds it). Prose is brittle; CLI verbs are self-documenting. Friction logged for future infra factory consideration: a generic "playbook runner" that takes a YAML procedure and executes it deterministically.

## L-010 (2026-05-18) — Agent-layer vs shell-layer must be explicit in every cron task
Second iterator-cron failure: packet listed `memory_queries_to_run` and the cron interpreted them as shell commands. memory_search is an AGENT tool, not a CLI. Generalizable principle: any cron task description must explicitly distinguish (a) commands the agent runs via its built-in tool layer (memory_search, run_subagent, send_notification, etc) from (b) shell commands invoked via bash. Renamed packet field to `memory_queries_for_agent_layer` with a `note` field clarifying the distinction. Future packets and cron-task descriptions should use parallel naming conventions for any agent-layer vs shell-layer split.

## L-011 (2026-05-18) — Cron-fired agents do NOT have run_subagent / memory_search / memory_update
Third iterator escalation: the cron-fired background agent has only shell, file, and external-tool wrappers. Agent-layer tools (memory_search, memory_update, run_subagent) are NOT available in this execution context. The fix was to build scripts/backtest_runner.py — a fully self-contained shell pipeline that does the entire iteration (prepare → backtest → 3 falsifiers → PR write → finalize → release) without any agent-layer dependency. This is also better architecturally: deterministic, repeatable, no LLM-in-the-loop noise.

## L-012 (2026-05-18) — Shell-executable iteration beats agent-spawning iteration for the common case
After three iterator-cron failures across two architectures (orchestrator.py iterate vs. agent-layer subagent spawn), the right design is: cron does the common-case 80% in pure shell, agent-layer ticks (interactive sessions or higher-context crons) handle the analytical 20%. The shell runner is now the default; the agent path is the upgrade. Both can coexist: the weekly meta-eval cron uses agent-layer reasoning, but the hourly iterator should not.

## L-013 (2026-05-18) — Persistent data cache + event calendars unblock historical sweeps
Overnight sweep cron escalated because no historical data was on disk and no frontier.json existed. Built three new pieces: scripts/data_fetcher.py (persistent yfinance + FRED cache under data/cache/), data/events/fomc_history.csv + cpi_history.csv (134 + 75 events), scripts/historical_sweep.py (BH-corrected event-study runner), scripts/frontier.py (surviving-tuples writer). First real sweep: 40 FOMC events × SPY/TLT/GLD, T-1 to T+5. SPY shows mean +0.6% post-FOMC (hit 65%, uncorrected p=0.14, NOT BH-significant). The system correctly says "interesting lead, not deployable" — exactly the multiple-testing discipline we want.

## L-014 (2026-05-18) — Sweep results are leads, not theses
A BH-survivor from historical_sweep.py is a starting point — t-stat on event-window returns, no entry/exit logic. The right pipeline is: sweep → if survivor, scaffold a new SEEDED thesis with the structure encoded → iterator cron picks it up and runs full backtest_runner. Don't ARM directly from sweep output.

## L-015 (2026-05-18) — Single source of truth for "what is a thesis directory"
Iterator picked up `runs/SWEEPS/` as a fake thesis because every script walking `runs/` had its own ad-hoc filter (some checked STATUS, some checked __pycache__, none agreed). Fixed by extracting scripts/_thesis_dirs.py with `is_thesis_dir()` and `list_thesis_dirs()`. Every script that walks runs/ now imports from here. Generalizable principle: when N scripts each implement the same predicate, that predicate WILL drift and produce a bug. Extract early.

- NVDA on FOMC_decision (runs/SWEEPS/20260519_0711/sweep_results.json): mean=0.0358, t=3.13, q_bh=0.0086, hit=0.700
- META on FOMC_decision (runs/SWEEPS/20260519_0711/sweep_results.json): mean=0.0282, t=2.79, q_bh=0.0131, hit=0.575

## L-016 (2026-05-19) — Two cascading verdict bugs masked all real signal
For 16 hours the cron infrastructure ran flawlessly but produced zero meaningful output, masking two stacked bugs:
1. Python truthiness: `(p_value or 1) < 0.05` → when `p_value == 0.0`, evaluates `(1) < 0.05 = False` → strong placebo results never reached the ARM gate.
2. Overlapping returns: `fwd = pct_change(N).shift(-N)` creates N-day-ahead returns placed on each calendar day; treating each as daily P&L over-compounds by ~N×, producing Sharpe 4.2 with -98% drawdown and 393,674× total return — pure artifact.
Fix: explicit None-check on p_value, and non-overlapping sampling `pnl_per_day.iloc[::N]` with periods_per_year scaling. Plus sanity rejection of total>100× or Sharpe>5 on n<100 periods.
Generalizable principle: any "amazing result" should be presumed bug until proven otherwise. The system's response to its first arm-eligible result should be increased skepticism, not relief.
- 2026-05-20T06:59:03Z — FOMC (t-1..t+5): NVDA mean=+3.58% (t=3.13, q=0.0087, hit=0.70) and META mean=+2.82% (t=2.79, q=0.0131, hit=0.575). See runs/SWEEPS/20260520_0658/sweep_results.json
- 2026-05-20T10:57Z sweep-survivor: NVDA on FOMC_decision window[-1,+5] ( t=3.132	 q=0.00865	 hit=0.7); results: runs/SWEEPS/20260520_1057/sweep_results.json
- 2026-05-20T10:57Z sweep-survivor: META on FOMC_decision window[-1,+5] ( t=2.793	 q=0.01307	 hit=0.575); results: runs/SWEEPS/20260520_1057/sweep_results.json
- SURVIVOR: SPY around earnings (derived calendar) window[-1,+5]: t=2.911, q=0.00903, hit=0.80, mean=0.0192 | runs/SWEEPS/20260521_0249/sweep_results.json
- SURVIVOR: TLT around earnings (derived calendar) window[-1,+5]: t=-2.256, q=0.04015, hit=0.20, mean=-0.0103 | runs/SWEEPS/20260521_0249/sweep_results.json
- SURVIVOR: QQQ around earnings (derived calendar) window[-1,+5]: t=3.095, q=0.00985, hit=0.90, mean=0.0273 | runs/SWEEPS/20260521_0249/sweep_results.json

## L-017 (2026-05-21) — Meta-orchestrator's persistent signal can be a regex bug
The deep meta-orchestrator drafted 3 consecutive HPRs against pr_format (E-REG-02 fails 36→98, E-REG-03 39→101). The "bottleneck" was a regex mismatch: deep_iterate.py wrote falsifiers but called them "Falsifier: random-label placebo" rather than using the keyword "falsifier". Real fix took 2 minutes (template + backfill). Lesson: meta-orchestrator persistence can mean either (a) real binding constraint, or (b) measurement bug. Treat 3+ consecutive HPRs on the same component as "go look manually". Self-check: every regex eval should be unit-tested against the actual writers.

## L-018 (2026-05-21) — Sweep BH-survivors are leads, not always-on strategies
NVDA had q=0.009, hit 70% on FOMC T+1..T+5. When we tested it via continuous price_momentum strategy on NVDA daily 5y, Sharpe 1.16 but placebo p=0.94 → KILL. The placebo correctly distinguishes "NVDA went up, so any NVDA-long strategy looks good" from "this signal predicts NVDA's outperformance on specific days". L-018 = L-001 validated: sweep findings require event-conditional iteration, not always-on. Until that iterator exists, swept_* theses will all fail with high placebo p-values, which is the correct answer.
