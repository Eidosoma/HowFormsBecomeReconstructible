# Results and live status

Status: **prospective held-out test COMPLETE and independently audited**,
inspected on the user's status request, 2026-09-17. No automatic post-launch
polling. Frozen science, predictors, shuffle and cohort remained unchanged.

## Held-out primary result: no demonstrated challenge advantage

Registered label: **PREDICTIVE_DIFFERENCE_UNRESOLVED**.
The fixed challenge did not show better prediction than the equally costly
passive observer. Its MSE was **0.4361% worse** at the point estimate.

Passive-minus-challenge MSE = **-0.00002767874754**; registered 95% whole-founder-
block bootstrap interval **[-0.00035517437249, +0.00029508535404]**. Positive
values favor challenge. The interval spans benefit and harm; this is not
evidence of equivalence. Nine blocks favor challenge, seven favor passive,
but the mean difference favors passive because the magnitudes differ.
Uncertainty uses 16 independent founder blocks, not 256 independent cases:
10,000 bootstrap draws, seed 14120260917.

| Predictor | Held-out mean squared error | Mean absolute error, preference points | Root mean squared error, preference points |
| --- | ---: | ---: | ---: |
| Starting measurements only | 0.006461683 | 5.4252 | 8.0385 |
| Passive: two intact cycles | 0.006347166 | 5.1654 | 7.9669 |
| Challenge: intact + 25%-site shuffle | 0.006374845 | 5.1487 | 7.9843 |

MSE uses squared raw preference units; absolute and root-mean-square errors
are multiplied by 100. Unlike development, **starting-only is not the best
held-out predictor**: passive and challenge have 1.7722% and 1.3439% lower MSE
than starting-only. Those are descriptive point estimates, not separately
established improvements. Challenge's slightly lower secondary absolute error
does not replace the unresolved primary MSE comparison. Selected alpha remains
0.001 for starting-only and 1 for both diagnostic predictors; no held-out refits.

Calibration is descriptive regression of observed outcome on saved forecast.
Starting-only intercept/slope: -0.004078 / 1.011505; passive: -0.013309 /
1.055316; challenge: -0.005160 / 1.031097. All four family-by-writer groups
have slightly higher challenge than passive MSE; no subgroup success claim.

## Apparatus controls and law-level interpretation

All readout, content, read-off, write-off, wrong-record, lesion and rescue
gates pass. Protected-copy and other controls are retained but excluded from
the primary forecast contest. The control label
**ALIGNED_SERIAL_RENEWAL_ADVANTAGE** is a separate, secondary result—not the
prospective prediction verdict.

| Secondary terminal contrast | Pooled preference-point difference [95% block interval] | Family A | Family B |
| --- | ---: | ---: | ---: |
| Aligned minus ordinary/translated writer | +3.6774 [+1.5381, +6.1921] | +0.4150 [-0.3052, +1.1047] | +6.9397 [+2.6978, +12.0671] |
| Aligned minus protected copying | -1.6357 [-2.6184, -0.6958] | +1.1047 [+0.7080, +1.4771] | -4.3762 [-6.2622, -2.4780] |

Alignment still helps retained content on average, especially B; its overall
deficit relative to protected copying remains. Neither secondary finding
establishes challenge-based prediction or complete shape preservation.
L20 remains **STRESS_TESTED / MIXED**. This fixed external diagnostic has not
earned a prospective advantage under the tested conditions; the study does
not establish autonomous interface repair or universal claims about challenges.
Do not search for a favorable replacement perturbation on these test outcomes.

## Held-out execution, sealing and independent audit

Completed **2026-09-17 at 13:36:43.029165 UTC**, runtime **869.159896 seconds**
(14.49 minutes), output size **337154257 bytes / 321.54 MiB**, external only.
At most six workers/CPUs, one numerical thread per process. All 16 founder
blocks 90000–90015, all four lives, both families and both writers retained:
256 forecast cases, zero exclusions, zero refits, no retry or successor.

All 256 forecasts were sealed at **13:25:59.372445 UTC**, before the actual
outcome-stage receipt at **13:26:00.757608 UTC**. Diagnostic bodies and records
did not enter the main lineages; diagnostic and lineage noise streams remained
separate. The frozen model and all prepared input hashes remain unchanged.

The job independently replayed every production life. A fresh-process saved
audit on this status request **passes**: 1144 input hashes, 102 indexed output
files, 256 cases / 16 blocks, 768 diagnostic cycles, 3072 main generation
read/write paths and 1536 terminal reader paths. It also reconstructs saved
features, forecasts, controls and scoring, checks the forecast-before-outcome
barrier and COMPLETE seal, and generates **zero new dynamics**.

Additional retained accounting: 128 founder acquisitions, 128 founder
pre-readers, 256 F0 writers; 1536 diagnostic readers and 1536 diagnostic
selectors; 2304 enabled main rewrites, 4352 main selector decisions and 1728
main aliases. Counts exclude independent replay unless stated otherwise.

No new experiment was launched by that status request. The user subsequently
approved the saved-state review below and the separate D142 repeated-futures
study, now complete. Neither rescues or replaces this registered comparison.

## Post-result saved-state review — exploratory

[Full review and next proposal](reviews/HELDOUT_LATE_LOSS_2026-09-17.md).
All 256 primary cases retained, no new dynamics or refitted models. Ordinary-B
negative preferences rise 0/3/6/10 across G1–G4; nine of the ten terminal-
negative cases still favored B in U0, U1 and C1. Some negative outcomes are
marginal, others substantial; the continuous primary measure is unchanged.
Ordinary B accounts for 81.43% of passive squared error.

Aligned B's guide labels stay B, while mean best record correlation declines
0.82353→0.76929→0.73123→0.69968. The reading/reference transfer loses shape
in all 192 aligned-B comparisons; writing partly recovers it on average.
This separates recognition from fidelity and locates degradation, but cannot
causally allocate loss or distinguish stable fragility from a noisy future.

12 synthetic tests and an independent saved reconstruction pass: 1024 actual
and 768 diagnostic preferences, 3328 FFT shape checks, all source hashes.
New numerical artifacts ~2.90MiB, external only, analysis runtime 6.82s.
The user subsequently approved D142's four fresh independent futures per case
under a [separate protocol](repeated-futures/PROTOCOL_V1.md). That study is now
complete and independently audited: all 1024 outcomes, 16 blocks, no refits or
exclusions, no new founders. [Full D142 results](repeated-futures/RESULTS.md).
Ordinary-B repeatability is 48.1% [32.1%,61.6%]; aligned B 92.3% [88.3%,95.1%],
pointwise founder-block intervals. Alignment greatly reduces future noise,
but mean aligned-B shape still falls 0.824→0.701 and 4/256 terminal preferences
are negative. These are record–host differences, not record-only causation.
On these fixed secondary fresh-future scores, starting-only has the lowest
aggregate MSE; challenge is slightly worse than passive in each group.
This does not alter D141's original prospective result or L20's mixed verdict.
Completed 15:34:45 UTC in 585.81s / 9.76min, 222.81MiB external, max six CPUs.
Requested saved audit passes 1265 inputs / 36 outputs / 1024 futures with zero
new dynamics. No automatic polling, retry or successor run. The user then
approved the [saved-stage review](reviews/REPEATED_STAGE_DIVERGENCE_2026-09-17.md),
now complete: most ordinary-B shape-score spread appears across rewriting;
alignment avoids extra spread but does not reduce its own input spread on
average. Reading builds an imperfect reference and aligned writing restores
only part of B's missing shape. All 1024 futures retained; 37 tests and
independent saved checks pass, 1.09MiB external, zero new dynamics. Redrawn
feedback addresses and other noise are not yet separated; a crossed test is
the next proposal only. These are exploratory descriptions, not a new result
for the unchanged original challenge-prediction comparison.

## Historical development qualification and execution

76 qualification tests passed. Development specification frozen with 1081
input hashes; prepared manifest has 1085 including qualification artifacts.
Disposable benchmark independently replayed 48 cycles / 96 fresh readers /
96 selectors; exact dynamics, maximum feature/selector discrepancy 9.99e-16.
Saved-output benchmark audit passed without new dynamics.

Completed 2026-09-17 at 12:34:37.200949 UTC in 179.729841 seconds (~3 minutes),
using at most six CPUs. Output size 67934444 bytes (64.79 MiB), external only.
The conservative budget was 665.48 seconds / 113.17 MiB. No failure, retry,
exclusion or successor. No held-out founders or outcomes were generated during
development.

Saved-output audit passes: 1085 input hashes, 36 output hashes, all 16 blocks /
64 lives / 256 cases, 768 diagnostic cycles, 1536 fresh readers and 1536
routing decisions. Every production life received an independent dynamic
replay; saved audit checks provenance, retained states, features, model fitting
and summary without new dynamics. Maximum recorded discrepancy 1.22e-15.

## Development results only

Leave-one-founder-block-out cross-validation, with the registered regularization
selection. The same CV results also selected alpha, so these estimates are
selection-affected; they are not an independent test of the hypothesis.

| Predictor | CV mean squared error | CV mean absolute error, preference points | Selected alpha |
| --- | ---: | ---: | ---: |
| Starting measurements only | 0.008031014 | 5.8293 | 0.001 |
| Passive: two intact cycles | 0.008323774 | 5.7237 | 1 |
| Challenge: intact + 25%-site shuffle | 0.008266656 | 5.7617 | 1 |

MSE uses squared raw preference units; absolute errors are multiplied by 100.
Challenge's passive-minus-challenge MSE difference is +0.00005711855,
a **0.6862% relative reduction**. Nine blocks favor challenge, seven favor
passive. This is a small development edge, not a supported prospective gain.
Challenge is slightly worse than passive on secondary mean absolute error.

Starting-only has the lowest MSE: passive is 3.65% worse and challenge is
2.93% worse than this baseline. Thus the diagnostic cycles have not shown
added value over starting measurements on the main squared-error metric
in development. Do not substitute the secondary absolute-error result for
that observation, and do not treat any difference here as a held-out verdict.

The fixed perturbation and fitting rules remain unchanged. L20 remains
STRESS_TESTED / MIXED; this stage does not establish challenge-based prediction.

## Historical held-out qualification, benchmark and launch

This window reviewed the executor and verified all1135 frozen inputs;44 tests
passed in196.170s. The [handoff review](reviews/HELDOUT_HANDOFF_REVIEW_2026-09-17.md)
records the forecast-before-outcome safeguards. No scientific design changes.

The disposable benchmark completed at13:18:24.555076 UTC:158.6081s for the
complete four-life block,48 diagnostic cycles,192 generation paths and96
terminal readers, with full independent replay. Its fresh-process saved audit
passed all7 benchmark artifact hashes, founders, diagnostics, forecasts,
lineages and score reconstruction without new dynamics. Maximum replay/check
discrepancy1.11e-15. This disposable fixture is not scientific evidence.

Prepared the single-use main run with1144 input hashes. Conservative full-run
forecast2723.9664s (~45.4min), projected509478027 bytes (485.88MiB); max6CPUs,
numeric threads1, external-only storage. Parallel execution may finish sooner;
the budget deliberately assumes no parallel speedup.

Detached launch acknowledged at2026-09-17T13:22:13.870072+00:00, PID3434853.
No post-ACK progress, log, status or output inspection occurred until the user
returned for status. The complete run and subsequent independent audit are
reported above. No automatic retry, replacement block, exclusions, refitting
or successor. Late-B follow-up remains separate and has not been launched.

## Sealed held-out sources

Held-out run: `runs/l20_extension1_heldout_v1_attempt1/`.
Held-out outputs: `outputs/l20_extension1_heldout_v1_attempt1/`.
Log: `logs/l20_extension1_heldout_v1_attempt1_execute.log`.
All under the same external extension root below.

Held-out freeze SHA256: `fc3cbc853f7da921c59ac24cb2c11e475a8a42ec5b400ff1ba4f6dae778400c1`.
Benchmark timing SHA256: `ebd340a54af3effcd38fe845694d97dbdbc02ba92f0b651e873752d0677a1a6e`.
Prepared manifest SHA256: `3148592d9b7a64022c24bd63dd602bf7b4003b50214350bdd10a86544a1551b1`.
Forecast seal SHA256: `b7efd9047db42543a3558042e896d7c157c00f3a67e3fde8809151e897bbc510`.
Held-out COMPLETE SHA256: `818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918`.
Held-out summary SHA256: `f22377763f33e5f0d6ee06b13a15671f28dc80e453edcccd5f1f96a3d4580d4a`.

## Sealed development sources

Development COMPLETE SHA256: `e4eb6955a54c27392d31f0c7fef804c6b16e488556ca0db9c4f3767c2357c295`.
Model SHA256: `742719994cea7cdec793f13afb06ecdd43ea793011d9bce2420056cbbfb1e0c5`.
Summary SHA256: `5ed6bdedd2bd4b2ada5b4d6a7634970ed6e6dfb5e833d693b23eb26f7563f842`.

Development run: `runs/l20_extension1_development_v1_attempt1/`.
Outputs: `outputs/l20_extension1_development_v1_attempt1/`.
Log: `logs/l20_extension1_development_v1_attempt1_development.log`.
All relative to `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.

Development diagnostics and cross-validation are labelled **development**.
The prospective result above uses all 256 saved forecasts, a verified pre-outcome
seal and the independent 16-block held-out score. L20's overall verdict is unchanged.
