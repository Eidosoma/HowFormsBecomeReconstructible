# D154 — one-copy information baseline results

Completed and freshly audited **2026-09-20**.
[Fixed protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[previous matched-setting result](../matched-regularization/RESULTS.md).

## Plain-language result

**One undisturbed diagnostic copy has lower original-outcome MSE than every
two-copy observer, at all three fixed settings.** In particular, the previously
promising control − has **3.067%, 1.166% and 0.745% higher MSE** than this
cheaper one-copy baseline. Beating two undisturbed copies was not enough to
beat one.

This does not mean extra observation is intrinsically useless. It says that
the present learner does not consistently turn the second copy's measurements
into better forecasts on these observed cases. Added estimation complexity,
redundant measurements and their regularization are possible contributors,
not causes established by this comparison.

Starting measurements alone still have the lowest original MSE at .001/.01;
one copy has the lowest at .1. One copy has the lowest original MAE at .001/.01,
while control − has the lowest at .1. Saved-future comparisons are mixed.
There is no general challenge-prediction win, no new prospective evidence
and no selected winning setting or perturbation.

All 32 observed blocks / 512 cases remain. Former held-out founders are
DEVELOPMENT. No new tissue simulations, diagnostic copies, outcomes or founders.
D141's unresolved prospective result and L20 STRESS_TESTED / MIXED are unchanged.

## What was added — and what was not

Only one new information baseline: seven starting features plus six endpoints
from the common undisturbed U0 diagnostic. No second-copy measurements, recovery
features, hidden response contrasts, IDs or seeds enter it. U0 completes the
same one read–rewrite–fresh-read cycle as before.

The D152/D153 partially pooled group-sensitive model is unchanged: four group
intercepts and 52 penalized coefficients for 13 features, same common/deviation
penalty ratio one. Training-only transformations; predictions clipped to [-1,1].
At each fixed alpha .001/.01/.1, each whole founder is held out and the model
fits the other 31 blocks. No inner selection or repeated-future labels in training.

All **96 new fits / 1,536 predictions** are independently reconstructed by
group-coordinate SVD. D153's six fixed-setting observers and nested references
are reused exactly, without refitting. All 90 D153 contrasts and scores are
retained unchanged; 21 predeclared one-copy comparisons are added.

The new baseline has a **smaller observation budget**. It is not a replacement
for the equal-two-copy passive/challenge contest. Equal numeric alpha does not
equate effective complexity across 7, 13 and 19 features. Model performance
does not establish the absence or presence of additional information for every
possible learner.

## Original outcomes: complete fixed-setting panel

Lower is better. Target: unchanged terminal own-minus-alternative preference
after three replacements. MSE is in squared fractional preference units, not
survival probability or complete-shape preservation.

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.006698674 | 0.006643819 | 0.007093564 |
| One undisturbed copy | 0.006862477 | 0.006652330 | 0.006809440 |
| Two undisturbed copies | 0.007133111 | 0.006793766 | 0.006878771 |
| Shuffle | 0.007254431 | 0.006862676 | 0.006941898 |
| Attenuation | 0.007644903 | 0.007013843 | 0.006922637 |
| Control + | 0.007326047 | 0.006893307 | 0.006897118 |
| Control − | 0.007072939 | 0.006729890 | 0.006860192 |

Mean absolute error, in preference points:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 5.0229 | 5.0214 | 5.3090 |
| One undisturbed copy | 4.8384 | 4.8014 | 5.0419 |
| Two undisturbed copies | 4.9698 | 4.8469 | 4.9989 |
| Shuffle | 5.0227 | 4.9293 | 5.0555 |
| Attenuation | 5.0328 | 4.8997 | 5.0368 |
| Control + | 4.9878 | 4.8487 | 4.9912 |
| Control − | 4.9606 | 4.8219 | 4.9890 |

Root mean squared error, in preference points:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 8.1845 | 8.1510 | 8.4223 |
| One undisturbed copy | 8.2840 | 8.1562 | 8.2519 |
| Two undisturbed copies | 8.4458 | 8.2424 | 8.2938 |
| Shuffle | 8.5173 | 8.2841 | 8.3318 |
| Attenuation | 8.7435 | 8.3749 | 8.3202 |
| Control + | 8.5592 | 8.3026 | 8.3049 |
| Control − | 8.4101 | 8.2036 | 8.2826 |

All new paired contrasts below use **positive = candidate improves MSE**.
Negative values mean worse. No confidence interval or equivalence claim is made.

| Candidate versus reference | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| One undisturbed copy / Starting only | −2.445% | −0.128% | +4.005% |
| Two undisturbed copies / One undisturbed copy | −3.944% | −2.126% | −1.018% |
| Shuffle / One undisturbed copy | −5.712% | −3.162% | −1.945% |
| Attenuation / One undisturbed copy | −11.402% | −5.434% | −1.662% |
| Control + / One undisturbed copy | −6.755% | −3.622% | −1.288% |
| Control − / One undisturbed copy | −3.067% | −1.166% | −0.745% |
| Mean control loss / One undisturbed copy | −4.911% | −2.394% | −1.016% |

At .01, one-copy MSE is only 0.1281% higher than starting-only. That small
observed gap is not evidence of equivalence: its sign changes in 12 of the
32 single-block SCORE omissions. In contrast, both beat every two-copy
observer on the original full-panel MSE at that setting.

The full D153 summary, including its exact old nested reference and comparisons,
is embedded in the new external summary. Nothing was replaced or rescored as a
new prospective outcome.

## Founder, cohort and group limits

The original-outcome disadvantage of two undisturbed copies versus one copy
survives all 32 single-block score omissions at .001/.01. At .1, omitting
block 90001's scores reverses it. Control − loses to one copy under all 32
omissions at .001, but omitting 90001 reverses that comparison at .01/.1 too.

These are changes to saved score averages, not refits, removals from the study,
jackknife confidence intervals or evidence that 90001 is invalid. It remains
in every primary development aggregate. The two substantive challenges
(shuffle and attenuation) remain worse than one copy under every original
single-block score omission at every setting.

Control − versus one-copy, original MSE reduction by cohort:

| Setting | D135, 8 blocks | D140, 8 blocks | Former test, 16 blocks | Better/worse blocks overall |
|---|---:|---:|---:|---:|
| 0.001 | −13.078% | +3.402% | +1.603% | 13/19 |
| 0.01 | −7.044% | +4.390% | +0.954% | 14/18 |
| 0.1 | −2.498% | +3.261% | −1.110% | 18/14 |

The D140 cohort favors the second control copy at all three settings;
D135 favors one copy at all three. Former-test original outcomes favor
control − at .001/.01 and one copy at .1. The aggregate is not uniform.

Ordinary B remains the difficult group. Control − versus one copy worsens
ordinary-B MSE by 0.000954/0.000500/0.000693 and improves aligned-B MSE by
0.000119/0.000211/0.000494 across the settings. Both A groups worsen slightly.
The aligned-B improvement does not offset the ordinary-B loss in the original
aggregate. Starting-to-one-copy also contains opposing ordinary/aligned-B
changes. All group and cohort scores are saved; none is selected for reporting
as a new isolated success.

## Secondary saved futures

These are the same four D142 saved outcomes per case on the 16 former-test
blocks (1,024 labels), never fitting or selection targets. They are not a fresh
cohort or independent new evidence of prospective advantage.

Individual-future MSE:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.006934551 | 0.006542999 | 0.006932775 |
| One undisturbed copy | 0.006791235 | 0.006405755 | 0.006671629 |
| Two undisturbed copies | 0.006933798 | 0.006471422 | 0.006641863 |
| Shuffle | 0.007097728 | 0.006531997 | 0.006763317 |
| Attenuation | 0.007144561 | 0.006466938 | 0.006638654 |
| Control + | 0.006759403 | 0.006388323 | 0.006643264 |
| Control − | 0.006953838 | 0.006442691 | 0.006612408 |

Individual-future MAE in preference points:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 5.0792 | 5.0143 | 5.2656 |
| One undisturbed copy | 4.9610 | 4.8123 | 5.0153 |
| Two undisturbed copies | 5.0074 | 4.8387 | 4.9667 |
| Shuffle | 5.0843 | 4.8573 | 5.0429 |
| Attenuation | 5.0493 | 4.8305 | 4.9627 |
| Control + | 4.9410 | 4.7926 | 4.9638 |
| Control − | 5.0027 | 4.8237 | 4.9602 |

All new relative MSE reductions:

| Candidate versus reference | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| One undisturbed copy / Starting only | +2.067% | +2.098% | +3.767% |
| Two undisturbed copies / One undisturbed copy | −2.099% | −1.025% | +0.446% |
| Shuffle / One undisturbed copy | −4.513% | −1.971% | −1.374% |
| Attenuation / One undisturbed copy | −5.203% | −0.955% | +0.494% |
| Control + / One undisturbed copy | +0.469% | +0.272% | +0.425% |
| Control − / One undisturbed copy | −2.394% | −0.577% | +0.888% |
| Mean control loss / One undisturbed copy | −0.963% | −0.152% | +0.656% |

One copy improves over starting-only on these saved futures at every setting.
At .001 that edge reverses when 90014's scores are omitted; at .01/.1 all
16 omissions stay positive. Control + improves slightly over one copy at
all three settings, but its sign reverses under some single-block score
omissions at every setting. Control − only improves over one copy at .1,
and that sign also reverses under some omissions. These are descriptive
point estimates, not resolved uncertainty or equivalence.

The difference from original outcomes is not just mixing different cohorts.
On the *same* 16 former-test blocks, one copy versus starting-only is
−3.738%/−1.073%/+5.234% on original outcomes and
+2.067%/+2.098%/+3.767% on saved-future averages. Control − versus one copy is
+1.603%/+0.954%/−1.110% on original outcomes and
−2.394%/−0.577%/+0.888% on saved futures. Ranking sensitivity therefore persists
when cohort membership is held fixed. This does not identify its cause.

Individual-future RMSE, mean-target scores, every block/group/cohort result and
all signed/absolute/squared case errors are retained externally. Independent
checks confirm the within-future-variance and paired-loss identities. No
inferred noise ceiling or post-result choice of an easier scoring target.

## Bounded conclusion and next proposal

The second copy has **not earned a consistent predictive advantage under
the tested learner**, and the previous control-minus lead does not clear the
one-copy baseline on the original aggregate. This is useful negative development
evidence; it does not prove that second-copy information is absent.

One bounded next check would test whether the extra six fitted inputs are a
contributor: combine the two permitted endpoint profiles by a fixed arithmetic
mean, retaining seven starting features plus six mean features (13 total).
Apply that same compression to passive and all four edited second-copy
observers, at the same three settings; keep the one-copy and original two-copy
models and every case as references. This would use saved data only.

Such a check would ask whether a simpler encoding of two observations helps,
not prove that overfitting explains the current losses. It sacrifices separate
response/difference information and changes predictor geometry, so positive or
negative results would need that qualification. Specify/freeze it separately;
do not select a favorable direction or setting. **Not launched here.**

No new prospective cohort, deployment model, challenge retuning, autonomous
repair claim or complete-shape claim follows from D154.

## Qualification, cost and integrity

- First qualification: **53 tests pass**, no failures/skips, 127.61s.
  External report logs/d154_qualification_v1.xml, fixtures tmp/d154_qualification_v1.
- Freeze **15:00:29.392507 UTC**, 2,054 inputs, before actual-case baseline fits.
- Synthetic benchmark COMPLETE **15:01:21.529619 UTC**:
  full comparison/check/roundtrip 9.874866s; hash check9.870792s.
  Conservative main forecast159.491316s /83.381454MiB; synthetic outputs4.845364MiB.
- Main manifest **15:02:14.279271 UTC**; COMPLETE **15:02:38.640792 UTC**.
  Recorded execution **24.361544s**, excluding preflight;
  **5,556,049 bytes (5.298661MiB)** external outputs.
- Fresh durable audit **15:03:25.075785 UTC**, 25.558336s: **2,063 inputs /
  nine indexed outputs**, all96 fits, exact reference identities,
  21 new +90 retained contrasts and75 case-error arrays pass.
- One numerical worker, threads one, affinity CPUs0–5. Attached because forecast
  <600s. All numerical artifacts external, code/docs only here. No reference
  refits, new dynamics, automatic retry, detached-job polling or successor.

Run: l20_extension1_one_copy_dev_v1_attempt1.

External base:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`.

Outputs under outputs/<run>/:
dataset.npz, predictions.npz, fits.json, reference_predictions.npz,
reference_nested_predictions.npz, case_errors.npz, summary.json,
verification.json, input_hashes.sha256, plus output_hashes.sha256.
The summary includes the exact retained D153 summary and all new one-copy
comparisons; every founder, group, life and predeclared setting is retained.

SHA256:

- Freeze: 1c09c15293cb8eb819debfa097dc134d5703462aec76fd982e167efc9b821a2c
- COMPLETE: 334838d061d1523d14055c6e76149f38ff86452768cdbb704fbdade588473ab9
- Summary: 101c0b8abc6fde3d07ace3c421edf434f4881fe4e8cff413938e1488e510a6a3
- Verification: 141ec9c6e091429b808c13d04ae145029d2244200afb20c26fa517b20d152add
- Manifest: 5b5e7dca52bf8189bc67e00a2db6bd9ec0cce50e2d12d86084708d2f26d056c0
- Output index: 7e043a23d72a64c511644efaf7331a6b5137d4ffca40965c55321fad45f20979
- Fresh audit: 64077c703bf3812b72ed6aa375a25d55197d4eb2a5f9fdfa6ede5294f290eee2

Receipt: logs/l20_extension1_one_copy_dev_v1_attempt1_saved_audit_v1.json.
