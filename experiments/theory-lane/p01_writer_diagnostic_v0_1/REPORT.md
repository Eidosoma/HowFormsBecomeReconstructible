# Native writer diagnostic: useful next-cycle information, no first-generation long-horizon gain

**Status: retrospective development analysis of eight E051 blocks.** The proposed writer/reader interaction occurs in saved native states and supplies useful next-cycle predictive information in a fixed comparison. The simpler explanation based on sign flips alone is incomplete. First-generation features do not improve the 32-cycle forecast. The running E051 experiment was not altered, and its full dynamics audit and scientific decision remain separate.

![Writer diagnostic](results/writer_diagnostic.png)

## What was actually checked

The cohort is blocks 34000–34007, identified in E051's saved early-look record: four founders and four recipients per block, 128 lineages per condition. We selected the four already discussed cue pairings and the original/tolerance histories, using all 32 boundaries. This gives **32,768 body contexts**, with eight independent blocks. Repeated boundaries and condition pairs are not independent replicates.

For each saved developed body, an independent implementation applies the original writer, the fixed 1e-4 tolerance writer, and a control that restores original signs while keeping tolerance magnitudes. All comparisons hold the body and surviving-edge mask fixed. The control is evaluated only through a linear normalized-reader calculation; it is not a simulated native rescue.

All 32,768 recomputed actual-policy packets match the saved outgoing bytes. Array commitments and score calculations were checked against retained records. The six numerical counts previously supplied by the user are reproduced, and two additional counts from the same selected cohort are reported below. This is an audit of selected writer/endpoint calculations, **not** an independent replay of the developmental dynamics.

| Rebuilding cue pairing | Original writer, terminal success | Tolerance writer, terminal success |
|---|---:|---:|
| Matched | 120/128 (93.75%) | 3/128 (2.34%) |
| Noise correlation .999 | 126/128 (98.44%) | 80/128 (62.50%) |
| Independent cue noise | 126/128 (98.44%) | 122/128 (95.31%) |
| Initial-state correlation .99 | 119/128 (92.97%) | 3/128 (2.34%) |

The endpoint is the original h32 normalized scattered-injury terminal both-cue assay. Teaching and terminal-assay cue randomness remain matched. These partial-cohort values do not constitute E051's full-cohort decision or a new confirmatory test of RDT.

## The divergence appears during repeated repair

At generation 1 the original and tolerance writers produce identical packets in every selected case. All current and next-body assays pass. Under matched cues the writers also coincide at generation 2. A post-hoc byte check at the first observed divergence establishes:

| Pairing | First writer difference | Identical pre-write bodies | Different outgoing packets |
|---|---:|---:|---:|
| Matched | Generation 3 | 128/128 | 98/128 |
| Noise .999 | Generation 2 | 128/128 | 124/128 |
| Independent noise | Generation 2 | 128/128 | 22/128 |
| Initial-state .99 | Generation 3 | 128/128 | 98/128 |

For matched cues at generation 3, both policy histories still have the same current performance, 126/128 passes, because their bodies are byte-identical. The difference is introduced by writing. This is a stronger mechanistic observation than comparing unrelated failed and successful late bodies. The onset generations were selected after examining the main diagnostic and are explicitly exploratory.

Under matched cues, tolerance histories increasingly enter the regime where nonzero cue contrast is replaced by coactivity. The mean fraction of available edges affected is **1.20% at generation 3, 18.13% at generation 8, 45.48% at generation 16 and 55.43% at generation 32**. The corresponding original-history fractions are 1.20%, 4.26%, 5.40% and 4.75%. These are the *additional* substitutions caused by the tolerance, excluding exact-zero fallback shared by both rules.

At generation 32, the tolerance history's mean normalized-reader row change relative to the original writer on that same body is .8521, compared with .09334 on original-history bodies. The mean absolute change in incoming drive can be consequential even when raw edge weights are small. The growing affected fraction, changes in normalized influence and loss of performance are consistent with feedback in which weakened cue responses expose more edges to substitution. The analysis does not identify that feedback as the unique causal mechanism.

Independent cue noise provides an informative contrast. At generation 32 only .276% of available edges on tolerance-history bodies receive these additional substitutions, and terminal success is 122/128. This supports investigating the distribution of cue contrasts relative to the fixed cutoff. It does not show that noise is generally beneficial or that arbitrary tolerances are safe.

## The sign-only explanation needs narrowing

On bodies from the original matched-cue histories, averaged over generations 2–32, the tolerance substitutes 4.72% of available edges and flips 1.33% of their signs. The mean normalized-reader row L1 difference is .09126. This confirms that the tolerance is not an innocuous treatment of physically irrelevant numbers.

However, the control preserving tolerance magnitudes while restoring original signs closes only a small part of the linear cue-transfer difference:

| Same original-history bodies | Original writer | Tolerance writer | Original signs, tolerance magnitudes |
|---|---:|---:|---:|
| Matched cues | .067023 | .065632 | .065811 |
| Noise .999 | .075910 | .075275 | .075327 |
| Independent noise | .079482 | .079153 | .079207 |
| Initial-state .99 | .067063 | .065666 | .065851 |

These are **64-step linear cue-transfer scores**, not probabilities of reconstruction. For matched cues, restoring signs closes approximately 13% of the mean original-to-tolerance gap in this surrogate. Magnitude reweighting and the resulting paths of influence need attention alongside signs. No native trajectory was run with the sign-restored control, so a claim that sign restoration succeeds or fails as a native repair would be premature.

There is a second qualification: original matched-cue packets average 14.31% negative nonzero plaquettes while reconstruction remains strong. Under the two noise-mismatch conditions the original writer's corresponding fraction is zero. The pure-contrast algebra remains valid, but the original bridge can include fallback edges, and perfect local sign consistency is not necessary for its observed performance. Plaquette counts alone would be an inadequate universal predictor. A balanced network can also encode the wrong task or transmit too slowly.

## Prediction beyond current expression

The fixed development comparison leaves one whole block out at a time. Both models use the same rows and the same fixed regularization. The baseline uses current minimum output margin, current pass/fail, pairing, writer policy and generation. The augmented model adds actual-packet signed cue transfer, unsigned cue access, normalized conflict mass and body cue-difference alignment. Scaling is fitted only in training blocks. Full predictions and fit coefficients are retained.

| Forecast | Baseline Brier | With mechanistic features | Change |
|---|---:|---:|---:|
| Next rebuilding body, generations 1–31 | .031518 | **.026498** | 15.93% lower error; improves all 8 held-out blocks |
| h32 terminal assay from generation 1 | **.064385** | .064561 | .27% higher error; improves 4/8 blocks |

Next-body log loss also improves, from .13170 to .10843. Terminal log loss is essentially unchanged (.243424 versus .243398). The first result supplies native predictive traction for the measured features. The second is a retained negative result for the proposed first-generation long-horizon use.

The primary comparison includes 31,744 repeated body transitions but only eight independent blocks. It pools four pairings and two policies; these averages do not establish improvement in each condition separately. This is grouped validation within an already exposed experiment, not an untouched test across founder families or substrates. The baseline is a useful current-expression/context comparator, not the strongest possible nonlinear native predictor. Additional model selection or feature ablations would be further development and must be labelled accordingly.

## What this changes for P01

The useful lead is now **cue-specific writing under a normalized reader, including how that organization survives a damage-and-return sequence**. Counting fallback events or sign conflicts is insufficient. The absolute tolerance can change relative influence and can repeatedly replace small task contrasts with common-response correlations.

A first-generation probe misses the mechanism in this cohort: the candidate writers have not yet produced different records. The next theory question should concern short probes that actually include damage, cell return and another rewrite. The observed paired onset at generation 3 motivates that choice; it does not establish a universal three-generation minimum. Testing a revised probe against long continuations requires a new version and an explicitly exposed/development or genuinely prospective data designation.

The most informative later intervention would compare original, tolerance and sign-restored **native** continuations from an identical pre-divergence boundary, with matched damage and random streams. That would separate a causal effect on future reconstruction from the linear surrogate. It is not part of this completed diagnostic and should not duplicate the running E051 experiment.

The existing P01 v0.2 snapshot remains unchanged. Its toy no-go result and rare-loss warning stand; this native analysis supplies a more concrete candidate representation and a reason to design probes around the repair process.

## Reproduction and limits

The [protocol](PROTOCOL.md) and [configuration](config.json) were saved before feature extraction. [Extraction provenance](results/COMPLETE.json) binds selected inputs and code; [analysis](results/analysis.json) retains block summaries and model fits; [per-body features](results/features.csv) and [held-out predictions](results/held_out_predictions.csv) support recomputation. The [divergence check](results/first_divergence_checks.json) records its post-hoc status. Five independent implementation tests passed, including dense-matrix reader/propagation comparisons and strict scoring. Full extraction took 96 seconds and model analysis 6.4 seconds on one numerical thread. No new native dynamics were simulated.

Run commands from the lane, using Python with NumPy, SciPy, Matplotlib and pytest; keep numerical threads at 1 and `MPLCONFIGDIR` in the lane cache:

```bash
python -B p01_writer_diagnostic_v0_1/verify.py
python -B -m pytest -q -p no:cacheprovider p01_writer_diagnostic_v0_1/test_core.py
python -B p01_writer_diagnostic_v0_1/extract.py --output p01_writer_diagnostic_v0_1/reproduction
python -B p01_writer_diagnostic_v0_1/analyze.py p01_writer_diagnostic_v0_1/reproduction
python -B p01_writer_diagnostic_v0_1/check_divergence.py
```

Output directories and files refuse overwrite. Timestamps and elapsed times vary. The selected raw input files must remain available at the recorded source path. Numerical equality of source-derived calculations does not substitute for the pending independent E051 dynamics audit. No claim here establishes autonomous machinery, general noise invariance or a validated long-horizon reconstruction law.
