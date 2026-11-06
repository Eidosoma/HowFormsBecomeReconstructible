# E119 — duration of the pruning reversal

**Complete; reviewed 2 November 2026.** Under repeated renewal injury, pruning
gives +6.787 points immediately, −4.736/−4.492 after one/two rewrites, and
−0.928/−0.586 after three/four. The cost weakens, but the frozen ±3-point
simultaneous equivalence test does not establish catch-up. Without further
renewal injury no successor penalty is resolved. Cumulative failures and all
individual gains/harms remain. [Interpretation](INTERPRETATION.md).

Finished **1 November 21:04:52 UTC**, **7h35m15s**; all 32 blocks and every new
state independently replayed. [Closeout](analysis/closeout_v1.json) passed:
**1,378 outputs / 55 inputs** verified, figure inspected, 2.656 GB retained.

## Launch record

**Scientific run launched 1 November 2026, 13:29:37 UTC.** `duration_v1`,
PID **2922651**, two workers on CPUs 0–1. Startup passed **13:29:40 UTC**;
55 inputs frozen. Expected **5h30m35s** (about 19:00 UTC); conservative
**16h25m44s**. No scientific outcomes inspected at launch.

All 13 shared checks pass, including byte-exact archived E077 writer replay.
The full-width `benchmark_v2` completed in **88.41s**: **104 outputs** verified,
479,232 new record-steps independently replayed, 2,880 condition rows and 1,152
mechanism rows retained. Figure inspected; all case bytes match the initial
benchmark after exact duplicate assessment reuse. Original benchmarks remain.

Follow all 32 original E077 source pairs through four actual rewrites, with and
without additional renewal injury. Prune once, transmit failures, independently
assess generations 0–4, and require ±3-point equivalence to claim convergence.
Retain useful absolute performance, recovery time, accumulated failures,
re-isolation, coupling/capture diagnostics and every individual harm.

[Protocol](PROTOCOL.md), [shared implementation](experiment.py),
[data dictionary](DATA_DICTIONARY.md), [forecast](analysis/forecast_v1.json),
[startup](jobs/duration_v1/startup.json),
[reviewer and manuscript handoff](../REVIEWER_2026-11-01_DELAY_AND_REGIME_PLAN.md).

Shared runner: `bash run_python.sh E119_reversal_duration/run.py` with
`--study duration`. E120 and E121 have separate source registries, scientific
freezes, run directories and results. No automatic successor is configured.
