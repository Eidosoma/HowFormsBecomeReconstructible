# D150 — recovery features did not improve aggregate prediction

COMPLETE and independently audited, 2026-09-19. All 32 observed founder
blocks / 512 cases retained. **This is post-result development, not a new
prospective experiment.** The former D141 held-out cohort is development here.
[Fixed protocol](PROTOCOL_V1.md); [execution history](WORKLOG.md).

## Plain-language result

Watching how the copies recovered did not improve the overall squared-error
forecast with these fixed features and models. Challenge + recovery was
0.0739% worse than passive + recovery. Both were about 4% worse than the
strengthened starting-only baseline. The tiny challenge–passive difference is
a point estimate, not evidence of equivalence.

There are mixed details: passive endpoints reduce average absolute error,
and passive recovery helps A-family predictions, while ordinary B remains
the largest error source. These are retained below rather than treated as
a universal failure of every diagnostic or every possible predictor.

## Five fixed models: original terminal outcomes

Each prediction excludes its entire founder block from both fitting and
regularization selection. Both observers receive exactly two allowed copies,
the same model family and the same seven starting measurements. The six new
measurements per diagnostic track changes during reading, early writing and
late writing. No actual-lineage state or future label is a feature.

MSE is in squared fractional-preference units; MAE and RMSE are preference
points (100 times fractional score), not percentages of successful survival.
Lower error is better.

| Model | MSE | MAE, points | RMSE, points |
|---|---:|---:|---:|
| Starting only | 0.007109798 | 5.6537 | 8.4320 |
| Passive endpoints | 0.007153288 | 5.3218 | 8.4577 |
| Challenge endpoints | 0.007331457 | 5.4916 | 8.5624 |
| Passive + recovery | 0.007398930 | 5.3229 | 8.6017 |
| Challenge + recovery | 0.007404396 | 5.4989 | 8.6049 |

Starting-only has the lowest aggregate MSE. Passive endpoints have the lowest
aggregate MAE. These statements are compatible: squared error penalizes the
larger misses more. Adding recovery increases MSE versus the corresponding
endpoint model by 3.434% for passive and 0.995% for challenge.

The central declared development contrast is reference MSE minus candidate
MSE: passive recovery minus challenge recovery =
−0.000005466187 (−0.073878%). Challenge improves 14 founder blocks and worsens
18. No confidence interval, significance test, equivalence claim or selected
deployment model is produced by this post-result stage.

All fixed contrasts follow. Reduction is reference MSE minus candidate MSE:
positive favors the candidate; negative means worse. Block counts are
lower/higher/equal candidate MSE.

| Candidate versus reference | MSE reduction | Relative reduction | Better/worse/tied blocks |
|---|---:|---:|---:|
| Challenge + recovery versus Passive + recovery | −0.000005466 | −0.074% | 14/18/0 |
| Challenge endpoints versus Passive endpoints | −0.000178169 | −2.491% | 14/18/0 |
| Passive + recovery versus Passive endpoints | −0.000245643 | −3.434% | 16/16/0 |
| Challenge + recovery versus Challenge endpoints | −0.000072940 | −0.995% | 19/13/0 |
| Passive endpoints versus Starting only | −0.000043489 | −0.612% | 20/12/0 |
| Challenge endpoints versus Starting only | −0.000221659 | −3.118% | 17/15/0 |
| Passive + recovery versus Starting only | −0.000289132 | −4.067% | 15/17/0 |
| Challenge + recovery versus Starting only | −0.000294598 | −4.144% | 17/15/0 |

## Retained family/writer and source-cohort detail

“Ordinary” means the original translated-feedback writer. Every group has
128 cases, so none is excluded or selected to improve the aggregate result.

| Model | A ordinary MSE | A aligned MSE | B ordinary MSE | B aligned MSE |
|---|---:|---:|---:|---:|
| Starting only | 0.0017297 | 0.0011629 | 0.0207349 | 0.0048117 |
| Passive endpoints | 0.0013184 | 0.0008401 | 0.0229201 | 0.0035345 |
| Challenge endpoints | 0.0013126 | 0.0008689 | 0.0230503 | 0.0040941 |
| Passive + recovery | 0.0010897 | 0.0006105 | 0.0238788 | 0.0040167 |
| Challenge + recovery | 0.0014819 | 0.0008611 | 0.0235408 | 0.0037338 |

Passive recovery improves the two A-group point estimates over passive
endpoints, but worsens both B-group estimates. Challenge recovery has a mixed
group pattern. Ordinary B dominates aggregate MSE under every model. This
describes the error distribution; it does not identify the cause or establish
a noise-only prediction ceiling.

| Model | D135, 8 blocks | D140, 8 blocks | Former D141 test, 16 blocks |
|---|---:|---:|---:|
| Starting only | 0.0094594 | 0.0056236 | 0.0066781 |
| Passive endpoints | 0.0097822 | 0.0054380 | 0.0066965 |
| Challenge endpoints | 0.0098024 | 0.0060043 | 0.0067596 |
| Passive + recovery | 0.0101563 | 0.0053201 | 0.0070596 |
| Challenge + recovery | 0.0096586 | 0.0053663 | 0.0072963 |

These are slices of the same 32-block nested fit, not three independent
prospective replications. All per-block MSE/MAE and individual predictions are
retained in the sealed artifacts below.

## Four previously saved futures: secondary scores only

The same out-of-block predictions were scored on D142's 1,024 saved futures
from the 16 former-test blocks. No repeated-future outcomes entered training,
scaling or regularization selection. These are not new founders or newly
generated outcomes.

| Model | Individual-future MSE | Individual-future MAE, points | Four-future-mean target MSE |
|---|---:|---:|---:|
| Starting only | 0.007167774 | 5.6867 | 0.003026883 |
| Passive endpoints | 0.007080392 | 5.3877 | 0.002939501 |
| Challenge endpoints | 0.007229165 | 5.5193 | 0.003088273 |
| Passive + recovery | 0.007552466 | 5.4674 | 0.003411575 |
| Challenge + recovery | 0.007624553 | 5.6016 | 0.003483662 |

Passive endpoints have the lowest MSE in this supplementary panel, 1.219%
below starting-only for individual futures. Neither recovery model improves
its own endpoint model. Challenge recovery is 0.954% worse than passive recovery
for individual futures; against their means it is 2.113% worse. The absolute
paired MSE difference is the same, −0.000072086479, with 8 blocks favoring
challenge and 8 favoring passive. The change in relative percentage reflects
the smaller mean-target denominator, not additional predictive information.

| Candidate versus reference | MSE reduction, either target | Individual-future reduction | Mean-target reduction | Better/worse/tied blocks |
|---|---:|---:|---:|---:|
| Challenge + recovery versus Passive + recovery | −0.000072086 | −0.954% | −2.113% | 8/8/0 |
| Challenge endpoints versus Passive endpoints | −0.000148772 | −2.101% | −5.061% | 5/11/0 |
| Passive + recovery versus Passive endpoints | −0.000472074 | −6.667% | −16.060% | 5/11/0 |
| Challenge + recovery versus Challenge endpoints | −0.000395388 | −5.469% | −12.803% | 4/12/0 |
| Passive endpoints versus Starting only | +0.000087382 | +1.219% | +2.887% | 8/8/0 |
| Challenge endpoints versus Starting only | −0.000061390 | −0.856% | −2.028% | 5/11/0 |
| Passive + recovery versus Starting only | −0.000384692 | −5.367% | −12.709% | 6/10/0 |
| Challenge + recovery versus Starting only | −0.000456778 | −6.373% | −15.091% | 4/12/0 |

For completeness, each saved future index is shown below as MSE / MAE points,
256 outcomes per column. These arithmetic slices use the same saved predictions;
no extra model fits or outcome-based selection. Vectorized totals were also
checked against explicit sums of all case errors, and their means against the
sealed pooled-future scores.

| Model | Future 0 | Future 1 | Future 2 | Future 3 |
|---|---:|---:|---:|---:|
| Starting only | 0.0062946 / 5.434 | 0.0067386 / 5.618 | 0.0080343 / 6.045 | 0.0076035 / 5.650 |
| Passive endpoints | 0.0068828 / 5.322 | 0.0067863 / 5.241 | 0.0073872 / 5.690 | 0.0072652 / 5.297 |
| Challenge endpoints | 0.0071840 / 5.506 | 0.0067956 / 5.359 | 0.0076735 / 5.854 | 0.0072636 / 5.359 |
| Passive + recovery | 0.0071104 / 5.302 | 0.0073197 / 5.448 | 0.0078507 / 5.712 | 0.0079291 / 5.407 |
| Challenge + recovery | 0.0073013 / 5.488 | 0.0072593 / 5.410 | 0.0083830 / 6.061 | 0.0075545 / 5.448 |

The checker verifies the paired loss-difference identity block by block.
All group and block scores are retained; averaging futures cannot by itself
turn the diagnostic into a better predictor.

## Nested tuning and verification

There are five models × 32 outer folds = 160 held-out fits, with 4,960 inner
validation folds total, each evaluating the same six alpha values. Training
means, group intercepts and scaling are recomputed inside every fold. Selected
alpha counts, in outer-fold models:

| Model | .001 | .01 | .1 | 1 | 10 | 100 |
|---|---:|---:|---:|---:|---:|---:|
| Starting only | 32 | 0 | 0 | 0 | 0 | 0 |
| Passive endpoints | 1 | 31 | 0 | 0 | 0 | 0 |
| Challenge endpoints | 0 | 26 | 6 | 0 | 0 | 0 |
| Passive + recovery | 1 | 2 | 0 | 29 | 0 | 0 |
| Challenge + recovery | 1 | 20 | 1 | 10 | 0 | 0 |

The complete coefficients, group means, scales, block identities, inner loss
grids and predictions are saved. No full-panel deployment refit was made.
Regularization differences are observations, not proof of a particular
overfitting mechanism.

71 qualification tests passed. The fresh-process audit checks all 1,320
frozen inputs and six indexed outputs; independently reconstructs features
using FFT correlations, source labels and repeated-future outcomes; refits
nested ridge models using SVD instead of the production normal-equation solver;
and checks every reported score. No tissue dynamics are generated.
The source D141/D142 controls and original protocol remain unchanged and
hash-pinned; D150 does not add a new apparatus-control experiment.

## Interpretation and next decision

This particular richer observation interface has not earned an overall
prediction benefit in the declared development comparison. It does not rescue
D141, prove passive/challenge equivalence, or establish that continuation is
fundamentally unpredictable. The endpoint models here use a stronger baseline
and nested refitting; they are not D141's original frozen predictors.

Original D141 remains PREDICTIVE_DIFFERENCE_UNRESOLVED; L20 remains
STRESS_TESTED / MIXED. D149's causal intervention remains a separate result,
not evidence that it predicts which founders will fail.

A reasonable next proposal is a separately specified, mechanism-directed
diagnostic based on the writer-address or competing-component weaknesses
already identified. Keep starting-only and equal-budget passive baselines,
all families/writers/cases, and development explicitly separate from a future
new-founder test. Do not retune this shuffle or select favorable subgroups
to make its old result appear positive. No new challenge, model selection,
cohort or successor has been launched.

## Costs and provenance

- Benchmark COMPLETE 16:49:42 UTC; checked feature block 1.1973s, full synthetic
  nested model/check/roundtrip 12.5176s, hash recheck 4.7328s. Conservative main
  budget 192.81s / 73.53MiB; below the ten-minute detachment threshold.
- Main manifest sealed 17:06:27.612583 UTC; COMPLETE 17:07:10.354156 UTC.
  Execution 42.7416s; output 2,701,385 bytes (2.576MiB), external only.
- Fresh audit COMPLETE 17:08:11.043890 UTC, 36.8976s, with durable receipt.
  One worker, numerical threads one, affinity CPUs0–5 (maximum six).
- No automatic retry, successor or new dynamics. All failed/null/mixed cases
  retained; there was no failed main attempt.

External run: `l20_extension1_recovery_prediction_dev_v1_attempt1`.

- [Complete numerical summary, all block/group scores](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recovery_prediction_dev_v1_attempt1/summary.json)
- [All out-of-block predictions](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recovery_prediction_dev_v1_attempt1/predictions.npz)
- [Every nested model and tuning record](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recovery_prediction_dev_v1_attempt1/fits.json)
- [Complete extracted panel and separate labels](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recovery_prediction_dev_v1_attempt1/dataset.npz)
- [Sealed verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recovery_prediction_dev_v1_attempt1/verification.json)
- [Fresh audit receipt](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d150_saved_audit_v1.json)

SHA256:

- Freeze: `09bb047883f0bc0d5bae88345813f61d39fe9f8753176609874d4f55cc697824`
- Benchmark: `34c04e9aeb5533bab4364a22837f0728eab12352119f85e6e98aa941f7bb08a8`
- Main manifest: `d755a46ae6c665b472779ea4e8dd9ed38d1c8c10f9f2fe32d8775b0b6bc78398`
- COMPLETE: `4ab1e508b8249ffc28f339ccc4f1ceb2bd5a8ebb51efc892017ceb815ae33b6e`
- Summary: `800016bf63c1d8a06c0dac46e704c9f4be0c4be90bfb0d6d5d07246dabdf5285`
- Verification: `4db86af64beb363546e670ff313ec1d766f45dda319692c31ff2a61e09f13a61`
- Fresh audit: `9d6b8161d54923ec4a1b2e0213078baa1eca3d0c32092811fcf32da51576f8a5`
