# L23 — Causal local contact intervention, D084

Status: **COMPLETE and independently checked on the user's status request**.
Finished **13:05:57 UTC, 2026-09-10**; first inspection **15:13:07 UTC**.
No polling between detached launch and the user's request.
L23 remains `MIXED`, `STRESS_TESTED`. L22 stays parked at D080.

**Main finding:** local diffusion across donor joins is a causal contributor
to composition error in this fixed assay. Halving join links reduces matched
checkerboard standardized composite error by **.048409/.039678** at the two
norms; composition rescue is **.029590/.021270**, and its advantage over the
matched internal-edge manipulation is **.035008/.022990**. All three contrasts
are positive in all sixteen blocks after averaging the twelve pairs. Full cuts
give larger pooled benefits. The single-donor comparator improves too: this
is not an apparent rescue manufactured by damaging that comparator.

CD at the primary norm remains an exception for standardized composition
rescue/contact specificity, despite an absolute composite improvement. The
half-dose record-off specificity has one negative block at each norm. This
is stronger than D083's localization evidence, not a universal law, learned
boundary address, proof of complete isolation or hereditary renewal.

The user approved the completed [D083 recommendation](L23_SEAM_LOCALIZATION_2026-09-09.md)
with “let's go” on 2026-09-10. The [new protocol](../protocols/L23_CONTACT_INTERVENTION_V1.md)
is a separately frozen, outcome-informed causal test, not fresh replication.

## Plain-language question

Are the pieces disturbing one another through their joins? We now weaken
links across those joins while leaving the pieces and instructions in place.
We compare that with weakening the same link pattern inside the pieces.
The original model and half-strength/full-cut versions give five arms.

This tests one specific communication route. A whole-sheet mean constraint
still links the regions, even when their local diffusion links are cut.
All twelve pairings and both instruction strengths remain, including the
previously contrary BD/CD cases. Success must improve the composite itself;
merely making the single-donor comparison worse is not a rescue.

## Source design review

Inspected the frozen [blueprint engine](../../blueprint_web/src/blueprint_web/engine.py),
[ladder engine](../../ladder_web/src/ladder_web/engine.py),
[alphabet reader](../../alphabet/src/alphabet/pipeline.py) and
[tissue configuration](../../setpoint_rewrite/src/setpoint_rewrite/runner.py).
Rung T at `c_m=0` has local nearest-neighbour diffusion plus global drift/noise
centering. R and EMA are updated but do not influence V. The new kernel changes
only symmetric diffusion edge weights, retaining the fixed denominator four.

The internal control translates the selected join-edge graph to donor/tile
midlines: `(0,4)/(4,0)/(2,2)` in canonical/rotated/checker layouts. This matches
edge count, orientation, weakened-degree histogram and graph topology by
translation, without changing the records, V, targets or paired noise. It is
one fixed phase, not every possible internal control or a learned join address.

## Implementation and validation log

- New [runner](../src/laws_confirmation/l23_contact_intervention.py),
  [independent checker](../scripts/audit_l23_contact_intervention_outputs.py),
  [tests](../tests/test_l23_contact_intervention.py) and
  [resource-limited launcher](../scripts/run_l23_contact_intervention.sh).
- Initial **76 tests passed in 20.41 seconds**, synthetic/disposable short
  trajectories only. Artifacts preserved at
  `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/tmp/l23-contact-tests-FcgA4t/`.
  No failing tests, new scientific effects or predecessor edits.
- Added complete short factorial save/readback and frozen-launch corruption
  guards after that initial pass; **136 scoped tests passed in 34.00 seconds**
  (90 new, 38 D083, six trace-observer and two output-isolation tests).
  Artifacts preserved at external `tmp/l23-contact-regression-VVkY7o/` (42 MiB).
  Full-duration
  disposable timing will cover all five arms, not select a favorable arm.
- Initial storage check: external **8,639,582,208 bytes free** (8.05 GiB),
  root **9,120,817,152 bytes free** (8.49 GiB). Gate is seven GiB external:
  four GiB reserve plus three GiB fixed output allowance. No cleanup.
- Retain final modified V, all checkpoint errors/flags, endpoint metrics,
  geometry, diagnostics and state hashes. Independently replay every trajectory.
  Do not duplicate original states or retain full intermediate state copies.

## Freeze and pre-benchmark checks

All 492 declared pre-benchmark input paths exist and are unique/absolute;
their files total **6,941,553,286 bytes**. All **44 imported repository
modules** are in the frozen closure. All **561 local links across nine
documents**, shell syntax and scoped whitespace pass. A read-only import
enumerator initially included the inline interpreter's non-file `<stdin>`;
excluding non-files corrected that check, without scientific-code changes.
Workspace remains **12 MiB**. External free about 8.1 GiB exceeds the seven-GiB
gate. Predecessor D083 scientific hashes and completed D082 review unchanged.

Frozen SHA-256 values:

| File | SHA-256 |
| --- | --- |
| Runner | `29ea7cde94848f2bb42cc27bf210d9375c1c9cb0a6d46f83e2eec8bab711c820` |
| Independent checker | `3a651ecfbbbb5a3d6b61bba5bd443a2e5f4fd0ff266e3849f0c354ad580074ce` |
| Tests | `9fad17211ef50392e1e3e4375dfec2f837c24a3ce05e4af4d63edcff62379315` |
| Launcher | `16584b2b1fa9c4bdcdce95b5715cdeea9d06ce6e0d6983c6be8bfffc1e5375c8` |
| Protocol | `f15bdc1ec27e5bea560011ff832d5911dd8ca070f5d1a3ddae827fbb788b7b46` |
| Completed D083 review | `ca442ea81cd965ff8449caa0cab2f985cbb220194a05408c452add0575812c29` |

The timing benchmark verifies all predecessor hashes and runs only
the fixed disposable block. Do not revise these scientific files after it.

## Timing and launch gate

Benchmark completed **2026-09-10 11:10:48 UTC**, all five arms passed their
full 300-sweep independent replay/observer checks. About 5.2 minutes wall time;
this bounded timing check was attached. All 492 frozen input hashes verified
before and after; disposable outcomes were not reported or used for selection.
Timing/log/data retained externally under the run's immutable benchmark names.

Arm compute seconds, original/join-half/internal-half/join-cut/internal-cut:
**20.913274 / 25.860701 / 26.939594 / 26.362057 / 26.120903**.
Aggregate save/readback **3.233197 seconds**; fixed per-panel estimate
**27.58623291980475 seconds**. Input hashing/source verification
**90.2366231973283 seconds**. The frozen formula yields
**13,601.865047900937 seconds**, **226.7 minutes / 3.78 hours**. This conservative
planning allowance does not credit four-worker speedup, not a promise of
completion at an exact time. No experimental effect is inferred from timing.

The run is detached. Preparation pinned **495 inputs**, including benchmark
metadata and both saved benchmark artifacts, and rechecked the seven-GiB gate.

## Detached launch record — user-owned polling

Launch **2026-09-10T11:15:11.981065+00:00**, **PID 762514**. CPU affinity 0–3,
at most four workers, one numerical thread each. The conservative planning
finish is approximately **15:02 UTC**; actual parallel execution may finish
sooner. This is an estimate, not an observed completion or live progress check.

External root: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`.

- Run records: `runs/l23_contact_intervention_v1_attempt1/`.
- User-owned status: `runs/l23_contact_intervention_v1_attempt1/STATUS.json`.
- Outputs: `outputs/l23_contact_intervention_v1_attempt1/`.
- Logs: `logs/l23_contact_intervention_v1_attempt1.{stdout,stderr}.log`.

Only the **parent launch metadata** was received on the launch turn. No child
process/status, log, completion marker or experimental output was inspected
until the user's next status request. The completed verification below was
performed on that request before interpretation. No automatic retry, sample
extension, cleanup or subsequent run. The law verdict remains MIXED/STRESS_TESTED,
and L22 remains parked.

## Frozen interpretation limits

Twenty fixed focal outcomes cover absolute composite rescue, reduction of
composition excess, advantage over matched internal weakening, and specificity
against off/scrambled readers, at both norms and both removal strengths.
All other strata and observers remain available as declared secondary views.
No new law pass gate, dose selection, threshold or inferred heredity.

The source and derived controls must verify before any scientific conclusions.
Do not call reduced comparison scores a rescue or local cuts full isolation.
This remains a fixed-pattern, hand-addressed, single-physics experiment.

## Completed run and status-time verification

Reported execution **6,551.147568312008 seconds (109.2 minutes)**, approximately
**110.8 minutes after launch**, including the startup input verification.
Completed **13:05:57.807597 UTC**, earlier than the conservative 15:02 estimate.
All sixteen blocks complete, COMPLETE present, FAILED absent, stderr empty.
No new simulation, replay, test run, retry or follow-on launch in this status turn.

The run itself independently replayed **480 panels / 2,400 V/EMA/R checkpoint
batches** and made **96 exact source bridges**. At the user's request, a new
read-only check in **77.692 seconds** verified:

- All **495 input / 36 output hashes**, unique absolute paths, exact frozen
  contracts, manifest/timing closure, completed status and output inventory.
- All sixteen saved block records, geometry, birth/budget/off/rotation aliases,
  paired RNG/state-hash metadata and **96 D082/D083 original-statistic bridges**.
- All **384 modified final V field hashes**, independently recomputed endpoint
  spatial errors/variance flags and all six recognition/fidelity metrics.
- All saved pooled means, per-block composition arrays, and all twenty focal
  distributions, including ranges, pair means and paired-start direction counts.

Maximum rotation discrepancy **1.8332557694122897e-13**; recorded independent
replay discrepancy **4.224953720211033e-13**, both below 1e-10. Zero inactive
V/template variance flags. Prior **136 scoped tests** stand; frozen scientific
files and predecessor inputs were not edited.

Hashed outputs total **1,971,336,919 bytes (1.84 GiB)**, all external, below the
three-GiB allowance. External free about **6.2 GiB**, root about **8.0 GiB** at
inspection; workspace remains code/docs only. No cleanup or deletion.

## All twenty focal outcomes

Checker4, matched mean, sweep 300, whole-region standardized squared error,
all twelve pairs. Positive rescue means lower error; contact specificity
means greater reduction of composition excess than under matched internal
weakening. Ranges are observed block ranges, not confidence intervals.
Direction columns are positive/tied/negative, with the frozen 1e-12 tolerance.
Paired counts total 1,536, not 1,536 independent physical replications.

| Norm | Removed | Outcome | Mean | Block range | Blocks +/=/- | Paired +/=/- |
| --- | --- | --- | --- | --- | --- | --- |
| .15 | .5 | normalized_rescue | +.048409 | [.043619, .054582] | 16/0/0 | 1525/0/11 |
| .15 | .5 | composition_rescue | +.029590 | [.027162, .031909] | 16/0/0 | 1352/0/184 |
| .15 | .5 | contact_specificity | +.035008 | [.032696, .037636] | 16/0/0 | 1338/0/198 |
| .15 | .5 | record_specificity_off | +.044421 | [-.004516, .074678] | 15/0/1 | 1148/0/388 |
| .15 | .5 | record_specificity_scrambled | +.052401 | [.031939, .065625] | 16/0/0 | 1296/0/240 |
| .15 | 1 | normalized_rescue | +.090554 | [.082359, .102012] | 16/0/0 | 1519/0/17 |
| .15 | 1 | composition_rescue | +.064650 | [.056668, .069915] | 16/0/0 | 1383/0/153 |
| .15 | 1 | contact_specificity | +.080293 | [.073640, .086438] | 16/0/0 | 1406/0/130 |
| .15 | 1 | record_specificity_off | +.083284 | [.031161, .120230] | 16/0/0 | 1127/0/409 |
| .15 | 1 | record_specificity_scrambled | +.101218 | [.055022, .129762] | 16/0/0 | 1259/0/277 |
| .30 | .5 | normalized_rescue | +.039678 | [.035428, .044104] | 16/0/0 | 1536/0/0 |
| .30 | .5 | composition_rescue | +.021270 | [.018437, .022637] | 16/0/0 | 1422/0/114 |
| .30 | .5 | contact_specificity | +.022990 | [.019295, .024561] | 16/0/0 | 1396/0/140 |
| .30 | .5 | record_specificity_off | +.035690 | [-.012325, .064169] | 15/0/1 | 1106/0/430 |
| .30 | .5 | record_specificity_scrambled | +.044284 | [.033269, .059092] | 16/0/0 | 1402/0/134 |
| .30 | 1 | normalized_rescue | +.065582 | [.056686, .070845] | 16/0/0 | 1530/0/6 |
| .30 | 1 | composition_rescue | +.037951 | [.031607, .042811] | 16/0/0 | 1429/0/107 |
| .30 | 1 | contact_specificity | +.043380 | [.037046, .047064] | 16/0/0 | 1391/0/145 |
| .30 | 1 | record_specificity_off | +.058313 | [.005278, .093633] | 16/0/0 | 1054/0/482 |
| .30 | 1 | record_specificity_scrambled | +.076114 | [.047954, .110763] | 16/0/0 | 1337/0/199 |

Every focal endpoint's full-precision **twelve pair means and sixteen block
means**, plus all direction counts, are retained in the verified
[analysis JSON](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l23_contact_intervention_v1_attempt1/analysis.json).
No focal endpoint was dropped or replaced after results.

## Absolute outcomes: the comparator was not sacrificed

Matched checkerboard endpoints, all pairs. N = normalized composite,
I = same-intervention virtual isolated donors. NSE is standardized squared
error. Recognition means intended-form label recognition, **not** per-pixel
accuracy; sign error is per-pixel error. This distinction matters here.

| Norm | Arm | NSE N | NSE I | NSE N−I | Recognition N | Pixel sign error N |
| --- | --- | --- | --- | --- | --- | --- |
| .15 | original | .370087 | .332576 | +.037511 | .911241 | .171242 |
| .15 | join_half | .321678 | .313756 | +.007922 | .972982 | .141055 |
| .15 | internal_half | .383535 | .340605 | +.042930 | .938368 | .182266 |
| .15 | join_cut | .279533 | .306672 | −.027139 | .996419 | .112574 |
| .15 | internal_cut | .425559 | .372406 | +.053153 | .969727 | .208682 |
| .30 | original | .243251 | .226054 | +.017198 | .994141 | .105268 |
| .30 | join_half | .203574 | .207646 | −.004073 | .999674 | .080442 |
| .30 | internal_half | .240944 | .222026 | +.018918 | .997233 | .107048 |
| .30 | join_cut | .177670 | .198423 | −.020753 | 1.000000 | .065033 |
| .30 | internal_cut | .250574 | .227946 | +.022627 | 1.000000 | .117599 |

Isolated-donor NSE also improves under join weakening in every pooled block:
**.018819/.025903** for primary half/full removal and **.018408/.027631**
for secondary half/full removal. Absolute composite advantage over internal
weakening is **.061857/.146026** primary, **.037370/.072904** secondary,
positive in every block. These are not just changes in the comparator.

Recognition alone is misleading: at the stronger norm **both full-cut arms
recognize every intended label**, yet pixel sign errors are **6.50% at joins
versus 11.76% for internal cuts**. At the primary norm internal weakening
raises label recognition while making standardized/raw/pixel errors worse.
Do not describe every improvement in recognition as improved pattern anatomy.

## Companion observers, layouts and budgets

At matched checkerboard endpoints, normalized rescue, composition rescue and
contact specificity are positive in **all sixteen blocks at both norms and
both removals for all four observers**. Whole-region alignment shortfall
equals NSE here because all variance flags are active. Raw and sign errors
give genuinely distinct companions; these do not rely on standardization.

| Norm | Removed | Observer | Normalized rescue | Composition rescue | Contact specificity |
| --- | --- | --- | --- | --- | --- |
| .15 | .5 | raw_squared_error | +.081356 | +.056886 | +.069986 |
| .15 | .5 | sign_error | +.030187 | +.019618 | +.024457 |
| .15 | 1 | raw_squared_error | +.149595 | +.128876 | +.164870 |
| .15 | 1 | sign_error | +.058668 | +.044342 | +.056295 |
| .30 | .5 | raw_squared_error | +.064520 | +.039123 | +.044963 |
| .30 | .5 | sign_error | +.024826 | +.014000 | +.016246 |
| .30 | 1 | raw_squared_error | +.101440 | +.071333 | +.089528 |
| .30 | 1 | sign_error | +.040235 | +.025625 | +.033539 |

Canonical layout gives the same direction, with smaller standardized effects.
Its half/full normalized rescue is **.017753/.032229** primary and
**.012439/.019205** secondary; contact specificity **.009334/.020646** and
**.007824/.013266**, respectively. Absolute advantage over the internal
control, isolated-donor improvement and composition rescue are also positive
in all sixteen blocks. Rotation matches numerically; it is not a separate
learned invariance result.

For checkerboard NSE, all three core contrasts remain positive in every block
under **neutral, matched and opposite** budgets, both norms/removals. In
the matched arm, both source-eligible AB/BA and the excluded-ten stratum retain
all-positive pooled blocks. Excluded-ten contact specificity is
**.028894/.071019** primary half/full and **.021252/.039563** secondary.
The result is not driven solely by the originally eligible pair orientations.
Full pair/budget/layout/observer/start/region arrays remain in the block NPZs
and [summary NPZ](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l23_contact_intervention_v1_attempt1/summary.npz).

## Pair exceptions and time course

All twelve pair-mean **absolute normalized rescues** are positive at both
norms and removals. This does not mean every paired start improves: the focal
table explicitly retains the negative individual contrasts.

Primary-norm CD is the only pair-mean NSE exception for both composition
rescue and contact specificity. Its isolated donors improve more than the
composite; it is **not** an absolute worsening of the composite:

| Norm | Removed | CD composite rescue | CD isolated rescue | CD composition rescue | CD contact specificity |
| --- | --- | --- | --- | --- | --- |
| .15 | .5 | +.019321 | +.028279 | −.008958 | −.010491 |
| .15 | 1 | +.038964 | +.045717 | −.006753 | −.015046 |
| .30 | .5 | +.031344 | +.021436 | +.009908 | +.008469 |
| .30 | 1 | +.057304 | +.027657 | +.029647 | +.013368 |

CD's exception depends partly on observer. Primary raw-error composition
rescue/contact specificity are positive at both doses; primary sign-error
composition rescue is negative at both, while sign contact specificity is
negative at half removal and positive at full removal. All four observers
give positive CD core contrasts at the secondary norm. BD, despite its D083
interior-dominant localization, has positive pair-mean NSE composition rescue
and contact specificity at both norms/doses. Localization was not an infallible
predictor of an intervention's effect.

Birth differences are exactly zero. At sweep 1, the checkerboard's standardized
absolute composite rescue is slightly **negative in all sixteen blocks**:
primary **−.000637/−.001299**, secondary **−.001223/−.002496** (half/full).
By saved sweep 50, absolute rescue, composition rescue and contact specificity
are positive throughout, persisting at 150/300. This is not an immediate
universal improvement at every time or a precise onset estimate.

At the endpoint, standardized normalized rescue is larger per seam cell than
per interior cell: primary half **.055691/.026564**, full **.101461/.057832**;
secondary half **.049081/.011469**, full **.079396/.024139**. Both bands improve
in every block. These are shared-normalization contributions, not a unique
spatial causal decomposition or proof of outward propagation.

## Conservation caveat and bounded conclusion

Local weighted diffusion is conservative before clipping, but the original
global reaction-mean constraint remains and clipping still changes the bulk
mean slightly. For matched checkerboard normalized lives, mean-of-life-maximum
absolute mean drift is **.002584 → .002923 → .003693** (original/half/full join)
at the primary norm and **.005032 → .005488 → .006379** secondary. Worst
secondary full-join drift is **.019745**; worst per-sweep clipped fraction is
**.019531**. Rescue does **not** coincide with better preservation of mean in
these summaries. This intervention identifies a total effect within the
clipped source dynamics, not its unique mediation through diffusion versus
downstream clipping/global constraints.

**L23 connection:** correct, budget-compatible instructions can still interfere
through the way neighbouring regions interact. D084 supplies causal support
for local join interference in this assay, beyond D083's error localization.
It strengthens the bounded compositional-mechanism finding but does not
validate conservation as a necessary pre-screen, general additivity, unlimited
capacity, autonomous addresses or a renewable hereditary carrier. Keep L23
**MIXED/STRESS_TESTED**; no broad verdict upgrade and no L22 reopening.

**Recommendation only, not approved or launched:** one small, separately frozen
edge-position control before parking this mechanism. Compare the true checker
joins with additional equally matched internal translations, retaining existing
midline/original controls, both norms/removals and every pair including CD.
Ask whether the donor boundary is privileged beyond the single midpoint phase
used here. No new write threshold, dose search, automatic sample expansion or
heredity/PX study. Recheck external storage before designing any new retention.

Final documentation QA: all **42 result-table rows** agree with the verified
saved data (twenty focal, ten absolute-arm, eight companion and four CD rows).
All **565 local links across eight updated documents**, scoped whitespace,
and frozen D084 scientific/completed-D083-review hashes pass. The read-only
table-QA helper initially omitted the region selector for companion rows;
restoring that axis and asserting its shape resolved the check. No reported
number, scientific implementation, input or output needed changing.
