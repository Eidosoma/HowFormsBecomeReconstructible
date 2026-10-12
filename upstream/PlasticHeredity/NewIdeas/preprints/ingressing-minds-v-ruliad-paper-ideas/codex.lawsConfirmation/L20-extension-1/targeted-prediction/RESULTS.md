# D151 — targeted diagnostic did not improve the main forecast

COMPLETE and independently audited, 2026-09-20. All 32 observed founder blocks /
512 cases and 1,536 new diagnostic cycles retained. This is post-result
DEVELOPMENT, not a new prospective experiment. [Protocol](PROTOCOL_V1.md);
[worklog](WORKLOG.md).

## Plain-language result

Attenuation scored 0.4373% worse than passive observation and 1.0517% worse than
starting-only on the declared squared-error measure. Both matched residual
controls also scored better than attenuation. No targeted prediction advantage
is demonstrated. These small differences are descriptive point estimates,
not equivalence or established harm.

The matched diagnostic copies improve on average: B preference increases
0.9705 points with ordinary writing and 0.6561 with aligned writing. These
local improvements did not make the original lineage's outcome better
predicted. Edited copies never entered the actual lineage; this study cannot
determine how their repair would last through later replacements.

## All six models: original terminal outcomes

Lower error is better. MSE is squared fractional preference; MAE and RMSE are
preference points, not survival percentages. All predictions exclude their
whole founder block from training and tuning. Three D150 baseline models and
predictions are reused exactly. Every diagnostic observer gets two copies.

| Model | MSE | MAE, points | RMSE, points |
|---|---:|---:|---:|
| Starting only | 0.007109798 | 5.6537 | 8.4320 |
| Passive | 0.007153288 | 5.3218 | 8.4577 |
| Original shuffle | 0.007331457 | 5.4916 | 8.5624 |
| Targeted attenuation | 0.007184570 | 5.3655 | 8.4762 |
| Residual sham + | 0.007124527 | 5.3137 | 8.4407 |
| Residual sham − | 0.007148104 | 5.3197 | 8.4546 |

Starting-only has the lowest MSE; sham + has the lowest MAE. Squared error
weights larger misses more. No predictor was selected for deployment.

Reduction is reference MSE minus candidate MSE, positive favoring candidate.
Founder counts are better/worse/tied. Mean sham averages losses, not predictions.

| Candidate versus reference | MSE reduction | Relative reduction | Blocks |
|---|---:|---:|---:|
| Targeted attenuation versus Passive | -0.000031283 | -0.4373% | 12/20/0 |
| Targeted attenuation versus Starting only | -0.000074772 | -1.0517% | 17/15/0 |
| Targeted attenuation versus Original shuffle | 0.000146887 | 2.0035% | 18/14/0 |
| Targeted attenuation versus Residual sham + | -0.000060043 | -0.8428% | 16/16/0 |
| Targeted attenuation versus Residual sham − | -0.000036466 | -0.5101% | 11/21/0 |
| Targeted attenuation versus Mean sham loss | -0.000048254 | -0.6762% | 11/21/0 |
| Residual sham + versus Passive | 0.000028760 | 0.4021% | 15/17/0 |
| Residual sham − versus Passive | 0.000005183 | 0.0725% | 16/16/0 |
| Passive versus Starting only | -0.000043489 | -0.6117% | 20/12/0 |
| Original shuffle versus Passive | -0.000178169 | -2.4907% | 14/18/0 |

No confidence interval, p-value, new threshold or equivalence claim is introduced
by this post-result stage.

## Family, writer and cohort detail

Ordinary means translated-feedback writing. Each group contains 128 cases;
none is excluded or selected as a replacement primary.

| Model | A ordinary MSE | A aligned MSE | B ordinary MSE | B aligned MSE |
|---|---:|---:|---:|---:|
| Starting only | 0.0017297 | 0.0011629 | 0.0207349 | 0.0048117 |
| Passive | 0.0013184 | 0.0008401 | 0.0229201 | 0.0035345 |
| Original shuffle | 0.0013126 | 0.0008689 | 0.0230503 | 0.0040941 |
| Targeted attenuation | 0.0013538 | 0.0008724 | 0.0228108 | 0.0037013 |
| Residual sham + | 0.0013131 | 0.0008274 | 0.0228822 | 0.0034754 |
| Residual sham − | 0.0013155 | 0.0008378 | 0.0228901 | 0.0035490 |

Ordinary B contributes 79.37% of attenuation's total squared error despite
being 25% of cases. Passive observations improve MSE over starting-only in
the other three groups but worsen it for ordinary B. This motivates examining
the model and errors, not declaring shared slopes causal or dropping cases.

| Model | D135, 8 blocks | D140, 8 blocks | Former D141 test, 16 blocks |
|---|---:|---:|---:|
| Starting only | 0.0094594 | 0.0056236 | 0.0066781 |
| Passive | 0.0097822 | 0.0054380 | 0.0066965 |
| Original shuffle | 0.0098024 | 0.0060043 | 0.0067596 |
| Targeted attenuation | 0.0094644 | 0.0056282 | 0.0068229 |
| Residual sham + | 0.0098392 | 0.0054129 | 0.0066230 |
| Residual sham − | 0.0096808 | 0.0054894 | 0.0067111 |

## Four saved alternative futures: secondary only

The 1,024 D142 outcomes on 16 observed blocks never enter fitting, scaling or
tuning. They are not new founders or prospective validation. Attenuation is
0.1013% better than passive on pooled future MSE, but 0.1850% worse than mean
sham loss. Sham + has the lowest MSE and MAE. This does not change the main
negative development comparison.

| Model | Individual-future MSE | MAE, points | Four-future-mean MSE |
|---|---:|---:|---:|
| Starting only | 0.007167774 | 5.6867 | 0.003026883 |
| Passive | 0.007080392 | 5.3877 | 0.002939501 |
| Original shuffle | 0.007229165 | 5.5193 | 0.003088273 |
| Targeted attenuation | 0.007073218 | 5.3779 | 0.002932327 |
| Residual sham + | 0.007015194 | 5.3521 | 0.002874303 |
| Residual sham − | 0.007105120 | 5.3972 | 0.002964229 |

| Candidate versus reference | MSE reduction, either target | Individual-future reduction | Mean-target reduction | Blocks |
|---|---:|---:|---:|---:|
| Targeted attenuation versus Passive | 0.000007174 | 0.1013% | 0.2441% | 9/7/0 |
| Targeted attenuation versus Starting only | 0.000094556 | 1.3192% | 3.1239% | 7/9/0 |
| Targeted attenuation versus Original shuffle | 0.000155946 | 2.1572% | 5.0496% | 12/4/0 |
| Targeted attenuation versus Residual sham + | -0.000058024 | -0.8271% | -2.0187% | 8/8/0 |
| Targeted attenuation versus Residual sham − | 0.000031902 | 0.4490% | 1.0762% | 9/7/0 |
| Targeted attenuation versus Mean sham loss | -0.000013061 | -0.1850% | -0.4474% | 9/7/0 |
| Residual sham + versus Passive | 0.000065198 | 0.9208% | 2.2180% | 9/7/0 |
| Residual sham − versus Passive | -0.000024728 | -0.3492% | -0.8412% | 9/7/0 |
| Passive versus Starting only | 0.000087382 | 1.2191% | 2.8869% | 8/8/0 |
| Original shuffle versus Passive | -0.000148772 | -2.1012% | -5.0611% | 5/11/0 |

Absolute paired MSE differences are identical for individual futures and their
mean. Smaller relative-error denominators do not represent extra information.
Each future below retains 256 outcomes, shown as MSE / MAE points.

| Model | Future 0 | Future 1 | Future 2 | Future 3 |
|---|---:|---:|---:|---:|
| Starting only | 0.0062946 / 5.434 | 0.0067386 / 5.618 | 0.0080343 / 6.045 | 0.0076035 / 5.650 |
| Passive | 0.0068828 / 5.322 | 0.0067863 / 5.241 | 0.0073872 / 5.690 | 0.0072652 / 5.297 |
| Original shuffle | 0.0071840 / 5.506 | 0.0067956 / 5.359 | 0.0076735 / 5.854 | 0.0072636 / 5.359 |
| Targeted attenuation | 0.0068997 / 5.339 | 0.0066877 / 5.221 | 0.0075740 / 5.705 | 0.0071315 / 5.247 |
| Residual sham + | 0.0068313 / 5.293 | 0.0066316 / 5.203 | 0.0073813 / 5.667 | 0.0072165 / 5.246 |
| Residual sham − | 0.0069184 / 5.343 | 0.0068832 / 5.258 | 0.0073504 / 5.688 | 0.0072685 / 5.300 |

## Verification and costs

84 qualification tests passed before the unchanged freeze. Every new diagnostic
cycle was independently physics-replayed. Raw trajectories, cases, predictions,
nested fits, all scores and original apparatus/source closure are retained.
The user-requested fresh-process saved audit passes 1,834 inputs / 71 indexed
outputs, independent SVD model and saved-output checks, with zero new dynamics.
That read-only status check did not create a durable audit receipt.

Selected alphas over 32 outer folds:

| Model | .001 | .01 | .1 | 1 | 10 | 100 |
|---|---:|---:|---:|---:|---:|---:|
| Starting only | 32 | 0 | 0 | 0 | 0 | 0 |
| Passive | 1 | 31 | 0 | 0 | 0 | 0 |
| Original shuffle | 0 | 26 | 6 | 0 | 0 | 0 |
| Targeted attenuation | 1 | 31 | 0 | 0 | 0 | 0 |
| Residual sham + | 0 | 32 | 0 | 0 | 0 | 0 |
| Residual sham − | 1 | 31 | 0 | 0 | 0 | 0 |

- Main startup: 2026-09-20 10:41:32 UTC; COMPLETE 10:47:33.563952 UTC.
- Execution: 361.564764s (6.03min); 135,145,163 bytes (128.88MiB), external only.
- Maximum six CPUs, numeric threads one; no automatic polling/retry/successor.
- No new founders or actual lineages; D141 unresolved and L20 MIXED unchanged.

Run: `l20_extension1_targeted_prediction_dev_v1_attempt1`.
Base: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`.
Outputs and terminal receipts are respectively under `outputs/RUN/` and
`runs/RUN/`; all individual predictions, group/cohort/block and future scores
are in `predictions.npz`, `dataset.npz`, `fits.json`, `summary.json`,
`diagnostics.json` and `verification.json`.

SHA256:

- COMPLETE: `68742ebaa28c3594dcd72123e481561f7e51a6549a6c752f6e56196764e9a13f`
- Summary: `7f4a8ea250e336f96517f0cc66b952508756468f682f4c13018a14430ece9f23`
- Verification: `79672c42902dec970e1a5cb7052db64cd692714b700fa6b4f0de60dde9cd95ac`
- Manifest: `ce3ab1bcb59e50d08c4e725f3a9c6a771a32a2dda69434f0ef99e76b27cc1878`

## Approved next scope

A separate saved-case review will examine the error distribution and diagnostic
responses, retaining all cases/controls, without new dynamics or new fitted
predictors. It cannot turn D151 into a positive prospective result. A changed
predictor or new address challenge requires a subsequent decision/specification.
