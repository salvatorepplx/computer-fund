# Meta-Orchestrator

The reasoning layer that sits ABOVE both the thesis loop and the eval suite. It runs after every iteration (or batch of iterations) and answers one question:

> **"Given everything we just learned across the entire system, which single harness component is now the binding bottleneck, and what's the smallest change that would relieve it?"**

This is what makes the system truly self-improving — not the evals themselves (which just measure), and not the per-eval self-improve script (which acts in isolation per eval). The meta-orchestrator integrates signal across ALL harness components, prioritizes, and writes one Harness PR per cycle with a binding rationale.

---

## Architecture

```
                  ┌─────────────────────────────────┐
                  │  THESIS LOOP (per-tick)         │
                  │  generates PRs, runs falsifiers │
                  └────────────┬────────────────────┘
                               │ trace + outcome
                               ▼
                  ┌─────────────────────────────────┐
                  │  EVAL SUITE (run_evals.py)      │
                  │  CAP / REG / JUDGE scores       │
                  └────────────┬────────────────────┘
                               │ scores + failure cases
                               ▼
                  ┌─────────────────────────────────┐
                  │  META-ORCHESTRATOR ◀── runs HERE │
                  │  reasons across all harness     │
                  │  components, picks ONE          │
                  │  bottleneck, drafts ONE HPR     │
                  └────────────┬────────────────────┘
                               │ proposed HPR
                               ▼
                  ┌─────────────────────────────────┐
                  │  SHADOW EVAL + USER APPROVAL    │
                  │  lock-in test on prior 5 PRs    │
                  └────────────┬────────────────────┘
                               │ approved diff
                               ▼
                  ┌─────────────────────────────────┐
                  │  APPLY → references/*           │
                  │  memory_update on success       │
                  └─────────────────────────────────┘
```

---

## Harness Components Under Scrutiny

Every meta-orchestration pass scores each of these and picks the worst:

| Component | File(s) | Eval signal | Reasoning question |
|---|---|---|---|
| **Conviction bar** | `references/conviction-bar.md` | E-CAP-01, E-CAP-06 | Are our thresholds discriminating winners from losers? |
| **Falsifier set** | `references/falsification-playbook.md` | E-CAP-02, E-CAP-05, E-REG-02 | Is the falsifier suite catching what it should? Are we missing any test that hindsight would have demanded? |
| **PR format** | `references/pr-format.md` | E-REG-03, E-JUDGE-03 | Are PRs forcing the right discipline at draft time? |
| **Seeder prompt** | embedded in cron task + `corpus/lessons.md` | E-CAP-03 | Are seeded theses surviving to ARMED? |
| **Reviewer prompt** | embedded in iteration subagent prompts | E-CAP-01, E-JUDGE-01 | Is the reviewer adversarial enough? Properly skeptical? |
| **Catalyst corpus** | `corpus/catalysts.md`, `corpus/universe.md` | E-CAP-03 | Are we seeding from the right opportunity set? |
| **Lessons file** | `corpus/lessons.md` | (cross-cutting) | Are the lessons we extracted being respected by the seeder? |
| **Action budget** | `references/continuous-loop.md` | iteration latency | Is the per-tick budget producing rushed PRs or wasted ticks? |
| **Kill switches** | `paper_engine.py` thresholds | E-CAP-06, paper P&L | Are we cutting losers fast enough / late enough? |
| **Meta-eval coverage** | `evals/registry.json` | (self-referential) | Are we measuring the right things? |

---

## The Reasoning Protocol

The meta-orchestrator runs as a fresh-context subagent with this exact protocol:

### Inputs it gathers
1. Latest eval scores (`evals/scores/<latest_week>.json`)
2. Eval-score time series (last 4 weeks) — to detect drift
3. All PRs from the last cycle (since last meta-orchestration run)
4. CORPSES.md (recent kills)
5. Paper-trade P&L deltas since last run
6. `corpus/lessons.md`
7. Previous Harness PRs (HPR-*) — what was tried, what worked
8. Memory: `memory_search` for "what improvements has autoresearch tried recently?"

### The hard question (must answer all 5 sub-questions)
The subagent must produce a structured response:

```yaml
bottleneck_diagnosis:
  binding_component: <one of the 10 components above>
  evidence:
    primary: <which eval(s) are firing>
    corroborating: <which PRs / paper outcomes back this>
    counter_evidence: <what would argue AGAINST this being the bottleneck>
  why_now: <why this component is the binding constraint THIS cycle, not last cycle>

proposed_change:
  file: <reference file path>
  smallest_change: <exact diff intent in 1-2 sentences>
  expected_eval_delta:
    primary_eval: <which eval should improve, by how much>
    risk: <which eval could regress as a side effect>
  reversibility: <how easily can we roll back if it breaks things>

shadow_eval_design:
  replay_set: <which 5 prior PRs to replay against the new reference>
  must_not_regress: <list of evals that must stay within ±1 of baseline>
  promote_threshold: <numeric delta needed on primary eval>

alternative_considered:
  next_best_bottleneck: <runner-up component>
  why_deferred: <why we picked the primary over this one>

self_check:
  am_i_chasing_noise: <yes/no + reasoning>
  is_this_just_overfitting_to_the_last_pr: <yes/no + reasoning>
  would_a_fresh_reviewer_agree: <yes/no + reasoning>
```

This is the "hard thought" — the subagent cannot skip any field. If it cannot fill `counter_evidence` or `am_i_chasing_noise` honestly, it must return `action: NOOP` and explain why.

### Outputs
- A new `references/HARNESS-PRS/HPR-NNN.md` containing the structured diagnosis + proposed diff
- An entry in `evals/meta_log.csv` recording the bottleneck chosen and rationale
- A `memory_update` call if action was non-NOOP

---

## Cadence: Two Trigger Modes

### Mode A — After every iteration (hot path)
Runs as the final step of every thesis-loop tick that produced a new PR. Quick pass: takes 1-2 min, uses cached eval scores. May only emit a "watchlist" entry — flags components showing signal but below the action threshold.

### Mode B — Weekly deep pass (Sunday 5pm PT)
Full reasoning. Runs the entire eval suite first, then the protocol above. Always emits either a Harness PR or a NOOP-with-rationale. This is the cycle that actually changes the system.

Mode A feeds the watchlist that informs Mode B's reasoning — so when Sunday comes, the meta-orchestrator already has 5 days of "something is off here" signals.

---

## Anti-Patterns the Meta-Orchestrator Must Avoid

1. **Tweaking the conviction bar after one bad iteration** — minimum 3 data points before any threshold change.
2. **Adding falsifiers reactively to last week's specific failure mode** — must show pattern across ≥2 dead theses.
3. **Lowering bars to make pass rates look good** — capability evals are hill-climbs; never relax targets.
4. **Recursive infinite-improvement loops** — if two consecutive Harness PRs target the same component, escalate to user.
5. **Loss of audit trail** — every applied change must reference back to evidence; no "feel-based" tweaks.
6. **Goodharting calibration** — if E-CAP-01 (reviewer→P&L correlation) goes up due to fewer ARMED trades (smaller sample), flag it as a sample-size artifact, not a win.

---

## Files

- `scripts/meta_orchestrator.py` — runs the protocol, spawns the reasoning subagent
- `evals/meta_log.csv` — append-only log of every bottleneck chosen
- `evals/watchlist.json` — Mode A flags awaiting Mode B's full pass
- `references/HARNESS-PRS/HPR-NNN.md` — proposed harness changes
- `references/HARNESS-PRS/APPLIED.md` — log of approved + applied HPRs
