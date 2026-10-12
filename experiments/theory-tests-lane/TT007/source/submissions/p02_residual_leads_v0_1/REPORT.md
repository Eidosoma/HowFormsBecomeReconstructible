# The sharper lead is later success after current failure

Exploratory follow-up to P02, using the same saved excluded-block predictions.
No models were fitted, no simulations were run and no matching threshold was
changed. All outcomes were already known. The questions were written in
[PROTOCOL.md](PROTOCOL.md) before computing this decomposition.

**The signed-transfer increment comes entirely from the currently failing
cases. It does not improve the aggregate forecast among currently passing
cases.** This narrows the mechanism worth pursuing: retained ability to succeed
later after poor current expression, rather than an established warning signal
for apparently healthy lineages.

## Where the forecast increment comes from

Of 512 history-lineage records, 448 pass their generation-14 body test and 64
fail. Of the failing cases, 29 pass the generation-32 terminal assay; of the
passing cases, 34 fail that later assay. Histories remain related within eight
blocks, and the body and final fresh scattered assay are different challenges.
These counts are not estimates of recovery or loss under one fixed challenge.

The table uses equal-block Brier error, matching P02's inference unit. Lower is
better. Both sides of the primary comparison retain current output, history,
unsigned access and all ten quadratic output terms.

| Generation-14 stratum | Records | Later terminal successes | Primary baseline | Add signed transfer | Blocks improved |
|---|---:|---:|---:|---:|---:|
| Currently pass | 448 | 414 | 0.071702 | 0.072032 | 4/8 |
| Currently fail | 64 | 29 | 0.214616 | 0.173078 | 6/8 |
| All | 512 | 443 | 0.092186 | 0.087626 | 6/8 |

The original overall Brier improvement, 0.004560, decomposes exactly into a
**+0.004809 contribution from failing cases** and a **−0.000249 contribution
from passing cases**. These are each stratum's summed error change divided by
all 512 records; they are not the conditional errors in the table. The overall
records are balanced across blocks. Within-stratum block sizes differ, so
record-weighted conditional and equal-block conditional errors differ.

The secondary comparison shows the same pattern: a +0.007894 overall-score
contribution from failing cases and −0.000381 from passing cases, totaling
+0.007513. Thus this finding does not depend on choosing whichever of the two
already declared increments gives a favorable decomposition.

A new, explicitly post-hoc comparison of the secondary signed model with the
simpler expression/history model also localizes the apparent benefit:

| Stratum | Expression/history | Secondary model with unsigned and signed transfer |
|---|---:|---:|
| Currently pass | 0.070682 | 0.072075 |
| Currently fail | 0.209480 | 0.153731 |

This comparison adds two diagnostics together and does not isolate signed
transfer. It does not replace the original primary comparison. The primary
signed model remains worse than the simpler expression/history model overall,
as the previous report stated.

The 64 failing cases comprise 5 original, 10 single-pulse, 16 spaced and 33
clustered records; later success counts are 2, 5, 7 and 15 respectively. There
are only 4–16 failing cases per block. The block is the unit of inference, and
this limited panel provides a development hypothesis, not a subgroup validation.

## The combined predictors do not rescue the matched-pass decision result

Another possible lead was that the combined forecast, rather than raw signed
transfer alone, might choose the better of two apparently similar states. On
the unchanged 84 close-output pairs, it does not beat the current-margin rule.

| Choice rule | Terminal successes /84 | Correct on 9 discordant pairs |
|---|---:|---:|
| Always spaced | 75 | 5 |
| Current minimum margin | **77** | **7** |
| Raw signed transfer | 76 | 6 |
| Expression/history forecast | 75 | 5 |
| Secondary signed forecast | 75 | 5 |
| Primary signed forecast | 76 | 6 |

All forecast choices use the previously saved probability from the model that
excluded the pair's entire block. No coefficients were trained on these pairs.
The selection of these follow-up comparisons is still outcome-informed, and
nine discordant pairs cannot settle small decision differences. The negative
finding is retained rather than adding another tuned decision rule.

## A discriminating next test

The narrower proposed claim is: **among currently failing bodies, a record
diagnostic predicts later fresh-body success beyond continuous expression and
conventional summaries.** The present calculation motivates this claim; it does
not establish it. Current-pass failures remain an unresolved forecasting problem.

The useful experiment would separate three possibilities:

1. The current body happened to fail a difficult or noisy read while its record
   remained usable. Repeated fresh reads of a fixed record, with a fixed injury
   and declared reset/noise distribution, measure that possibility.
2. Original rewriting and subsequent development restore competence. Comparing
   the incoming record with the outgoing O record of the same failed body,
   under the same fresh-read conditions, separates a writer change from merely
   repeating a read. Continued O rewriting then tests a distinct, longer claim.
3. Later success follows an easier disturbance realization. Separately varying
   injury while holding the read budget and record fixed measures this effect;
   it must not be pooled with the fixed-injury test and called repair.

This gives P03 a concrete starting point: forecast how native fresh-read success
from a fixed record changes with **injury and available read time**, then ask
whether rewriting moves that boundary. Keep a current-expression predictor,
unsigned access and direct repeated-read estimates as competitors. The last is
a potentially expensive but strong baseline whose probe cost must be counted.

The decisive negative result would be that the apparent record advantage
disappears under repeated reads, continuous-expression control, or a fixed
challenge. A useful positive result would predict which failed states can
reconstruct under a resource/damage contract before their outcomes are seen.
Neither long-horizon continuation nor autonomous maintenance follows from a
one-read result.

Before a new experiment, freeze the enrollment rule, model, injury/time levels,
budget, comparator and uncertainty target; benchmark its native runtime and
record programme-wide exposure. All current E051 blocks are already exposed.
This note launches no new cohort and assigns no confirmatory sample size.

The earlier pulse evidence also cautions against requiring return to the exact
ancestral network: competence persisted while the normalized record distance
grew. The boundary should concern task recovery, with historical specificity
tested separately, rather than distance to a particular network implementation.

## Artifacts and verification

- [Results](results.json) retain every stratum/model/block score and contrast.
- [Decision rows](matched_decisions.csv) retain every pair and all six rules.
- [Audit](audit.py) checks source hashes and recomputes every saved Brier error.
- [Separate verifier](verify.py) reconstructs the three strata, all scores and
  contrasts, the 84-pair matching set and all six choices directly from the
  source records/probabilities, without importing the audit or prior analysis.
- The [original P02 report](../p02_common_future_v0_1/REPORT.md) and its frozen
  source package are unchanged. This is an additional development exposure.
