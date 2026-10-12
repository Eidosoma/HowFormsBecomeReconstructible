# E051 — cue-pairing robustness

**Complete and independently verified: PAIRING_ROBUSTNESS_ESTABLISHED.**
Finished **9 October 2026 at 06:18 UTC**, including independent replay and
figures. Closeout passed at **10:29 UTC** on the user's requested status check.

All five prespecified primary requirements passed on 32 fresh independent
blocks, 512 lineages per condition and 32 rebuilding generations. For the
original exact-zero writer, both mild perturbations remain within the declared
five-percentage-point loss allowance, with the paired and both challenged
absolute lower 95% bounds above 75%.

| Original exact-zero writer | h32 scattered-terminal both-cue success | 95% block-bootstrap interval |
| --- | ---: | ---: |
| Matched noise and reset | 458/512 (89.45%) | 86.13–92.38% |
| Noise correlation .999 | 497/512 (97.07%) | 95.12–98.63% |
| Noise correlation .99 | 494/512 (96.48%) | 94.73–98.05% |
| Noise correlation .9 | 492/512 (96.09%) | 94.53–97.66% |
| Independent noise | 495/512 (96.68%) | 95.12–98.05% |
| Reset correlation .99 | 457/512 (89.26%) | 86.13–92.19% |
| Independent reset | 456/512 (89.06%) | 85.94–91.99% |

The two primary challenged-minus-paired differences are **+7.62 points
[5.08,10.35]** for noise correlation .999 and **−0.20 points [−0.98,0.59]**
for reset correlation .99. Other perturbations and policy comparisons are
secondary, pointwise estimates. Independent noise gives **+7.23 points
[4.10,10.55]** for the original writer.

The fixed tolerance `1e-4` is unfavorable: **13/512 (2.54%)** under matched
cues versus 458/512 (89.45%) for exact writing, a **−86.91-point difference
[−90.23,−83.59]**. With noise correlation .999 it achieves **320/512 (62.50%)**
versus 497/512 (97.07%), a **−34.57-point difference [−39.26,−29.49]**.
With independent noise it reaches **485/512 (94.73%)**. This concerns the
prespecified threshold; no alternative threshold was selected after outcomes.

The reviewer's predicted branch change is confirmed. Across boundaries 2–32,
the exact writer uses ordinary fallback on **100%** of available returning
edges with matched cues and **0%** in every noise-mismatch arm. Nevertheless,
all available returning edges become nonzero in the noise-mismatch arms and
terminal performance remains high. Pure contrast has **0/512** terminal
successes with matched cues and the same h32 success rates as exact writing
in each noise-mismatch arm. Initial-state mismatch alone leaves returning-edge
fallback selection at 100% under the declared reader and settling schedule.

A further secondary finding limits generalization of the policy ranking:
under matched cues, preservation gives **368/512 (71.88%)**, below full
rewriting's 89.45%. With independent noise, preservation gives **511/512
(99.80%)**, above full rewriting's 96.68%, a preservation-minus-rewrite
difference of **+3.13 points [1.56,4.69]**. The paired-cue advantage of full
rewriting therefore does not extend uniformly across the tested noise regimes.

For the preprint, the supported distinction is that cue pairing changes how
connections are written, but is not required for high endpoint performance
under the tested rebuilding perturbations. The mechanism of the performance
gain is not isolated by these comparisons. Teaching and terminal-assay cues
remain paired and combined noise/reset perturbations are untested.
[E052](../E052_precision_normalization/README.md) subsequently tested numerical
precision, record corruption and normalization floors: its paired-cue primary
criterion was not met, while independent rebuilding cue noise showed much
smaller losses in the secondary comparisons. Combined numerical stresses remain
open; this later result does not change E051's declared scope or outcome.

The complete results supersede the descriptive
[eight-block early look](analysis/early_look_v1/REPORT.md), which is preserved
as a dated record. [Full report](runs/robustness_v1/REPORT.md),
[independent audit](runs/robustness_v1/INDEPENDENT_AUDIT.json),
[figure](figures/robustness_v1/cue_pairing.png),
[closeout verification](analysis/closeout_v1.json).

Tests the reviewer's concern that E041's exact-zero ordinary-coactivity fallback
is supported by identical randomness across rebuilding cues. The study separates
cue-noise correlation from initial-state matching and tests one fixed finite
fallback tolerance. Teaching, holding and terminal assays remain unchanged.

32 fresh independent blocks **34000–34031**, four founders and four recipients
per block: **512 lineages per condition**, followed through **32 damaged
rebuilds**. The same lineages receive 35 counterfactual histories; these are not
17,920 independent samples. Inference resamples the 32 blocks.

| Pairing condition | Initial-state correlation | Update-noise correlation |
| --- | ---: | ---: |
| Paired reference | 1 | 1 |
| Nearly paired noise | 1 | .999 |
| Noise .99 | 1 | .99 |
| Noise .9 | 1 | .9 |
| Independent noise | 1 | 0 |
| Reset .99 | .99 | 1 |
| Independent resets | 0 | 1 |

Each pairing condition has five policies: original exact-zero rewriting,
tolerance-based rewriting (`abs(cue product) <= 1e-4`), ordinary-coactivity
rewriting, pure-contrast rewriting and exact-zero bridge preservation. Both
Gaussian marginals remain unchanged. Common random draws match policies while
cue-pair correlations change. Every history passes its own record forward.
The tolerance is fixed before outcomes and is not selected from a sweep.

The primary endpoint is E041's h32 normalized scattered-terminal both-cue
success. The primary question is whether the original writer remains within
five percentage points of paired performance under **noise rho=.999** and
**reset rho=.99**, with the paired and both perturbed absolute lower 95% bounds
above 75%. All five requirements must pass. Failure to establish noninferiority
alone is inconclusive; a loss exceeding five points is separately identified
when the contrast's upper 95% bound is below minus five. Stronger perturbations,
the modified writer and other policy comparisons are secondary, pointwise.

Retained mechanism measures distinguish exact-zero products, ordinary selection,
nonzero/strong edge repair, connection magnitudes and access to the cue input.
The ordinary-selection counts describe the capture rule; preservation can
retain a strong edge instead. Returning edges have erased inherited weights.
End activities, outgoing packets, masks, per-lineage counts/sums, all body scores
and terminal scores are retained, with commitments for omitted intermediates.
This focused study does not repeat E041's full 17-part durability/control battery.
No result establishes robustness of teaching/assays under independent cue noise,
combined noise/reset mismatch, or indefinite heredity.

Twenty scientific inputs froze at **2026-10-08T14:09:09.916426+00:00**. All 12
synthetic/excluded checks passed on the first frozen attempt. The complete
fixture and benchmark passed independent replay of teaching, all 32 rebuilding
and holding sequences, capture, connectivity/counts, assays and 1,966 inference
summaries. In both runs, paired exact rewriting, ordinary rewriting and bridge
preservation reproduced E041's original 32 histories and selected own-record
assays byte exactly. Each technical run retained 64 original outputs. Their
figures were inspected; scientific decisions remain null.

The benchmark workflow took **228.22 seconds**, with simulation/audit workers
108.91/114.45 seconds. The frozen conservative forecast is **171,654.50seconds
(47h 41m 35s)**, including independent audit and figures. Storage reserve is
**8,037,819,584 bytes**, versus **64,462,409,728 bytes** free at preflight.

Launched 8 October at **14:17 UTC**, PID **1960934**, eight workers on CPUs 0–7,
one numerical thread each, stdin `/dev/null`. The bounded startup check passed
at **14:17:40.842541 UTC**. Actual complete workflow time was **57,652.84 seconds
(16 hours 1 minute)**, ahead of the frozen conservative forecast.

The scientific independent audit passed replay of **1,146,880 rebuilding-body
cue observations**, **448,512 terminal cue observations**, every teaching,
rebuilding, holding, capture and connectivity calculation, and **1,966 inference
summaries**. Closeout verified all **1,335 original scientific outputs**, all
64 outputs in each excluded technical run, the 20 frozen inputs, job receipts
and figure provenance. The scientific figure was inspected. Scientific retained
data total **4,498,906,526 bytes**; free space at closeout was
**59,148,808,192 bytes**. No successor was started.

[Protocol](PROTOCOL.md), [source provenance](SOURCE_DATA.json),
[technical validation](analysis/technical_v1.json),
[benchmark forecast](analysis/forecast_v1.json),
[startup verification](analysis/scientific_launch_verification_v1.json),
[model](model.py), [independent auditor](audit.py),
[reviewer assessment](../E041_full_rewrite_confirmation/analysis/reviewer_noise_pairing_v1/REVIEWER_RESPONSE.md).
