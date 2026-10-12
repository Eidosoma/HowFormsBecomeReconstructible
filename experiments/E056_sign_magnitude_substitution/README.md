# E056 — sign/magnitude substitutions

**Complete and independently verified on 12 October 2026 at 00:08 UTC.**
Artifact closeout passed at **11:11 UTC**, after inspection of both scientific
figures. The additional v2 scheduling receipts also passed verification.
All 32 E055 blocks, 1,506 summaries, 221 original output files and 26 frozen
inputs were verified. Controls passed. The independent implementation replayed
all substitutions, diagnostics and every reader-state hash, covering **92,160
terminal cue observations**. There are 512 lineages per history, clustered in
32 independent source blocks; acquired records repeated across recipient slots
are not independent acquisitions.

In the primary shared-noise history, early capture and scattered injury:

| Record supplied to a fresh reader | Both-cue success |
| --- | ---: |
| Unstressed reference | 461/512 (90.04%) |
| Pulse-written record | 448/512 (87.50%) |
| Restore only unstressed signs | 448/512 (87.50%) |
| Restore only unstressed magnitudes | 461/512 (90.04%) |

Replacing magnitudes improved success by **2.54 percentage points**, with a
family-adjusted **99% interval [0.98, 4.30]**, under either choice of signs.
Replacing signs had zero estimated average effect, **[−0.98, 0.98]**, under
either choice of magnitudes. The observed factorial interaction was zero
**[0, 0]**. The frozen classifications are two positive magnitude effects and
three unresolved contrasts; zero estimates are not proof of null effects.

This supplies causal evidence that the placement of magnitudes in these
pulse-written records affects reconstruction. Signs remain important more
generally, as E054 demonstrated with different interventions. Equal aggregate
success does not establish identical lineage outcomes or complete restoration.
The hybrids receive the matched unstressed reference, so this does not establish
autonomous repair. The shared cohort and outcome-informed primary selection
also leave fresh-source confirmation outstanding.

The late shared-noise pulse/sham scores were **89.65%/89.84%**. The secondary
sham-adjusted improvement from delaying capture was **2.34 points [0.98, 3.91]**
(pointwise 95%). Independent-noise early scores were **94.73% pulse versus
96.09% sham**; restoring magnitudes matched the sham average, while restoring
signs matched the pulse average. All four acquired-record versions scored 100%
under scattered injury, and erased records scored zero. These comparisons use
new E056 reader streams; their percentages need not equal E055's.

[Scientific report](runs/substitution_v1/REPORT.md),
[independent audit](runs/substitution_v1/INDEPENDENT_AUDIT.json),
[artifact closeout](analysis/closeout_v1.json),
[scheduling closeout](analysis/schedule_closeout_v2.json),
[all-history figure](figures/substitution_v1/substitutions.png),
[primary contrasts](figures/substitution_v1/primary_contrasts.png).

The detached run took **2h10m including independent audit**, within its 4h26m
forecast. It used four single-thread workers on CPUs 0–3, launched on 11 October
at 21:58 UTC with PID 3521444. Startup verification matched all 26 frozen inputs,
four source/readiness/controller receipts and all four workers/logs before any
scientific outcomes were inspected.

[Job status](jobs/substitution_v1/status.json),
[verified launch](analysis/scientific_launch_verification_v1.json),
[frozen manifest](jobs/substitution_v1/manifest.json),
[retained forecast](analysis/forecast_v2.json),
[technical readiness](analysis/technical_v2.json).

This asks which changes in a disturbed body's outgoing record affect the next
body. Compare the original unstressed and pulse-written records with two hybrids:
restore only unstressed signs, or restore only unstressed magnitudes. Keep early
and late capture, all three histories and every E055 source case. Add an erased
control and test common fresh readers under three injury conditions.

The primary follow-up is shared-noise history at early capture under scattered
injury, selected because E055's secondary loss is now known. Five conditional
sign/magnitude effects and their interaction use family-adjusted 99% intervals.
This is mechanism testing on reused records, not fresh-source confirmation or
autonomous repair. E055's failed primary transfer-protection claim is unchanged.

- [Frozen design](PROTOCOL.md) and [settings](plan.py).
- [Source receipts](SOURCE_DATA.json).
- [Substitutions and reader](model.py), [independent replay](audit_model.py).
- [Inference](inference.py), [audit](audit.py), [twenty checks](tests.py).
- [Workflow](workflow.py), [qualification and closeout](analysis/prepare.py).
- [Prior E055 result](../E055_stress_capture_recovery/README.md) and
  [candidate list](../EXPERIMENT_LEADS.md).

All **20 synthetic checks passed**, including full independent packet/trajectory
replay and nonconstant factorial inference. The retained fixture and benchmark
each independently verified **1,506 statistical summaries**, all source
substitutions, every reader-state hash and diagnostic. Controls passed and all
four technical figures were inspected. Technical classifications remain null.

The fixture completed in 21.43 seconds (simulation/replay workers 6.46/8.33s).
The benchmark's simulation worker took 19.42s and independent replay 21.74s.
Its foreground launcher exited with code 143 before starting audit; the cause
was not established. The completed simulation and all frozen inputs were retained.
An explicit detached completion ran only its missing audit and figures; no
simulation was repeated. [Interruption record](jobs/benchmark_v1/interruption_v1.json)
and [completion record](jobs/benchmark_v1/status.json) preserve the event.

The initial six-worker readiness/forecast remains as v1. A subsequent launch
preflight found seven other busy numerical CPUs and stopped before creating a
scientific job. The current v2 receipts select **four workers**; the final launch
check found six others, giving ten within the twelve-CPU ceiling. A separately pinned
[scheduling controller](analysis/launch_v2.py) invokes the unchanged frozen stage
executor. The design, simulation, audit and inference code were not modified.
The forecast applies a threefold time margin to benchmark step/recipient/worker
scaling. Storage reserve is **0.95 GB**, below **31.20 GB** free when the resource
adjustment was selected.

[Decisions and operational history](DECISIONS.md),
[passing checks](analysis/tests_v1.log),
[fixture audit](runs/fixture_v1/INDEPENDENT_AUDIT.json),
[benchmark audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json).

The user's status request triggered inspection and closeout; no successor was
started. The next proposed test is a frozen confirmation on newly generated
source blocks, keeping E055's pulse and capture windows and E056's substitutions
unchanged. Test capture timing and the magnitude substitution jointly with a
declared primary family. Persistence through later rewriting is a separate
question. E055's failed primary claim remains unchanged.
