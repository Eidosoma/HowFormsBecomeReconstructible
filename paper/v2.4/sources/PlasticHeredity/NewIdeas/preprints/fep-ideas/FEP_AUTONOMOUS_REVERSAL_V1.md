# Autonomous reversal v1: can structured beliefs pay for their own evidence?

Specified 16 October 2026 before any new main outcomes. The user's “lets go”
authorizes the autonomous comparison recommended after the
[matched-feedback study](FEP_STRUCTURED_REVERSAL_V1_REPORT.md).

## Question and fixed comparison

Does the previously frozen structured reversal model improve recovery when
each learner must choose and pay for its own labels? The preceding constructed
histories showed better use of supplied evidence, but did not demonstrate
effective acquisition. This fresh, bounded study tests that missing link.

Compare only `CT4-anytime` (301 hypotheses) and `CT4-structured` (401 hypotheses).
Import both frozen implementations unchanged. The structured model has the
specified 50:50 G/R prior split, shares the original error law across reversal,
and retains the same total change mass, possible onsets 1–100, one-change limit,
calibration, four-step task-cost planner and terminal truncation. There is no
forced feedback, exploration bonus, horizon search or model/prior adjustment.

A wrong unaided answer costs 1; a purchased correct answer costs .1 and enters
that learner's subsequent belief updates. Unpurchased targets are withheld.
Both agents receive the same free warnings and calibration, but can acquire
different evidence. Physical change type, time and true law stay evaluator-only.
Always purchasing costs exactly .1 per task and requires no simulated arm.

## Fresh fixed population

Reuse all 27 physical base laws from the completed horizon population, without
pooling its outcomes. Draw 32 fresh independent blocks per base: 864 blocks.
Each block contains 64 calibration samples and a shared 100-task physical
stream. Use all six change families at onsets 13, 38, 63 and 88, plus stable:

- A-loss, B-loss and global reversal;
- A-partial, B-partial and both-partial (the existing independent .25 flips);
- stable, with no physical change.

These are 25 conditions per block, 675 base/condition combinations, 21,600
paired physical episodes and 4,320,000 policy decisions. This is deliberately
smaller than the previous horizon campaign; uncertainty may leave conclusions
unresolved. There is no sample-size extension or selection of favorable laws.
All zero-headroom conditions remain. The earlier supported onsets 26/51/76
are outside this bounded follow-up, not silently pooled with these four times.

Use the frozen physical generator and its draw order. Fresh main prefix:
`fep-autonomous-reversal-v1`; transfer-flip suffix: `-transfer-flips`.
Qualification, parallel checks and benchmark have separate prefixes and use
only the existing synthetic law. Freeze every main seed before generating
main observations. Verify separation from prior seed manifests and all current
synthetic seeds. Main indices are 0–31 for every base.

## Outcomes fixed before execution

Primary: **structured minus anytime realized post-change reversal cost per
task**, averaged equally across the four onsets, the 32 blocks within each
base and all 27 bases. For each episode, post-change cost is
`(10 * wrong_answers + purchased_answers) / (10 * (101 - onset))`.
Also report both absolute costs and their contrasts against .1.

The two-part autonomous reversal success criterion is (a) the upper endpoint
of the paired 95% Monte Carlo interval is below zero and (b) the structured
absolute-cost upper endpoint is below .1. A paired gain alone does not establish
economical recovery. This criterion is scoped to reversal, not general safety
across changes. No equivalence or non-inferiority margin is invented.

Secondary panels retain full-episode and post-change costs for each family,
the A-loss/B-loss/reversal core, all non-reversal changes, partial transfers,
and all changes. Stable has full-episode cost only. Report every base/condition
signed contrast, including stable and non-reversal harms and known-law floors.
For core recovery, separately report the same absolute and paired gates as
descriptive secondary checks, without replacing the reversal primary.

Intervals use independent blocks within each fixed base stratum. Average
paired conditions within a block first; do not count conditions or time steps
as independent. For base/block values x with B=27 and n=32,
`SE = sqrt(sum_b sample_variance(x_b) / (B*B*n))`, interval mean ± 1.96 SE.
Per-condition intervals use that base's 32 blocks. These are Monte Carlo
intervals on this fixed environment population, not uncertainty over real-world
environments, exact small-sample coverage, or multiplicity-adjusted discoveries.

Record the first paid answer after change, including the fraction with none,
and capped delay (101-onset when no answer arrives). Split post-change cost and
conditional regret into before / at / after the first paid answer; these are
mechanism descriptions of different selected histories, not causal mediation.
Track purchases during confident agreement (00/11 and subjective answer risk
strictly below .1), both overall and after change, with exposure denominators.
Retain extra purchases attributable to future information value, saved label
masks, predictive orientation error, information values, and posterior masses
for any completed change and completed reversal. Stable posterior crossings
are descriptive false alarms, not policy actions.

Evaluator-only conditional regret splits into insufficient checking,
wrong-direction answering and excess checking against the known-law decision
floor. Conditional risk is diagnostic; realized paid task cost is primary.
Do not compare full-history model evidence between agents that chose different
labels as though they saw the same data.

## FEP interpretation

The intervention enriches the generative model's structured uncertainty while
holding the task-cost objective fixed. Bayesian inference and finite-horizon
planning are components of this FEP-focused investigation. A positive result
would show that this specified relationship helps an agent acquire/use evidence
economically; a failure separates remaining acquisition and model-use limits.
The prior exact conditional VFE checks remain valid, but this study measures
no new VFE trajectory, canonical EFE advantage or autonomous structure discovery.

## Qualification, storage and stopping

Freeze this specification, runner, separate readback, model dependencies,
population and seeds. Qualify batched versus scalar policy histories, mask
unpaid labels, compare short-support decisions with the rational reference,
check terminal truncation, reproduce the previous evaluator on synthetic
streams, verify serial/four-worker fingerprints, and independently rebuild
cost/regret accounting from saved action traces. Reuse the prior frozen model
qualification instead of rerunning its full rational benchmark.

Benchmark four synthetic blocks per worker (four workers), with the same 25
conditions and two policies. Forecast seconds =
`120 + 3 * benchmark_wall_seconds * 864 / 16`.
The fixed feasibility ceiling is seven days. If it fails, preserve the record
and stop before main outcomes; do not resize or retune. Main chunks contain four
blocks (216 chunks). Use at most four CPUs, one numerical-library thread per
worker, no bytecode and lower scheduling priority. Forecasts over ten minutes
run detached with durable logs and no automatic progress polling.

Source and notes stay in `fep-ideas/`. All generated records, including tests,
snapshots, logs and compact action traces, go to
`/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/`.
Verify the mount and free space before writing. Never fall back to local data.
On main completion, automatically aggregate and run a separate saved-data
readback; do not run new scientific episodes during readback. Preserve failed
attempts, freeze identities and all previous studies. No automatic successor,
main-outcome tuning, manuscript edits or sister-project writes.
