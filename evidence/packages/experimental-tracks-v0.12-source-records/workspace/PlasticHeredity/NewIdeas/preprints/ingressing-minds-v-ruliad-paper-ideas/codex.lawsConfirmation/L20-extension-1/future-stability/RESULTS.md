# D156 — original / repeated-future stability review

Completed and freshly audited **2026-09-20**.
[Fixed protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[D155 mean-compression result](../mean-compression/RESULTS.md).

## Plain-language result

The ranking reversal has a clear location and an exact arithmetic account,
but not a proven causal explanation for what the models learned.

**Ordinary B is the difficult, variable condition.** Its original terminal
outcome differs from the mean of its four saved repeat futures by 16.31
preference points RMS, versus 2.15–3.99 points in the other three groups.
Ordinary B supplies 86.84% of the observed within-case future variance.

For mean-passive versus separate-passive, ordinary B supplies almost all
of the negative change in prediction advantage between original and repeat
outcomes. Founder 90001 alone contributes 55.94–86.82% of the net change,
depending on setting. Other founders still contribute, sometimes with opposite
signs. Every founder remains; this is not evidence that 90001 is invalid.

The previously interesting control-minus nudge is also sensitive to future
realization. At .01 and .1 its average repeat-future advantage over mean-passive
is +0.112% and +0.200%. **Omitting future 2 reverses both signs.** At .001
its average is already unfavorable. This is a fragile development lead,
not a dependable challenge benefit, equivalence or a reason to drop a repeat.

There is a more useful next question: would learning from several outcomes
per case, rather than one realized outcome, give more stable forecasts?
This review does not train that model or establish that it would help.

## What was retained and independently checked

All **42 existing forecast series**: 12 observers at each fixed setting
.001/.01/.1, plus six earlier nested reference observers. The fixed panel
contains starting-only, one undisturbed copy, five separate-copy observers
and five mean-copy observers. Both residual controls stay.

All 32 original founders / 512 cases remain. The comparison across outcomes
uses the same 16 former-test founders, four lives, four groups: **256 cases
with one original and four saved D142 futures each**. Those 1,024 repeated
outcomes are not 1,024 independent founders. No source or case was filtered.

All **201 existing contrasts** keep their original orientation, including
fixed-versus-nested comparisons and mean control loss. Every original source
score was bridged back to D153–D155. Forecasts are reused bit for bit.
No feature extraction, refitting, model selection, new forecast, simulation,
diagnostic, new lineage, founder or outcome was generated.

Former held-out data are DEVELOPMENT. D141's unresolved prospective result,
the original diagnostics, controls and L20 STRESS_TESTED / MIXED are unchanged.
The audit pins the previous apparatus checks; it does not rerun their dynamics.

## Same founders, different realized outcomes

Positive = candidate reduces MSE relative to the named reference. These
original-outcome columns use only the same 16 founders with repeated futures,
not D155's full 32-founder aggregate.

“Positive repeats” counts favorable scores when each of the four future IDs
is scored separately. “Positive repeat omissions” averages the remaining
three individual-future losses. “Positive founder omissions” averages all four
futures after omitting one founder's scores. These are descriptive sensitivity
counts, not confidence levels, refits or data exclusions.

| Setting | Candidate / reference | Same-founder original | Four-future average | Positive repeats | Positive repeat omissions | Positive founder omissions |
|---|---|---:|---:|---:|---:|---:|
| 0.001 | Mean passive / Separate passive | +3.761% | −0.970% | 2/4 | 1/4 | 2/16 |
| 0.001 | Mean passive / One copy | +5.472% | −3.089% | 1/4 | 0/4 | 0/16 |
| 0.001 | Mean passive / Starting only | +1.938% | −0.959% | 2/4 | 1/4 | 1/16 |
| 0.001 | Mean control − / Mean passive | −0.304% | −0.587% | 1/4 | 0/4 | 1/16 |
| 0.01 | Mean passive / Separate passive | +6.114% | −0.251% | 1/4 | 3/4 | 4/16 |
| 0.01 | Mean passive / One copy | +6.429% | −1.279% | 2/4 | 0/4 | 0/16 |
| 0.01 | Mean passive / Starting only | +5.424% | +0.845% | 3/4 | 3/4 | 15/16 |
| 0.01 | Mean control − / Mean passive | +0.256% | +0.112% | 1/4 | 3/4 | 14/16 |
| 0.1 | Mean passive / Separate passive | +5.874% | −0.168% | 1/4 | 2/4 | 3/16 |
| 0.1 | Mean passive / One copy | +4.415% | +0.279% | 2/4 | 2/4 | 12/16 |
| 0.1 | Mean passive / Starting only | +9.418% | +4.035% | 3/4 | 4/4 | 16/16 |
| 0.1 | Mean control − / Mean passive | +0.201% | +0.200% | 2/4 | 3/4 | 14/16 |

Each comparison with separate-passive changes sign across individual repeats.
Mean-passive versus one-copy is unfavorable under every repeat omission and
every founder omission at .001/.01. Its .1 advantage is less stable. Against
starting-only, mean-passive at .1 retains a favorable four-future average
under every repeat and founder omission, but one individual future still
favors starting-only. No setting is selected as a new winner.

The complete four-repeat panel for those same fixed focal comparisons:

| Setting | Candidate / reference | Future 0 | Future 1 | Future 2 | Future 3 |
|---|---|---:|---:|---:|---:|
| 0.001 | Mean passive / Separate passive | −2.424% | +2.172% | −5.065% | +1.502% |
| 0.001 | Mean passive / One copy | −8.555% | −1.674% | +0.186% | −3.298% |
| 0.001 | Mean passive / Starting only | −7.455% | −0.941% | +1.773% | +1.414% |
| 0.001 | Mean control − / Mean passive | −1.158% | −0.711% | +0.386% | −0.989% |
| 0.01 | Mean passive / Separate passive | −1.583% | +3.047% | −1.032% | −1.234% |
| 0.01 | Mean passive / One copy | −5.228% | +0.890% | +1.734% | −2.993% |
| 0.01 | Mean passive / Starting only | −4.774% | +3.146% | +3.495% | +0.729% |
| 0.01 | Mean control − / Mean passive | −0.422% | −0.166% | +0.974% | −0.052% |
| 0.1 | Mean passive / Separate passive | −1.028% | +2.005% | −0.178% | −1.317% |
| 0.1 | Mean passive / One copy | −2.960% | +2.407% | +2.162% | −0.701% |
| 0.1 | Mean passive / Starting only | −1.829% | +7.805% | +6.674% | +2.866% |
| 0.1 | Mean control − / Mean passive | −0.105% | −0.201% | +0.877% | +0.158% |

For control − versus mean-passive, future 2 is the only favorable individual
repeat at .001 and .01, and one of two favorable repeats at .1. At .01/.1
removing it gives absolute MSE gains −0.000012983 and −0.000002456.
All repeats remain in the full averages above. Observing this sensitivity is
not permission to choose a favorable stream or change the challenge.

## Exact accounting of the reversal

For fixed candidate prediction c, reference prediction r, original outcome y0,
and four-future mean mu:

    gain(y) = (r-y)^2 - (c-y)^2
    gain(mu) - gain(y0) = 2*(c-r)*(mu-y0)

The identity holds case by case and after aggregation. The saved panel retains
each case's forecast difference, realized-target change and product, together
with every founder/group contribution. For a mean control loss, c or r in
the product is the first moment of the two control forecasts; the scored loss
is still the mean of their separate squared errors, never ensemble loss.

This identifies where the observed change comes from. It does not identify
why a predictor learned its coefficients, causally isolate overfitting,
establish a distribution shift, or estimate population prediction bias.

For mean-passive versus separate-passive:

| Setting | Total gain change | Ordinary-B contribution | Founder 90001 contribution | 90001 share of net change |
|---|---:|---:|---:|---:|
| 0.001 | -0.000315342 | -0.000353970 | -0.000273778 | 86.82% |
| 0.01 | -0.000401928 | -0.000415550 | -0.000282578 | 70.31% |
| 0.1 | -0.000392128 | -0.000386974 | -0.000219371 | 55.94% |

These are MSE differences in squared fractional preference units. Group and
founder contributions are already weighted contributions to the 16-block
aggregate, not unweighted group-specific errors. Contributions from different
partitions overlap; do not add the ordinary-B and founder-90001 columns.

Ordinary B accounts for 112.25%, 103.39%, 98.69% of the net change. Values
above 100% reflect offsetting gains in other groups, not an impossible fraction.
90001 is the largest negative founder contributor at every setting. Removing
its scores leaves the gain-change term negative at all three settings:
−0.000044335, −0.000127307, −0.000184275. This does not claim the full original/
future ranking still reverses under that omission; it describes the change
term alone. No founder was removed from any reported aggregate.

## Outcome variation and forecast error are different quantities

All target means below use preference points. RMS change is the case-level
original outcome minus its four-future mean, not uncertainty on a group mean.

| Group | Original mean (points) | Four-future mean (points) | RMS original-to-mean change (points) | Within-future variance |
|---|---:|---:|---:|---:|
| A ordinary | 43.3411 | 43.3716 | 3.4047 | 0.000563025 |
| A aligned | 43.7561 | 43.6462 | 2.1531 | 0.000264555 |
| B ordinary | 20.7703 | 19.6503 | 16.3065 | 0.014384598 |
| B aligned | 27.7100 | 27.0386 | 3.9893 | 0.001351386 |

The pooled within-case future variance is **0.004140891**. For any fixed
forecast p, this exact finite-sample identity holds:

    mean_r (p-y_r)^2 = (p-mu)^2 + mean_r (y_r-mu)^2

The variance uses divisor four, specifically for this identity. It is **not**
the true population variance, a proven irreducible prediction limit or a
claim that the current model cannot improve. The four-future mean itself
remains a noisy estimate of an expected future outcome.

For mean-passive, within-case dispersion accounts algebraically for
59.15%, 63.83%, 62.24% of observed repeat-future MSE at .001/.01/.1.
Its signed error against the four-future mean is +0.6744, +0.4703, +0.1941
preference points. Squared pooled mean error is only 1.59%, 0.94%, 0.15%
of its mean-target MSE; most of that error is variation across cases.
Pooled bias can conceal group differences, which are all retained.

Crucially, the within-future variance is the **same for every predictor** on
these cases. It cancels from paired MSE differences. Large variability alone
is therefore not the arithmetic explanation for a ranking reversal.
The reversal requires the forecast-difference / realized-target-change
interaction above. Mean-target scoring has the same absolute paired MSE
differences as four-future scoring, although relative percentages differ.

## Complete fixed-observer absolute MSE panel

Lower is better. All three settings are retained. Original same-founder MSE:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.006473568 | 0.006262153 | 0.006738734 |
| One copy | 0.006715561 | 0.006329361 | 0.006386025 |
| Separate: passive | 0.006596206 | 0.006308144 | 0.006485008 |
| Separate: shuffle | 0.007068832 | 0.006503384 | 0.006565016 |
| Separate: attenuation | 0.007516928 | 0.006721745 | 0.006586862 |
| Separate: control + | 0.007011628 | 0.006503658 | 0.006534046 |
| Separate: control − | 0.006607907 | 0.006268972 | 0.006456931 |
| Mean: passive | 0.006348099 | 0.005922476 | 0.006104060 |
| Mean: shuffle | 0.006536972 | 0.006006528 | 0.006155200 |
| Mean: attenuation | 0.006601028 | 0.006074409 | 0.006197187 |
| Mean: control + | 0.006478232 | 0.006003196 | 0.006130810 |
| Mean: control − | 0.006367412 | 0.005907325 | 0.006091799 |

Mean individual-future MSE, averaging all four futures:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.006934551 | 0.006542999 | 0.006932775 |
| One copy | 0.006791235 | 0.006405755 | 0.006671629 |
| Separate: passive | 0.006933798 | 0.006471422 | 0.006641863 |
| Separate: shuffle | 0.007097728 | 0.006531997 | 0.006763317 |
| Separate: attenuation | 0.007144561 | 0.006466938 | 0.006638654 |
| Separate: control + | 0.006759403 | 0.006388323 | 0.006643264 |
| Separate: control − | 0.006953838 | 0.006442691 | 0.006612408 |
| Mean: passive | 0.007001032 | 0.006487682 | 0.006653043 |
| Mean: shuffle | 0.007279984 | 0.006651484 | 0.006790027 |
| Mean: attenuation | 0.007049290 | 0.006499778 | 0.006687043 |
| Mean: control + | 0.006909992 | 0.006448634 | 0.006652310 |
| Mean: control − | 0.007042102 | 0.006480429 | 0.006639730 |

MSE against the four-future mean:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.002793660 | 0.002402108 | 0.002791883 |
| One copy | 0.002650344 | 0.002264864 | 0.002530738 |
| Separate: passive | 0.002792907 | 0.002330531 | 0.002500972 |
| Separate: shuffle | 0.002956837 | 0.002391105 | 0.002622425 |
| Separate: attenuation | 0.003003670 | 0.002326047 | 0.002497763 |
| Separate: control + | 0.002618512 | 0.002247432 | 0.002502373 |
| Separate: control − | 0.002812947 | 0.002301800 | 0.002471517 |
| Mean: passive | 0.002860141 | 0.002346791 | 0.002512152 |
| Mean: shuffle | 0.003139093 | 0.002510593 | 0.002649136 |
| Mean: attenuation | 0.002908398 | 0.002358887 | 0.002546152 |
| Mean: control + | 0.002769101 | 0.002307743 | 0.002511418 |
| Mean: control − | 0.002901211 | 0.002339538 | 0.002498839 |

The six reused nested references, with no re-selection or fitting:

| Nested reference | Same-founder original MSE | Four-future MSE | Mean-future MSE |
|---|---:|---:|---:|
| Separate: attenuation | 0.006858606 | 0.006748733 | 0.002607842 |
| Separate: passive | 0.006398497 | 0.006494626 | 0.002353735 |
| Separate: control − | 0.006268972 | 0.006442691 | 0.002301800 |
| Separate: control + | 0.006753900 | 0.006535765 | 0.002394874 |
| Separate: shuffle | 0.006588114 | 0.006567900 | 0.002427008 |
| Starting only | 0.006555419 | 0.006826328 | 0.002685437 |

Every series' MAE, RMSE, signed mean error, groups, founders, individual repeats
and repeat omissions are in summary.json. All signed/absolute/squared case
errors and exact predictions are in panel.npz. All 201 contrasts have the
same complete contribution and sensitivity panels; the focal tables above
are not the only comparisons retained.

## Qualification, freeze, timing and audit

First qualification: 58 passed, one failed in126.13seconds. A test required
bit equality between differently ordered floating-point sums:
0.13322825036547725 versus0.13322825036547722. The assertion was corrected
to absolute tolerance1e-14. Production and independent analysis arithmetic
were unchanged; the failed report and fixtures were retained.

Full rerun: **59 passed**, no failures/skips, in **125.35seconds**. Qualification
used synthetic predictions; no actual-case review had been extracted.

- Freeze: **2026-09-20 15:54:23.743703 UTC**, **2,116 inputs**.
- Full checked synthetic benchmark: **19.918162seconds**; hashing
  **9.641449seconds**. Main forecast **179.119221seconds**, projected storage
  **164,199,812bytes**, within256MiB allowance and4GiB external reserve.
- Main manifest prepared **15:56:19.220228 UTC**; COMPLETE
  **15:56:52.434604 UTC**. Main **33.214398seconds** excluding preflight;
  **17,037,579bytes /16.248302MiB** output payload.
- Fresh saved audit: **15:57:56.720918 UTC**, **32.979855seconds**.
  All **2,125 input hashes / four indexed outputs**, 20 panel arrays,
  42 forecast series, 201 source contrasts and all new decomposition/
  sensitivity summaries pass.
- One numerical worker, numerical threads one, affinity CPUs0–5.
  Under the ten-minute detachment threshold. No retry of the main study,
  automatic successor, fitting or dynamics.

Payload size excludes qualification fixtures, the benchmark and earlier
studies. All numerical artifacts, logs, fixtures and caches remain under
/mnt/bioIce1; only code and documentation are in this workspace.

## Provenance

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`

Run: `l20_extension1_future_stability_review_v1_attempt1`.

Artifacts beneath that root:

- `tmp/l20_extension1_future_stability_review_v1_attempt1_freeze.json`
- `runs/l20_extension1_future_stability_review_v1_attempt1/MANIFEST.json`
- `runs/l20_extension1_future_stability_review_v1_attempt1/COMPLETE.json`
- `outputs/l20_extension1_future_stability_review_v1_attempt1/`:
  panel.npz, summary.json, verification.json and input/output hash indexes.
- `logs/l20_extension1_future_stability_review_v1_attempt1_saved_audit_v1.json`
- `logs/d156_qualification_v1.xml` (one failed precision assertion) and
  `logs/d156_qualification_v2.xml` (all59 passed).

| Artifact | SHA-256 |
|---|---|
| Freeze | `09cead01a3bdc52219e3c9731a397e40022bf110527330bea2ea1d6ce745a847` |
| Manifest | `164817a13edbc86c390d30ed11c1dc7ea974fdf7082b996ec2c5bbde1a2988a0` |
| COMPLETE | `617dd74843502b240acd66521ccd0f51977d24cadbe6827a0a28c00c4ba90a0f` |
| Summary | `60adf122eff96918230fe2817f33368c910f1af191b88ace2d6dd89dc5a2b219` |
| Verification | `a6477e038787da126fba74c8955cce9412fe244ce688bf1f22d206df8a6003b5` |
| Output index | `c7609e3d0a14405fc91b1d1cbcced5c3a9138641ad524231eb050a9a5363e2cd` |
| Fresh audit | `5da46910ebeb65feadb3c3fa7ea5db521b7d9a3d5f2de4e68869ae706b254883` |

## Next lead — proposal only, not launched

A learning-target check would now be more informative than another challenge
dose or encoding sweep. On the same16 repeat-covered founder blocks, compare
training each observer on the original outcome, on each of the four saved
single-repeat outcomes separately, and on the four-repeat mean. Keep all12
fixed observer definitions and all three settings; no favorable stream choice.

Use identical whole-founder folds for all training-target arms, with all
outcomes of the held-out founder excluded from fitting and preprocessing.
Score against the same retained held-out future panel, keeping individual
streams, all controls and starting/one-copy baselines. Compare the average
loss of the four single-repeat-trained predictors, not a selected predictor
or an unregistered ensemble. The four-repeat target uses more training
outcome information; that budget difference must be explicit and common to
all observers. Do not compare a new15-founder training fold directly against
D155's31-founder fold as if only the target had changed.

That separately frozen development experiment would ask whether more stable
training targets improve forecasting, and whether any challenge advantage
survives the same improvement to passive observation. It would not itself
confirm prospective superiority or prove that previous failures were caused
by noisy targets. No such refit or new cohort has been launched here.
