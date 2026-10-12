# D163 — why did plus and minus behave differently?

Completed and freshly audited 2026-09-22. Explicitly **post-test explanation**,
not another prospective result. [Protocol](PROTOCOL_V1.md), [complete table
appendix](TABLES.md), [D162 prospective results](../confirmation/PILOT64_RESULTS.md).

## Simple terms

There is a useful lead, but not a new confirmed challenge advantage. In the
64-founder pilot, the plus-direction diagnostic's small advantage over passive
observation comes almost entirely from the difficult B family with ordinary
rewriting. The original minus-direction test still did not show a dependable
advantage. We retained that result.

The plus forecasts shift toward the eventual outcomes often enough to pay for
the extra forecast movement at the two lower regularization settings. The
minus forecasts do not do that reliably. This is mostly case-to-case matching,
not merely fixing a shared tendency to predict too high or too low.

However, each diagnostic condition has its own previously fitted predictor.
Both changed readings and changed predictor weights contribute to the plus/minus
gap. On the older development cohort the direction was reversed: minus did
better than plus throughout. That makes the next question about the stability
of the observation-to-forecast mapping, not a conclusion that plus is a
universally revealing disturbance.

D162 stays PREDICTIVE_DIFFERENCE_UNRESOLVED; D141 stays unresolved and L20 stays
STRESS_TESTED / MIXED. No cases were dropped, no model/challenge was retuned, and
no new founder, simulated lineage, fit or deployed forecast was generated.

## What plus and minus mean

These are the two fixed, equally sized residual-pattern rotations inherited
from [D151](../targeted-prediction/PROTOCOL_V1.md). They preserve the record's
mean, overall strength, own-axis field and competing-axis field while rotating
its remaining spatial component in opposite directions. They are not “good”
and “bad” labels or positive/negative rewards. They are also not D141's original
25%-position shuffle, which remains in every complete comparison panel.

Each observer still gets the same starting measurements and only two diagnostic
copies: one untouched copy and its assigned second copy. Diagnostic copies do
not enter the actual lineage. The paired terminal preference is own-minus-
alternative content after three replacements, not complete shape preservation.
The tissue carrier is 2,048 bytes, distinct from the earlier 64-byte DoorKey germ.

The accounting uses all 64 pilot founders and all 16 development founders,
separately. Each has four lives, four public family/writer groups and four saved
futures. Development uses out-of-founder predictions trained on 15 founders;
pilot models were fitted on all 16 development founders. We cannot separate a
cohort change from a training-set/model change by comparing those two panels.
No pooled 80-founder inference, new bootstrap, p-value or equivalence claim.

## The direction reversal

Positive values below mean lower MSE than the matched passive observer. Alpha
is the frozen regularization setting. These are descriptive point estimates;
the already reported D162 primary interval is unchanged. The .01 row was the
primary setting, but only minus versus passive was the primary comparison.

<!-- table:direction_reversal -->
| Alpha | Development plus gain % | Development minus gain % | Pilot plus gain % | Pilot minus gain % |
| --- | --- | --- | --- | --- |
| 0.001 | -0.6429 | -0.0512 | +1.2346 | +0.0878 |
| 0.01 | -1.1596 | +0.1763 | +0.8406 | -0.0453 |
| 0.1 | -0.7061 | +0.2988 | -0.0487 | -0.2355 |

Plus beats minus in all nine pilot encoding/setting comparisons; minus beats
plus in all nine development comparisons. These are correlated comparisons,
not nine independent replications. Nor does beating minus mean beating passive:
for example both tied directions lose to passive at .1 in the pilot. All three
encodings and settings appear in the appendix, including unfavorable rows.

## Where the .01 tied result comes from

Units in the next tables are millionths of MSE (1e−6), not preference points or
percentages. Groups carry equal weight, so one quarter of each group mean
contributes to the pooled mean. Family labels and writer conditions were public
inputs in the original study; their retrospective inspection is not a new
subgroup success test.

<!-- table:group_location -->
| Cohort | Group | Plus vs passive | Minus vs passive | Plus vs minus |
| --- | --- | --- | --- | --- |
| development | A ordinary | -1.3546 | +2.6812 | -4.0359 |
| development | A aligned | +2.9646 | +0.2739 | +2.6908 |
| development | B ordinary | -300.1173 | -2.7775 | -297.3398 |
| development | B aligned | -3.1858 | +45.6993 | -48.8852 |
| pilot | A ordinary | +2.6190 | +0.9914 | +1.6276 |
| pilot | A aligned | +1.7712 | -3.6872 | +5.4585 |
| pilot | B ordinary | +209.6394 | -3.4977 | +213.1371 |
| pilot | B aligned | -13.5679 | -4.6043 | -8.9635 |

Pilot B-ordinary contributes +52.4099 millionths to the pooled plus/passive gain
of +50.1155; the other three groups net −2.2944. That is 104.6% of the net pooled
gain because other groups partly offset it—not a causal fraction. The same
group is strongly unfavorable for development plus/passive. Prior work already
found this group dominated future variability; that is context, not a new
explanation of this sign reversal.

At .01, pilot plus/passive is positive in 40/64 founder means and in all four
future means. Dropping any one founder's scores leaves its pooled sign positive.
Minus/passive is positive in 30/64 founder means; its future and omission signs
are mixed. The leave-outs below are score-only sensitivity summaries, not
refits, new independent samples or confidence intervals. No founder is removed
from the reported result.

<!-- table:sensitivity -->
| Cohort | Direction | Positive founder means | Future 0 | Future 1 | Future 2 | Future 3 | Omit-one-founder minimum | Maximum | Omit-one-future minimum | Maximum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | sham_plus | 4/16 | -165.2711 | +38.3542 | -143.7557 | -31.0206 | -117.3880 | -33.5960 | -113.3491 | -45.4740 |
| development | sham_minus | 8/16 | +62.3424 | -21.8172 | +4.5841 | +0.7676 | -11.3665 | +31.1156 | -5.4885 | +22.5647 |
| pilot | sham_plus | 40/64 | +130.8197 | +25.6152 | +5.3649 | +38.6620 | +43.2190 | +57.5247 | +23.2141 | +65.0323 |
| pilot | sham_minus | 30/64 | +34.0299 | -25.5234 | +7.5514 | -26.8557 | -9.0629 | +1.7652 | -14.9426 | +5.3526 |

## Better matching versus the cost of moving the forecast

For a candidate shift d = candidate − passive and passive error y − passive:

    MSE gain = 2 mean[d × passive error] − mean[d²].

The first term is alignment with later outcomes; the second is the squared
shift cost. Alignment splits into a pooled bias term and a centered covariance
term. This identity describes the saved predictions; it does not mean the
observer was allowed to see the future. All original pilot forecasts were
sealed before any actual lineage outcomes.

<!-- table:alignment -->
| Cohort | Direction | Alignment | Bias part | Covariance part | Shift cost | Net gain |
| --- | --- | --- | --- | --- | --- | --- |
| development | sham_plus | -47.6882 | +0.0046 | -47.6927 | +27.7351 | -75.4233 |
| development | sham_minus | +25.2798 | -0.0004 | +25.2801 | +13.8105 | +11.4692 |
| pilot | sham_plus | +69.1934 | +0.6877 | +68.5058 | +19.0780 | +50.1155 |
| pilot | sham_minus | +8.8421 | +0.4060 | +8.4360 | +11.5415 | -2.6994 |

For pilot plus at .01, +69.1934 alignment exceeds 19.0780 shift cost; for minus,
+8.8421 alignment falls short of 11.5415 cost. The covariance term supplies most
of plus's alignment (+68.5058), versus only +0.6877 from pooled bias correction.
On development the plus alignment itself is negative. This narrows where to
look, without proving that the perturbation has added usable information.

The companion common/directional identity keeps both signs symmetric. At tied
.01, pilot common gain is +23.7080 and directional gain +26.4075: plus is their
sum and minus their difference. Development common and directional terms are
both negative. The midpoint used for this identity is algebra only, not an
extra-copy observer or an evaluated ensemble. The appendix retains all 18
cohort/encoding/setting rows.

## Changed readings versus different fitted predictors

All 51 pilot affine models and 52,224 raw/clipped forecasts reconstructed from
the saved training means, scales, slopes and public-group offsets. Maximum raw
reconstruction error: 1.78e−15. No pilot forecast clipped.

The plus-minus raw forecast difference is split symmetrically, in the declared
raw-feature coordinates, into changed readings under averaged weights, changed
weights/intercepts on averaged readings, and clipping. Multiplying each part by
2y − plus − minus gives an exact accounting of the plus-over-minus MSE gain.
The independent checker also verifies this identity by forward evaluation.
Those algebraic cross-evaluations are not deployed or scored as new observers.

<!-- table:model_split -->
| Encoding | Alpha | Reading contribution | Model contribution | Clipping contribution | Total plus-over-minus |
| --- | --- | --- | --- | --- | --- |
| separate | 0.001 | +66.5920 | -15.2973 | +0.0000 | +51.2946 |
| separate | 0.01 | +65.5570 | +13.8594 | +0.0000 | +79.4164 |
| separate | 0.1 | +54.6784 | -23.4752 | +0.0000 | +31.2032 |
| mean | 0.001 | +12.2091 | +60.8522 | +0.0000 | +73.0613 |
| mean | 0.01 | +21.3364 | +20.0548 | +0.0000 | +41.3911 |
| mean | 0.1 | +23.4480 | -14.4600 | +0.0000 | +8.9879 |
| tied | 0.001 | +9.7313 | +60.1560 | +0.0000 | +69.8874 |
| tied | 0.01 | +21.6556 | +31.1593 | +0.0000 | +52.8149 |
| tied | 0.1 | +27.1307 | -15.8602 | +0.0000 | +11.2705 |

At tied .01, readings contribute +21.6556 and model differences +31.1593 to the
+52.8149 total. Within B-ordinary those contributions are +35.0367 and +178.1004;
B-aligned has positive reading contribution but a larger negative model term.
The accounting is therefore neither “only the disturbance” nor “only the model.”

These are coordinate-dependent additive contributions, not identifiable causal
shares. The predictors were fitted to different diagnostic distributions.
They may have learned useful transformations, unstable correlations, or both.
This audit does not establish which, or independently prove extra information
in the changed-reading channel. In particular it does not establish autonomous
interface repair, learned ontology or a biological genome.

## Keep the absolute errors and cheaper baselines visible

These .01 main-observer and preselected cheap-baseline rows are included for
both cohorts. RMSE/MAE are preference points (100 × preference units). The plus
row is explicitly secondary; it is not a replacement primary.

<!-- table:absolute_selected -->
| Cohort | Observer | Alpha | MSE | RMSE points | MAE points | Bias points |
| --- | --- | --- | --- | --- | --- | --- |
| development | starting | 0.001 | 0.006512955766 | 8.07029 | 5.00983 | +0.01551 |
| development | one_copy | 0.01 | 0.006514522320 | 8.07126 | 4.87063 | -0.00656 |
| development | tied:passive | 0.01 | 0.006504356780 | 8.06496 | 4.84472 | -0.00167 |
| development | tied:sham_minus | 0.01 | 0.006492887552 | 8.05785 | 4.83057 | -0.00275 |
| development | tied:sham_plus | 0.01 | 0.006579780071 | 8.11158 | 4.87956 | +0.01201 |
| pilot | starting | 0.001 | 0.006215812899 | 7.88404 | 4.86080 | -0.12558 |
| pilot | one_copy | 0.01 | 0.006019101537 | 7.75829 | 4.66330 | -0.07721 |
| pilot | tied:passive | 0.01 | 0.005961523977 | 7.72109 | 4.60787 | -0.16504 |
| pilot | tied:sham_minus | 0.01 | 0.005964223422 | 7.72284 | 4.60521 | -0.15274 |
| pilot | tied:sham_plus | 0.01 | 0.005911408518 | 7.68857 | 4.60232 | -0.14421 |

The original selected-baseline comparisons are retained unchanged below.
Their gains are not a test of a two-copy challenge advantage over two-copy
passive observation. The pilot's roughly 4% gains over starting-only coexist
with an unresolved primary challenge comparison; the original intervals versus
one-copy also remain unresolved. No new intervals were constructed here.

<!-- table:cheap_baselines -->
| Cohort | Candidate | Candidate alpha | Reference | Reference alpha | MSE gain % |
| --- | --- | --- | --- | --- | --- |
| development | tied:sham_minus | 0.01 | starting | 0.001 | +0.3081 |
| development | tied:sham_minus | 0.01 | one_copy | 0.01 | +0.3321 |
| development | tied:passive | 0.01 | starting | 0.001 | +0.1320 |
| development | tied:passive | 0.01 | one_copy | 0.01 | +0.1560 |
| pilot | tied:sham_minus | 0.01 | starting | 0.001 | +4.0476 |
| pilot | tied:sham_minus | 0.01 | one_copy | 0.01 | +0.9117 |
| pilot | tied:passive | 0.01 | starting | 0.001 | +4.0910 |
| pilot | tied:passive | 0.01 | one_copy | 0.01 | +0.9566 |

The complete appendix includes every original shuffle, attenuation, residual
control and mean-control-loss comparison, all encodings/settings, and all
absolute scores. Mean control means mean of losses, never loss of an averaged
forecast. The external summary also retains every founder/group/future and
every requested omission with its own correctly centered decomposition.

## Verification, controls, storage and limits

The synthetic qualification passed 42 tests. The analysis was frozen before
performing this new accounting, but **after the D162 outcomes were known**.
That does not convert a post-test investigation into prospective evidence.
A complete 64-founder synthetic panel set a conservative 130.45-second stage
budget; actual execution took 3.17s and the separate fresh-process saved
audit 1.44s. Both were short attached jobs, one numerical worker/thread,
affinity CPUs 0–5, within the six-CPU cap. No long job or polling was required.

The saved audit checked 67 pinned inputs and three outputs; both cohorts'
277 comparisons/51 absolute model rows/nine sign identities; nine pilot model
decompositions and 18 arrays. Numerical bridges reproduce all 268 D162 loss
comparisons and 51 absolute rows, plus all 69 D161 development comparisons.
The new numerical outputs total 11.582 MiB, entirely on /mnt/bioIce1.
Only source code and Markdown documentation were added here.

This is deliberately a reduced-scope saved-data audit. It rehashes every
consumed small artifact and imported repository code, and pins prior COMPLETE,
forecast-barrier, qualification and full-audit receipts. It does **not** rerun
tissue dynamics or rehash unconsumed raw states. The D162 full controls and
fresh 2,311-input/712-output audit remain the apparatus provenance; they are
not new controls for this post-test algebra. All control gates passed there;
aligned writing improved pooled preference by 4.2747 points over ordinary
writing but remained 1.7845 points below protected copying. Full-shape
preservation and autonomous repair did not follow.

Run: l20_extension1_asymmetry_v1_attempt1.
[External summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_asymmetry_v1_attempt1/summary.json),
[model parts](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_asymmetry_v1_attempt1/model_parts.npz),
[verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_asymmetry_v1_attempt1/verification.json),
[completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_asymmetry_v1_attempt1/COMPLETE.json),
[fresh saved audit](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/l20_extension1_asymmetry_v1_attempt1_saved_audit_v1.json),
[freeze](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/tmp/l20_extension1_asymmetry_v1_attempt1_freeze.json),
[qualification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d163_qualification_v1.xml).

Completion SHA256: 4afa03e6b33f644c8b56c967eee832ba1eb8d9c9724486b9fa168ab4f7bddba2.
Audit SHA256: 968298055265b47002577dc1e38ff6667cf279750444fb3b5bacafcebb5fd4a3.
Freeze SHA256: 7aa5cff1e02099bb46735e0e289c89345ac83ea776c58b3e034328bff548afda.
Summary SHA256: a6aecac7df406ed494886dd070f59edf1054c37d2912478fca447274c1b9777c.

## Next lead, proposed only

The useful question is whether the plus/minus difference survives a common,
direction-blind prediction rule, so that the two signs cannot benefit from
separately fitted mappings. A bounded saved-data follow-up could specify such
a matched decoder using development data only, retain both signs/all groups
and the cheap baselines, and label pilot re-use as post-test analysis. It would
require a separate protocol and qualification; it would not confirm the original
claim on already observed founders.

Before any new simulation, that is more informative than choosing plus as a
new winner or expanding the old primary cohort. Do not tune the edit, dose,
setting or population to rescue the observed secondary edge. No successor,
new fit, enlarged cohort or pending background job was launched.
