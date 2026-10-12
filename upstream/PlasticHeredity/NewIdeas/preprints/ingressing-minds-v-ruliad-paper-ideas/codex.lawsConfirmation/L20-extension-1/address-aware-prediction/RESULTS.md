# D171 — known diagnostic settings did not improve development forecasts

Completed and independently audited 2026-09-23.
[Frozen protocol](EXECUTION_PROTOCOL_V1.md), [complete tables](TABLES.md),
[qualification](QUALIFICATION.md), [work log](WORKLOG.md).

## Simple terms

Telling the observers the diagnostic reconstruction settings did not help
this prediction model. It made average squared prediction error worse in
**all 21 observer/regularization comparisons**, by 0.525%–2.134%. The result
remains unfavorable after every score-only single-founder omission.
This is an overall comparison, not a claim that every group or founder worsens.

Our focal challenge still has a tiny average edge over passive observation:
0.176% without the extra settings, 0.178% with them. It helps in eight of the
sixteen founders and hurts in eight. Removing one founder from scoring can
reverse that average. There is no new convincing challenge advantage here.

Keep the cheap comparator visible: at the focal regularization setting,
the augmented challenge very slightly beats augmented starting-only. But
when starting-only uses its own development-minimizing regularization, it
does better than that challenge. Unaugmented starting-only does better still.
Those selected-alpha comparisons are explicitly selection-affected context,
not an unbiased ranking of deployment candidates.

**Recommendation: park this additive-settings lead; do not fund a fresh
simulation cohort for this model on these results.** This does not settle
the original challenge-prediction idea, and does not prove settings contain
no useful information. D141/D162 remain unresolved; L20 remains
STRESS_TESTED / MIXED.

## What was compared

All sixteen already-studied founders 90000–90015, four lives, two target
families and ordinary/aligned writers were retained: 256 cases. Each model
was fitted on fifteen founders and evaluated on the excluded founder. Its
training label was the arithmetic mean of four saved three-replacement
terminal preferences. The original single-future label was not used in fitting.
Every individual saved future remained in scoring.

The sole feature extension was the same pair of known diagnostic compatibility
settings, q0/q1, added to all seven observers: starting-only, one undisturbed
copy, two undisturbed copies, original shuffle, attenuation, residual-plus and
residual-minus. Two-copy models retained equal corresponding raw reading
weights. The group ridge class, penalty convention and three fixed alphas
(.001/.01/.1) were unchanged. The new inputs add free coefficients: this is
an information/capacity extension, not a change in tissue physics.

Exactly 336 new models and 5,376 out-of-fold forecasts were produced. The
seven old reference model panels and forecasts were reused in place. No new
tissue, founders, diagnostics, lineages or futures; no pilot application,
full-cohort deployment fit, deletion refit or new challenge selection.
The independent saved audit did not call the production fitter.

## Extra settings: all fixed conditions and regularization values

Entries below are the percentage **increase** in individual-future MSE
relative to that same observer without settings. Positive here means worse.
The full paired-gain tables use the opposite, explicitly labeled convention:
positive reference-minus-candidate MSE means improvement.

| Observer | Alpha .001 | Alpha .01 | Alpha .1 |
| --- | ---: | ---: | ---: |
| Starting-only | +0.791% | +0.985% | +0.763% |
| One-copy | +1.714% | +1.407% | +0.929% |
| Passive two-copy | +1.843% | +1.508% | +0.553% |
| Shuffle | +2.134% | +1.577% | +0.621% |
| Attenuation | +1.616% | +1.417% | +0.655% |
| Residual-plus | +2.012% | +1.587% | +0.637% |
| Residual-minus | +1.829% | +1.506% | +0.525% |

All 21 whole-cohort means and all 336 score-only omissions favor the old
interface. These overlapping scores are not independent replications or a
confidence interval. No threshold or formal success test was introduced.

The error increase is concentrated in B-ordinary at the focal alpha: that
group contributes 93.97% of passive's overall MSE increase and 93.70% of
residual-minus's. Some other group changes have the opposite sign. Aligned
effective q is constant; its forecasts can still change when shared model
weights are refitted. Such changes are not evidence of an unused-shift leak.

## Focal residual-minus versus matched passive at .01

| Interface | Passive MSE | Challenge MSE | Passive RMSE points | Challenge RMSE points | Challenge MSE reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| No settings | 0.006504357 | 0.006492888 | 8.06496 | 8.05785 | +0.1763% |
| Same settings in both | 0.006602473 | 0.006590692 | 8.12556 | 8.11831 | +0.1784% |

These percentages use each row's passive MSE as denominator. The raw
challenge/passive gap changes only from 1.146923e−5 to 1.178148e−5 MSE:
an increase of 3.122470e−7, not a rescued prediction effect.

With settings, the gain is positive in 8/16 founders and negative in 8/16.
Score-only single-founder omission gains range from −1.091998e−5 to
+3.162919e−5 MSE; excluding 90012 reverses the sign. These are sensitivity
checks of fixed forecasts, not refits or uncertainty intervals.

The four group gains (A-ordinary, A-aligned, B-ordinary, B-aligned) are
+2.694483e−6, +3.011992e−7, −5.774691e−7, +4.470769e−5 MSE respectively.
The small overall edge is mainly B-aligned, not B-ordinary. All shuffle,
attenuation and plus results at every alpha remain in the complete tables;
none replaces the frozen focal pair.

## Cheap baselines matter

At the same alpha .01, augmented residual-minus has 0.0387% lower MSE than
augmented starting-only and 0.2341% lower MSE than augmented one-copy.
It has 0.9456% higher MSE than old starting-only and 1.1692% higher MSE than
old one-copy at that same alpha. Thus even the same-alpha comparisons do
not justify treating the new model as the better available predictor.

Allowing each cheap baseline its own predeclared development-minimizing
alpha gives the following **selection-affected context**, not deployment
selection. The diagnostic candidate remains residual-minus at .01; no new
diagnostic alpha was chosen after results.

| Cheap baseline | Its selected alpha | Baseline MSE | Augmented challenge's error relative to baseline |
| --- | ---: | ---: | ---: |
| Old starting-only | .001 | 0.006512956 | 1.1936% higher |
| Settings starting-only | .001 | 0.006564496 | 0.3991% higher |
| Old one-copy | .01 | 0.006514522 | 1.1692% higher |
| Settings one-copy | .01 | 0.006606157 | 0.2341% lower |

For the augmented focal pair, individual-future MSE equals mean-target MSE
plus the same saved within-case dispersion, 0.0041408911. Mean-target errors
are 0.0024615823 passive and 0.0024498008 challenge. Paired gains are identical
under both scoring conventions; a smaller absolute averaged-target error
is not additional predictive information. No old or new forecast clipped.

## Verification, cost and limits

The unchanged frozen implementation passed its 90 synthetic qualification
tests before real fitting. All 367 input hashes rechecked. Every saved old
reference optimum and every new model passed preprocessing, stationarity,
raw-tie, nesting and forecast checks; new fits also matched independent
group-coordinate SVD solutions. Largest SVD forecast residual: 2.08e−14;
raw-reading tie residual: 1.11e−16; projected stationarity residual: 2.84e−16.

The augmented un-clipped training objective decreased for every fit, as
required by nesting, while aggregate excluded-founder error worsened for
every model/alpha panel. This is compatible with unhelpful extra flexibility
on a small development set. It does not by itself establish the cause, or
prove that all possible uses of the settings would be uninformative.

This does not contradict D169's controlled address-swap result. D169 changed
where feedback acted and measured reconstruction; D171 left that physics
unchanged and supplied a forecaster with two summaries of the diagnostic
settings. A physical cause can matter without this particular representation
and fitting rule improving forecasts of later three-boundary retention.

Main fitting/reporting/saved check: **3.49 seconds, 3,598,288 bytes
(3.432 MiB)**. Separate fresh saved audit: **2.92 seconds**. All retained D171
qualification attempts, synthetic benchmark, real run, logs, manifests and
receipts totaled **14,478,426 bytes (13.808 MiB)** before the result-document
receipt. This stays well below the 48.427 MiB reservation and 128 MiB cap.
All numerical artifacts are external; only code/docs were added here.
One worker, one numerical thread, affinity CPUs 0–5. No long job, automatic
polling, retry, cleanup or successor.

These founders were repeatedly studied before this design. No confidence
interval, population equivalence, general impossibility claim or prospective
confirmation follows. This additive model also does not test whether a
setting-dependent interpretation of a reading (an interaction) would work;
that is a different hypothesis requiring a separate design, not an automatic
post-result modification. No such model or new experiment was launched.

## Reproducible artifacts

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
Run namespace: `l20_extension1_settings_prediction_dev_v1_attempt1`.

- `runs/<namespace>/COMPLETE.json`, SHA-256
  `41a9fa1d8d63bdcdfab971b5470ab614bf4d2b13cd3a73555a8f239130db51d4`.
- `outputs/<namespace>/summary.json`, `case_losses.npz`, `settings.npz`,
  `fits.json`, `predictions.npz`, `raw_predictions.npz`, `verification.json`
  and `output_hashes.json` retain all cases and conditions at full precision.
- `logs/<namespace>_saved_audit_v1.json`, SHA-256
  `eb5b76b5d456fe8054a16e3de4270152158bef8f7437cae58a9f8123cae5fab2`.
- [Table checker](check_results.py) verifies the immutable run/audit and
  every rendered table against the audited files without new fits.

The prior design and qualification notes remain historical records.
No frozen protocol, challenge, alpha grid, carrier or guide was changed.
