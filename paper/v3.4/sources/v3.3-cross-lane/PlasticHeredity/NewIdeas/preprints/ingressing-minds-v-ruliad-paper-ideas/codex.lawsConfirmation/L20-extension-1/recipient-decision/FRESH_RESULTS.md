# D199: family matching transfers; record details add no demonstrated benefit

2 November 2026. **COMPLETE / separately SAVED-AUDITED.**
[Frozen contract](FRESH_V1.md), [complete tables](FRESH_TABLES.md),
[qualification](FRESH_QUALIFICATION.md), [current status](FRESH_STATUS.md),
[metadata clarification](FRESH_METADATA_NOTE.md).

The fixed family rule improved terminal target-specific preference on fresh
founder histories by **0.139618 points** over the best common setting selected
in development. Its adjusted interval is **[0.051498, 0.239563] points**. This
is a small prospective benefit from coarse family-to-recipient matching under
the tested apparatus.

The registered primary, detailed record rule minus family-by-writer, is
**exactly zero on this cohort**. The detailed rule, family rule and
family-by-writer rule made identical choices for all **256 decisions**.
Record detail supplied no additional decision benefit. A zero-width observed
difference interval does not establish equivalence on unseen packets or show
that packet information is intrinsically useless. No model was refitted.

## What was tested prospectively

All 16 registered founder histories, 319900–319975 in steps of five, all four
lives, both target families and both descendant writers were retained: **128
distinct 2,048-byte F0 packets and 256 packet/writer decisions**. Each candidate
recipient coupling, 0.75, 1.0 or 1.25, was used throughout three replacements.
Four paired future streams, 2–5, and the complete six-condition panel remain.
The experiment retained 9,216 paths and 18,432 terminal-reader rows.

D198's exact model, six static features, lambda100 coefficients, feature
scales/clipping, tie rule and simple baselines were frozen before acquisition.
All policies receive known target-family and writer context. The detailed
rule also receives the initial packet and frozen guide; it receives no founder
identity, source body, acquisition history or descendant outcome. Family labels
and templates are supplied apparatus, not autonomously learned concepts.

All 256 decisions were sealed together on 1 November at **11:25:37.051158 UTC**.
The descendant barrier followed at **11:25:40.915158 UTC**, with zero descendant
outcomes at sealing. The disposable benchmark 519900 is excluded from fitting
and main inference. All actual analysis IDs were checked despite a misleading
metadata field described below. No interim selection or adaptive enlargement
occurred.

## Decision values and all registered comparisons

Preference is the common reader’s match to its own target minus its match to
the alternative target, multiplied by 100 for points. These are not success
percentages. Futures are averaged within cases,
then 16 cases within each founder, then 16 founders equally. Nested lives and
future streams do not increase the independent sample size.

| Policy | Frozen recipient choice | Mean preference points |
| --- | --- | ---: |
| Native | 1.0 for every case | 33.901215 |
| Development-selected common | 0.75 for every case | 35.050583 |
| Writer-only | 0.75 for either writer | 35.050583 |
| Family | A→1.25, B→0.75 | 35.190201 |
| Family-by-writer | A→1.25, B→0.75, either writer | 35.190201 |
| Detailed record rule | Identical choices to family in all 256 cases | 35.190201 |

Intervals use 100,000 whole-founder bootstrap resamples, fixed PCG64 seed
319900198, linear percentile interpolation. The six-comparison Bonferroni
intervals have 99.1666667% nominal coverage per comparison. A positive adjusted
lower endpoint is the registered positive decision. Coverage is approximate
with 16 blocks. Duplicate baselines remain in the declared comparison family.

| Comparison | Difference, points | Ordinary 95% interval | Adjusted interval | Record gains / harms / ties |
| --- | ---: | --- | --- | --- |
| **Record − family-by-writer, primary** | **0** | [0, 0] | [0, 0] | 0 / 0 / 256 |
| Record − family | 0 | [0, 0] | [0, 0] | 0 / 0 / 256 |
| Record − common | +0.139618 | [0.071716, 0.213623] | [0.051498, 0.239563] | 80 / 40 / 136 |
| Record − writer | +0.139618 | [0.071716, 0.213623] | [0.051498, 0.239563] | 80 / 40 / 136 |
| Record − native | +1.288986 | [1.000214, 1.597214] | [0.911965, 1.706314] | 173 / 67 / 16 |
| **Family − common, coarse matching** | **+0.139618** | [0.071716, 0.213623] | **[0.051498, 0.239563]** | 80 / 40 / 136 |

The primary supplies no positive fine-matching result. The positive coarse
comparison was separately registered; it does not replace the primary.
The detailed rule's gains over common/native are fully explained by its
agreement with the family rule. No feature clipping occurred in any decision.

## Harms, families and futures

Family versus common is positive in **13 founder histories** and negative in
**3**. The losing histories are 319910 (−0.036621 points), 319930 (−0.012207),
and 319940 (−0.024414). At the case level, its positive contribution is
+0.205612 points and its negative contribution −0.065994, giving the net
+0.139618. The complete tables retain every founder and decision.

Only A cases change coupling relative to common. Their 128 changed decisions
include 80 gains, 40 harms and 8 outcome ties. All 128 B decisions use the same
0.75 setting as common and therefore tie. Positive aggregate evidence does not
mean improvement for every record or every founder.

| Family / writer | Family policy preference | Family − common, points | Gains / harms / ties |
| --- | ---: | ---: | --- |
| A ordinary | 43.801880 | +0.355530 | 41 / 21 / 2 |
| A aligned | 44.097900 | +0.202942 | 39 / 19 / 6 |
| B ordinary | 22.520447 | 0 | 0 / 0 / 64 |
| B aligned | 30.340576 | 0 | 0 / 0 / 64 |

The pooled family-minus-common effect is positive in all four future streams:
**+0.128174, +0.178528, +0.160217 and +0.091553 points** for streams 2–5.
These are descriptive repeated outcomes on the same founders, not four
independent confirmations. Under the native terminal reader, the family rule
scores 35.315704 versus common's 34.829712 points. The registered common-reader
endpoint remains primary.

The retrospective per-record maximum is 35.369492 points, only **0.179291
points above family matching** on these observed future averages. This is an
optimistic outcome-informed reference; it is not deployable, independent
validation, or a proven attainable ceiling. It may include noise-selected
exceptions and cannot establish that a richer predictor would improve.

## Shape preservation and apparatus checks

Initial own-shape correlation averages **0.887568**. It ends at **0.831579**
under the family/record policy, compared with 0.827711 for common and 0.808317
for native. Recognition and continuous fidelity remain distinct. Family A
starts at 0.932279 and ends at 0.948849 under family matching; B starts at
0.842857 and ends at 0.714309. The pooled guide-label retention is 96.582031%,
which does not imply preservation of all shape detail.

Protected copying, both disabled-reading writers and disabled writing remain
outside the policy contest and appear in full for each coupling, assay and
founder. At native coupling, B ends at correlation **0.612081** with ordinary
writing, **0.729623** with aligned writing and **0.842857** with protected
copying, equal to its incoming packet correlation. B preference under those
conditions is respectively 19.363403, 28.616333 and 33.349609 points. Its
reading-disabled controls have adverse preferences, −20.968628 and −21.572876
points. Writing disabled gives zero terminal packet correlation. These controls
support the declared apparatus checks without turning a small matching gain
into complete reconstruction or autonomous repair.

## Integrity, metadata and computation

All 67 qualification tests had passed before the design freeze. The main
verification retained full independent source/descendant replay, all controls,
independent scalar policy values and bootstrap weights, and **46,592 exact
alias checks**. The separate audit passed on 1 November at **16:49:14.311626 UTC**
in **280.909558 seconds**, with no new dynamics or models. Its full proof matches
main completion. On 2 November, all **1,748 frozen inputs**, both execution-seal
inputs and **390 main output hashes** were verified again.

The saved report's top-level and interval `benchmark_excluded` flags are
misleadingly named: they mark whether the artifact itself is the excluded
benchmark, so are false for the main report. Actual complete record keys,
choices, founder weights and controls exclude 519900. This is a metadata
clarification, not a changed cohort or corrected numerical result. The
[separate note](FRESH_METADATA_NOTE.md) records the inherited checker limitation;
frozen code and receipts remain unchanged.

Main runtime **4h01m34s**; audit **4m41s**. One low-priority CPU6/thread,
nice10; main peak RSS 197.11 MiB, audit peak 150.64 MiB. Entire D199 retention at
review was **2,204,558,702 bytes (about 2.053 GiB)**, including qualification,
benchmark and audit, all on `/mnt/bioIce1`. Only code and docs are local.
The 8 GiB cap and 4 GiB free-space reserve passed. Both stages completed;
no successor was launched.

Deployment selects one recipient per case and realized future. Evaluation
ran all three recipient choices and the full six-condition control panel,
then independently replayed them. Its 9,216 paths should not be presented as
the inference cost of using the family rule. No separate inference timing or
extra-worker speedup is claimed.

## Meaning for the laws and next lead

For **L20**, the usability of transmitted acquired information depends partly
on its reconstruction setting, and a frozen family-based choice improves the
average outcome prospectively. For **L22**, this supports a bounded role for
recipient context; it does not identify a new body-proofreading mechanism.
Known labels, templates, guide and external rule remain supplied. It does not
establish autonomous interface repair, a learned ontology, complete shape
preservation, or the original challenge-over-passive prediction claim.
**L20/L22 remain STRESS_TESTED / MIXED.**

The next useful small step is to examine whether exceptions to the family
rule repeat across independent future streams in the already saved data.
That would distinguish stable within-family opportunities from favorable
noise before building another predictor. It is explicitly an exploratory
diagnostic on now-exposed data, not another prospective result. The
[next-lead plan](NEXT_LEAD.md) was subsequently completed as
[D200](../recipient-exceptions/RESULTS.md): selected exceptions lose value on
other futures, favoring the family rule. D199 remains unchanged. No new
experiment is running.
