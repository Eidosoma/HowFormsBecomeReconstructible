# D153 — matched-regularization development results

Completed and freshly audited **2026-09-20**.
[Fixed protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[preceding D152 saved-fit review](../group-sensitive-prediction/SAVED_FIT_REVIEW_V1.md).

## Plain-language result

The promising control retains a small advantage over two undisturbed copies
when both predictors use the same regularization setting: **0.27–0.94% lower
original-outcome MSE**, not the earlier 2.45%. Thus differing setting choices
inflated that earlier comparison, but were not its entire explanation.

This is not yet a convincing challenge-prediction result. Starting measurements
alone beat that control at the two weaker penalties. The opposite control
direction loses to passive on original outcomes at every setting. Saved-future
comparisons change with setting and control direction. The targeted attenuation
and original shuffle still lose to passive on original outcomes at all three
settings. Nothing here licenses choosing the favorable setting or direction.

All 32 observed founder blocks / 512 cases, six observers and three predeclared
settings remain. No new simulations, diagnostic copies, founders, lineages,
features or held-out test. Former test founders are explicitly DEVELOPMENT.
D141's unresolved prospective comparison and L20 STRESS_TESTED / MIXED stay.

## What was controlled

Same D152 partially pooled group-sensitive model for every observer; same
public target/writer groups, fixed feature definitions, training-only centering/
scaling and label intercepts, common/deviation penalty ratio one and clipping.
Each alpha (.001, .01, .1) is applied to all six observers on all 32 whole-founder
outer folds, trained on the other 31 blocks. No inner selection or future labels
in fitting. These settings were specified from the already observed D152 choices,
not a blind discovery of settings.

All **576 fitted models / 9,216 predictions** are independently checked by
group-coordinate SVD. All 192 selected-alpha models / 3,072 predictions recover
the exact old nested reference within the declared numerical tolerance; copied
source arrays and old records themselves are exact. Old nested validation was
not rerun. Equal numeric alpha removes differing setting choices within this
parameterization, but does not equate effective complexity across feature sets.

## Original outcomes: complete observer panel

MSE is in squared fractional preference units; lower is better. The target is
the unchanged terminal own-minus-alternative preference after three replacements,
not percentage survival or complete-shape fidelity.

| Observer | 0.001 | 0.01 | 0.1 | Old nested reference |
|---|---:|---:|---:|---:|
| Starting only | 0.006699 | 0.006644 | 0.007094 | 0.006831 |
| Passive | 0.007133 | 0.006794 | 0.006879 | 0.006899 |
| Shuffle | 0.007254 | 0.006863 | 0.006942 | 0.006944 |
| Attenuation | 0.007645 | 0.007014 | 0.006923 | 0.007189 |
| Control + | 0.007326 | 0.006893 | 0.006897 | 0.007171 |
| Control − | 0.007073 | 0.006730 | 0.006860 | 0.006730 |

MAE in preference points (100 times the fractional error); lower is better:

| Observer | 0.001 | 0.01 | 0.1 | Old nested reference |
|---|---:|---:|---:|---:|
| Starting only | 5.0229 | 5.0214 | 5.3090 | 5.0706 |
| Passive | 4.9698 | 4.8469 | 4.9989 | 4.9035 |
| Shuffle | 5.0227 | 4.9293 | 5.0555 | 4.9758 |
| Attenuation | 5.0328 | 4.8997 | 5.0368 | 5.1016 |
| Control + | 4.9878 | 4.8487 | 4.9912 | 5.0362 |
| Control − | 4.9606 | 4.8219 | 4.9890 | 4.8219 |

RMSE in preference points:

| Observer | 0.001 | 0.01 | 0.1 | Old nested reference |
|---|---:|---:|---:|---:|
| Starting only | 8.1845 | 8.1510 | 8.4223 | 8.2651 |
| Passive | 8.4458 | 8.2424 | 8.2938 | 8.3060 |
| Shuffle | 8.5173 | 8.2841 | 8.3318 | 8.3328 |
| Attenuation | 8.7435 | 8.3749 | 8.3202 | 8.4788 |
| Control + | 8.5592 | 8.3026 | 8.3049 | 8.4684 |
| Control − | 8.4101 | 8.2036 | 8.2826 | 8.2036 |

At .001 and .01, starting-only has the lowest original-outcome MSE.
At .1, control − has the lowest MSE, but starting-only has also become worse
under that stronger penalty. Control − has the lowest original MAE at all
three settings. Different error criteria are retained, not used to pick a model.

Paired relative MSE reductions below: **positive favors the candidate**;
negative means worse. These are descriptive development comparisons, not CIs.

| Candidate versus reference | 0.001 | 0.01 | 0.1 | Old nested |
|---|---:|---:|---:|---:|
| Control − / Passive | +0.844% | +0.940% | +0.270% | +2.452% |
| Control − / Starting only | −5.587% | −1.296% | +3.290% | +1.484% |
| Control − / Control + | +3.455% | +2.371% | +0.535% | +6.156% |
| Control + / Passive | −2.705% | −1.465% | −0.267% | −3.947% |
| Mean control loss / Passive | −0.931% | −0.262% | +0.002% | −0.748% |
| Attenuation / Passive | −7.175% | −3.239% | −0.638% | −4.203% |
| Shuffle / Passive | −1.701% | −1.014% | −0.918% | −0.645% |

The mean-control comparator averages separate squared errors, not predictions.
Its +0.001694% original edge at .1 is a tiny numerical point estimate, not
equivalence, a significance claim or evidence of robust improvement.
Every setting, including this near-zero and the unfavorable results, stays.

## How much of the old gap involved setting choice?

At .01, control − is exactly its old nested predictor on all 32 blocks.
Only passive's two previously .1 outer models (78005 and 90010) change.
Passive MSE falls from 0.006899044815 to 0.006793765506; the paired control −
advantage falls from 0.000169155118 to 0.000063875810. This removes
**62.24% of the old absolute MSE gap**, while leaving a smaller
positive gap. This refitted comparison is different from the prior audit's
67.42% descriptive contribution of the two mismatched-alpha blocks.

At that same setting, starting-only improves from 0.006831247160 to
0.006643818732. Control − does not change, so its old 1.484% edge over
starting-only becomes a **1.296% disadvantage**. This is a useful warning:
an advantage over an imperfectly selected reference need not beat the simpler
reference when its setting is fixed too. It does not show that .01 should now
be chosen using these results.

## Cohorts, groups and score influence

Control − versus passive, original-outcome relative reductions:

| Setting | D135, 8 blocks | D140, 8 blocks | Former test, 16 blocks | Better/worse blocks |
|---|---:|---:|---:|---:|
| 0.001 | +2.101% | +0.832% | −0.177% | 17/15 |
| 0.01 | +1.461% | +0.695% | +0.621% | 18/14 |
| 0.1 | +0.195% | −0.007% | +0.433% | 18/14 |

Every single-block-omitted original score average still favors control − over
passive at every setting. Retained MSE-reduction ranges are:

| Setting | Minimum | Maximum |
|---|---:|---:|
| 0.001 | 9.142102e-6 | 9.722428e-5 |
| 0.01 | 3.364304e-5 | 8.082233e-5 |
| 0.1 | 2.568732e-6 | 3.056022e-5 |

These are omissions from saved score averages, not refits, deletions from the
study, jackknife uncertainty or proof about new founders. Cohort differences
remain: the weakest-penalty former-test comparison loses, and the strongest-
penalty D140 comparison is slightly negative.

At .01 and .1, control − has lower group MSE than passive in all four groups;
at .001 the two A groups worsen. The ordinary-B group remains harder for
control − than for starting-only at **every** setting, while aligned B improves.
Group-specific gains and losses therefore still offset each other; all four
groups, all cases and every contrast are present in the external summary.

## Secondary saved futures

These are the same four saved D142 outcomes per case on the 16 former-test
blocks: 1,024 labels, used only for scoring. Not fresh founders, independent
training examples, a second prospective study or a basis for tuning.

Individual-future MSE, lower is better:

| Observer | 0.001 | 0.01 | 0.1 | Old nested reference |
|---|---:|---:|---:|---:|
| Starting only | 0.006935 | 0.006543 | 0.006933 | 0.006826 |
| Passive | 0.006934 | 0.006471 | 0.006642 | 0.006495 |
| Shuffle | 0.007098 | 0.006532 | 0.006763 | 0.006568 |
| Attenuation | 0.007145 | 0.006467 | 0.006639 | 0.006749 |
| Control + | 0.006759 | 0.006388 | 0.006643 | 0.006536 |
| Control − | 0.006954 | 0.006443 | 0.006612 | 0.006443 |

Individual-future MAE in preference points:

| Observer | 0.001 | 0.01 | 0.1 | Old nested reference |
|---|---:|---:|---:|---:|
| Starting only | 5.0792 | 5.0143 | 5.2656 | 5.0770 |
| Passive | 5.0074 | 4.8387 | 4.9667 | 4.8672 |
| Shuffle | 5.0843 | 4.8573 | 5.0429 | 4.8952 |
| Attenuation | 5.0493 | 4.8305 | 4.9627 | 4.9677 |
| Control + | 4.9410 | 4.7926 | 4.9638 | 4.8870 |
| Control − | 5.0027 | 4.8237 | 4.9602 | 4.8237 |

Same paired contrasts, relative individual-future MSE reduction:

| Candidate versus reference | 0.001 | 0.01 | 0.1 | Old nested |
|---|---:|---:|---:|---:|
| Control − / Passive | −0.289% | +0.444% | +0.443% | +0.800% |
| Control − / Starting only | −0.278% | +1.533% | +4.621% | +5.620% |
| Control − / Control + | −2.877% | −0.851% | +0.464% | +1.424% |
| Control + / Passive | +2.515% | +1.284% | −0.021% | −0.633% |
| Mean control loss / Passive | +1.113% | +0.864% | +0.211% | +0.083% |
| Attenuation / Passive | −3.040% | +0.069% | +0.048% | −3.913% |
| Shuffle / Passive | −2.364% | −0.936% | −1.829% | −1.128% |

Control − versus passive is −0.289%, +0.444%, +0.443% across the three settings.
At .01 it turns negative after one of the 16 single-block SCORE omissions;
at .1 all 16 remain positive. Control − versus control + is negative at .001
and .01, positive at .1. Control + has the lowest saved-future MSE at .001
and .01; control − at .1. Thus the original-outcome direction ordering does not
transport uniformly to these saved futures.

Mean control loss improves on passive in all three saved-future averages,
unlike the original outcomes, but is not an available ensemble forecast.
All mean-target MSEs, block/group losses and absolute errors are also saved.
The independent checker confirms the within-future-variance and paired-loss
identities. No inferred noise ceiling or uncertainty interval is claimed.

## Bounded conclusion and next lead

The strongest defensible statement is: **a small original-outcome control −
advantage over passive remains under all three matched penalties in this
observed panel; much of the earlier gap depended on reference setting choices.**
This does not establish a general challenge advantage, superiority to starting-
only, autonomous interface repair, or preservation of complete shape.

A useful next proposal is one explicitly specified **starting + common U0
undisturbed-copy baseline**, at the same three settings, using saved data only.
Both diagnostic observers already receive U0. Comparing against this restricted
information baseline would ask whether the paid-for second diagnostic copy
adds useful prediction at all, before interpreting its particular perturbation.
Keep all six current observers/settings and starting-only. This baseline would
use fewer observations; it is an information-ablation check, not a replacement
for the equal-budget passive/challenge contest. No new baseline, alternative
perturbation, prospective cohort or successor is launched here.

## Qualification, cost and provenance

- First qualification: **55 tests pass**, zero failures/skips, 59.11s.
  External logs/d153_qualification_v1.xml; fixtures tmp/d153_qualification_v1.
- Freeze **14:38:42.441209 UTC**: 2,023 inputs, before actual-case fits.
- Synthetic benchmark COMPLETE **14:39:34.506962 UTC**:
  full checked comparison 12.660217s; source hash check 10.180635s;
  main forecast 165.681703s / 97.644318 MiB. Benchmark artifacts 8.411079 MiB.
- Main manifest **14:40:39.180613 UTC**; COMPLETE **14:41:07.286782 UTC**.
  Recorded execution **28.106189s**, excluding preflight; **10,696,925 bytes
  (10.201383 MiB)** external outputs.
- Fresh durable audit **14:41:52.540760 UTC**, 30.315096s:
  **2,032 inputs / nine indexed outputs**, all 576 fits, exact source identities,
  selected-alpha bridge, 72 observer contrasts + 18 fixed-versus-nested
  comparisons and 72 case-error arrays pass.
- One numerical worker, numerical threads one, affinity CPUs0–5.
  All numerical artifacts under /mnt/bioIce1; code/docs only here.
  Attached because forecast <600s; no retry, polling of a long detached run,
  successor, new tissue dynamics or change to old frozen science.

Run: l20_extension1_matched_regularization_dev_v1_attempt1.

External base:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`.

Outputs under outputs/<run>/:
dataset.npz; predictions.npz; fits.json; nested_predictions.npz; nested_fits.json;
case_errors.npz; summary.json; verification.json; input_hashes.sha256, plus
output_hashes.sha256. Summary retains all 90 declared contrasts, original/
secondary/mean-target scores, groups/cohorts and every score-omission average.
No favorable-only retained subset.

SHA256:

- Freeze: fda61f263b7c0e53145cf15244dab7375d5fc1797bc87f87aa14bf12032f5d33
- COMPLETE: 9bf970f7a18fdfce684764a0bfbb697faefc9b24904ab57e892f99b86e2e131a
- Summary: afdd604c6010ff7487be7567371629cbf7bcddf7dfe173a6ee3fb1cbbb16801c
- Verification: 4972c32ac0bd2719be1fd132b7eb22cc2f2164e4464dd4a5d8680a00d713a3a8
- Manifest: d5840ff802c41f67ed1b8340aa2dd63685d1a7b1a715db24058e52471e348ce7
- Output index: 74837548886d75efbaf1d91624798eb0e44aba4ca982f46342ed1a93ec3a17e2
- Fresh audit receipt: f3176e0f9ce7c7a25978c11dd1879689f67feeb6291f4277cb624a33380b2380

Receipt: logs/l20_extension1_matched_regularization_dev_v1_attempt1_saved_audit_v1.json.
