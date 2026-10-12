# E004 — fresh confirmation

[Report](runs/confirmation_v1/REPORT.md) · [Protocol](PROTOCOL.md) ·
[Audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json)

The original complete-sequence criteria passed on 32 fresh heterogeneous blocks.
All 128 founders were retained; 107 met formation criteria. Terminal own-record
specificity was +1.86 [1.22, 2.56] percentage points, with 31/32 positive block
means. Renewal still lost 5.42 points relative to protected copies.

This confirms the heterogeneous result on new founders within the same model
and codebase. Dynamics, controls, measurements, and criteria were unchanged.
The independent audit reproduced all 10,240 observations and intervals. Main
runtime: 49.82 seconds. Source snapshots and raw data are under `runs/`.

From the experiments root, the following reproduces the same cohort into a
new directory; it does not create another independent confirmation:

```bash
bash run_python.sh E004_fresh_confirmation/run.py --workers 12 --output E004_fresh_confirmation/runs/NEW_RUN
bash run_python.sh E004_fresh_confirmation/audit.py E004_fresh_confirmation/runs/NEW_RUN
```
