
## 2026-05-20T20:24:55+00:00Z
Binding component: **pr_format**.
Impact: E-REG-02 (falsifiers per PR) and E-REG-03 (pre-registered targets per PR) are failing at scale, suggesting PR schema/formatting is blocking downstream validators.
Unblock: enforce required PR fields + run-all-falsifiers hook in PR template / CI; auto-populate targets block.

## 2026-05-21T04:10:36Z
- binding_component: pr_format (consecutive=2)
- note: HPR stub drafted/updated; unblock by enforcing PR template/required fields + running full falsifier set + CORPSES entries.
