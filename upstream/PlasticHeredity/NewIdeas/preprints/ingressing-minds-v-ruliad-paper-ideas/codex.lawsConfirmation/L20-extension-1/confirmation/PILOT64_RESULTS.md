# D162 — fixed 64-founder prospective pilot: audited results

2026-09-22. **COMPLETE and freshly audited. Primary: PREDICTIVE_DIFFERENCE_UNRESOLVED.**

[Frozen protocol](PILOT64_PROTOCOL_V1.md) · [execution and audit provenance](PILOT64_EXECUTION.md) ·
[complete numerical tables](PILOT64_TABLES.md).

## Verdict in plain terms

Watching what a record reconstructs was more useful than measuring its starting
appearance alone in this experiment. However, adding the registered residual-minus
challenge did **not demonstrate an extra prediction benefit over equally costly
passive reconstruction**. Its squared error was 0.0453% higher, with uncertainty
allowing a small benefit or harm. This is an unresolved difference, not equivalence.

Both primary observers outperformed the fairly tuned starting-only baseline by
about 4% in squared error. Neither demonstrated an advantage over the selected
one-copy baseline in the secondary pointwise intervals. The apparatus controls
passed, so the primary result is not explained by a failed registered control gate.

The positive renewal result and the unresolved prediction result answer different
questions: aligned writing helps carry acquired content through replacements;
this particular diagnostic challenge has not shown it forecasts that retention
better than passive reconstruction. L20 remains **STRESS_TESTED / MIXED**.

## What was fixed before outcomes

This is the user-approved, separately registered 64-founder pilot, not an interim
look at the proposed 768-founder experiment. No sample extension follows this
result. All founders 100000–100063, four lives and four family/writer groups were
retained: 1,024 primary cases, four independent futures each, 4,096 terminal
outcomes. There are 64 statistical blocks, not 4,096 independent replicates.

The carrier is the existing 2,048-byte tissue record, read through the one frozen
D131 guide. Three read–erase–rewrite boundaries are followed by a fresh G4 reader.
Full control lineages occur on every founder under future0; the other three
futures contain only the ordinary/aligned primary paths. Diagnostic copies never
enter an actual lineage. This is not the 64-byte DoorKey experiment.

The primary edit is D151's fixed residual-minus rotation, not D141's original
25%-position shuffle. It changes the residual spatial pattern while preserving
the packet mean, norm and own/competing-axis components, with the existing
degenerate identity cases retained. Residual-plus is its equal-dose opposite
direction; attenuation and original shuffle also remain in the fixed secondary
panel. Supplied family information and geometric axes are not learned ontology.

Each primary observer uses starting measurements, its public family/writer group
and two complete diagnostic read–rewrite–fresh-read cycles: U0 + intact U1 for
passive, U0 + residual-minus for challenge. Six physical diagnostic cycles per
case supply the entire panel, but no individual observer receives a third copy.
Noise is separated from actual lineages.

All 17 observers × 3 settings were fitted once on the same 16 development founders'
four-future means. Primary alpha .01 and independently selected cheap-baseline
settings (.001 starting-only, .01 one-copy) were frozen before any pilot founder.
The tied model constrains the two raw reading slopes under the original ridge
penalty; it is not the separately standardized mean-reading model. No test-stage
fitting, normalization, tuning or case selection occurred.

The model freeze preceded founders. All **52,224 forecasts were globally sealed
at 12:14:30.557744 UTC on September 21**, before any actual primary/control lineage
started at 12:14:31.751734 UTC.

## Primary comparison and absolute errors

The outcome is the existing terminal qualified own-minus-alternative preference.
Loss averages individual-future squared errors equally over futures, lives,
groups and founder blocks. Gain = passive MSE − challenge MSE.

- Absolute gain: **−0.000002699445 MSE**.
- Whole-founder percentile-bootstrap 95% interval:
  **[−0.000023801300, +0.000019234350]**, 20,000 draws, seed 16120260920.
- Rescaled by observed passive MSE: **−0.045281%**
  **[−0.399249%, +0.322641%]**. This is a fixed-denominator rescaling of the
  absolute interval, not a separately bootstrapped ratio interval.
- Positive block gains: 30/64; negative: 34/64. Every block remains included.

| Frozen observer | Alpha | MSE | RMSE, preference points | MAE, preference points | Bias, preference points |
| --- | --- | --- | --- | --- | --- |
| tied:sham_minus | 0.01 | 0.005964223422 | 7.72284 | 4.60521 | -0.15274 |
| tied:passive | 0.01 | 0.005961523977 | 7.72109 | 4.60787 | -0.16504 |
| starting | 0.001 | 0.006215812899 | 7.88404 | 4.86080 | -0.12558 |
| one_copy | 0.01 | 0.006019101537 | 7.75829 | 4.66330 | -0.07721 |

MAE is slightly lower for challenge while the registered MSE is slightly higher;
changing loss functions after seeing that difference would not rescue the primary.
No forecast in the complete 51-model panel was clipped. Calibration intercepts/
slopes and all settings are retained in the [table appendix](PILOT64_TABLES.md).

These intervals condition on the one frozen trained-model set and tested host
distribution. They do not estimate variability across independently retrained
learners. Small positive gains of roughly the development estimate's relative
size (+0.176% there) remain compatible with this pilot; they are not demonstrated.
Development used its own reference MSE and leave-one-founder-out models, while
deployment fitted all16 development founders. This is not a formal test of a
development/test difference, and the reused development selection scores were
never prospective evidence.

## Fair cheaper baselines

These are the four registered **secondary** selected-setting comparisons, not
alternate success gates. Gain is reference MSE minus candidate MSE; intervals
below are in millionths of MSE and are pointwise, not multiplicity-adjusted.

| Candidate (alpha .01) | Selected reference (alpha) | Relative MSE gain | 95% interval, ×10⁻⁶ MSE |
| --- | --- | --- | --- |
| tied:sham_minus | starting (0.001) | +4.0476% | [+120.4240, +382.5803] |
| tied:sham_minus | one_copy (0.01) | +0.9117% | [-17.8086, +126.7633] |
| tied:passive | starting (0.001) | +4.0910% | [+121.8448, +386.3270] |
| tied:passive | one_copy (0.01) | +0.9566% | [-19.7092, +134.7268] |

Starting-only and one-copy MSE are .006215812899 and .006019101537, respectively.
We do not substitute a less favorable baseline setting to improve the headline.

## Group and future variation

All four groups contribute equally. These are descriptive partitions, not
separately powered confirmations or grounds for exclusions.

| Group | Challenge MSE | Passive MSE | Gain, ×10⁻⁶ MSE |
| --- | --- | --- | --- |
| A ordinary | 0.0006729669 | 0.0006739583 | +0.9914 |
| A aligned | 0.0004440913 | 0.0004404041 | -3.6872 |
| B ordinary | 0.0200212869 | 0.0200177892 | -3.4977 |
| B aligned | 0.0027185487 | 0.0027139443 | -4.6043 |

| Future | Challenge MSE | Passive MSE | Gain, ×10⁻⁶ MSE |
| --- | --- | --- | --- |
| 0 | 0.0064885128 | 0.0065225427 | +34.0299 |
| 1 | 0.0065155353 | 0.0064900118 | -25.5234 |
| 2 | 0.0053252115 | 0.0053327629 | +7.5514 |
| 3 | 0.0055276341 | 0.0055007784 | -26.8557 |

Within-case variance across the four realized futures (divisor four) is
0.003931378946. The exact saved identity is individual-future
MSE = error to the four-future mean + this shared variance term. Passive error
to that mean is 0.002030145031; challenge is
0.002032844476. The shared term cancels from the paired gain, so it
cannot explain away an unfavorable primary comparison. Four repeats do not
establish an irreducible-noise ceiling or reveal the exact conditional mean.

## Complete secondary context

All 264 same-setting contrasts (including the one primary row), four
selected-baseline contrasts, and 51 absolute-score rows are printed in the
[appendix](PILOT64_TABLES.md). No favorable row replaces the primary.

The primary candidate versus matched passive remains unresolved at **all three**
settings:

| Alpha | Relative MSE gain | 95% interval, ×10⁻⁶ MSE |
| --- | --- | --- |
| 0.001 | +0.0878% | [-18.3746, +29.9110] |
| 0.01 | -0.0453% | [-23.8013, +19.2343] |
| 0.1 | -0.2355% | [-34.0913, +4.4214] |

The earlier development lead from simplifying the passive predictor also does
not demonstrate a new-cohort benefit. Tied versus separate passive:

| Alpha | Relative MSE gain | 95% interval, ×10⁻⁶ MSE |
| --- | --- | --- |
| 0.001 | +0.8925% | [-68.9517, +179.1242] |
| 0.01 | -0.3374% | [-119.0004, +76.3126] |
| 0.1 | -0.2103% | [-65.7173, +39.5906] |

Original shuffle has higher MSE than its matched passive observer in all nine
encoding/setting comparisons; every corresponding pointwise interval is below
zero. This is frozen secondary evidence in this cohort, not a replacement
confirmatory verdict for the earlier, differently trained D141 test.

There is a contrasting **secondary lead**: tied residual-plus at .01 has
+0.8406% relative MSE gain over tied passive, with a pointwise interval rescaled
to [+0.1111%, +1.5835%]. It is also favorable at .001 but not resolved at .1;
separate/mean encodings and the mean of plus/minus losses have mixed results.
Both directions and every setting are shown. These many correlated pointwise
comparisons are not multiplicity-adjusted. Selecting plus now would be a
post-test hypothesis choice, not confirmation or a revised D162 winner.

## Controls: renewal is real here, protection is still better on average

All registered readout, content, read-off/write-off continuity, wrong-content,
lesion and external-rescue qualification gates passed. No gate failure or
excluded case is hidden. The full 228 contrast rows (both qualified/sign
readouts, all stages and roles) and all terminal conditions are in the appendix.

Terminal qualified preference effects below average both targets; units are
preference points, with whole-founder pointwise 95% intervals.

| Contrast | Effect, points | 95% interval, points |
| --- | --- | --- |
| aligned_minus_translated | +4.2747 | [+3.3523, +5.2467] |
| aligned_minus_copy | -1.7845 | [-2.2781, -1.3016] |
| aligned_minus_aligned_read_off | +36.6341 | [+35.6941, +37.5572] |
| aligned_minus_aligned_write_off | +36.6341 | [+35.6941, +37.5572] |
| aligned_minus_aligned_wrong | +73.2681 | [+71.3882, +75.1145] |
| aligned_minus_aligned_lesion | +37.7159 | [+36.3747, +39.0770] |
| aligned_rescue_minus_aligned_lesion | +36.5341 | [+35.2310, +37.8517] |
| translated_minus_copy | -6.0593 | [-7.1297, -5.0239] |
| aligned_minus_aligned_post_shuffle | +36.4632 | [+35.1524, +37.7648] |
| aligned_minus_aligned_pre_shuffle | +36.3953 | [+35.1455, +37.6709] |
| ideal_minus_zero | +46.1098 | [+45.9839, +46.2357] |
| copy_minus_zero | +38.4186 | [+37.8204, +38.9961] |
| aligned_minus_zero | +36.6341 | [+35.6941, +37.5572] |
| translated_minus_zero | +32.3593 | [+31.0089, +33.6594] |

Aligned writing improves over ordinary translated writing by **4.2747
[3.3523, 5.2467] points**, but loses to protected copying by **1.7845
[1.3016, 2.2781] points** on the pooled measure. The first difference is
0.3281 points for A and 8.2214 for B; the full directional results are retained.
A/B also differ for aligned-versus-copy, so the pooled disadvantage is not a
claim that alignment loses for both targets.

The controls establish bounded content-dependent engineered renewal under a
fixed supplied guide. Protected copy is not renewable writing; rescue supplies
an external backup. Passing these gates does not establish autonomous repair,
complete shape preservation, universal low-pass cleaning, biological heredity
or an autonomously learned address. The prediction contest excludes controls.

## Audit, costs and reproducibility

45 qualification tests passed. The fresh post-run saved audit completed
**2026-09-21 22:38:35.643241 UTC** in **519.099189s (8m39s)**, checking all
2,311 pinned inputs, 712 indexed outputs plus their hash index, 52,224 forecasts,
4,096 outcomes, 6,144 diagnostic cycles and full controls. Every case retained;
zero new dynamics. Audit receipt binds the main COMPLETE hash, rechecked for this
report; the summary and key barrier/check files still match their completion
index. This report transcribes audited saved results, without new fits or runs.

- Main: **5,876.202232s (97.94min)**, at most six workers/CPUs, one numerical
  thread each. Actual wall time is not a measured CPU-hour total.
- Main retained output: **2,313,989,474 bytes (2.155GiB)**, versus measured
  planning allowance 5.726GiB and hard cap 8GiB plus 4GiB reserve.
- Complete disposable benchmark: 280.715245s checked block work plus
  39.920377s final hash verification; 36,674,120 retained bytes.
- All numerical states, models, data, temporary files and logs stay on
  `/mnt/bioIce1/`. Only code and documentation are in this workspace.
- Long stages were detached, checked only on user requests, with no automatic
  polling, retries or successor runs.

External evidence:

- [Saved summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_pilot64_v1_attempt1/summary.json), SHA256
  `b979292bf0bb3f59bbc0073bd60beed4562b93b8b0870f845a9975c250538283`.
- [Main completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_pilot64_v1_attempt1/COMPLETE.json), SHA256
  `d77470be6d251f4d42344a6acfe0173fe3a542b04be2649de6e998bcfd95da53`.
- [Fresh audit receipt](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/l20_extension1_pilot64_v1_attempt1_saved_audit_v1.json), SHA256
  `822a61ccf5b8d26ff466a51cce226c12b20d0f5d5293778477e54a06323fd191`.
- [Full output hash index](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_pilot64_v1_attempt1/output_hashes.sha256).
  All per-founder/per-group/per-future absolute losses and calibration values
  remain in the saved summary; no raw results were pruned.

## Closeout and recommended next decision

**Close D162 as this fixed, audited, unresolved prospective pilot.** Do not
silently add founders, change the challenge, select a new alpha, claim
equivalence, or upgrade L20. The original D141 result stays unresolved.

I recommend a **small saved-data plus/minus asymmetry audit before considering
another simulated cohort**. Its question would be why the two already-fixed
opposite edits change relative prediction error differently, and why the
development ranking did not carry into this cohort. Keep the models, settings,
all founders/futures and both directions fixed; separate forecast shifts,
error covariance, and group/future contributions, while showing all other
edits and cheap baselines as context.

That would be explicitly post-test explanation, not new prospective evidence,
not a search for a preferred direction, and not a reason to redefine D162.
No protocol, new numerical analysis job or experiment for that follow-up has
been launched here. If it provides no stable explanatory pattern, park this
probe family and return to another law. Any later prediction claim needs its
own registration and genuinely untouched founders; D162 is now observed data.
