# E114 — matched-amplitude shared/cue component intervention

**Complete and verified.** `matched_v1` finished **28 October 2026 at
22:59:35 UTC**, in **17 min 14.75 s**, within the 22-minute forecast.
User-triggered closeout passed at **29 October 11:56:49 UTC**: **845 output
hashes / 87 frozen inputs** verified, figure inspected, **519.26 MB** retained.

The sole mixture primary is **UNRESOLVED**: matched gross m/d sensitivities
are **0.276 / 0.460 points**, difference **−0.184 [−0.547, 0.000]**. The upper
bound is exactly zero; the entire excess comes from one row in one source.
The shared-component ordering did not persist in the point estimate, but a
reversed ordering is also unconfirmed. Native excess is −0.709 [−1.678, 0.000],
secondary. All **50 gains / 34 losses** across 84 dependent transitions remain.
See [interpretation and manuscript wording](INTERPRETATION.md),
[report](runs/matched_v1/REPORT.md), [figure](runs/matched_v1/matched.png)
and [closeout](analysis/closeout_v1.json).

E113 found that natural shared-component changes were about 17 times larger
than cue-component changes. E114 attenuates both directions to one common
smaller mean absolute size, pooled across C/F, and compares their effects in
the same complete E112 cohort. The ranges are centered on their original O/N
midpoints, so neither stream is favored. No direction is amplified.

The sole primary is eligible-mixture gross m−d sensitivity of C−F success.
All 32 sources, 4,096 identities, 554 eligible rows, earlier endpoints and
individual gains/harms remain. This is a controlled intervention on known
sources, not fresh-source confirmation; E112's unresolved primary is unchanged.
Every new continuation is independently replayed. The complete inventory is
**8,864 variant continuations / 9,076,736 later variant updates**, plus independent
replay. There are **87 frozen inputs**, 681 pinned scientific source files and
a **3.03 GB** storage reserve; launch had **13.12 GB** free. Four other busy
workers were sampled, within the shared twelve-CPU ceiling.

Expanded analytic/excluded [tests](analysis/tests_attempt_002.json) passed in **15.64 s**:
independent normalization and initial fields, O/N symmetry, zero targets,
both attenuation directions, all eight full-size archived resumptions exactly,
independent short matched reads, corruption rejection, empty batches, strict
thresholds, all success-transition categories and clustered-denominator handling.
An additional signed-zero midpoint case was fixed before scientific freeze;
the [original benchmark and issue evidence](analysis/signed_zero_issue_v1.json)
remain. The primary, norm, sample and intervention design were unchanged.

The qualified [excluded benchmark v2](runs/benchmark_v2/REPORT.md) passed in
**35.59 s**: 224 variant continuations / 57,344 steps independently replayed,
all 14 eligible rows retained, **152 output hashes** verified, figure inspected.
Maximum actual norm mismatch was **2.17e−18**, component leakage **1.11e−16**;
all injected states were valid without clipping. Excluded outcomes are not
scientific evidence for the component ordering.

[Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[decisions](DECISIONS.md), [source registry](SOURCE_DATA.json).
[Qualification](analysis/qualification_v1.json), [forecast](analysis/forecast_v1.json),
[sample freeze](SAMPLE_FREEZE.json), [startup](jobs/matched_v1/startup.json),
[launch/log directory](jobs/matched_v1), [durable status](runs/matched_v1/STATUS.json).
The bounded startup and user-triggered closeout followed
[RUN_POLICY.md](../RUN_POLICY.md). The run has exited. The user subsequently
authorised [E115](../E115_original_anchor_components/README.md): retain original
starting states at the same matched perturbation sizes. Its first launch
failed the CPU guard before any new readers. The unchanged experiment was
resubmitted on 30 October at 14:16 UTC; startup now verifies the reader stage.
E114's primary and frozen artifacts remain unchanged.
