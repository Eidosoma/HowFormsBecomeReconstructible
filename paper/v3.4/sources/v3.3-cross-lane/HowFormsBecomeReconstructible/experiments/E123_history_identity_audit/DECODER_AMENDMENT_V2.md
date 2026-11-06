# E123 numerical-budget amendment after retained_v1 stopped

2 November 2026. This amendment supersedes only the optimizer iteration cap in
[the original design](DECODER_DESIGN_V1.md). It is recorded after the failed
retained-data fit and before the replacement run. The audit remains post hoc.

`retained_v1` stopped at 17:27:15 UTC after 89.15 seconds. Ingestion completed
for all 64 source blocks and both budgets. The first eight record-observer
models were saved, but no complete probability table, prediction seal or
aggregate decoding score was produced. Those partial models are not scientific
results. The failure occurred while fitting the factor-1 body observer in
outer fold 0: a ridge-0.001 inner fit reached 300 iterations. Its final gradient
infinity norm was 1.419081e-6, below the separate 1e-5 check, but the solver
reported iteration exhaustion. The original rule correctly rejected it.

Use **maxiter = 2000** uniformly for every ridge fit, every input view, every
fold, both budgets and the shuffled-label control. Keep zero initialization,
L-BFGS-B, ftol 1e-12, gtol 1e-7, finite-result checks, solver-success requirement
and gradient infinity norm at most 1e-5. Converged fits stop early; the larger
cap is not an instruction to use 2000 iterations. Any further failed fit stops
the new release, with no automatic retry or model substitution.

All scientific choices remain those of V1: sources and inclusion, donor target,
features, grouping, ridge/temperature grids, probability smoothing, primary
contrast, endpoints, tie rules, controls and uncertainty. No held-out decoding
result is used to select this repair. E122's native outcomes were already
inspected before this amendment; the status is not a fresh prospective study.

Before a new launch:

1. Preserve the complete failed job/run and their original frozen inputs.
2. On the already implicated factor-1/body/outer-0 development data, reproduce
   the cap failure at 300 and test the fixed 2000 cap across its four ridge-0.001
   inner training subsets. Retain objectives, gradients, iteration counts and
   source exclusions. Do not predict or score outer-held-out cases in this check.
3. Repeat the excluded synthetic full-pipeline qualification against the exact
   revised code, including sealing, grouping and leakage safeguards.
4. Freeze the amendment and implementation under a distinct `retained_v2` job.
   Repeat source verification and the full prescribed analysis from the start;
   do not splice incomplete V1 models into V2. Launch detached on one numerical
   thread, using a measured runtime forecast and a bounded startup check.

The optimizer receipt additionally records its supplied iteration cap. The run
and prediction manifests include this amendment's hash. These are provenance
changes, not added fitting or selection degrees of freedom. Original V1 design,
freeze, qualification, forecasts and failure artifacts remain unmodified. No
manuscript changes or new native simulations are part of this repair.
