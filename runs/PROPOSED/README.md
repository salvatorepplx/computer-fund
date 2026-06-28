# PROPOSED Artifacts

`runs/PROPOSED/<id>.json` is the only machine handoff path for pre-ARMED trade ideas. Artifacts here
are propose-only: they may ask Computer to perform live checks, but they must not include execution
intent, sizing, broker/account state, order parameters, live quotes, or any field that authorizes a
trade.

The schema supports two writer profiles:

- `writer=teammate`: offline/simulated sal-bot proposals with required `provenance`, `validation`,
  and `payload.offline_eval_refs`.
- `writer=computer`: Computer-generated propose-only outputs from `execution/alpha_pipeline.py`,
  with observed `simulated=false` signal provenance and conviction ranking fields. These are still
  not ARMED and cannot authorize execution.

The reviewer-facing JSON Schema is `schemas/proposed.schema.json`. The deterministic offline
validator mirrors it and adds content checks for Computer-only execution authorization fields.

Validate committed proposals with:

```sh
env -u PYTHONPATH python -m evals.proposed_validator runs/PROPOSED docs/integration/fixtures/proposed/example-proposed-offline.json docs/integration/fixtures/proposed/example-computer-alpha-pipeline.json
```

Only Computer may promote a proposal into `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, or
`runs/KILLED/` after connector-backed Charter review.
