# Short observation forecast baseline development

TT001 uses existing E041 lineages to establish a reproducible P01 evaluator and conventional baselines. It is retrospective development on an outcome-known cohort. RDT is not a fitted contestant, and no RDT pass or fail will be inferred.

## Source and independent unit

Use all 32 E041 blocks 32000 through 32031, all four founders and all four descendant lineages per founder. The only policy is full bridge rewriting. The independent resampling and splitting unit is the block, not the 512 descendant lineages or repeated readouts. Reuse compact E046 measurements, verify their recorded completion hashes, and independently compare body success, body margins and final terminal success with original E041 case arrays. E042 intermediate measurements support a separate check of the diagnostic-column mapping.

Read only the selected completed E041, E042 and E046 sources. E050/E051 scientific outputs and E052 future outcomes are excluded from this study. Source identity checks do not rerun the original dynamics or prove that historical audits were correct.

## Forecast boundary and targets

Make separate forecasts immediately after rebuild k=3 and k=8, including the current write. A test lineage supplies only generations 1 through k. The targets are:

- `terminal`: both-cue success at generation 32 under the original normalized, scattered-injury fresh-recipient assay.
- `future_path_and_terminal`: every rebuilding body from k+1 through 32 passes its saved both-cue readout, and the terminal assay passes.

The second target permits earlier failures in the observed prefix. It does not confuse a known prefix failure with an unpredictable future failure, or assert correctness between samples. Also report all-32-body success and terminal success as separate cohort checks against the published 205/512 and 428/512 counts.

Training blocks supply complete body-success histories and their terminal labels. Test blocks supply only prefixes to the predictors. Consequently this measures prediction across blocks, not short-only calibration or unseen-horizon extrapolation. Acquisition, ports, reader and writer remain fixed; historical specificity, causal interventions, other tasks and cross-apparatus transfer are outside scope.

## Measurements and costs

The current-readout model uses current body success, worst signed margin, both cue amplitudes and both absolute output biases, six features. The prefix models use last value, observed mean and observed linear slope for all 24 E046 diagnostic columns, plus minimum body margin, prefix failure fraction and trailing failure count, 75 features. The diagnostic columns include externally recorded incoming/outgoing weight summaries and current/past writing and repair measurements. They require observation and storage of those quantities; they are not claimed to reside in the inherited packet. Missing prior-write values at generation one are masked rather than treated as measured zeros.

The theory comparator must receive the same available data and charge any extra probes. TT001 reports k, measured dimensions, training counts, model fit counts and elapsed computation; it makes no physical energy or autonomous-control claim.

## Baselines and fixed fitting rules

1. Training prevalence with a Jeffreys pseudocount.
2. A two-state body-success Markov model. Estimate a transition matrix for each generation from training lineages, shrinking each row by 16 observations toward the pooled training transition row. Estimate the terminal readout conditional on the final body state with Jeffreys smoothing. Propagate ordered matrices from the observed state at k. For the path target retain only transitions into a passing next body before applying the terminal readout. The full training trajectory is explicitly available for this fit.
3. Standardized current-readout ridge logistic regression.
4. Standardized 75-feature prefix ridge logistic regression.
5. Histogram gradient boosting on the same 75 features, maximum 100 iterations, learning rate 0.1, minimum leaf size 24, and internal early stopping disabled.

Logistic C is chosen from [0.01, 0.1, 1, 10]. Boosting chooses maximum leaf nodes from [3, 7] and L2 penalty from [1, 10]. Ties take the first listed setting. Single-class training folds return their Jeffreys-smoothed prevalence. Scaling is fitted only on the appropriate training fold. All candidates and both cutoffs and endpoints are reported, including failures; there is no favorable-subgroup substitution.

## Splits and scoring

Outer folds are `(block_id - 32000) mod 4`, fixed independently of outcomes. Each fold trains on 24 blocks and predicts eight. Within each outer training set, sorted unique block IDs are assigned cyclically to three inner folds for tuning by mean block Brier loss. Every lineage and related founder in a block stays together. The same outer split is used across endpoints and cutoffs.

Brier loss is the main development score and clipped binary log loss is secondary (epsilon 1e-6 for scoring only). Report all out-of-fold probabilities, per-block losses, prevalence, mean prediction and ten fixed probability-bin summaries. Report paired Brier improvements over training prevalence, with 4096 seeded block resamples of the fixed out-of-fold loss differences. These are descriptive intervals conditional on fitted predictions; overlapping training sets and model selection uncertainty prevent treating them as confirmatory confidence intervals. No hypothesis test, empirical superiority margin or RDT qualification is assigned.

## Technical qualification and stopping

Before development scoring, run synthetic tests for grouped splitting, future-data exclusion, test-label exclusion, constant-class fitting, block weighting and analytical terminal/path probabilities. Include a correlated-success example that rejects multiplying a marginal pass rate by an ordinary transition matrix. Include two finite processes with identical short readouts and different later outcomes; these demonstrate the need for assumptions, not a new empirical discovery.

Benchmark the complete fitting workflow on excluded synthetic arrays with the same dimensions. Run one process with one numerical thread. Require projected runtime at most 600 seconds for foreground execution; otherwise follow the parent detached-run policy. Set a 512 MiB storage reserve. Abort on source-hash mismatch, nonfinite values, shape/schema mismatch, optimizer nonconvergence, endpoint disagreement or any test/verification failure. Preserve the failed run without changing scientific semantics. Any substantive change after per-lineage results are read becomes a new developmental version.

Freeze code, this protocol, plan and source completion identities before the scored development run. Save portable selected input arrays, fitted-model metadata, all predictions, source hashes, software versions, split memberships and a separate calculation check. A byte-identical replay may verify these developmental outputs; it is not external replication.
