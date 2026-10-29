# Change at any task: a bounded FEP model extension

**10 October 2026. Prospective design, before this cohort's outcomes.**
The user's next "lets go" approves the proposed response to the
[unexpected-timing failure](FEP_UNEXPECTED_CHANGE_V1_REPORT.md). This study
changes one supplied model assumption: when its single change can occur.
It does not retune the old model or alter any previous scientific record.

## Model and question

Add **CT3-anytime** to all nine unchanged policies. It is CT3-flat's model
with possible change times **1 through 100**, rather than 26/51/76. Task 1
means immediately after the separate calibration phase. Preserve the total
prior probability **1/2 of no deployment change** and **1/2 of one change**.
Conditional on change, assign equal probability to every task and equal
probability to the general, A-loss and B-loss hypotheses. Each time/kind
therefore has prior mass **1/600**; there are 301 mixture components.
The prior probability of change at task t conditional on no earlier change
is **1/(201-t)**. This is a uniform finite-episode onset prior, not a constant
hazard or a recurrent-change process. Do not fit it to the new outcomes.

Keep the conditional sensor model and weak new-phase priors unchanged.
Old calibration informs the old phase; general change draws the original
Dirichlet(1/2,1/2,1/2,1/2) prior, and each single-loss hypothesis uses a fair
failed sensor with Beta(1,1) for the other sensor's error rate. Retain exact
Bayesian updating from free warnings and purchased labels only. Never supply
truth, physical law, change time, change status or unpaid answer feedback.

Use the same three-decision contingent expected-task-cost objective, 100
deployment tasks, 64 calibration examples, prices and rational tie rules.
Allowing an imminent change must affect hypothetical future branches as well
as live inference. No pruning or posterior approximation is introduced.
The implementation may exactly merge future-time hypotheses while they have
identical histories, but must agree with explicit component enumeration.

The FEP question is whether a less restrictive generative model supports
useful adaptation despite uncertainty. Conditional inference obeys
`F(q;h,c) = KL(q || p(theta|h,c)) - log p(h|c)`; policy selection retains its
separately specified cost objective. This tests a supplied temporal model,
not autonomous structure learning, a new canonical EFE or a uniquely FEP
advantage. Do not infer a measured VFE trajectory from task performance.

## Unchanged population and fresh pairing

Retain the previous 27 base laws, all six transformations and all 43 physical
conditions per base. The old supported schedule 26/51/76 and the challenge
schedule 13/38/63/88 remain separate panels; those names describe the old
model's support. Stability is simulated once per block. Keep every family,
late change, adverse condition and zero-headroom case.

Use **1,024 fresh paired blocks per base**, 27,648 independent blocks,
1,161 unique conditions and 1,188,864 physical episodes, each scored by all
ten policies. Prefix `fep-anytime-change-v1`, root 20260924, and a separate
`-transfer-flips` prefix use the existing SHA-256 seed rule and draw order.
Verify separation from every preceding cohort and qualification/benchmark
streams. No earlier sample is pooled. All policies receive the same physical
streams; their purchases alone determine their retained label histories.

## Frozen endpoints and decisions

The primary endpoint is CT3-anytime's **unexpected-core recovery cost minus
0.1** (always purchasing the correct answer). A complete success claim needs
all three upper nominal 95% bounds strictly below zero:

1. Unexpected-core recovery below always purchasing.
2. Paired unexpected-core recovery below unchanged CT3-flat.
3. Paired complete unexpected-core episode cost below unchanged CT3-flat.

The second rule measures improvement over the model actually being changed.
Comparisons with C3, C-Y and every other control remain reported; they cannot
replace the absolute criterion. Report the corresponding supported-schedule
criteria descriptively, without combining schedules into a favorable mean.
Failure or equality is failure of a gate, not a reason to change it.

Use the previous exact weights: half stable/half changed for full panels;
equal families, times and 27 base strata for changed panels. Normalize each
condition's recovery by its own remaining tasks. Keep weight denominator 144
and post scale 34,234,200. Full costs include 0.064 calibration per episode;
post-change and early windows exclude that sunk cost. Retain paired block
uncertainty `SE² = sum_base Var(block_base)/(27² × 1024)`, mean ±1.96 SE.
These are fixed-population Monte Carlo intervals, not simultaneous guarantees
or arbitrary-world uncertainty.

Stable-world total cost and purchase cost are mandatory separate endpoints,
including paired CT3-anytime minus CT3-flat and comparisons with 0.1. Report
all whole-episode and recovery family/time/condition means and signed harms.
Do not describe every extra purchase as unnecessary: it may acquire useful
future evidence. Additionally record, for CT3-anytime, the number of tasks
with posterior change probability above 1/2, first such task (101 if absent),
and the posterior change probability summed over the episode. In a truly
stable world these are descriptive false-alarm measures, not a new action or
a gate. Record them after that task's available label update. Also record
whole-episode evaluator-only physical risk, known-law floor, insufficient
checking, wrong-direction regret, excess checking and subjective risk. This
distinguishes purchase frequency from checking that is costly relative to a
known-law myopic oracle; it is not a causal intervention comparison.

Preserve first post-change purchases, before/first/after-purchase diagnostics,
planning values, posterior categories at 25/50/75/100, and 25-task recovery
windows (13 tasks for onset 88). Own-schedule windows partition each recovery
endpoint; overlapping windows from different schedules are never summed.
Retain known-law floors and all zero-headroom cases.

## Qualification, execution and preservation

Freeze this design, new source and scalar qualification source, population,
weights and both seed sets before main outcomes. Import all old policies and
the physical simulator unchanged. Verify every inherited identity and preserve
all failed attempts. A source correction requires a new attempt and recorded
reason; no design or outcome-driven tuning, sample extension or retry that
discards evidence is permitted.

Qualify against an independent rational scalar filter and direct contingent
planning, including changes at task 1, early/interior/late tasks, consecutive
times, near-terminal horizons, missing versus purchased labels, exact ties,
and hypothetical future resets. Integrate short complete latent paths to
verify posterior evidence and the conditional VFE identity. Restricting the
new model to 26/51/76 must reproduce frozen CT3-flat. Verify the 301-component
prior and time-100 no-change probability, all old arrays byte for byte after
projection, scalar endpoint/interval/sign calculations, window/phase closures,
new stable diagnostics, and serial/four-worker fingerprints.

Benchmark **32 synthetic blocks** (eight per worker), all 43 conditions and
ten arms, on four CPUs. Forecast `120 + 3*benchmark_wall*27648/32`; do not use
scientific outcomes for runtime selection. Execute 864 fixed chunks of 32
blocks. A forecast over 600 seconds requires detached execution, durable logs
and no automatic progress polling. Use at most four CPUs and one BLAS thread
per worker; disable bytecode. Keep generated data, logs, snapshots and any
failed attempts under the verified mount
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1/attempt-NN/`.
No workspace-disk fallback. Source and research notes stay in this folder.

Complete a verified report and the six live notes, or a qualified detached
checkpoint. At a requested later check-in, inspect completion/failure once
and independently reconstruct saved results before interpretation. Preserve
the old failure and all prior confirmations. This authorization covers this
one extension; no automatic successor, hazard/prior/horizon tuning, manuscript
integration or sister-project writes.
