# graph/ — RETIRED from the live critical path (2026-06-26)

Status: PARKED, not deleted. Decision per self-audit forcing function (weakest axis).

The knowledge-graph was early-scaffolding for the seed "predate-public-sentiment"
thesis. It is NOT used by the live capture -> verdict -> trade path; only the offline eval harness
(evals/run_offline_evals.py) references it to test invariants.

Why parked, not killed: if the seed lead-lag thesis dies under the permutation null (currently
trending that way), a knowledge-graph layer is a credible NEXT candidate thesis, and this code is
a head start. Until a thesis actually needs it, it must NOT be mistaken for live infra.

Re-activation trigger: a future thesis explicitly requires a knowledge graph -> wire sim into
that thesis's verdict path and remove this marker. Otherwise it stays parked and is excluded from
the live-axis health score.
