# D154 — marginal value of the second diagnostic copy

Approved 2026-09-20 after D153. This is post-result development on observed
founders, not an unobserved prospective test. D153's small control-minus edge
over passive motivates asking whether either beats the first copy alone.
Freeze this scope and qualified code before fitting the new actual-case model.

## Only one new information baseline

Add **one_copy = seven starting features + six common U0 endpoint features**,
in that order (13 inputs). U0 is the undisturbed diagnostic shared by every
two-copy observer. It already completes one read–rewrite–fresh-read cycle.
Do not use U1, shuffle C1, targeted/sham endpoints, recovery features, ID, seeds,
hidden matched-response contrasts, future labels or additional diagnostics as
predictor inputs. Public target-family/writer groups remain available as before.

Use the identical D152/D153 group-sensitive model: group feature means and
label intercepts, pooled within-group population scales (<=1e-12 replaced by
one), common slope plus zero-sum group deviations, penalty ratio one, and
prediction clipping to [-1,1]. This baseline has 52 penalized coefficients
and four unpenalized intercepts. All preprocessing uses training blocks only.

At each predeclared alpha **0.001, 0.01, 0.1**, hold out each of the 32 founder
blocks, train on the other 31, and predict all four lives/four groups. No inner
selection, alternative grid, final deployment fit or favorable-setting choice.
Retain all 96 new fits / 1,536 new predictions. All 32 observed blocks / 512
cases stay, including D135, D140 and the former D141 test (now development).

Reuse D153's six fixed-setting observers, old nested forecasts, all scores and
90 contrasts exactly. Do not refit any reference predictor. Keep starting-only,
passive, shuffle, attenuation, both control directions and mean control loss.
Previous apparatus controls stay pinned outside the prediction contest.
No new diagnostic, tissue dynamics, actual lineage, founder, threshold or dose.

## Fixed comparisons and limits

At each of the three settings, report these seven additional contrasts:

- one_copy versus starting;
- passive, shuffle, attenuation, control plus and control minus versus one_copy;
- mean control loss versus one_copy.

Positive paired MSE reduction favors the candidate. Mean control loss is the
average of two separate losses, not the loss of a mean prediction. These 21
new contrasts accompany all 90 original D153 contrasts. The focal descriptive
questions are one_copy versus starting, passive versus one_copy and control
minus versus one_copy; no new prospective primary or selected winner.

Report all original-outcome MSE, MAE/RMSE in preference points, groups, cohorts,
block differences and each single-block-omitted score average. Save all case
predictions and signed/absolute/squared errors. Score omissions are descriptive
influence checks, not refits, exclusions, jackknife uncertainty or independent
replicates. No p-value, confidence interval or equivalence claim.

The target stays terminal own-minus-alternative preference after three
replacements. The four existing D142 futures per case on the 16 former-test
blocks (1,024 labels) are secondary scoring only, never training or selection.
Report individual-future MSE/MAE/RMSE and mean-target errors, and independently
verify within-future-variance and paired-loss identities. All outcomes remain.

This is an **information-ablation baseline with a smaller observation budget**,
not a replacement for the equal-two-copy contest. Under this fixed learner,
adding inputs may help or hurt because of estimation and regularization as well
as information. Equal alpha does not equate effective complexity across 7/13/19
inputs. Failure to improve does not prove the second copy contains no information.
Improvement does not establish causal repair, autonomous diagnosis, complete
shape preservation or generalization to new founders.

## Source integrity and execution

Pin D153 COMPLETE
9bf970f7a18fdfce684764a0bfbb697faefc9b24904ab57e892f99b86e2e131a,
its 2,032 inputs / nine indexed outputs, full transitive closure, and audit
f3176e0f9ce7c7a25978c11dd1879689f67feeb6291f4277cb624a33380b2380.
Pin D153 RESULTS.md, this protocol, new models/checker/runner/tests/launcher.
Do not modify older frozen science. Synthetic qualification precedes freeze.

Independent checking uses group-slope SVD versus production common/contrast
normal equations. Check all new fits, training/held-out isolation, U0-only
feature access, group permutation, constants, clipping, deliberate corruption,
all new/old scores and exact source identities. Source fits are validated by
the pinned audit/closure, not refitted; old scores are independently recomputed.

Benchmark a full 32-block synthetic comparison, new fits, all score checks and
external roundtrip. Synthetic reference predictions are generated stand-ins,
not trained or scientific evidence. Benchmark forecast: 4 times qualified
full-comparison seconds +120. Main forecast: 2 times checked benchmark seconds
+2 times hash seconds +120. Storage: 4 times benchmark bytes +64MiB, cap256MiB
with 4GiB reserve. Single-use run l20_extension1_one_copy_dev_v1_attempt1.

One numerical worker, threads one, affinity CPUs0–5, at most six CPUs. Data,
fixtures, outputs, logs and caches under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1; code/docs only here. Runs forecast
above600s detach with null stdin/new session/durable log. No automatic progress
polling, retry or successor. Preserve failures and every unfavorable result.

D141's unresolved prospective result and L20 STRESS_TESTED / MIXED remain
unchanged. This approval does not launch a fresh cohort or a further diagnostic.
