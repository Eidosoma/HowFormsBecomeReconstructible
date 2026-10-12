# E052 — precision and normalization robustness

**Complete and independently verified: NUMERICAL_ROBUSTNESS_NOT_ESTABLISHED.**
Finished **10 October 2026 at 09:10 UTC**, including independent replay and
figures. Closeout passed at **11:53 UTC** on the user's requested status check.

The prespecified nine-part primary criterion under matched rebuilding cue noise
was not met: two requirements passed. Fixed-grid quantization, record noise
SD 1e-4 and denominator floor 1e-4 each demonstrate a loss exceeding five
percentage points. The float32-arithmetic comparison remains unresolved under
the five-point noninferiority criterion; it does not demonstrate a five-point
loss. These distinctions are preserved in the formal result.

Final native-reader scattered-injury both-cue success after 32 rebuilds, on
**512 lineages per condition in 32 fresh independent blocks**:

| Regime | Matched cue noise | Noise correlation .999 | Independent cue noise |
| --- | ---: | ---: | ---: |
| Reference | 427/512 (83.40%) | 491/512 (95.90%) | 494/512 (96.48%) |
| Stored float32, float64 calculation | 425/512 (83.01%) | 491/512 (95.90%) | 494/512 (96.48%) |
| Float32 calculation and record | 416/512 (81.25%) | 491/512 (95.90%) | 494/512 (96.48%) |
| Grid spacing 2^-16 | 41/512 (8.01%) | 434/512 (84.77%) | 489/512 (95.51%) |
| Grid spacing 2^-12 | 0/512 (0.00%) | 389/512 (75.98%) | 479/512 (93.55%) |
| Record noise SD 1e-4 | 326/512 (63.67%) | 441/512 (86.13%) | 482/512 (94.14%) |
| Denominator floor 1e-4 | 356/512 (69.53%) | 471/512 (91.99%) | 490/512 (95.70%) |
| Denominator floor 1e-2 | 95/512 (18.55%) | 400/512 (78.12%) | 481/512 (93.95%) |

The paired reference has a 95% interval of **[78.71,87.70]%**. The primary
challenged-minus-reference differences, in percentage points, are:

- Float32 calculation: **−2.15 [−5.66,1.37]**, unresolved.
- Grid spacing 2^-16: **−75.39 [−79.88,−70.70]**, loss exceeds five points.
- Record noise SD 1e-4: **−19.73 [−25.78,−13.48]**, loss exceeds five points.
- Denominator floor 1e-4: **−13.87 [−18.75,−8.98]**, loss exceeds five points.

This is not a general collapse on switching to float32: stored float32 alone
changes paired performance by **−0.39 points [−0.98,0.00]**. Fixed grids can
erase small nonzero weights that floating-point representations still retain.

Independent cue noise provides a strong **secondary** lead. For those same four
primary-level numerical challenges, differences from the independent-noise
reference are respectively **0.00 [0.00,0.00]**, **−0.98 [−2.15,0.20]**,
**−2.34 [−3.71,−0.98]**, and **−0.78 [−1.95,0.20]** points. These are
pointwise comparisons, not a replacement primary or a new joint qualification.
Across all eleven independent-noise regimes, observed success ranges from
92.97% to 96.48%. The stronger record-noise SD 1e-3 contrast is
**−3.52 [−5.47,−1.56]** points and does not establish the five-point allowance.

Changing only the final reader does not remove most of the loss in paired floor
histories. At floor 1e-4, common-reader success is **362/512 (70.70%)** versus
native **356/512 (69.53%)**; at floor 1e-2 it is **106/512 (20.70%)** versus
**95/512 (18.55%)**. This shows that the effect is not confined to the final
reader's floor. It does not prove irreversible information loss or isolate a
causal mechanism. For record-only changes native/common readers are identical
and explicitly deduplicated; their equality is not an independent rescue test.

The supported conclusion is sensitivity of the original matched-noise regime
to these declared representation, corruption and normalization changes, alongside
much higher performance with independent rebuilding cue noise. Teaching and
terminal-assay cue randomness remain paired. Combined numerical challenges,
independent teaching/assay noise and indefinite heredity remain untested.
Fresh confirmation of independent-noise performance under combined numerical
challenges is now running as [E053](../E053_combined_numerical_confirmation/README.md),
launched on 10 October at 12:51 UTC. It uses fresh cases and a fixed combined-stress
primary; E052 remains a completed study with its original failed primary.

[Full result table and intervals](runs/robustness_v1/REPORT.md),
[independent audit](runs/robustness_v1/INDEPENDENT_AUDIT.json),
[scientific figure](figures/robustness_v1/numerical_robustness.png),
[closeout verification](analysis/closeout_v1.json).

Tests whether E041's rebuilding mechanism remains useful when tiny connections
are rounded, corrupted or weakened by a minimum normalization denominator.
E051's experiment and frozen files are unchanged.

The fixed design has **32 fresh blocks, 512 lineages per condition, 32 rebuilds
and 33 matched conditions**: eleven numerical regimes under paired, almost paired
and independent rebuilding cue noise. The original exact-zero writer is fixed.

The comparisons separate stored float32 values from float32 reader/writer
calculations, add two fixed grid resolutions and two record-noise levels, and
test three denominator floors. An additional noise control can create connections
from zero values while keeping physical erasures intact. Each final record is evaluated with its native
reader and the original reader to help locate the effect.

Four declared challenges under paired cues form the main robustness test:
float32 computation, grid spacing 2^-16, record-noise SD 1e-4 and floor 1e-4. Each
must remain within five percentage points of reference performance, with an
absolute lower 95% bound above 75%; the reference must also meet that absolute
threshold. Failure to establish this joint criterion is not automatically
evidence of a demonstrated loss. Other levels and pairing interactions are
secondary. Settings were selected independently of E051 scientific outcomes.

Authorized to implement, validate and launch on 9 October 2026. The model and
independent auditor now implement the original planning matrix without changing
its numerical settings, cohort, writer or primary criteria. All 18 synthetic
checks passed on the first frozen attempt. The complete excluded fixture also
passed independent replay of all 32 generations, typed calculations, channels,
assays, diagnostics and 4,084 inference summaries. All three reference histories
reproduce E051's excluded records and scores byte exactly. The fixture retained
70 original outputs; its figure was inspected. The complete benchmark then
passed the same independent replay and three-reference compatibility checks,
retaining another 70 original outputs. Its figure was inspected as well.

Twenty-five scientific inputs froze at **2026-10-09T12:41:34.565067+00:00**.
The fixture simulation worker took **38.96 seconds** and the independent audit
worker **43.02 seconds**; all technical checks, fixture, replay and figure took
**90.36 seconds** in total. Technical scientific decisions are null; the short
reader's zero terminal performance is not a scientific failure.

The benchmark completed in **209.76 seconds**, with simulation and audit workers
**99.88/104.09 seconds**. The frozen full-workflow forecast is **156,769.64 seconds**;
storage reserve **12,347,466,368 bytes** is below **58,894,319,616 bytes** free at
preflight. The original working ETA used the unbuffered benchmark scaling and
E051's completed workflow, and remains retained separately from the conservative
forecast. Actual complete workflow time was **73,352.62 seconds (20h22m33s)**;
the independent audit took **38,173.82 seconds (10h36m14s)**.

Launched PID **2394523** at **2026-10-09T12:47:56.343891+00:00**, eight workers
on CPUs 0–7 with one numerical thread each and stdin `/dev/null`. The single
bounded startup check passed at **12:47:56.906101 UTC**, verifying the detached
session, all 25 frozen inputs, all eight worker logs and the scientific cohort
and settings. The shared capacity snapshot found two other single-thread
numerical workers: ten workers total, within the twelve-CPU ceiling.

The completed independent audit verified **1,081,344 body cue observations**,
**771,072 unique terminal cue observations**, all dynamics, channels and
diagnostics, and **4,084 inference summaries**. Closeout verified **1,372 original
scientific outputs**, all 70 outputs in each technical run, all 25 frozen inputs,
job receipts and figure provenance. The scientific figure was inspected.
Scientific retained data total **7,947,774,601 bytes**; free space at closeout
was **48,809,553,920 bytes**. No successor was started during closeout; E053
was authorized and launched separately afterward.

Float32 calculations run in separate typed arrays; offline scores always use
float64. The native/common assay mapping computes 50 unique panels per horizon,
plus an unmodified acquisition panel at h0. Records receive exactly one channel
application at acquisition and after each of 32 writes. Diagnostics track
denominator floors, channel errors, subnormals, zero products and the survival
of newly repaired connections into the next body.

The original draft and PLAN.json remain preserved as planning records; their
planning-only operational flags are superseded by the final protocol and job
receipts. Long execution follows RUN_POLICY, with no automatic status polling
or successor.

[Final protocol](PROTOCOL.md), [original draft](DRAFT_PROTOCOL.md),
[condition matrix and parameters](PLAN.json), [model](model.py),
[independent replay](audit_dynamics.py), [auditor](audit.py),
[technical validation](analysis/technical_v1.json),
[benchmark forecast](analysis/forecast_v1.json), [working ETA](analysis/operational_eta_v1.json),
[startup verification](analysis/scientific_launch_verification_v1.json),
[second-reviewer assessment](../REVIEW_2026-10-08_SECOND_REVIEWER.md).
