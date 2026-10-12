# D152 — group-sensitive prediction: completed development comparison

2026-09-20. COMPLETE and independently audited. [Fixed protocol](PROTOCOL_V1.md),
[work log](WORKLOG.md). No new founders, diagnostic simulations or lineages.

## In plain terms

Letting the prediction rule differ somewhat between target/writer groups helps
several forecasts. It improves starting-only MSE by 3.92% and passive MSE by
3.55%. But it does not rescue the targeted challenge: its original-outcome MSE
is 4.20% higher than equally upgraded passive observation and 5.24% higher than
equally upgraded starting-only. The original shuffle also loses to passive.

One matched residual control, sham_minus, now scores best. That is a possible
lead, not a confirmed challenge advantage: the other direction performs worse,
and the average of the two control losses is 0.75% worse than passive on the
original outcomes. Do not select the favorable direction retrospectively and
present it as prospective confirmation. These are already studied founders.

The difficult ordinary-B group is still the main problem. Most of the gains
come from the other groups, not from solving its reconstruction uncertainty.
This establishes sensitivity of these development scores to the prediction
class; it does not establish shared slopes as the cause of poor prediction.
D141's unresolved prospective result and L20's STRESS_TESTED / MIXED verdict
remain unchanged.

## What was compared

All 32 observed founder blocks / 512 cases: 8 D135 + 8 D140 + 16 former D141 test,
four lives and four public target/writer groups per block. Every case retained.
All six observers use the identical original features: 7 starting-only, or 19
starting + U0 + allowed second-copy endpoint features. No retrospective
U1-minus-edit response, extra copy, new measured feature or changed perturbation.
The former held-out cohort is explicitly DEVELOPMENT now.

The single new class adds regularized, zero-sum group slope deviations to a
shared slope. Its common/deviation penalty ratio is fixed at 1. Four public
group intercepts and within-fold centering/scaling remain; 28 or 76 penalized
coefficients. The same six-alpha grid is selected inside whole-founder nested
validation, without outer labels or saved-future labels. All six original
D151 shared-slope forecasts and fit records are reused exactly. No deployment
fit or post-result model-class search.

Outcome remains terminal own-minus-alternative preference after three
replacements (strict abs(V)>.2; sign V>0; denominator256). MSE is in squared
fractional preference units. MAE/RMSE are preference points (100 times fraction),
not percentages of organisms surviving. Positive MSE reduction favors the
candidate. All comparisons are development point estimates, not equivalence
tests, confidence intervals or prospective success categories.

## Original outcomes: complete six-observer panel

Reduction is relative to that observer's old shared-slope MSE, NOT evidence
that its diagnostic information beats another observer.

| Observer | Shared MSE | Group-sensitive MSE | MSE reduction % | Shared MAE points | Group MAE points | Group RMSE points |
|---|---:|---:|---:|---:|---:|---:|
| starting | 0.007109798 | 0.006831247 | 3.918 | 5.654 | 5.071 | 8.265 |
| passive | 0.007153288 | 0.006899045 | 3.554 | 5.322 | 4.904 | 8.306 |
| shuffle | 0.007331457 | 0.006943570 | 5.291 | 5.492 | 4.976 | 8.333 |
| attenuate | 0.007184570 | 0.007189002 | -0.062 | 5.365 | 5.102 | 8.479 |
| sham_plus | 0.007124527 | 0.007171349 | -0.657 | 5.314 | 5.036 | 8.468 |
| sham_minus | 0.007148104 | 0.006729890 | 5.851 | 5.320 | 4.822 | 8.204 |

The targeted observer improves MAE but not MSE relative to its own old version;
these loss measures must not be conflated. Sham_minus has the lowest MSE and
MAE here. It has 2.452% lower MSE than passive, with 18 better /14 worse blocks.
Its MSE is also 1.484% lower than starting-only (a descriptive absolute-score
comparison, not an additional pre-specified inferential test). Starting-only
still beats passive on MSE; passive has lower MAE.

For each observer's new-versus-old aggregate MSE, better/worse founder counts
are: starting24/8, passive19/13, shuffle20/12, attenuation16/16, sham_plus16/16,
sham_minus20/12. No tied block in these six comparisons. Tiny deterioration in
attenuation's own MSE is not equivalence or evidence of an invariant predictor.

## All ten fixed observer comparisons

Reference loss minus candidate loss: positive favors the named candidate.
Main block counts are out of32; saved-future counts are out of16. All ties zero.
The saved-future column is secondary and does not replace the original target.

| Candidate / reference | Shared main reduction % | Group main MSE reduction | Group main reduction % | Main better/worse | Group saved-future reduction % | Future better/worse |
|---|---:|---:|---:|---:|---:|---:|
| attenuate / passive | -0.437 | -2.899571e-4 | -4.203 | 11/21 | -3.913 | 6/10 |
| attenuate / starting | -1.052 | -3.577547e-4 | -5.237 | 15/17 | 1.137 | 7/9 |
| attenuate / shuffle | 2.004 | -2.454323e-4 | -3.535 | 13/19 | -2.753 | 9/7 |
| attenuate / sham_plus | -0.843 | -1.765281e-5 | -0.246 | 12/20 | -3.258 | 8/8 |
| attenuate / sham_minus | -0.510 | -4.591122e-4 | -6.822 | 15/17 | -4.750 | 5/11 |
| attenuate / mean_sham_loss | -0.676 | -2.383825e-4 | -3.430 | 14/18 | -3.999 | 7/9 |
| sham_plus / passive | 0.402 | -2.723043e-4 | -3.947 | 11/21 | -0.633 | 9/7 |
| sham_minus / passive | 0.072 | 1.691551e-4 | 2.452 | 18/14 | 0.800 | 9/7 |
| passive / starting | -0.612 | -6.779765e-5 | -0.992 | 17/15 | 4.859 | 7/9 |
| shuffle / passive | -2.491 | -4.452477e-5 | -0.645 | 13/19 | -1.128 | 7/9 |

The primary development comparison is -0.00028995708430639246:
upgraded passive MSE minus upgraded attenuation MSE. The targeted diagnostic
does not earn an advantage here. Mean-sham loss averages two separate losses;
it is not a pooled observer, a third diagnostic copy or a prediction ensemble.
Every shared and group-sensitive contrast and block difference is saved.

## Which groups and cohorts benefited?

Group-sensitive MSE reduction relative to the SAME observer's shared model:

| Observer | A ordinary % | A aligned % | B ordinary % | B aligned % |
|---|---:|---:|---:|---:|
| starting | 52.68 | 58.02 | -5.83 | 15.31 |
| passive | 35.10 | 41.00 | -1.75 | 17.27 |
| shuffle | 34.64 | 41.78 | -1.94 | 28.83 |
| attenuate | 38.18 | 42.95 | -5.35 | 8.38 |
| sham_plus | 38.00 | 41.12 | -6.14 | 10.88 |
| sham_minus | 34.84 | 41.02 | 0.56 | 20.95 |

The new class reduces A-group errors substantially and also improves aligned B.
It worsens ordinary B for five observers; sham_minus has only a 0.56% improvement
there. Ordinary B now contributes 83.57% of attenuation's total squared error
despite representing25% of cases. Its attenuation MAE/RMSE are11.878/15.502
points, versus2.308/2.893 for A ordinary,1.776/2.231 for A aligned, and4.444/5.823
for B aligned. The hard-group limitation remains; no case was excluded.

There is also cohort heterogeneity. New-versus-old MSE reduction:

| Observer | D135 % | D140 % | Former D141 test % |
|---|---:|---:|---:|
| starting | -0.20 | 15.78 | 1.84 |
| passive | -1.34 | 10.15 | 4.45 |
| shuffle | 3.78 | 13.96 | 2.54 |
| attenuate | -4.29 | 8.17 | -0.52 |
| sham_plus | -1.13 | 3.43 | -1.98 |
| sham_minus | -0.90 | 15.96 | 6.59 |

These are slices of the same nested development forecasts, not separate
replications, a justification to drop D135, or a prospective held-out claim.

## Previously saved alternative futures

Four D142 outcomes per case for16 former-test blocks,1,024 labels total. None
entered model fitting or alpha selection. Improvements relative to each old
model are larger here, but attenuation again loses to equally upgraded passive
and both controls. It is1.137% better than starting-only on this secondary
outcome; that must not hide its poorer original-outcome score.

| Observer | Individual-future MSE | MAE points | Four-future-mean MSE | MSE reduction vs own shared % |
|---|---:|---:|---:|---:|
| starting | 0.006826328 | 5.077 | 0.002685437 | 4.764 |
| passive | 0.006494626 | 4.867 | 0.002353735 | 8.273 |
| shuffle | 0.006567900 | 4.895 | 0.002427008 | 9.147 |
| attenuate | 0.006748733 | 4.968 | 0.002607842 | 4.588 |
| sham_plus | 0.006535765 | 4.887 | 0.002394874 | 6.834 |
| sham_minus | 0.006442691 | 4.824 | 0.002301800 | 9.323 |

Sham_minus retains the lowest MSE/MAE, but its advantage over passive is only
0.800%,9 better/7 worse blocks. It is not independent validation on new founders.
Individual-future MSE minus mean-target MSE is the same within-case population
variance0.004140891134738922 for every observer/architecture. All paired absolute
MSE differences agree between the individual-future and mean-target scores.
The four saved outcomes do not establish an irreducible noise ceiling.
All individual-future, group and block scores are retained in the full summary.

## Regularization and the next possible lead

Outer-fold selected alpha counts (all other frozen grid values have zero):

| Observer | .001 | .01 | .1 |
|---|---:|---:|---:|
| starting | 3 | 29 | 0 |
| passive | 0 | 30 | 2 |
| shuffle | 0 | 30 | 2 |
| attenuate | 0 | 5 | 27 |
| sham_plus | 0 | 9 | 23 |
| sham_minus | 0 | 32 | 0 |

The two control directions are not neutral duplicates: both change residual
spatial organization, though their distance is matched. Their score difference
could reflect predictive structure, sampling variability, sensitivity to inner
alpha selection, or a combination. The alpha counts alone do NOT identify the
cause. No alpha, penalty ratio, challenge direction or feature is changed here.

Recommended next proposal, not launched: a saved-fit/error audit of ALL six
observers, keeping starting and passive prominent, to see which founders and
groups account for the control difference and how that lines up with existing
alpha selections. No refitting, dose search or selecting the favorable control
as a prospective result. Only after that review should a separate experiment
or new prospective cohort be considered. This remains an external diagnostic,
not autonomous interface repair or complete shape preservation.

## Verification, costs and immutable provenance

- Qualification v1:48 passed /2 failed,23.94s. A reused fixed16-case divisor
  was inappropriate for the new single-group summary. Corrected ONLY the new
  checker with shape-counted divisors and explicit regression tests. No actual
  case had been fitted. Earlier code/science and v1 artifacts remain intact.
- Qualification v2:52 passed,13.05s. Normal-equation fits agree with independent
  whitened group-coordinate SVD; fold exclusion, budget boundaries, arithmetic,
  corruption, source identity, resource and detachment checks pass.
- Freeze12:35:42.980738 UTC seals1,971 inputs before actual-case fitting.
  Complete D151 / saved-review transitive closure and durable audit retained.
- Synthetic benchmark COMPLETE12:36:24.618495 UTC. Six complete outer folds,
  186 inner folds, six alphas; independently checked full-size fold1.100709s,
  source hash recheck11.411563s. Conservative main budget213.268531s/79.76MiB.
- Main manifest12:37:10.664738 UTC; COMPLETE12:37:59.440838 UTC. Recorded main
  execution48.776121s;6,301,786 bytes (6.010MiB) external. Preflight checks are
  outside this execution timer. Attached because projected runtime<600s.
- Fresh-process audit12:39:10.344032 UTC,42.847211s:1,976 input hashes and nine
  indexed outputs verified. All192 new outer /5,952 inner folds independently
  recomputed; all six shared models/data exact; all case errors and scores pass.
- One numerical worker, threads one, affinity CPUs0–5. All fixtures/output/logs
  external; no tissue dynamics, new cohort, automatic retry or successor.
  Protected/disabled apparatus controls remain pinned source checks, not new
  easy cases or newly simulated controls in this prediction contest.

Run: `l20_extension1_group_prediction_dev_v1_attempt1`.

- [Full score and comparison summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_group_prediction_dev_v1_attempt1/summary.json)
- [New predictions](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_group_prediction_dev_v1_attempt1/predictions.npz)
- [All nested fit records](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_group_prediction_dev_v1_attempt1/fits.json)
- [All signed, absolute and squared case errors](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_group_prediction_dev_v1_attempt1/case_errors.npz)
- [Independent verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_group_prediction_dev_v1_attempt1/verification.json)
- [Fresh audit receipt](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/l20_extension1_group_prediction_dev_v1_attempt1_saved_audit_v1.json)

SHA256:

- Freeze: `94c7c70495d6e146d1842f56b073043448d922e342715d8502b04f50c5b901b9`
- COMPLETE: `5188ad1597fb086ce653fc10cf1c80e7f388b2a8adb384f2551857360a73026d`
- Summary: `68bffac3645b97377318e55680136c6b13dc60126211f7aa2ce62a347cf64257`
- Verification: `e3539ca0a0a3709d2c51b32d68db0aa44ee8956b1b4720860efb8fd88c7f460f`
- Manifest: `ad7dcd58b8e0b3ea40f6c5d962655166df9e422d6ffdd28799b07490e81570cf`
- Output index: `3ad13f546a85031a071d3ec6c3325594c5dd41128075c08f706890d42593047e`
- Fresh audit: `d6e8a3ea7305869ccab16af8897de828793ab3f628446907a82e21bd5a4a1a36`
