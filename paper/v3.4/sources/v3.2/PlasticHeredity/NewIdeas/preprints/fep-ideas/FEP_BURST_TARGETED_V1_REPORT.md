# Targeted reliability policies — detached startup checkpoint

**Status as of the single startup check, 31 October 2026 at 12:57:29 UTC:**
qualification passed and the main calculation started detached. No scientific
result, candidate selection, transfer outcome or independent readback has
been inspected for this checkpoint. This report is incomplete until those
artifacts have been checked; startup is not evidence of success.

The [prospective protocol](FEP_BURST_TARGETED_V1.md) follows the
[existing-pool infeasibility result](FEP_BURST_POOL_FEASIBILITY_V1_REPORT.md).
That certificate applies to the original policy pools and remains unchanged.

The new generating model retains 44 hidden states and the same paid-feedback
interface, costs, reversal prior and ten-task horizon. One supplied class
changes from constant persistence .75 to alternating .9/0; the other remains
independent errors. The model infers the class jointly with orientation and
current sensor error. This is a targeted generative-model change, not arbitrary
structure discovery or evidence that the unchanged model could solve the task.

Six new full planners and six paired reliability-freezing planners are
generated with the original penalties and loss on every reversal onset.
Each family is added to its original seven-policy pool. Exact selection over
the ten exposed profiles retains the hard stable budget and maximizes the
common budget/recovery margin. Original policy choices remain available, so
the expanded optimum cannot be worse. The ablated policy behavior and values
must reproduce the old ablated family exactly.

After selection is frozen, the pipeline tests eight new physical profiles:
constant persistence .1/.7, persistence beginning/ending after task 3 or 7,
and low/high alternating blocks of two transitions. Novelty was checked
against nineteen distinct earlier burst profiles. Every new profile includes
unchanged worlds and all ten genuine reversal onsets. Development and transfer
criteria remain separate; a failed development optimum remains a failed
diagnostic even if some new profiles pass.

Both FEP checks are retained: correlated-error false confidence and the
same-weight reliability-freezing intervention. Separately optimized ablated
pool outcomes are a distinct comparison. Previous selected mixtures, simple
controls, the previously selected best fixed schedule and matched ordinary
Bayesian planning are included. All purchased feedback is charged. The audit
distinguishes acquisition, interpretation and economic failure. Bayesian/VFE
inference remains the FEP mechanism; actions optimize the declared task costs.

Qualification passed **461 assertions** in **1.704 seconds**, covering all
273 short contingent trees, 72 short Bellman states, independent time-dependent
filter checks, reliability resets, stationary marginals and exact LP
reproduction with duplicate expansion. This is preflight qualification;
the full-horizon independent audit is still part of the detached pipeline.
All four new inputs were snapshotted, with **41 source/input identities** frozen.

The T=7 benchmark took .083139 seconds for the two planners and .025544 seconds
per graph/profile for independent diagnostic flow. The predeclared forecast
is **1,241.915 seconds**, about **20.7 minutes**, including verification.
It is a conservative forecast, not a completion promise. Because it exceeds
ten minutes, execution is detached with durable logs and no automatic polling.

| Startup property | Recorded value |
| --- | --- |
| Main start | 2026-10-31 12:57:28.383018 UTC |
| Startup check | 2026-10-31 12:57:29.257153 UTC |
| PID / session ID | 3895130 / 3895130 |
| CPU affinity | CPU 0 only |
| Priority | nice 10 |
| Detached | yes |
| Verified stage | GENERATION_START |

The launch uses one CPU, library threads one and `python -B`. Its expected
finish by the forecast is roughly 13:18 UTC, but completion must be established
from saved artifacts. The startup process was alive and had no exit code at
the one check. No later process or progress check was made for this checkpoint.

All generated files are under:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-targeted-v1/`.
The attempt is `attempt-01/`; launch output is `launch-attempt-01.log` outside
the attempt so changing process output cannot invalidate a scientific freeze.
`LAUNCH-attempt-01.json` and `STARTUP-attempt-01.json` record launch and the
single check. Immutable preparation records include FREEZE.json,
QUALIFICATION.json, LP_FIXTURES.json, NOVELTY.json and BENCHMARK.json.

The detached script records stage transitions in RUN_LOG.txt, freezes
candidates before TEST_STARTED.json, writes the complete result/manifest and
then invokes the independent verifier. A successful audit writes READBACK.json;
failures are preserved explicitly. Do not treat a manifest without successful
readback as a completed verified study.

On the next user-requested inspection, check completion or failure, verify
the preserved identities, report development and transfer separately, complete
both FEP interpretations and update this report and the six live notes.
No new experiment, retuning, manuscript integration or sister-project write
is queued. Earlier sealed studies and their adverse results remain unchanged.
