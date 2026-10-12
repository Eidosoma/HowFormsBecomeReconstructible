# D158 — whole-founder training-influence audit

Approved 2026-09-20 after D157. Development sensitivity analysis on previously
observed founders; not a new prospective test, jackknife confidence interval
or permission to discard a founder. Freeze this protocol, qualified code and
source closure before actual refits. Earlier frozen science stays unchanged.

## Fixed scope

Use all16 founders90000–90015, four lives/four family-writer groups, all256
cases and all four saved futures. Only D157's fixed future-mean training arm:
same12 observers, feature definitions, group-sensitive ridge, penalty ratio
one, alphas .001/.01/.1, training-only group centering/scaling and clipping.
No inner selection, deployment model, alternative challenge or new dynamics.

For each founder d, remove its entire block from the training and evaluation
panel. For each of the remaining15 founders b, train on the other14 (neither
d nor b), and predict all16 cases of b. Keep every deletion, observer, setting,
group and repeat, including all unfavorable outcomes. 8,640 new scientific
fits,138,240 forecasts; save coefficients, raw and clipped predictions.

Reuse D157's full-cohort mean-target forecasts exactly, not refitting them.
They supply two references: full16-founder scores, and scores restricted to
the same15 founders as each deletion while keeping the original forecasts.
The latter isolates a score-composition change from retraining influence.
The full-cohort D157 record remains the development reference; no deletion
becomes a preferred dataset. Both controls, mean-control losses and cheaper
starting/one-copy baselines stay. All other D157 arms remain pinned.

## Scores and decomposition

Score original outcomes, every future, mean individual-future MSE, and MSE
against the four-future mean. Retain MSE,MAE,RMSE,bias, groups, blocks, all case
errors and clipping. Four repeats are not four independent founder blocks.

For all55 fixed observer pairs at each setting (165 orientations), retain:
full-cohort panel,16 score-only deletion panels,16 refitted deletion panels.
Every panel retains all four individual-repeat and repeat-omission scores and
founder-score omissions. These last omissions are descriptive, not extra fits.
Mean control losses are averages of separate losses, never ensemble forecasts.

For every contrast and outcome scope save full gain G, score-only gain S_d,
refitted gain R_d, score-composition change S_d-G, training change R_d-S_d,
and total change R_d-G. Independently verify the additive decomposition.
Report all16 signed values, sign counts, ranges and founder identities; do
not select a favorable omission or convert overlapping deletion panels into
independent replication, p-values, CIs or equivalence.

Also compare refitted and score-only errors for each12 observer and both
mean-control-loss conditions (672 direct training-effect comparisons);
retain signed forecast changes, MAE/RMS/max changes and group detail.
All55 orientations x3settings x33panels =5,445 observer comparison records,
plus672 direct training-effect records;165 decomposition records.
The primary interpretive focus remains control− versus matched passive,
with both encodings, starting/one-copy comparisons and the full control panel.

No causal claim about tissue repair follows from predictor-training influence.
D141 remains unresolved and L20 STRESS_TESTED / MIXED unchanged.

## Qualification, freeze and budget

Pin D157 COMPLETE
47af756037fe868f90e93858fd8d127e339d6d2e2e537ffaa9489f3870e6a913,
its2,150 inputs/eight indexed outputs, fresh audit
1e5b1ea708da3ddb0f278982564da4ec8072de652cedb2bf14e1759c44f67cd9,
and RESULTS.md. Bridge all six source arrays and D157 mean-target forecasts
exactly; independently reproduce their165 comparison scores without old fits.

Synthetic qualification checks both excluded-founder boundaries, target and
feature isolation, independent group-coordinate SVD, all encodings/settings,
permutations, constants/rank deficiency/clipping, controls, score/refit
decomposition, corruption, saved roundtrip and execution safeguards.
A complete five-founder synthetic audit is timed in qualification.
Benchmark the complete16-founder workflow including independent checks and
saved roundtrip. Synthetic baseline preparation is included in benchmark
time/storage but never scientific evidence or actual reference refitting.

Benchmark forecast=48*qualified_small_audit_seconds+120.
Main forecast=2*checked_full_audit_seconds+2*hash_seconds+120.
Projected storage=4*benchmark_bytes+64MiB, at most1GiB with4GiB external reserve.
Single-use run l20_extension1_training_influence_dev_v1_attempt1.

One numerical worker,threads one,affinity CPUs0–5,maximum six CPUs. All data,
fixtures,logs,cache and outputs under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1; code/docs only here. Forecast>600seconds:
detach with null stdin,new session,durable log; no automatic polling,retry or
successor. Preserve failures. No new prospective cohort is authorized.
