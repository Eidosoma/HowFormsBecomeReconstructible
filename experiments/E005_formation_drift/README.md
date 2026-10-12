# E005 — saved-state formation diagnostic

[Report](runs/diagnostic_v1/REPORT.md) · [Protocol](PROTOCOL.md) ·
[Individual results](runs/diagnostic_v1/founders.csv) ·
[FFT audit](runs/diagnostic_v1/INDEPENDENT_AUDIT.json)

Simple translation did not account for the homogeneous formation failure.
Alignment fitted in two quarters gave no aggregate improvement in the other
two; even optimistically fitting translation directly to the original
half-window comparison left 17/32 temporal failures, versus 19/32 originally.
Spatial organization measurements remained fairly steady across quarters.

This is a post-hoc diagnostic of all saved founders, not new simulation or a
revised success criterion. It leaves deformation and temporal fluctuation as
possible contributors without identifying one uniquely. Original source files
and verdicts remain unchanged. Runtime: 2.20 seconds.

```bash
bash run_python.sh E005_formation_drift/tests.py
bash run_python.sh E005_formation_drift/run.py --output E005_formation_drift/runs/NEW_RUN
```
