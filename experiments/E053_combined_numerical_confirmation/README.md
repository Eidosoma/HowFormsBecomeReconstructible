# E053 — combined numerical confirmation

**Complete and independently verified. The primary robustness criterion did not
pass.** Independent replay and figure generation finished on **11 October 2026
at 03:14 UTC**; artifact closeout passed at **12:38 UTC** on the requested status
check. All 32 simulation blocks are retained. The full workflow took 14h23m,
including 7h18m for independent replay; the simulation had finished on 10 October
at 19:55 UTC. No frozen settings or criteria changed.

The audited primary result is **472/512 (92.19%; 95% CI 89.06–94.92%)** under all
four stresses with independent rebuilding cue noise, versus **487/512 (95.12%;
92.58–97.27%)** for its unstressed reference. Both absolute lower bounds exceed
75%. The paired difference is **−2.930 percentage points [−5.078, −1.172]**:
its lower bound does not clear the prespecified −5-point threshold. Two of three
requirements pass, so combined numerical robustness is **not established**;
the loss classification is **unresolved**. This does not establish a loss
exceeding five points, either.

In the secondary matched-cue-noise comparison, combined stresses give
**326/512 (63.67%)** versus **421/512 (82.23%)** for the reference: **−18.55
points [−23.63, −13.28]**. The independent-noise configuration retains high
observed success under these stresses, but its five-point noninferiority remains
unresolved. Teaching, initial activity and final-assay cue pairing are unchanged;
this is not a test of fully independent randomness throughout the apparatus.

The independent audit replayed **655,360 body cue observations**, **556,032
terminal cue observations**, every mechanism diagnostic and **2,561 inference
summaries**. Closeout verified all **1,372 original scientific outputs**, frozen
inputs, technical receipts and figure provenance; the scientific figure was
visually inspected. E054 subsequently launched at the user's request on
11 October at 12:55 UTC and has since passed independent audit and closeout.
After a separate user instruction, [E055](../E055_stress_capture_recovery/README.md)
completed technical validation and launched its frozen stress/capture test on
11 October at 16:48 UTC.

[Audited report](runs/robustness_v1/REPORT.md),
[independent audit](runs/robustness_v1/INDEPENDENT_AUDIT.json),
[figure](figures/robustness_v1/numerical_robustness.png),
[closeout receipt](analysis/closeout_v1.json).
The earlier [full-cohort status receipt](analysis/full_cohort_pending_audit_v1.json)
is retained as a dated snapshot from before replay completed.

Earlier requested look at **10 October 15:55 UTC**: on **128 lineages per condition**,
independent rebuilding cue noise gives **122/128 (95.31%)** under all four stresses
versus **124/128 (96.88%)** for its unstressed reference. Matched cue noise gives
**77/128 (60.16%)** versus **111/128 (86.72%)**. These are descriptive partial counts,
not a primary qualification. All 25 frozen inputs match and 40 assay score arrays
were recomputed from saved port means; full trajectory replay was pending at that check.
The scientific cohort, criteria and run remain unchanged.
[Early report and full comparison table](analysis/early_look_v1/REPORT.md).

Fresh confirmation of E052's independent-cue-noise lead. The original rewriting
rule faces float32 arithmetic, grid rounding 2^-16, record noise SD 1e-4 and a
normalization floor 1e-4 **together**. Matched-noise controls and single/partial
combinations help identify interactions if performance changes.

Fixed design: **32 fresh independent blocks, 512 lineages per condition,
20 conditions, 32 damaged rebuilds**. The primary combined condition must have
a lower 95% success bound above 75% and remain within five percentage points
of its independent-noise reference. The reference must also clear 75%.
All three criteria must pass; other comparisons are secondary.

The lead and settings were selected after seeing E052. No earlier scientific
cases are pooled. Record noise precedes rounding, so the combined transmitted
packet stays on the declared grid. Initial activity, teaching and final-test
cue randomness remain paired.

Twenty-five scientific inputs froze at **2026-10-10T12:45:49.974418+00:00**.
All **22** synthetic checks passed on the first frozen attempt. The complete
excluded fixture passed independent replay of every body, channel, assay and
diagnostic, plus **2,561 inference summaries**. All **ten** unchanged E052
single-stress histories matched byte exactly at all 32 boundaries and terminal
assays. The fixture retained 70 original outputs; its figure was inspected.
The complete technical workflow took **69.06 seconds**, with simulation and
audit workers taking **29.28/32.18 seconds**. Scientific decisions remain null
in these shortened technical runs.

[Protocol](PROTOCOL.md), [fixed design](PLAN.json), [source provenance](SOURCE_DATA.json),
[production model](model.py), [independent replay](audit_dynamics.py),
[technical validation](analysis/technical_v1.json),
[E052 result](../E052_precision_normalization/README.md).


The complete benchmark also passed independent replay of all 2,561 summaries
and the ten E052 single-stress histories. Its 70 original outputs and inspected
figure are retained. Benchmark workflow time was **146.89 seconds**; simulation
and audit workers took **68.65/73.16 seconds**. Storage reserve **7,819,277,120
bytes** was below **48,617,480,192 bytes** free at scientific preflight.

Launched PID **2854358** at **2026-10-10T12:51:04.016948+00:00**, eight workers
on CPUs 0–7, one numerical thread each, stdin `/dev/null`. The single bounded
startup check passed at **12:51:04.598899 UTC**, verifying the detached session,
all 25 frozen inputs, scientific configuration and eight worker logs. Two other
single-thread numerical workers and a test process restricted to two CPUs were
active: a total capacity of twelve, within the shared ceiling.

The scientific run retained **655,360 body** and **556,032 unique terminal cue
observations**, with **1,372 original scientific outputs** verified. Simulation
was followed by independent replay, inference verification and figures. Status
checks follow user requests; no automatic polling, restart or successor.

[Benchmark forecast](analysis/forecast_v1.json),
[working ETA](analysis/operational_eta_v1.json),
[capacity snapshot](analysis/resource_preflight_v1.json),
[startup verification](analysis/scientific_launch_verification_v1.json),
[scientific job status](jobs/robustness_v1/status.json).
