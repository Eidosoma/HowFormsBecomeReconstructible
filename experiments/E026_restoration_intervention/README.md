# E026 — which changes in rebuilt records preserve function?

Status: **complete; independent audit and artifact closeout passed**.
The diagnostic `restoration_v1` finished **21 September 2026 at 20:11:59 UTC**,
including independent replay and figures, in **110.03 minutes**. All 32 source
blocks were retained. The verdict is `RESTORATION_DIAGNOSTIC_COMPLETE`;
both focal restoration benefits have interval lower bounds above ten points.
The subsequent [E027 selective-renewal test](../E027_selective_renewal/README.md)
is complete and audited: preserving every nonzero surviving weight during
renewal failed to improve on full rebuilding in a fresh cohort.
The user authorized the four-packet comparison proposed in E025's
[rebuilding-leads note](../E025_rewriting_confirmation/analysis/REBUILDING_LEADS.md).
The protocol and all 21 scientific inputs were frozen before simulation.

This intervention reuses **all 32 E025 blocks 23000–23031**, 128 founders and
**512 lineages**. It tests contributions of restored connections, changed
values on surviving connections, and their combination. This is a **post hoc
diagnostic of final packets on an existing cohort**. Fresh confirmation and
the mechanism producing these connections across renewals remain untested.

Restored connections make a large causal contribution in this terminal assay.
With the local-strength receiver and scattered terminal damage, both-cue
success was:

| Final packet | Successes | Success, % [pointwise 95% interval] |
| --- | --- | --- |
| Existing cumulative-erasure copy | 318/512 | 62.11 [56.45, 67.77] |
| Copy plus restored connections | 425/512 | **83.01 [78.71, 87.11]** |
| Rebuilt, with restored connections removed | 312/512 | 60.94 [55.66, 66.21] |
| Full rebuilt record | 410/512 | 80.08 [75.98, 83.98] |

Adding restored connections to the copy gained **20.90 points [16.99, 25.00]**.
Removing them from the rebuilt record lost **19.14 points [15.23, 23.44]**.
Both focal effects exceed the original rebuilt-versus-copy difference of
**17.97 points [13.48, 22.66]** in mean magnitude. These comparisons include
the receiving reader's recomputed normalization after the intervention.

Changing surviving values offered no extra benefit here. With restoration
present, replacing copied survivors with rebuilt survivors reduced success
by **2.93 points [1.17, 4.88]**. Without restoration, that contrast was
**−1.17 points [−2.93, 0.39]**, which is unresolved, not evidence of equivalence.
The interaction was **−1.76 points [−3.32, −0.20]**. These are post hoc,
pointwise intervals, without adjustment for the wider set of comparisons.

The restoration benefit also appears with intact and square-lesion receivers:

| Final packet | Intact success, % | Scattered success, % | Square-lesion success, % |
| --- | --- | --- | --- |
| Copy | 91.80 | 62.11 | 89.26 |
| Copy plus restored connections | 97.85 | 83.01 | 97.07 |
| Rebuilt, restored connections removed | 88.67 | 60.94 | 87.11 |
| Rebuilt | 94.14 | 80.08 | 94.34 |

With local normalization, copy, copy-plus-restored and rebuilt each pass all
24 original individual-cue/control gates. Removing restoration from the rebuilt
record passes 23/24; the negative-rule scattered accuracy gate fails. These
context gates differ from both-cue success and are not an overall diagnostic
pass/fail criterion. All four fixed-four-reader packets fail the original
absolute reliability requirements; scattered both-cue success stays between
1.76% and 5.47%. The strong result remains conditional on the receiving reader.

The next practical lead is to test preserving surviving values while rebuilding
newly available connections during actual renewal, with a frozen comparison
on fresh blocks. The better terminal hybrid borrows connections produced by
full rebuilding; its 83% result does not establish that such a selective renewal
policy can generate them. E027 tested this policy prospectively and found
55.7% scattered-terminal success versus 79.5% for full rebuilding. Its rule
preserves even tiny nonzero repairs; whether allowing new connections to be
rewritten again enables useful maturation remains an open mechanistic question.

Masks define surviving coordinates as those present through every renewal,
and restored coordinates as those previously erased but physically available
in the third body. Every weak restored value is retained without thresholding.

| Packet | Values on surviving coordinates | Values on restored coordinates |
| --- | --- | --- |
| Existing copy | Copied | Zero |
| Copy plus restored connections | Copied | Rebuilt |
| Rebuilding with restoration removed | Rebuilt | Zero |
| Full rebuilt record | Rebuilt | Rebuilt |

The two focal contrasts measure what changes when restored connections are
removed from the rebuilt record and when they are added to the copy. Effects
of changed surviving values and their interaction are also reported. Intervals
are pointwise whole-block bootstrap intervals; an unresolved difference does
not establish equivalence or absence.

All four packets receive paired births, noise, injuries and shuffles in the
unchanged E023 terminal assay. Both receiving readers, three injury panels,
seven record/communication arms and both opposing cues are retained:
**eight terminal panels and 172032 individual scores**. Local denominators
are recomputed after each intervention and all controls. No new teaching or
renewal is run. Both unchanged endpoints must reproduce every saved terminal
packet, denominator, state and trace exactly.

All **five fixtures passed on the first attempt in 7.71 seconds** (8.00 with
launcher overhead). They check the mask partition and precise hybrid values,
pairing and original endpoint replay, contrast direction/interaction,
denominator recomputation, and independent end-to-end reconstruction. The
fixture audit reproduced all **2688 scores**, intervals and context gates
in **2.69 seconds**, using E025's excluded short fixture 900025.

The full-duration benchmark used E024's excluded source 900024, one lineage
per founder and one worker. It ran from **18:14:24 to 18:17:23 UTC on
21 September**, taking **178.90 seconds** against its retained 510.78-second
forecast. Worker time was **85.62 seconds**, simulation/reporting **86.17
seconds**, and independent audit **90.93 seconds**. Every update and all
**1344 scores** reproduced exactly, including both original endpoint arrays.
Its figure was inspected. These technical outcomes did not select the design.

The measured conservative full-run forecast is **7152.00 seconds (119.20
minutes; about two hours)** on **eight workers with one numerical thread
each**, including independent replay and figures. Storage with a 1 GiB reserve
is **1696620416 bytes (1.58 GiB)**, below **11.09 GiB** available at prelaunch.
All **28 fixture / 29 benchmark original outputs**, 21 scientific inputs,
CSV row counts, figure/runtime references and **136 required source raw files**
passed verification at **18:19:21 UTC**. E014–E025 frozen inputs and the earlier
diagnoses remain unchanged. No prior job was active.

The run launched at **18:21:57 UTC**, PID **889387**. The bounded host startup
check passed at **18:21:58 UTC**, with all eight
worker logs present, the supervisor in its own session and reparented to PID 1,
CPU affinity 0–7, and one numerical thread. All frozen job/run inputs, source
mode, 32 blocks and eight panels matched; no failure artifact existed. No
restart was needed. The full run ran detached under
[RUN_POLICY.md](../RUN_POLICY.md), with status checks requested by the user.

Simulation and reporting took **2872.07 seconds (47.87 minutes)**, and independent
replay took **3727.59 seconds (62.13 minutes)**. The complete workflow took
**6601.99 seconds**, **550.00 seconds (9.17 minutes)** below its forecast.
The independent auditor reproduced every receiving update and all **172032
individual scores**, recomputed intervention/control denominators, verified
source isolation, and reproduced all contrasts, intervals and context gates.
Both unchanged endpoints reproduced all original packets and terminal arrays
exactly. Closeout checked all **28 fixture / 29 benchmark / 153 diagnostic
original outputs**, all 21 frozen scientific inputs, the 136 required source
raw files, CSV row counts and operational/figure references. The scientific
figure was inspected. No experiment job remained active at E026 closeout.

Source hashes are fixed in [SOURCE_DATA.json](SOURCE_DATA.json). The new
auditor independently reconstructs the interventions and replays every
receiving update and score. Prior teaching/renewal audit provenance is checked;
those histories are not rerun. Prior results and frozen scientific inputs
remain unchanged. No automatic successor is configured.

[Scientific report](runs/restoration_v1/REPORT.md),
[full statistics](runs/restoration_v1/summary.json),
[scientific figure](figures/restoration_v1/restoration_intervention.png),
[independent audit](runs/restoration_v1/INDEPENDENT_AUDIT.json),
[closeout verification](analysis/closeout_v1.json),
[artifact verifier](analysis/verify_closeout.py).

[Frozen protocol](PROTOCOL.md), [fixture receipt](analysis/fixtures_v1.json),
[fixture audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[benchmark forecast](analysis/benchmark_forecast_v1.json),
[benchmark independent audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[benchmark figure](figures/benchmark_v1/restoration_intervention.png),
[full-run forecast](analysis/forecast_v1.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[startup verification](analysis/launch_verification_v1.json),
[completed diagnostic status](jobs/restoration_v1/status.json),
[diagnostic workflow log](jobs/restoration_v1/workflow.log),
[benchmark status](jobs/benchmark_v1/status.json),
[benchmark log](jobs/benchmark_v1/workflow.log).
