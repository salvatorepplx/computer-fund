# Computer Fund Lessons

Durable lessons distilled from killed theses, negative diagnostics, and review findings.
This is the seeder-facing companion to `runs/CORPSES.md`: CORPSES records what died;
this file records what future research should remember before proposing nearby variants.

This file is offline/propose-only. It must not touch Robinhood, live market data,
broker/account/order state, ARMED handoffs, sizing, or trading behavior. Lessons may
reference observed historical data only when provenance is explicit; deterministic
fixtures, simulations, and review notes must stay labeled as such.

## Discipline

When a corpse produces a reusable rule, add a lesson with these required fields:

- **Source corpse**: the `runs/CORPSES.md` entry or other offline artifact that produced the lesson.
- **Reusable lesson**: the general principle, not just a restatement of one failed thesis.
- **Seeder rule**: what future thesis-seeding prompts should prefer, avoid, or require.
- **Meta/eval linkage**: how the lesson should appear in offline review, especially the
  `memory_lessons` axis in `evals/meta_orchestrator.md` or a named deterministic eval.
- **Revisit trigger**: the exact new evidence that should cause the Fund to reconsider the lesson.

## Lessons

### 2026-06-26 — Narrative complexity must earn fidelity

- **Source corpse**: `runs/CORPSES.md` entry "Persistent-network / influencer-cascade simulator variants".
- **Reusable lesson**: realistic-looking sentiment diffusion mechanics are not automatically better;
  simulator changes must improve a named fidelity, lead-lag, or calibration metric.
- **Seeder rule**: future simulator seeds should not propose persistent network state or influencer
  cascades as standalone upgrades. They must name the missing fidelity target and the offline eval
  expected to improve before implementation.
- **Meta/eval linkage**: weekly meta passes should score repeated attempts to reintroduce these variants
  without new evidence as a `memory_lessons` regression; relevant evidence is this file plus
  `runs/CORPSES.md`.
- **Revisit trigger**: observed sentiment trajectory fixtures show a concrete lead-lag or calibration
  failure that the baseline resampled-network simulator cannot represent.

## Entry Template

Copy this block for each future distilled lesson.

```markdown
### YYYY-MM-DD — Short lesson name

- **Source corpse**: Link to `runs/CORPSES.md` entry or other offline artifact.
- **Reusable lesson**: General principle.
- **Seeder rule**: How future thesis prompts should change.
- **Meta/eval linkage**: `memory_lessons` evidence and/or named deterministic eval.
- **Revisit trigger**: Exact new evidence required before changing the lesson.
```

## 2026-06-26 — Substrate swap + burst-vs-time lesson (web_search > finance connector)
- KILLED reliance on finance_ticker_sentiment: 401 UNAUTHORIZED under any load; it is a
  static summarizer, not a moving signal. robinhood get_equity_quotes also 401ing (env-wide
  connector auth blip, not our code). Building lead-lag alpha on those = building on sand.
- NEW substrate: pplx_sdk.search.web (execution/web_sentiment.py). Reliable, no-auth,
  timestamped, MOVES as news moves, and carries explicit parseable readings (Adanos
  "% bullish across N sources", Stocktwits "extremely bearish", Perplexity Finance
  bull/bear split + analyst consensus, "Strong Buy/Sell"). Scorer blends explicit
  readings (high weight) + lexical bull/bear balance + EWMA. Self-tests discriminate
  bull(+0.67)/bear(-0.91)/mixed correctly. Confidence 0.95 on 16-doc corpus vs 0.2-0.65
  single noisy finance fetch. Price proxy now extracted from corpus (median of dense band)
  — reliable, with robinhood as fallback only.
- LESSON (burst vs time): bursting captures builds N fast but NOT real time-variation —
  intraday news corpus is slow-moving, so EWMA converges to a fixed point within a burst.
  Lead-lag on burst data = convergence artifacts (labeled PRELIMINARY, not capital-grade).
  A trustworthy verdict needs TIME-SPACED points (the */30 cron), where news actually
  changes between captures. Burst proved the pipeline end-to-end; cron produces the verdict.
- Equilibria from burst (calibration sanity, matches real narratives): NVDA ~+0.26 (Strong
  Buy but technically weak), RDDT ~+0.40 (Moderate/Strong Buy), TSLA ~+0.07 (range-bound/mixed).

## 2026-06-26 — Split-series bug (caught via cron-result cross-check)
- BUG: capture cron invoked capture_web_tick.py with lowercase bare symbols (nvda/rddt/tsla),
  which wrote to nvda.jsonl etc. — a PARALLEL series from the canonical TICKER_NVDA.jsonl that
  my burst captures used. Two fragmented series, neither feeding the other => silently ~2x'd
  time-to-verdict and corrupted the lead-lag input. Spotted because the cron result reported
  "series now 2 points" while local canonical files had 15 — the discrepancy was the tell.
- FIX: canonical_entity() in capture_web_tick.py normalizes ANY invocation
  (nvda / NVDA / TICKER:NVDA) -> TICKER:NVDA, so the series file is stable regardless of caller.
  Merged orphan points back in (no data lost): NVDA 17, RDDT/TSLA 13. Removed orphan files.
- LESSON: cross-check cron-reported state against ground-truth files every time. A subagent
  cron can invoke a script differently than intended; idempotency must live IN the script, not
  in the caller's discipline. State belongs in canonical files, normalized at the boundary.

## 2026-06-26 — Time-spacing the lead-lag (de-bursting) + small-N honesty
- Added time-spacing to leadlag_real.py: collapse captures <180s apart to the last in
  the cluster, so each retained point is genuine new info. NVDA 17 raw -> 8 time-spaced.
  Drops null-price rows too. Reports both n (spaced) and n_raw_points.
- HONESTY: with n_spaced=4-8 and small lag windows, best_corr trivially saturates to +/-1.0.
  That is small-N artifact, NOT edge. Probe correctly keeps verdict PRELIMINARY (non-authoritative
  until n>=24). Bursting cannot fix this — only TIME (the */30 cron) adds real spaced points.
- IMPLICATION: stop bursting for "depth"; it inflates n_raw but not n_spaced. The verdict is
  gated on wall-clock accumulation. Patience is the correct move now, not more captures.

## 2026-06-26 — Circularity / lookahead guard (chip-on-shoulder self-audit)
- Self-audited: is the sentiment score circular with price (reading price action back as
  "sentiment")? Contemporaneous corr(sentiment_level, price_level): RDDT +0.007, TSLA +0.034
  (clean, distinct signal) but NVDA +0.62 (yellow flag — possible mild circularity, inflated
  by early burst points spanning a wide price range).
- ADDED circularity guard to leadlag_real.py: compute contemp_corr; if |corr|>=0.6 set
  circularity_flag and BLOCK an EDGE verdict regardless of lead-lag. A possibly-circular
  signal must not masquerade as alpha. NVDA now flagged; RDDT/TSLA clean.
- Conservative by design: better to under-claim edge than trade on lookahead. Expect NVDA's
  contemp_corr to settle as genuinely time-spaced points replace burst inflation.

## 2026-06-26 — Price extraction hardening (SNDK exposed it)
- BUG: corpus price extractor (blind median of $-figures) failed badly on SNDK:
  bimodal corpus (small EPS/%/target figures + real ~$2316 quote) -> median landed at $112,
  then $21. Also: SNDK trades ~$2316, ABOVE the old $2000 sane-band cap -> real price excluded.
- FIXES (all generic, not SNDK-specific):
  1. Context-aware scoring: prefer $-figures with cents + near price-cue words ("closed at",
     "trading at", "shares", "current") + near the ticker. NVDA/TSLA/RDDT now spot-on.
  2. Raised band cap 2000 -> 5000; added a dedicated "stock price quote today closed at" query
     so every name gets a clean live-quote doc in its corpus.
  3. Series-consistency gate: reject a corpus price >35% off the last good price for that name
     (real intraday moves between captures rarely exceed that) -> fall back to broker, else hold
     last. SNDK's noisy price correctly REJECTED (held_last) instead of corrupting the series.
- LESSON: financial text is full of non-price $-figures; never trust a blind aggregate. Gate
  new data against history. A bad price proxy silently corrupts the lead-lag — data quality is
  upstream of every verdict.

## 2026-06-26 — Accelerate the verdict honestly (cadence, not bursting)
- Confronted the real bottleneck: authoritative lead-lag needs ~24 time-spaced pts; at */30
  that's ~8h. The goal is the FIRST TRADE, not endless hardening. Need a faster HONEST path.
- LEVER: tightened capture cron */30 -> */10. Every 10-min point is still >3min apart (de-burst
  threshold) = genuine new info, NOT bursting. Time-to-verdict ~8h -> ~2.5h. Legitimate accel.
- Rejected the dishonest shortcut (lowering N without a significance test). N stays 24 OR a
  proper p-value gate later; never fake the verdict.
- ACCOUNTABILITY: by ~16:00 PDT today, NVDA (the deepest series) should approach n_spaced~24 ->
  first AUTHORITATIVE verdict (EDGE or KILL). If EDGE & not circular -> alpha pipeline -> first
  tiny trade. If KILL -> seed strategy falsified, evolve/replace per constitution. Either is a win.

## 2026-06-26 — End-to-end dry-run caught a real integration bug (Q-005 hardening)
- Built evals/e2e_dryrun.py: exercises the FULL chain with a synthetic authoritative EDGE,
  places nothing. conviction -> PROPOSE-only artifact -> account allowlist -> sizing caps ->
  build_ticket -> kill_check, plus negative tests (circular/preliminary refused, Roth/margin rejected).
- CAUGHT: write_proposed() indexed conviction_row["verdict"] etc. via [], but conviction_from_verdict()
  doesn't return those keys (only rank() merges them). Direct call -> KeyError. This would have
  SILENTLY broken the live trade path the moment a real EDGE arrived. Fixed with .get().
- Result: 17/17 checks pass. Rails verified to FIRE (allowlist fail-closed on 875691461/671638849,
  oversize rejected, circuit breaker trips at -26% DD). Happy path builds a ticket WITHOUT placing.
- LESSON: unit-testing each link is not enough; integration-test the whole flow before live data
  depends on it. A dry-run with a synthetic verdict is the cheapest insurance against a silent
  failure at the worst possible moment (when the real edge finally appears).

## 2026-06-26 — TICKER:TICKER contamination (cron arg-split) — fixed at the boundary
- BUG (escalated by capture cron): cron invoked capture_web_tick.py with the entity split into
  separate tokens ('TICKER' 'NVDA' ...). canonical_entity saw bare 'TICKER' (no colon) and did
  sym=(e or symbol) -> picked 'TICKER' -> wrote ALL names into ONE file TICKER_TICKER.jsonl.
  Every run contaminated the shared file with cross-stock points (wrong-prior EWMA too).
- FIX: hardened canonical_entity to treat a bare/empty/'TICKER' entity token as NOT-a-symbol and
  fall back to the symbol arg; handles 9 invocation variants (verified). Also clarified cron task to
  quote the colon token AND self-verify entity!=TICKER:TICKER each run (defense in depth).
- CLEANUP: discarded the 4 contaminated points (cross-stock + wrong-prior EWMA = untrustworthy;
  4 pts not worth the contamination risk). Good series intact (NVDA 19/RDDT 14/TSLA 14/SNDK 2).
- LESSON (recurring theme): idempotency + input-normalization must live IN the script at the
  boundary, robust to ANY caller mangling. This is the 2nd cron-invocation bug (after lowercase);
  the boundary guard now covers the whole class. Cross-check entity/series_path in cron output.

## 2026-06-26 — Permutation null test: the "edges" are noise so far (CRITICAL honesty)
- Built evals/leadlag_permutation.py: shuffle sentiment labels K=2000x against the REAL price path,
  p = fraction of shuffles whose best positive-lag |corr| >= observed. Low p => edge unlikely by chance.
- RESULT on real series: NVDA observed corr 0.64 BUT p=0.597 (shuffles beat it 60% of the time);
  RDDT/TSLA corr 1.0 but p=1.0 (every shuffle matches = pure small-N saturation). The
  PRELIMINARY_EDGE labels from the simple correlation gate are STATISTICALLY INDISTINGUISHABLE FROM NOISE.
- This is the system working as designed: a raw-correlation threshold is too easy to fool; the
  permutation test is the rigorous gate. So far the seed lead-lag thesis is NOT surviving null testing.
  That is real information, not failure (CORPSES candidate if it holds at N>=24).
- WIRED permutation significance (p<=0.10) into the alpha_pipeline eligibility gate: a name needs
  authoritative EDGE AND non-circular AND permutation-significant to ever produce a PROPOSED artifact.
  e2e dryrun now 18/18 (added: EDGE-failing-permutation is rejected).
- LESSON: always null-test an apparent edge before believing it. "Looks correlated" at small N is
  almost always luck. The honest path: if the edge stays insignificant at N>=24, KILL the seed
  strategy and evolve (predate-sentiment may need a different signal/horizon/structure).

## 2026-06-26 — Cron git-add pathspec bug stranded commits (3rd cron-invocation failure)
- BUG (escalated): capture cron ran `git add ... runs/evals/leadlag_real/*.json ...` — a path that
  doesn't exist -> the whole `git add` returned nonzero -> later commit saw "no changes" -> series
  points captured but NEVER committed/pushed. Data sat in the working tree at risk of sandbox recycle.
- FIX: scripts/capture_and_commit.sh — ONE hardened wrapper the cron calls. Each `git add <path>`
  is independent with `|| true` (a missing/empty path can't block the commit); set -uo pipefail
  but NOT -e; commit only fires if `git diff --cached` is non-empty; push failure leaves data staged
  for the next tick to retry. Also self-guards against TICKER:TICKER contamination.
- Pointed cron 8cdef537 at the wrapper; cron task forbids hand-rolled git add lines.
- LESSON (3rd cron bug, same root): the cron's fre/eedom to hand-write shell is the hazard. Collapse
  the cron to a SINGLE audited script; put ALL fragility (arg parsing, git add, commit gating) inside
  it where it's tested. Never trust a generated bash block to get git plumbing right.

## 2026-06-26 — Self-audit: enforce "no axis unscrutinized" (meta-RSI)
- Built scripts/self_audit.py: scores EVERY axis (signal, verdict, pipeline, safety, capture_infra,
  universe, state_memory, lessons, sim, graph, cron_tasks, meta_improvement) from ground truth,
  finds the weakest, writes runs/SELF_AUDIT.md, and inserts the weakest-axis fix at the top of QUEUE.json.
  The *completeness of improvement* is now itself an audited axis.
- First audit verdict: weakest = sim (0.3) and graph (0.3) — present but UNUSED in the live verdict
  path (early-scaffolding dead weight). signal (0.4) = single-source, no cross-source corroboration.
- DECISION (RSI pruning, not just adding): sim/ and graph/ are explicitly OFF the critical path. They
  are only exercised by the offline eval harness, not by capture->verdict->trade. Kept as reference,
  NOT deleted. They get reconsidered ONLY if the seed lead-lag thesis dies under the null and a
  diffusion-sim becomes the next candidate thesis. Until then they must not be mistaken for live infra.
- Next forced improvements (from audit, in order): wire OR formally retire sim/graph; add cross-source
  sentiment corroboration to raise signal health; schedule self_audit hourly; upgrade watch-cron prompt.

## 2026-06-26 — Slack dual-route + signal now regression-tested
- Slack read routes (connector call_external_tool vs external-tool CLI) fail INDEPENDENTLY during
  blips — connector gave UNAUTHORIZED while CLI worked the same minute. Resilience: try one, fall
  back to the other. Folded into watch flow.
- Never-idle tick: wired web_sentiment scorer invariants (7 checks) into run_offline_evals.py
  (was __main__-only -> audit scored signal tested=False). Harness now 10/10. signal axis 0.4->0.8.
- self_audit meta_improvement detection corrected: audit IS scheduled hourly (cron 253ff74b); 0.6->0.85.

## 2026-06-26 — Defensive series read (transient INSUFFICIENT verdict bug)
- SYMPTOM: capture cron reported all 4 names INSUFFICIENT (need >=3 aligned points) while files
  actually had 22-29 clean points. Root cause: load_series did json.loads(l) with NO error handling,
  so a single half-written line (capture append mid-flight OR concurrent git checkout swapping the
  file) crashed/garbled the whole read -> verdict collapsed to INSUFFICIENT.
- RISK if unfixed: a mid-write read race at the authoritative threshold (n>=24) could trigger a WRONG
  KILL or EDGE -> a bad real-money decision. Data-read robustness is upstream of the verdict.
- FIX: load_series now skips unparseable lines defensively, keeps all good rows, and logs a stderr
  warning (so genuine large-scale corruption is still visible, but a 1-line race is survived).
  Verified: eval on a corrupted file returns a valid verdict + warning, no crash. Harness 10/10.
- LESSON: every file READ on the critical path must tolerate a concurrent mid-write/checkout. Append
  is atomic per-line but a reader can still catch a torn tail; skip-and-warn, never crash-or-collapse.

## 2026-06-26 — Go WIDE: strategy portfolio, not a single thesis (Sal: "not nearly broad enough")
- HARD TRUTH: I went deep on ONE thesis (sentiment lead-lag, 4 hand-picked names) and hardened its
  plumbing while it was failing its null test. That is one fragile guess, not a portfolio. The mandate
  was a BROAD hypothesis space + "anything tradeable on Robinhood is in scope."
- BUILT research/strategy_space.py: the autoresearch grammar THESIS=(SIGNAL,UNIVERSE,HORIZON,STRUCTURE,RISK).
  Space = 4800 tuples (8 signals x 8 OPEN-universe selectors x 5 horizons x 5 structures x 3 risk).
  Universe is OPEN: RH scanners + web research resolve live tickers (all liquid US equities/ETFs, sector/
  index ETFs, crypto-beta names) — NOT a hardcoded basket.
- CAPABILITY-AWARE: each thesis declares which of MY OWN capabilities test it — pplx_sdk web research,
  research subagents (deep falsification), wide_browse (cross-sectional at scale), finance/RH scanners,
  parallel subagents. The edge is orchestration, not hand-coded heuristics.
- Registered a first 12-thesis portfolio (6 signal families) in runs/strategies/REGISTRY.json, all status
  proposed. Sentiment lead-lag is now ONE arm among many, not the whole fund.
- NEXT: build the per-signal test runners + a bandit/explorer that pulls arms each idle tick (breadth-first),
  and the cross-sectional generalization gate (a thesis must hold on >=30% of its universe, not 1 name).

## 2026-06-26 — Generation != breadth (Sal: hesitant we'd rely on 12 fast-made theses)
- CORRECTION: I sampled 12 random grammar tuples and registered them as "proposed" — implying they
  were portfolio-worthy. They were NOT: zero evidence, no mechanism, no research. Fast generation of
  combinations is curve-fit-by-volume dressed as breadth. Worse than the single thesis (which at least
  has real data). Demoted all 12 to status=candidate_unvetted (zero weight).
- FIX (structural): runs/strategies/LADDER.md status ladder — candidate_unvetted -> researched ->
  testing -> edge -> killed. ONLY `edge` (survived all falsifiers incl cross-sectional >=30%) can
  produce a PROPOSED trade. Real breadth = count of theses at `researched`+ with DISTINCT mechanisms,
  NOT count of generated tuples. No silent promotions; each rung needs logged evidence.
- The right SOURCE of breadth is real research (Computer web-research + Teammate's eng-org investigating
  mechanisms), not a tuple sampler. Generation proposes coordinates; evidence earns theses.

## 2026-06-28 — Hard-coded repo path broke BOTH cron wrappers (P1, found on cold-boot)
- **Bug:** `scripts/capture_and_commit.sh` and `scripts/watch_trigger.sh` both set
  `ROOT="/home/user/workspace/computer_fund"` (underscore). The real clone dir is `computer-fund`
  (hyphen). With `cd "$ROOT" || exit 1`, every capture and watch tick hit FATAL and exited BEFORE
  capturing or watching. This was a contributing cause to the overnight stall, independent of the
  sandbox outage — even when the sandbox was up, the wrappers self-aborted.
- **Why it hid:** The handoff narrated the wrapper as "the ONE hardened entry point," but no tick
  had actually exercised `cd "$ROOT"` against a fresh clone since the dir was renamed. Narration of
  robustness is not robustness.
- **Fix:** Derive `ROOT` from the script's own location
  (`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"`)
  so the wrapper works regardless of clone dir name. NEVER hard-code an absolute repo path again.
- **Lesson:** Any script meant to be run by a cold cron must locate the repo relative to itself, and
  must be smoke-tested from a clean clone, not just read.

## 2026-06-28 — Gating evals must not depend on live capture output (PR #20, change-requested)
- PR #20's KG observed-series diagnostic was wired into the gating `run_offline_evals` list but
  hard-asserted `row_count == 3`, `source == "finance_ticker_sentiment"`, a pinned score/event_id/
  momentum — all true only against a stale 3-row fixture. Live NVDA series is now 32 rows
  (4 finance_ticker + 28 web_search). Merging would have failed the whole suite + broken the verdict
  gate. **Disposal caught it by reading the diff against ground truth; Teammate's "validation PASS"
  was against the old snapshot.** Lesson: a gating eval must read a FROZEN committed fixture, never
  mutable live series output; if it reads live data it must assert structural invariants only.

## 2026-06-28 — Two ticks can collide; reconcile, don't fight
- On cold-boot, a parallel tick (cron firing as Computer) merged #32 + several PRs and committed the
  verbatim HANDOFF_CONTEXT.md while this thread was working from an older clone, producing an add/add
  conflict. Resolution: keep the better/verbatim remote artifact, `git reset --hard origin/master`,
  re-derive open work from live `gh pr list`. Lesson: never trust a local clone's snapshot over
  origin; always re-fetch + re-list before deciding what work remains. (Corollary: commit WIP before
  any `git reset --hard` — a hard reset wiped uncommitted self_audit.py edits when master moved under
  this thread. The repo is the only durable substrate across the two agents.)

## 2026-06-27 — Failure 2 structural fix landed (operating-doctrine skill + pr_queue audit axis)
- Added `skills/computer-fund-operating-doctrine/SKILL.md` (load at the START of every tick): encodes
  OBLIGATION A (drain Teammate's non-draft PR queue before declaring idle — P1, never "nothing to do";
  read the diff, merge-onto-master, run the suite, dispose) and OBLIGATION B (decisiveness: act on
  anything reversible/in-scope; `confirm_action` ONLY for trade placement + destructive ops; narration
  is not progress; finish the chain). This is the missing config that let the queue rot for ~24h.
- Wired a `pr_queue` axis into `scripts/self_audit.py`: 1.0 when drained, a P1 forcing function listing
  the open PR numbers when non-draft PRs are open, and a fail-safe 0.6 "unknown" when `gh` is
  unavailable (sandbox down). Also fixed `_has_test()` to scan `tests/` as well as `evals/` (tests
  moved to tests/), which honestly raised the signal axis to tested=True.

## 2026-06-27 — FIRST AUTHORITATIVE VERDICT: seed thesis KILLED (the system worked)
- NVDA reached n_spaced=24 (de-bursted from 35 raw web_search_sentiment points). First verdict to clear
  the authoritative threshold. leadlag_real=EDGE (best_corr=0.5079 @ lag2, non-circular) — but the
  permutation null (k=2000, seed=7) returned p=0.2075 > 0.10 => EDGE_IS_NOISE. The seed "predate public
  sentiment via lead-lag" thesis is statistically indistinguishable from chance. Trade gate (auth EDGE +
  non-circular + p<=0.10) NOT met; alpha pipeline emitted 0 proposals; no trade placed. KILLED, corpse +
  registry updated (TH-8008e62803 -> killed). This is the chip-on-shoulder discipline paying off: the
  raw-correlation EDGE label would have been a trap; the permutation p-value is the gate that mattered.
- NEXT (evolve, per CONSTITUTION): pursue the 5 researched mechanisms now seeded with committed evidence
  (runs/strategies/research/evidence/), not a variant of the dead single-name single-source lead-lag.
  Real breadth = theses at researched+ with distinct mechanisms tested cross-sectionally (>=30% of a
  >=30-name universe), not one ticker.

### 2026-06-28 — Permutation null test is the trade gate (edge-looking corr is not enough)

- **Source corpse**: `runs/CORPSES.md` entry "2026-06-28 — Permutation gate blocks lead-lag alpha (NVDA authoritative EDGE but p>0.10)".
- **Reusable lesson**: even with n_spaced>=24, a lead-lag correlation can be a small-sample or structure artifact; the permutation p-value is the only honest discriminator before risking capital.
- **Seeder rule**: future thesis seeds must target improving permutation significance (p<=0.10) or designing a different null test; do not propose trading logic off corr alone.
- **Meta/eval linkage**: this should move `self_audit` / wording to treat `perm=EDGE_IS_NOISE` as an authoritative KILL signal, not a blocked trade annoyance.
- **Revisit trigger**: a later run achieves p<=0.10 with circ=False at n_spaced>=24 on any name, or a new signal family passes an improved null test.

### 2026-06-28 — TSLA repeats the raw-EDGE / permutation-noise failure

- **Source corpse**: `runs/CORPSES.md` entry "2026-06-28 — TSLA raw lead-lag EDGE fails permutation null".
- **Reusable lesson**: TSLA now shows the same failure pattern as NVDA: authoritative, non-circular raw EDGE (`best_corr=0.4605` at lag 4) is still noise when the permutation p-value is 0.1575, above the 0.10 eligibility bar.
- **Seeder rule**: treat multiple single-name raw EDGE / permutation-noise outcomes as evidence against lag/correlation-only variants; require permutation significance, cross-sectional breadth, or a different pre-registered falsifier before proposing capital-facing lead-lag logic.
- **Meta/eval linkage**: threshold monitors should continue paging on new authoritative raw-EDGE/permutation-noise names only to record corpses and lessons, not to imply PROPOSED, sizing, ARMED handoff, or execution eligibility.
- **Revisit trigger**: TSLA or a cross-sectional basket later clears the complete gate (authoritative n_spaced>=24, non-circular, permutation p<=0.10) on committed observed data.

## 2026-06-28 — The live regex sentiment scorer is systematically over-bullish (signal-quality flaw)
- Spike (`scripts/spike_llm_extract.py`, `runs/spikes/2026-06-28_llm_extract_vs_regex.md`) compared the
  regex/lexical scorer in web_sentiment.py against pplx_sdk.llm.extract on a 22-doc NVDA corpus.
- Regex: +0.2293 (flagged 10 boilerplate quote pages as high-conf "explicit"). LLM honest read: +0.0939.
- The regex scorer treats generic quote-page text as bullish signal — a systematic upward bias. An
  over-bullish input feeding the lead-lag thesis could manufacture a false EDGE. The seed thesis dying on
  the permutation null may be partly masking that the underlying signal itself is mis-calibrated.
- Lesson: validate the SCORER, not just the verdict. We were stress-testing lead-lag (downstream) while
  the upstream sentiment scorer had an unaudited bias. Upgrade path = llm.extract in PARALLEL burn-in
  (score_llm alongside score_raw), never a hot-swap mid-thesis. Use the full pplx_sdk surface, not 1 call.

## 2026-06-28 — A robust permutation p-value does NOT certify edge if the PRICE axis is degenerate (RDDT)
- **Source corpse**: `runs/CORPSES.md` entry "2026-06-28 — RDDT lead-lag EDGE survives the permutation null but rides a DEGENERATE price proxy".
- **Reusable lesson**: the permutation null shuffles the SENTIMENT labels against the observed price path; it tests whether the sentiment->price association is better than chance GIVEN the price series. It is blind to corruption in the price series itself. RDDT showed a robust p (0.034-0.047 across 5 seeds) AND a non-circular EDGE AND was not a scorer-change artifact — yet the price_proxy had only 9 distinct values over 24 points, 8/23 zero returns, and a 24h gap. The "edge" was sentiment drift correlated against a step-function quote artifact. Capital-grade only if BOTH axes are clean.
- **Seeder rule**: add a price-series degeneracy gate UPSTREAM of (or inside) the verdict — reject a lead-lag verdict when, over the de-bursted points, distinct price values < ~15, zero-return fraction > ~20%, or any capture gap > ~2-3h. Prefer a real per-capture broker/finance quote over the corpus price extractor for any name that reaches the authoritative threshold. Do not propose a trade on a corpus-extracted price.
- **Meta/eval linkage**: candidate new deterministic eval `eval_price_proxy_not_degenerate` (offline, fixture-based) wired into `run_offline_evals`; and a `price_quality` axis in `scripts/self_audit.py`. The permutation gate stays, but it is necessary-not-sufficient.
- **Revisit trigger**: a name clears the full gate on a non-degenerate, real-quote price series (>=15 distinct prices, <20% zero returns, no multi-hour gaps, n_spaced>=24, p<=0.10).
