# E057 — fresh confirmation of capture timing and magnitude substitution

**Scientific run launched detached on 12 October 2026 at 11:38:59 UTC.** PID
**3756226**, eight single-thread workers on CPUs 0–7. Startup verification passed
at **11:39:55 UTC**, matching all 37 frozen inputs, five predecessor/readiness
receipts and all eight workers/logs. No scientific outcomes were inspected.

The conservative forecast is **5h15m including independent audit**, approximately
**17:00 UTC today** (12 October), subject to machine contention. The launch
resource sample found no other busy numerical processes, so eight workers fit
within the shared twelve-CPU ceiling. The storage reserve is **12.81 GB**, below
the **27.34 GB** free at launch.

[Job status](jobs/confirmation_v1/status.json),
[verified launch](analysis/scientific_launch_verification_v1.json),
[frozen manifest](jobs/confirmation_v1/manifest.json),
[forecast](analysis/forecast_v1.json),
[technical readiness](analysis/technical_v1.json).

This follows E055's secondary shared-noise timing effect and E056's controlled
magnitude substitution result. Generate **32 new blocks (38000–38031)** with
four founders and four recipients, **512 lineages per history**. Every record
is newly acquired; shared- and independent-noise histories each undergo 32
rebuilds before the unchanged E055 pulse/capture and E056 substitutions. The
acquired-record history remains a comparison group. Keep all failed cases.

Four primary requirements, for shared-noise records and scattered injury, ask
whether the disturbance causes an early loss, whether waiting before capture
reduces that loss after accounting for sham drift, and whether restoring
magnitudes helps under each of the two sign choices. All four adjusted interval
lower endpoints must exceed zero. The frozen family uses paired whole-block
bootstrap and **98.75% intervals** (nominal 95% Bonferroni family coverage).

This tests directional effects on fresh sources. It does not change E055's
failed five-point criterion, test autonomous repair, or treat an unresolved sign
effect as evidence that signs are irrelevant. The pulse, capture windows,
substitutions and reading apparatus remain fixed. No prior cases are pooled.

- [Frozen protocol](PROTOCOL.md) and [settings](plan.py).
- [Freshness register and technical references](SOURCE_DATA.json).
- [Source generator](source_model.py) and [independent source equations](source_audit.py).
- [Full pipeline](run.py), [independent audit](audit.py), [inference](inference.py).
- [Sixteen checks](tests.py), [passing log](analysis/tests_v1.log), [frozen inputs](analysis/freeze_v1/manifest.json).
- [Workflow](workflow.py), [qualification and closeout](analysis/prepare.py), [figures](plot.py).
- [Decisions](DECISIONS.md), [E055](../E055_stress_capture_recovery/README.md), [E056](../E056_sign_magnitude_substitution/README.md).

All **16 checks passed**. The retained fixture completed in **19.42 seconds** and
the benchmark in **50.61 seconds**. In each, all 32 technical renewal boundaries
matched the corresponding original E051 branches, independent replay passed
**1,868 summaries**, and controls passed. Both pairs of figures were inspected.
The scientific pipeline retains **92,160 terminal cue observations**, **65,536
source-body cue observations** and **18,432 perturbation-body cue observations**.

The technical block 900041 is excluded from science. Full independent replay
verifies acquisition, source chains, pulse/body states, transmitted packets,
substitutions, reader trajectories and block inference. The first
development test found only a signed-zero difference in the independent source
audit's ordinary-coactivity reduction; it was corrected before freezing. Both
development logs remain retained.

[Fixture audit](runs/fixture_v1/INDEPENDENT_AUDIT.json),
[benchmark audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json).

Long execution runs detached within the shared twelve-CPU budget, with one
numerical thread per worker. Scientific status checks are user-requested; there
is no automatic restart, polling or successor.
