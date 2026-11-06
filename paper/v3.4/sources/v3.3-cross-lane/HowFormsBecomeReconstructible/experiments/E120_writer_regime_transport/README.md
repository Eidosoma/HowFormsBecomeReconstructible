# E120 — writer-regime transport

**Complete; reviewed 2 November 2026.** The independent-noise tolerant primary
fails only its successor-cost gate: immediate pruning benefit +7.178 points,
later contrast +1.904 [−0.439, 4.199], pointwise 95%. All usefulness and retention
gates pass. Matched-exact writing retains a −5.908-point successor penalty;
independent-exact writing gives +0.146, unresolved. This does not establish
the reversal in the changed regime. [Interpretation](INTERPRETATION.md).

Finished **1 November 17:18:26 UTC**, **3h48m25s**; all 32 blocks and every new
state independently replayed. [Closeout](analysis/closeout_v1.json) passed:
**641 outputs / 55 inputs** verified, figure inspected, 1.176 GB retained.

## Launch record

**Scientific run launched 1 November 2026, 13:30:00 UTC.** `transport_v1`,
PID **2922955**, two workers on CPUs 2–3. Startup passed **13:30:05 UTC**;
55 inputs frozen. Expected **2h22m16s** (about 15:52 UTC); conservative
**7h00m48s**. No scientific outcomes inspected at launch.

All 13 shared checks pass. Full-width `benchmark_v2` completed in **39.29s**:
**80 outputs** verified, 217,088 new record-steps independently replayed,
2,304 condition rows and 576 mechanism rows retained. Figure inspected;
every case score is byte-identical to the retained initial benchmark.

On the same 32 archived E077 starting pairs, cross matched/independent ongoing
cue noise with exact/1e−4-tolerant capture. Resets remain shared, floor zero,
float64 arithmetic/storage. Tolerance comparisons reuse the identical supplying
body. Keep both endpoints, useful-performance gates and individual harms.

[Protocol](PROTOCOL.md), [implementation](../E119_reversal_duration/experiment.py),
[forecast](analysis/forecast_v1.json), [startup](jobs/transport_v1/startup.json),
[reviewer handoff](../REVIEWER_2026-11-01_DELAY_AND_REGIME_PLAN.md).
Runner: `bash run_python.sh E119_reversal_duration/run.py ACTION --study transport`.
