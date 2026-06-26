# Autoresearch Teardown — what transfers to the Computer Fund

Critical study of the user's `autoresearch` skill (6,674 lines, 3-loop RSI research system).
Stance per the Constitution: pick it apart, take only what genuinely transfers to OUR architecture
(real money, autonomous execution, sentiment-prediction core, two-agent Computer⇄Teammate Slack bus).
Wear the chip — autoresearch is prior art, not scripture. Some of it is strong; some is overbuilt
for a $1k single-account autonomous book; some doesn't fit our sentiment thesis at all.

## What autoresearch IS (architecture)
Three concurrent loops: (1) thesis loop generates+falsifies theses, (2) meta loop evaluates whether
the thesis loop is improving and PRs its own references, (3) infra loop builds reusable primitives.
Stateless, memory-backed, one action per tick. Paper-trades only; real deployment needs human confirm.
13 agent roles (CRO, quant_critic, signal_engineer, bug_hunter, etc.). Bandit search over a
(SIGNAL × UNIVERSE × HORIZON × STRUCTURE × RISK) grammar.

---

## TAKE (high-value, transfers directly)

### 1. The meta-orchestrator pattern — ADOPT as the core of our self-improvement axis
After every batch, a fresh-context reasoner asks ONE question: *"which single harness component is the
binding bottleneck, and what's the smallest change to relieve it?"* It must fill a structured diagnosis
(binding_component, evidence incl. **counter_evidence**, expected_eval_delta, **self_check: am_i_chasing_noise**)
or return NOOP. This is exactly our "recursively self-improve across every axis" made operational.
→ **This becomes Teammate's weekly deep pass.** Our axes (engineering, research, graph, sim, execution,
eval, memory, management, external systems) are the components it scores. Build `evals/meta_log.csv`.

### 2. The falsification playbook — ADOPT, adapt to sentiment + real fills
Tiered: unconditional (one fail → KILL), conditional (score −2), process (→ iterate). Directly useful:
- **Look-ahead leak audit** — maps onto Charter §6 (no look-ahead). Our version: every sentiment
  observation must predate the entry; simulated sentiment never enters a backtest as fact.
- **Random-label placebo** — shuffle the sentiment signal, re-test; if edge survives, we're fitting noise.
- **Universe placebo** — run the sentiment thesis on a name where it shouldn't work.
- **Date-range / regime split** — sentiment edges are regime-specific; this is mandatory for us.
- **Cost/slippage stress** — CRITICAL and *more* important for us than autoresearch: we take REAL fills
  on a $1k book where a few cents of slippage is a large % of edge. Add a real-fill slippage falsifier.
- NEW falsifier we need that autoresearch lacks: **sentiment-leadlag placebo** — does our predicted
  sentiment actually LEAD price, or is it coincident/lagging? If lagging, there's no predate edge.

### 3. Capability vs regression eval split — ADOPT for EVAL-0
CAP evals (want them to rise) vs REG evals (must stay at 100%, protect against drift). Our EVAL-0 harness:
- CAP: sentiment-prediction accuracy (did the sim's projected peak match observed sentiment?),
  predate-timing (did we enter before the peak?), realized P&L vs SPY, edge-after-costs.
- REG: account allowlist never violated (must be 100%), review-before-place ran every order,
  sizing caps never breached, every kill-switch breach acted on, simulated-sentiment-labeled.
→ The **calibration tracker** is the single most important eval: does our conviction score predict
realized P&L? Pre-register it now; compute once we have ≥10 closed positions.

### 4. The corpus/lessons + CORPSES discipline — ADOPT
Every killed thesis logged with the reason; lessons distilled and fed back to the seeder. "Corpses are
the most informative artifact." We already have `corpus/improvement_log.md`; add `runs/CORPSES.md`.

### 5. Agent-role specialization — ADOPT SELECTIVELY as Teammate worker types
autoresearch has 13 roles. We don't need 13. The ones that map to our two-agent model, run BY Teammate:
- **quant_critic** (adversarial review of ARMED tickets before they reach Computer) — yes.
- **bug_hunter** (finds bugs in the Fund's own code) — yes, core engineering axis.
- **signal_engineer** (implements sentiment signals from a registry) — yes, our edge depends on it.
- **lessons_distiller** — yes, cheap and high-value.
- **calibration_analyst** — yes, owns the calibration tracker.
Skip: capacity_analyst (we're $1k, capacity is irrelevant), literature_scout (fold into research).

### 6. Stateless memory-backed tick + action budget — ALREADY ADOPTED
Our loop is this. Keep their action-budget idea (bound each tick: 1 backtest, 1 critic spawn, N fetches).

---

## LEAVE (doesn't transfer / overbuilt for us)

- **The full (SIGNAL×UNIVERSE×HORIZON×STRUCTURE×RISK) bandit grammar** — autoresearch searches a huge
  generic factor space. OUR edge is narrow and specific: *predict-and-predate public sentiment* on
  contested battle locations. Adopting the whole factor zoo would dilute the thesis. Borrow the
  *structure* (a thesis is a tuple; search it with a bandit) but keep our universe = sentiment-driven
  battles, not the full quant menagerie.
- **$1M-notional capacity gates, borrow-availability for shorts** — irrelevant at $1k, cash account,
  no shorting. Drop entirely.
- **MERGED→DEPLOYED human-confirm gate** — autoresearch keeps a human in the loop at deploy. WE DO NOT:
  Sal granted full autonomous execution within the rails. Our ladder ends in autonomous EXECUTED.
- **continuous.py session-resident daemon (double-fork)** — clever hack to beat the 1h cron floor, but
  WE HAVE A REAL DAEMON: Teammate's heartbeat. Don't reinvent the fork hack; use Teammate.
- **13 roles as always-on swarm** — too heavy / too costly for a $1k book. Teammate runs roles
  on-demand per heartbeat, not a standing swarm.

## FIX (autoresearch's own admitted weaknesses we must NOT inherit)
- Its ethos.md confesses: "shipped two stacked bugs that made the entire system fake for 16 hours,"
  "flagship Sharpe-4.2 result was a position-sizing artifact," "first ARMING gate never fired due to
  `(p_value or 1) < 0.05`." → Lesson: **presume every amazing result is a bug.** Our REG evals exist
  precisely to catch the "system silently went fake" failure mode. Build a heartbeat REG eval that
  asserts the loop is actually executing real reviews, not no-op'ing.
- Conviction thresholds were "set by judgement, not calibration data." We'll do the same initially —
  but flag every threshold as provisional and let the calibration tracker reset them at N≥10.

---

## Net: what we build next, in priority order
1. **EVAL-0** harness with the CAP/REG split + calibration tracker (pre-registered). [Teammate owns]
2. **Falsification playbook** adapted to sentiment + real fills, incl. the sentiment-leadlag placebo. [Teammate]
3. **Meta-orchestrator** weekly pass scoring our axes. [Teammate]
4. **CORPSES.md + lessons** discipline wired into the loop. [shared]
5. The **alpha pipeline + tick state machine** that chains research→graph→sim→ranked→autonomous execution. [Computer]
