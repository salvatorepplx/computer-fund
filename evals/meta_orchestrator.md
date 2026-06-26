# Meta-Orchestrator Weekly Pass

The meta-orchestrator is a weekly, fresh-context review that turns recent offline evidence into at most one small harness-improvement proposal. It asks one question:

> Which single Computer Fund harness component is the binding bottleneck, and what is the smallest change that would relieve it?

If the evidence is weak, conflicting, or not actionable, the pass returns `NOOP` instead of inventing work.

## Cadence

- **Weekly deep pass:** run after the week's offline research/eval batch, before assigning new Teammate improvement work.
- **Fresh context:** the reviewer should start from the allowed inputs below, not from the worker that produced the latest batch.
- **One output:** write exactly one JSON entry under `runs/meta/` and optionally append its one-line summary to a future `evals/meta_log.csv`.
- **One proposal maximum:** if actionable, the entry identifies one binding component and one smallest follow-up change; otherwise it records `decision: "NOOP"`.

## Scored Axes

Score each axis from `-2` to `+2`, where `-2` means repeatedly blocking progress, `0` means no clear signal, and `+2` means healthy enough to ignore this cycle.

| Axis | Scope | Example offline evidence |
| --- | --- | --- |
| `engineering` | Code quality, determinism, packaging, testability | `python -m evals.run_offline_evals`, `git diff --check`, import failures |
| `research_depth_breadth` | Thesis quality, coverage, falsification readiness | Research notes, corpus gaps, killed hypotheses |
| `graph` | Knowledge graph freshness, provenance, observed-vs-simulated separation | Graph summaries, persistence checks, provenance audits |
| `sim_fidelity` | Simulation diagnostics and calibration | Offline sim-fidelity reports, invariant failures, calibration notes |
| `execution_observability` | Observability of execution-facing artifacts only | Static logs/docs/schema gaps; no broker/account/order reads or execution changes |
| `evals` | Offline eval coverage, regressions, blind spots | Eval JSON output, missing coverage, flaky or too-broad tests |
| `memory_lessons` | Lessons captured and reused | `corpus/improvement_log.md`, lessons files, stale decisions |
| `management_disclosure` | Human-reviewability, status clarity, disclosure quality | PR bodies, handoffs, risk disclosures, stale task state |
| `external_systems` | Connector-adjacent interfaces and documented dependencies | Static connector config/docs only; no live connector calls |

## Allowed Inputs

The pass is propose-only and offline. It may read:

- Repo files and docs, including `CHARTER.md`, `runs/AUTORESEARCH_TEARDOWN.md`, `evals/README.md`, `corpus/`, `graph/`, `research/`, and `sim/`.
- Deterministic eval output from `python -m evals.run_offline_evals`.
- Offline sim-fidelity diagnostic artifacts or static logs that previous workers committed or attached for review.
- Prior meta-orchestrator entries in `runs/meta/` and any future `evals/meta_log.csv`.
- Git diffs and local validation output for the current branch.

The pass must not read or mutate Robinhood, broker connectors, live market data, account/order state, order placement paths, ARMED tickets, or execution safety rails.

## Required Entry Fields

Each deep pass writes a JSON object with these fields:

- `schema_version`: currently `1`.
- `date`: UTC date of the pass.
- `mode`: `weekly_deep`.
- `decision`: `PROPOSE` or `NOOP`.
- `binding_component`: one scored axis when `decision` is `PROPOSE`; `null` for `NOOP`.
- `axis_scores`: object keyed by all scored axes, each with `score`, `evidence`, and `counter_evidence`.
- `evidence`: concise facts supporting the selected bottleneck.
- `counter_evidence`: concise facts arguing another component or `NOOP` could be right.
- `expected_eval_delta`: the offline eval, diagnostic, or review signal expected to improve, including direction and magnitude when measurable.
- `smallest_change`: one scoped follow-up change a Teammate worker can implement or a reason no change is justified.
- `noise_guard`: checks used to avoid overfitting to the latest batch.
- `self_check`: must include `am_i_chasing_noise`, `is_this_overlapping_active_work`, and `why_not_noop`.
- `allowed_inputs_used`: exact offline files/commands/artifacts used.
- `follow_up_for_teammate`: short instruction for the next worker, or `null` for `NOOP`.

## NOOP Criteria

Return `NOOP` when any of these are true:

- No axis has at least two independent pieces of supporting evidence.
- Counter-evidence is as strong as or stronger than the selected bottleneck evidence.
- The proposed change would touch live execution, broker connectors, account/order state, CHARTER safety rails, or trading decisions.
- The expected delta cannot be observed with an offline eval, static diagnostic, or human-reviewable artifact.
- The only signal is a single recent failure, a subjective preference, or work already assigned to another active task.

## Noise Guards

Before proposing work, the reviewer should verify:

- **Multiple signals:** at least two independent offline sources point to the same component.
- **Recent but not single-sample:** the issue appears outside one isolated PR, eval run, or research note.
- **Counter-evidence recorded:** plausible runner-up components and reasons to defer them are written down.
- **Eval-linked delta:** the expected improvement names an existing or clearly proposed offline validation path.
- **Overlap check:** the change does not duplicate active work such as falsification/lead-lag placebo tasks.

## Consuming the Output

Future Teammate workers should treat the newest `runs/meta/*.json` entry as a prioritization hint, not as authorization to trade or deploy. A worker may pick up `follow_up_for_teammate` only if it remains offline, minimal, and within the Charter. If the newest entry is `NOOP`, workers should not manufacture a meta-orchestrator follow-up; they should wait for new eval or diagnostic evidence.

A future lightweight logger can append these fields to `evals/meta_log.csv`: `date`, `decision`, `binding_component`, `score`, `expected_eval_delta`, `smallest_change`, `entry_path`.
