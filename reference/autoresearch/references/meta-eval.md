# Meta-Eval & Self-Improvement Harness

The autoresearch system has TWO learning loops running in parallel:

## Loop 1 — Thesis loop (already exists)
Generates and falsifies theses. State: SKILL.md, references/, runs/.

## Loop 2 — Meta-eval loop (this doc)
Asks: **"is our thesis loop itself improving?"** Treats the conviction bar, falsifier set, reviewer prompts, and seeder prompts as **artifacts under continuous evaluation**. When evidence shows a harness component is mis-calibrated, drift-prone, or producing low-quality output, the meta-eval engine proposes a "Harness PR" against `references/` files.

Lineage: ports Anthropic's evals discipline (capability + regression), GEPA reflective prompt evolution, CriticGPT-style critic models, Arize agent-harness telemetry, and meta-labeling from quant trading.

---

## What we evaluate (the eval registry)

Each eval is a deterministic function over `runs/` artifacts and saves a JSON score to `evals/<eval_id>/scores.csv`. The full registry:

### Capability evals (we WANT these to improve over time)
| Eval ID | What it measures | Grader type | Target |
|---|---|---|---|
| `E-CAP-01` | Reviewer-score → realized-P&L correlation (Spearman) | deterministic | ≥ +0.5 |
| `E-CAP-02` | Falsifier hit rate on theses that lose money post-MERGE | deterministic | ≥ 80% |
| `E-CAP-03` | Seeder edge: % of seeded theses that survive to ARMED | deterministic | ≥ 35% |
| `E-CAP-04` | Iteration depth before MERGE (lower = better signal quality at seed) | deterministic | ≤ 3 |
| `E-CAP-05` | Time-to-kill on bad theses (we want fast kills) | deterministic | ≤ 2 iterations |
| `E-CAP-06` | Paper P&L vs benchmark (SPY) — armed portfolio Sharpe — annualized | deterministic | ≥ 1.0 |

### Regression evals (we want these to STAY high — they protect against drift)
| Eval ID | What it measures | Grader type | Threshold |
|---|---|---|---|
| `E-REG-01` | No look-ahead leak in any merged thesis (replay audit) | deterministic | 100% |
| `E-REG-02` | All falsifiers from playbook.md were run in every PR | deterministic | 100% |
| `E-REG-03` | Pre-registered conviction targets exist in every PR | deterministic | 100% |
| `E-REG-04` | Every MERGE has a paper-trade history ≥ 20 days | deterministic | 100% |
| `E-REG-05` | Every KILLED thesis has a CORPSES.md entry | deterministic | 100% |
| `E-REG-06` | Skill files validate against agentskills validator | deterministic | pass |

### LLM-as-judge evals (for subjective dimensions — calibrated against deterministic)
| Eval ID | What it measures | Grader |
|---|---|---|
| `E-JUDGE-01` | Reviewer adversarial-ness (did the reviewer steelman?) | fresh-context LLM judge with rubric |
| `E-JUDGE-02` | Thesis novelty (vs CORPSES.md and prior MERGED theses) | fresh-context LLM judge |
| `E-JUDGE-03` | PR clarity (could an external PM understand and audit?) | fresh-context LLM judge with rubric |

LLM judges must return `Unknown` when insufficient info, per Anthropic eval guidance. Each judge's verdict is compared against deterministic evals or against a sampled human review weekly to detect drift.

---

## Calibration tracker (the critical signal)

The single most important meta-eval: **does reviewer score actually predict realized P&L?**

`evals/calibration.csv` — appended on every paper-trade close:
- `thesis_id, pr_ref, reviewer_score, oos_sharpe_pred, oos_sharpe_real, paper_pnl_pct, paper_days, calibration_error`

Run weekly:
- **Spearman ρ(reviewer_score, paper_pnl_pct)** across all closed paper positions
- **MAE(oos_sharpe_pred, oos_sharpe_real)** — were pre-registered targets honest?
- **Brier score** on ARMED/MERGED predictions of "profitable" vs realized

If Spearman < +0.3 across ≥ 10 closed positions, the reviewer is mis-calibrated → open Harness PR against `references/conviction-bar.md` or `references/falsification-playbook.md`.

---

## Self-improvement engine (GEPA-style reflective evolution)

`scripts/self_improve.py` runs as the weekly meta-eval cron action. Its job:

1. Read all eval scores from the past week.
2. Identify the *worst-performing* eval that has actionable handles (a reference file we can rewrite).
3. Use a reflective LLM call to propose a textual diff to that reference file. Inputs include:
   - The eval definition
   - Last 4 weeks of eval scores
   - Sample failure cases (full PR text + paper-trade outcome)
   - The current text of the reference file
4. Run a **shadow eval**: replay the last N PRs against the proposed new reference and see if eval scores improve.
5. If shadow eval beats current by ≥ 10%, write a Harness PR at `references/HARNESS-PRS/HPR-NNN.md`. The diff is *not auto-applied* — user approves via confirm_action.
6. If shadow eval fails to improve, log the attempt and try a different handle next week.

The reflective LLM uses **textual feedback** (eval reasoning strings, not just scores) per GEPA's core insight. Specifically the prompt includes: "Here are 3 specific cases where this rubric scored a thesis 8/10 and it lost money — propose a textual change that would have lowered the score to ≤ 5/10 in these cases without lowering scores on the cases that made money."

---

## CriticGPT-style adversarial reviewer

`scripts/critic.py` — spawns a *fresh-context* reviewer subagent whose job is specifically to catch bugs the primary reviewer missed. It re-runs the entire PR validation pipeline from scratch and produces a critic score. If critic and primary diverge by > 2 points consistently (≥ 3 PRs in a row), the primary reviewer prompt needs evolution → open Harness PR.

Mirrors OpenAI's CriticGPT finding: critics catch ~63% of bugs human reviewers miss.

---

## Cadence

- **After every PR**: run regression evals (E-REG-*) inline. Any failure blocks the PR from MERGE.
- **Daily at 4:15pm PT** (in the EOD cron): append to calibration.csv for any closed positions.
- **Weekly Sunday 5pm PT**: run full eval suite + self-improvement engine. Notify user if a Harness PR is generated.

---

## Anti-Goodhart Guardrails

The meta-eval system itself can be gamed. Protections:
1. Capability and regression evals run on DIFFERENT slices of data.
2. No single eval can trigger a Harness PR — must be ≥ 2 weeks of consistent degradation.
3. Every Harness PR ships with a "lock-in test": a fixed set of 5 prior PRs whose grading must not move materially after the change.
4. The user approves every Harness PR. The system never silently rewrites its own conviction bar.
5. The meta-eval has its own kill switch: if any 2 consecutive meta-evals propose contradictory Harness PRs, escalate to user, pause auto-improvement.

---

## Files

- `evals/registry.json` — eval definitions and current thresholds
- `evals/calibration.csv` — reviewer-score vs realized-P&L
- `evals/scores/<eval_id>_YYYY-WW.json` — weekly scores
- `references/HARNESS-PRS/HPR-NNN.md` — proposed harness improvements
- `scripts/run_evals.py` — runs the deterministic eval suite
- `scripts/self_improve.py` — GEPA-style reflective evolution
- `scripts/critic.py` — CriticGPT-style adversarial reviewer
