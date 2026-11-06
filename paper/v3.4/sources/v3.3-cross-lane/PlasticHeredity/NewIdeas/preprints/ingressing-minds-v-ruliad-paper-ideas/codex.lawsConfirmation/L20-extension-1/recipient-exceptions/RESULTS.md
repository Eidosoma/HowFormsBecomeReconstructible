# D200: apparent exceptions mostly fail to transfer to other futures

2 November 2026. **COMPLETE / separately SAVED-AUDITED.**
[Fixed plan](PLAN_V1.md), [complete tables](TABLES.md),
[qualification](QUALIFICATION.md), [status](STATUS.md).

Choosing each case's recipient using two future measurements gave an apparent
**+0.302505 preference-point advantage** on those measurements. On the other
two futures, it gave **−0.234731 points** relative to the fixed family rule.
Mean effects were negative in **15 of 16 founders** and **all six selection/test
partitions**. This favors retaining the simple family rule rather than fitting
another fine matcher from these apparent exceptions alone.

This is exploratory reuse of D199's exposed data, not a new fresh-founder
prediction. The selector observes future outcomes unavailable to a deployable
packet-only rule. The result does not prove that stable exceptions are absent:
this two-future selection procedure fails to exploit them reliably here.
D199's prospective coarse gain and zero added detailed-rule benefit remain.

## Fixed calculation

All 16 D199 founders, four lives, both families/writers and four futures remain:
**256 cases**, three candidate couplings. For each case, choose the highest
common-reader preference on two futures and score it on the complementary two.
All six ordered partitions of futures 2–5 count. Exact ties keep the family
choice if possible, then use fixed action order 0.75/1.0/1.25. The selection
function receives only its selection-future integer score sums.

Preference is own-minus-alternative target match; points are that fraction
multiplied by 100, not a success percentage. Average six partitions within
cases, 16 cases within founders, and founders equally. The **1,536 overlapping
case/partition decisions are not independent samples**. Case gain/harm signs
follow partition averaging. No inferential interval or significance threshold
was added. Native-reader sensitivity scores the same common-selected actions.

Plan and code were sealed before split computation, but D199 outcomes had
already been exposed. This processing freeze is not a new scientific holdout.
No new cohort, dynamics, feature, classifier, seed search or favorable-split
selection was introduced. All cases and adverse outcomes remain.

## Absolute values and retained harms

| Procedure | Test-future preference points |
| --- | ---: |
| Fixed native coupling 1.0 | 33.901215 |
| Fixed common coupling 0.75 | 35.050583 |
| Fixed family rule A→1.25, B→0.75 | 35.190201 |
| D199 frozen detailed rule | 35.190201 |
| Choice made from two selection futures | **34.955470** |
| Maximum of each case's four-future means | 35.369492 |

The last row is an optimistic retrospective reference using the outcomes it
scores, not a deployable policy or proven attainable ceiling. The split-selected
procedure also falls **0.095113 points below common** on test futures.

After averaging partitions within cases, selected-minus-family has **39 gains,
122 harms and 95 ties**. Positive contributions average +0.105031 points and
negative contributions −0.339762, yielding the net −0.234731. The sole positive
founder is **319940 (+0.354004 points)**; the other 15 range from −0.168864 to
−0.547282. That favorable founder is retained, not selected as a new
confirmation cohort.

The procedure changed **526 of 1,536 choices**, affecting **165 cases** at least
once. Among changed choices, test outcomes improved in **188**, worsened in
**276**, and tied in **62**. Of the 95 case-average ties, 91 never changed choice
and 4 contain changes whose effects cancel. These are descriptive counts;
gain/harm magnitudes matter too.

## Families, writers and every partition

| Family/writer | Selection advantage | Test change | Case gains / harms / ties | Changed-decision test gains / harms / ties |
| --- | ---: | ---: | --- | --- |
| A ordinary | +0.287374 | −0.095113 | 12 / 36 / 16 | 50 / 90 / 24 |
| A aligned | +0.202942 | −0.013733 | 13 / 30 / 21 | 65 / 66 / 31 |
| B ordinary | +0.330098 | **−0.823975** | 4 / 34 / 26 | 19 / 72 / 2 |
| B aligned | +0.389608 | −0.006104 | 10 / 22 / 32 | 54 / 48 / 5 |

The largest loss comes from ordinary B. The aligned groups' means are close
to zero; the pooled loss is not strong harm in every subgroup. B aligned has
more improving changed decisions than worsening ones, yet their magnitudes
give a small negative mean. Counts alone do not determine decision value.

| Selection futures → test futures | Test change, points |
| --- | ---: |
| 2,3 → 4,5 | −0.236511 |
| 2,4 → 3,5 | −0.123596 |
| 2,5 → 3,4 | −0.244904 |
| 3,4 → 2,5 | −0.355530 |
| 3,5 → 2,4 | −0.233459 |
| 4,5 → 2,3 | −0.214386 |

Under the native terminal reader, the same actions lose **0.348536 points**:
34.967168 versus the family's 35.315704. Case changes give 32 gains, 133 harms
and 91 ties. This sensitivity agrees in direction but is not an independent
cohort or replacement endpoint. Every founder and individual choice is in the
tables.

## Integrity and computation

All **39 synthetic qualification tests passed**. They cover test-outcome
leakage, exact ties, persistent/transient exceptions, case/founder weighting,
complete rows, score quantization, wrong cohorts, corruption and write
isolation. A separate scalar implementation reconstructs every choice from
source rows and uses rational arithmetic for weighted summaries. It does not
call production selection or aggregation. Mutation tests catch changed choices,
contributions and inflated sample counts.

The **2,148-input freeze** was written at **18:49:48.829335 UTC**. The complete
first-founder timing check took **6.269933 seconds**; conservative full
allowance **135.398661 seconds**. Main completed **18:50:44.895004 UTC** in
**6.725388 seconds**, and separate audit completed **18:51:08.904968 UTC** in
**3.339411 seconds**. Main includes independent checking and saved readback.
These short tasks ran in the foreground under the ten-minute rule; no long
job or polling loop was needed.

All **18,432 source row keys**, 256 cases, six partitions, integer outputs and
rational summaries pass. Frozen family/common/native values and the optimistic
reference bridge back to D199. D199's apparatus controls and physics audit
remain intact; no new control simulation was generated. Actual cohort
membership excludes disposable 519900.

One CPU6/thread, nice10. Total new external retention **1,194,616 bytes
(about 1.14 MiB)**, including qualification, freeze, timing and audit, below
the **64 MiB cap**. All data stay on `/mnt/bioIce1`; only code/docs are local.
Receipts report **1,398.781250 MiB process high-water RSS**. This is not a
measurement of the isolated algorithm's working set; the small output size
does not establish a small peak-memory bound.

## Consequence for the mission

D199 supports a small prospective gain from supplied family-to-recipient
matching. D200 shows that selecting apparent exceptions from two noisy futures
loses value on complementary futures. Keep family matching as the reference
and **park further fine-matcher fitting in this apparatus** unless a new
mechanistic signal or better measurement motivates reopening it.

This does not prove all exceptions are noise or establish autonomous repair,
complete preservation, or the original challenge-over-passive forecast claim.
**L20/L22 remain STRESS_TESTED / MIXED.** No scientific successor has launched.
Any later reopening must retain these negative findings and receive its own
analysis plan or prospective test.
