# D161 — what a fair fresh-founder test would require

2026-09-20. **Planning only, not new evidence for L20.**
[Proposed scientific and execution rules](PLAN_V1.md).

## Simple terms

We have learned enough from the old cohort to stop making another small change
to it. The next useful test is to freeze a candidate and ask whether it works
on genuinely new founders. The candidate's apparent benefit is tiny, however:
another 16-founder experiment would be a weak way to settle it.

I recommend preparing a **768-founder, four-future-per-case confirmation** of
the unchanged residual-minus probe against passive observation. Both use the
simpler tied-reading predictor. This is not the original shuffle challenge,
and the fact that we chose this candidate after development is explicit.

That is a substantial run. Before authorizing it, implement and qualify the
executor and measure one complete disposable block. This turn does not generate
new founders, fit deployment models, launch a benchmark or start any lineage.

## Why this fitting rule

The primary pair must not receive different, selectively favorable settings.
Choose their common regularization from the existing three-setting development
panel by the mean of their two absolute errors, not by the size of their gap.
This symmetric rule gives **alpha .01**. The same selection outcome would follow
if the two observers' names were exchanged.

| Alpha | Tied passive MSE | Tied residual-minus MSE | Equal-weight selection score | Residual-minus relative gain |
|---|---:|---:|---:|---:|
| .001 | .006713854 | .006717290 | .006715572 | −.0512% |
| .01 | .006504357 | .006492888 | .006498622 | +.1763% |
| .1 | .006790183 | .006769891 | .006780037 | +.2988% |

These are reused, selection-affected development scores, not prospective
performance estimates. Choosing .1 just because its relative gap is larger
would ignore its worse absolute errors here. D160 itself selected no deployment
setting; the new common-setting decision belongs to this explicitly post-result
confirmation design.

Starting-only and one-copy choose their own settings by their own absolute
development error using the identical grid/tie rule:

| Proposed deployed rule | Selected alpha | Saved development MSE |
|---|---:|---:|
| Starting measurements only | .001 | .006512956 |
| One undisturbed diagnostic | .01 | .006514522 |
| Two undisturbed diagnostics, tied | .01 | .006504357 |
| Intact plus residual-minus diagnostic, tied | .01 | .006492888 |

The distinctions from the cheap baselines are also small. Their fairness
cannot be established by comparing all observers at a setting that happens to
over-regularize the cheap predictors. All four will be shown together in the
prospective interpretation. A candidate that beats passive but loses to a
cheaper baseline will not be presented as broadly useful diagnostic superiority.

The later deployment fit uses all 16 development founders, not the 15 in these
cross-validation folds. That change is one reason these planning numbers are
only approximate. No held-out outcomes or normalization enter deployment fits.

## One question first; other questions kept separate

Primary: residual-minus versus passive with the common .01 tied rule. Positive
means lower mean squared prediction error after three full replacements and
a fresh read. There is no biological survival threshold.

Secondary: does tying passive-reading weights improve over its separate-reading
version? At .01 its development gain is 2.459%, considerably larger than the
residual-minus edge. This would be useful evidence about predictor design, but
cannot serve as a substitute primary challenge success.

Other conditions at the primary pair's common setting remain unfavorable:

| Diagnostic versus tied passive | Relative development MSE reduction |
|---|---:|
| Original 25%-site shuffle | −.4127% |
| Competing-axis attenuation | −1.0948% |
| Residual-plus control | −1.1596% |
| Residual-minus control | +.1763% |
| Mean of the two residual-control losses | −.4916% |

Thus the proposal tests one development-selected direction; it does not claim
that perturbations in general work. Both controls, the literal original shuffle,
attenuation, all three settings/encodings, and all 17 observer definitions stay
in the planned secondary panel. Mean-control loss is not an ensemble forecast.
D141's already completed unresolved original-shuffle result remains unchanged.

## Founder count and precision

For the selected primary comparison, the saved gain is .0000114692 MSE and
the sample SD across the 16 founder-average paired losses is .0001422671.
Each founder retains all 16 cases and four futures. These are the variability
inputs, not 1,024 independent observations.

The planning calculation uses hypothetical normal half-width
1.9599639845 × SD / sqrt(N). Because SD is estimated from only 16 heavily
studied founders with overlapping training folds, show 1×, 1.5× and 2× SD.
These are sensitivity scenarios, not uncertainty bounds on SD. They do not
include all possible training/model-selection/distribution-shift uncertainty.

The operational target is ±.25% of development passive MSE at 1.5× SD.
It requires 662 founders by this approximation; rounding upward to a fixed
multiple of128 gives **768**. This target is a chosen resolution/cost trade-off,
not a meaningful biological cutoff, an equivalence margin or a power guarantee.

| Fresh founders | Half-width, base SD | Half-width, 1.5× SD | Half-width, 2× SD | Historical serial budget | Storage allowance |
|---|---:|---:|---:|---:|---:|
| 16 | ±1.072% | ±1.608% | ±2.143% | 1.69 h | 1.80 GiB |
| 128 | ±.379% | ±.568% | ±.758% | 12.34 h | 10.88 GiB |
| 256 | ±.268% | ±.402% | ±.536% | 24.52 h | 21.27 GiB |
| 512 | ±.189% | ±.284% | ±.379% | 48.88 h | 42.04 GiB |
| **768** | **±.155%** | **±.232%** | **±.309%** | **73.23 h** | **62.80 GiB** |
| 1024 | ±.134% | ±.201% | ±.268% | 97.59 h | 83.57 GiB |

Percentages refer to development-reference MSE, NOT preference points. These
are hypothetical widths, not confidence intervals calculated from new data.
At 768, the .232% allowance is still wider than the current .176% advantage.
An unresolved result is entirely possible. We should not promise that this
sample size will confirm the lead or continue sampling until the sign resolves.

For comparison, at 1.5× SD a .5% resolution requires166 founders, a1% resolution
42, and a2% resolution11. The .25% resolution would require1177 founders under
the2× SD scenario. Smaller fixed studies are legitimate if chosen for their
coarser resolution before outcomes; they are not disguised first stages of
optional stopping. No post-hoc power calculation was made.

## Cost and practical next gate

The 768-block proposal contains12,288 primary cases,49,152 terminal primary
outcomes, and73,728 diagnostic cycles, plus every founder's full apparatus
control panel on future0. Three other futures add ordinary/aligned paths only.
Every production path requires independent replay; repeats are independent
statistical futures, while replays are numerical checks of the same future.

Historical checked serial block costs are158.608s for D141 acquisition/original
diagnostics/full controls/first future,109.256s for D142's four additional primary
futures, and33.453s for D151's three extra diagnostics. Combining the first and
third with three quarters of the second gives274.003s per block. A25% margin
plus600s yields73.23h for768. This takes NO six-worker speed credit and is NOT
a measured ETA or a guaranteed upper bound for the new executor. CPU contention,
I/O, new auditing and model scoring may differ. Benchmark before launch.

Corresponding uncompressed component data sum to43,553,984 bytes per block.
Twice that total plus512MiB yields62.804GiB. A further4GiB reserve requires
66.804GiB free before launch. About89GiB was free when inspected, but this is a
shared data drive; recheck immediately before every stage. The root filesystem
has about3.1GiB free; all numerical artifacts stay external.

The immediate recommendation is therefore **implementation and disposable
qualification, followed by one complete disposable-block benchmark**, not the
full cohort. Any benchmark or run forecast over600s must detach, with at most
six CPUs, one numerical thread each, durable logs, no automatic polling/retry
or successor. Bring its measured time/storage budget back before full launch.

## Completed work and reproducibility

This turn added a saved-data calculator and a synthetic test suite, not a new
lineage executor. All38 tests passed in1.47s. A separate scalar-loop checker
recomputes losses and founder SDs, shared-setting selection and precision widths;
tests include malformed inputs, corruption, group/case aggregation, repeat/
founder order, exact mean-target gain identity and no fitting/dynamics/launch.

The saved design completed18:47:21.810045 UTC in13.03s. A fresh-process saved
audit passed in7.18s, checking2,270 source hashes and all69 fixed comparison
rows. There are zero new fits, forecasts, founders, diagnostics or lineages.
The independent calculator audit does NOT qualify the prospective executor.

External output directory:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_confirmation_design_v1_attempt1/`

It contains planning.json (all69 comparison/settings rows, founder/future loss
differences,20 absolute loss observers including three virtual means, width and
resource scenarios), verification.json and the source-pinned COMPLETE.json.
Total1,143,095 bytes (1.09MiB; filesystem allocation about1.2MiB).
Qualification receipt: `logs/d161_qualification_v1.xml` under the external root.

Hashes:

- COMPLETE: `d84b61f0eb6ba109cb2822f23685ce068cdf21ce1a55fdf8cde1df5b3bdedfe1`
- Planning: `0cc87333cfa1c472b5e1ce9f84955f0260834723b4fc44113f2e44b9b61b5c67`
- Verification: `15f4e2458963fdd5fa7c2d040521d367fd168a13faaa862e1875f14a2da342ad`
- Qualification: `acef711fce8453f442f8667670d0a19cd02ec98513fe0d87ed7c807b9c0ca2e6`

Reproduce the saved design audit with the retained Python environment, the
existing one-thread/CPU0–5 environment prefix, and:

```text
python -m l20_extension1.confirmation_plan --audit
```

The code and PLAN_V1.md are source-pinned. Revise a scientific choice by an
explicit new design version before new-cohort generation, never silently edit
this saved decision. D141 unresolved; L20 STRESS_TESTED / MIXED unchanged.
