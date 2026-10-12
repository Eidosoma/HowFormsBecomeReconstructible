# D168 — feedback geometry helps describe the passive-copy imbalance

Completed and freshly audited 2026-09-22. Post-test explanation, not a new
prospective test. [Fixed scope](PROTOCOL_V1.md), [complete tables](TABLES.md),
[execution record](WORKLOG.md), [report checker](check_report.py).

## Plain-language result

The first undisturbed copy was not simply a second identical trial of the
same reconstruction conditions. Both copies inherited the same record, but
their random streams also assigned different spatial shifts to the writer's
feedback. In the development B-pattern cases, U0 received a pattern-opposing
shift in 33 of 64 cases, compared with 18 of 64 for U1. In the larger pilot
the imbalance was smaller and reversed: 79 of 256 versus 92 of 256.

That difference is a concrete lead for the development copy-quality gap.
An exact accounting using the observed shift categories gives a +0.044129
mixture term within the +0.064221 U1-minus-U0 exported-shape gap; a +0.020091
residual remains. In the pilot the corresponding numbers are −0.009341 and
+0.006170, summing to the much smaller observed gap of −0.003171. Opposing
terms can conceal structure in a near-zero average.

This is not proof that the shifts caused those amounts of loss. The copies
also differed in body and noise history, and category means come from these
same data. Nor is it evidence that a challenged observer forecasts better.
It identifies an experimentally testable explanation for a diagnostic
imbalance without changing the germ, guide, predictor or primary result.

## What was measured, and what was not

Retained every one of the 16 development founders 90000–90015 and 64 pilot
founders 100000–100063, all four lives, A/B families, ordinary/aligned writers,
and both undisturbed copies: 2,560 diagnostic copies. No selected cases,
new threshold, challenge copies, fresh founders or additional tissue cycles.

[D167](../passive-stages/RESULTS.md) had localized the persistent development
B-ordinary gap mainly to rewriting. The earlier
[D143 audit](../reviews/CROSSED_ADDRESS_GEOMETRY_2026-09-17.md) had already
established a general feedback-geometry mechanism. D168 asks whether those
existing definitions describe this particular diagnostic-copy imbalance;
it is not a rediscovery or independent replication of D143.

Read the 160 existing raw diagnostic NPZ/JSON files in place
(338,093,200 bytes) and bridged the seven saved diagnostic responses to D167.
No actual main-lineage outcomes, forecast errors, predictor parameters,
development outcome labels or futures were used. “Final preference” below
always means the fresh reader of the diagnostic copy, not the original
record's actual three-replacement endpoint.

The geometry score q is the ideal target's autocorrelation after the assigned
shift. Positive values are pattern-compatible; negative values oppose the
ideal pattern. q=−1 reverses its signs, which does not by itself destroy its
best-translated shape. q=+1 can be a nonzero physical shift. All nine A levels
and five B levels were retained. For aligned writers the assigned shift is
unused: effective shift is zero and effective q is exactly one.

## Assigned geometries differ between copies and cohorts

For B-ordinary development, mean assigned q is −0.1953125 for U0 and
+0.1562500 for U1, a gap of +0.3515625. Founder gaps are positive for 12,
negative for two and numerically zero for two of the 16 founders. Pilot
means are +0.068359375 and +0.0078125, a gap of −0.060546875; 26 founder
gaps are positive, 34 negative and four numerically zero.

Every B level is shown here. Counts are diagnostic lives clustered within
founders, not 64 or 256 independent founder replications. Assignments are
shared across writer groups, so ordinary/aligned rows must not be counted
as extra independent shift assignments.

<!-- d168-table:result-b-levels -->
| Cohort | Group | q | U0 count | U1 count | U0 proportion | U1 proportion | U0 founders | U1 founders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | B_ordinary | -1 | 11 | 6 | 0.171875000 | 0.093750000 | 9 | 6 |
| development | B_ordinary | -0.500000000 | 22 | 12 | 0.343750000 | 0.187500000 | 13 | 9 |
| development | B_ordinary | 0 | 15 | 14 | 0.234375000 | 0.218750000 | 11 | 9 |
| development | B_ordinary | 0.500000000 | 13 | 20 | 0.203125000 | 0.312500000 | 9 | 12 |
| development | B_ordinary | 1 | 3 | 12 | 0.046875000 | 0.187500000 | 2 | 9 |
| pilot | B_ordinary | -1 | 27 | 29 | 0.105468750 | 0.113281250 | 23 | 21 |
| pilot | B_ordinary | -0.500000000 | 52 | 63 | 0.203125000 | 0.246093750 | 37 | 46 |
| pilot | B_ordinary | 0 | 71 | 75 | 0.277343750 | 0.292968750 | 47 | 49 |
| pilot | B_ordinary | 0.500000000 | 71 | 53 | 0.277343750 | 0.207031250 | 49 | 41 |
| pilot | B_ordinary | 1 | 35 | 36 | 0.136718750 | 0.140625000 | 28 | 26 |
<!-- d168-end -->

Support is unequal: for example, development U0 has only three q=+1 cases.
There are no empty or one-copy-only categories in the actual data, although
the implementation and tests preserve such cases. Conditional exported-own
means and supporting-founder counts for every group/level are in the
[complete tables](TABLES.md). They include within-category reversals; the
development pooled means are not strictly monotonic in q. They are not
noise-matched estimates of an intervention effect.

## Shape gap: mixture accounting plus a retained residual

For each cohort, group and response, pool both copies to form the observed
conditional mean mu(q). The observed gap G is U1 minus U0. Define
M=sum_q[(p1(q)−p0(q))*mu(q)] and residual R=G−M. This is exact descriptive
accounting, independently verified both through category sums and through
the response residuals Y−mu(q).

The following table retains every group's exported-record own-best shape
response. Values are correlation units, not success percentages. Omission
ranges remove one founder from the score while holding the full-cohort
mu(q) fixed. The omitted founder therefore remains in the reference profile:
these are sensitivity checks, not cross-validation or uncertainty intervals.

<!-- d168-table:result-own-mixture -->
| Cohort | Group | Response | Gap | Mixture term | Residual | Omit gap min | Omit gap max | Omit residual min | Omit residual max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | A_ordinary | outgoing_own | 0.001787617 | 0.006040810 | -0.004253193 | -0.000583686 | 0.003530165 | -0.005726163 | -0.002183079 |
| development | A_aligned | outgoing_own | 0.000695108 | -0.000001621 | 0.000696729 | -0.000101722 | 0.001227615 | 0.000175023 | 0.001115687 |
| development | B_ordinary | outgoing_own | 0.064220607 | 0.044129115 | 0.020091492 | 0.049349970 | 0.071497088 | 0.014223793 | 0.024426032 |
| development | B_aligned | outgoing_own | 0.000548166 | -0.001617918 | 0.002166084 | -0.000859135 | 0.002741181 | -0.000634895 | 0.004761108 |
| pilot | A_ordinary | outgoing_own | -0.000415223 | -0.001868695 | 0.001453472 | -0.001165183 | 0.000356919 | 0.001005696 | 0.002022317 |
| pilot | A_aligned | outgoing_own | -0.000118778 | -0.000126423 | 0.000007645 | -0.000512871 | 0.000207575 | -0.000386932 | 0.000278305 |
| pilot | B_ordinary | outgoing_own | -0.003171086 | -0.009340598 | 0.006169512 | -0.005443224 | 0.000345101 | 0.004063070 | 0.008228274 |
| pilot | B_aligned | outgoing_own | 0.003061743 | -0.001261944 | 0.004323687 | 0.002388833 | 0.003704968 | 0.003704633 | 0.004941743 |
<!-- d168-end -->

The development B-ordinary residual stays positive under every such
single-founder omission (+0.014224 to +0.024426). Shift-category mixture
alone is therefore not a complete account of this exported-shape gap.
The corresponding pilot residual also stays positive (+0.004063 to
+0.008228), while its mixture term is negative. Neither the near-zero pilot
total nor omission ranges establish equivalence.

At writer300, the development B-ordinary gap in *change from each copy's
writer-start shape* is +0.084093, with M=+0.083438 and R=+0.000656. At
writer1000 these are +0.058205, +0.047640 and +0.010564. These change scores
are distinct from D167's raw checkpoint-shape gaps. For diagnostic fresh-reader
preference the development values are +0.032288, +0.028300 and +0.003988;
pilot values are −0.000397, −0.005513 and +0.005116. Every response, including
zero change at writer0 and unfavorable rows, remains in the complete tables.

The ordinary A and aligned groups do not show the same large development
exported-shape gap. An aligned group's unused assigned q can still have a
nonzero mixture term or correlation because its finite diagnostic copies
have different noise and support. That is an important demonstration of
why this decomposition must not be called causal mediation or a percentage
of damage explained.

## Actual feedback alignment supports the lead, with a timing limitation

Native theta at writer1 closely tracks the current reference R in all four
B-ordinary copy/cohort averages (correlations approximately 0.9995). After
applying the assigned spatial shift, development means differ sharply:
−0.157794 for U0 versus +0.139103 for U1. Pilot means are +0.079470 versus
+0.001798. Thus the difference is visible in the actual saved feedback field,
not solely in the ideal-template category.

<!-- d168-table:result-b-alignment -->
| Cohort | Group | Step | Measurement | U0 mean | U1 mean | Paired gap | Pairs | U0 valid | U1 valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | B_ordinary | 0 | theta_applied_R | undefined | undefined | undefined | 0 | 0 | 0 |
| development | B_ordinary | 1 | theta_applied_R | -0.157793647 | 0.139103341 | 0.296896988 | 64 | 64 | 64 |
| development | B_ordinary | 300 | theta_applied_R | 0.681488830 | 0.755478435 | 0.073989605 | 64 | 64 | 64 |
| development | B_ordinary | 1000 | theta_applied_R | 0.746701712 | 0.801788649 | 0.055086936 | 64 | 64 | 64 |
| pilot | B_ordinary | 0 | theta_applied_R | undefined | undefined | undefined | 0 | 0 | 0 |
| pilot | B_ordinary | 1 | theta_applied_R | 0.079469852 | 0.001797733 | -0.077672119 | 256 | 256 | 256 |
| pilot | B_ordinary | 300 | theta_applied_R | 0.741143986 | 0.721723684 | -0.019420302 | 256 | 256 | 256 |
| pilot | B_ordinary | 1000 | theta_applied_R | 0.792163802 | 0.776615014 | -0.015548788 | 256 | 256 | 256 |
<!-- d168-end -->

The crucial temporal qualification is fixed in the protocol: the body at
step t is updated using theta(t−1), and only then is theta(t) updated and
saved. The table measures feedback available for step t+1, not necessarily
the input that caused the just-completed body change. Theta(1000) is not
applied again inside this completed diagnostic cycle. No extra step was run.

Theta0 is constant zero; its correlations are undefined, not measured zeros.
At later checkpoints both copies' applied feedback becomes positively
aligned with their current reference. That can include agreement with an
already altered state and is not proof that the original shape survived.
All reference autocorrelations, native/applied theta correlations with R
and V, differences, validity masks and founder contributions are retained.

## Paired associations: useful description, not a new prediction result

Across paired B-ordinary lives, the correlation between the U1-minus-U0
assigned-q difference and the exported-own difference is 0.747840 in
development and 0.659651 in the pilot. The corresponding descriptive slopes
are 0.147476 and 0.109068 correlation units per q unit. There are 64 and
256 paired lives respectively, clustered within 16 and 64 founders.

Start-reference compatibility has correlations 0.508011 and 0.498805;
actual applied theta/R alignment at writer1 has correlations 0.508607 and
0.499442. All four descriptors and seven responses for every group appear
in the complete tables, including undefined constant-descriptor statistics.

In B-aligned, correlations with the unused assigned q are 0.109346 and
0.055685; effective q is constant, so its slope and correlation are undefined.
No confidence intervals or p-values were registered for these descriptions.
No incremental forecast contest was performed, and these associations cannot
separate the effects of address, body history and noise.

## Verification, cost and provenance

All 39 qualification tests passed in 34.07 seconds. These include all 255
legal nonzero shifts, independent closed-form geometry and modular-index
correlations, constant fields, writer timing, aligned controls, copy reversal,
founder permutations, unequal/empty categories, mixture cancellation and
normalization, corrupted artifacts, forbidden outcome access and detached
execution safeguards. The complete synthetic 16/64 panel took 26.9749 seconds.

Frozen at 2026-09-22T16:42:10.682391+00:00, before extracting the actual new
geometry measurements. The conservative execution budget was 204.18 seconds,
below the 600-second detached threshold. Main analysis completed at
16:44:21.617408 UTC in 33.61 seconds; the separate fresh audit completed at
16:45:36.697902 UTC in 21.47 seconds.

The fresh audit passed all 311 input and three output hashes and independently
checked 66,560 geometry values, 61,440 validity flags, 17,920 responses and
all 608 scientific summary rows. Maximum measurement discrepancy was
7.77e−16; all 56 D167 group/response-gap bridges passed. Every founder and
diagnostic copy was retained.

Scientific output is 7,128,613 bytes (6.798 MiB); preserved qualification
fixtures add 6,744,154 bytes (6.432 MiB), plus small logs/receipts. No raw
archive was copied. All data, fixtures, logs, receipts and caches are under
the external root below; only code/docs are in this repository folder.
Affinity was limited to CPUs 0–5 with one numerical-library thread.
No automatic polling, retry or successor job; no active job at closeout.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`

Run identifier: `l20_extension1_passive_feedback_v1_attempt1`.

Relative external artifacts:

- `runs/l20_extension1_passive_feedback_v1_attempt1/COMPLETE.json`
- `runs/l20_extension1_passive_feedback_v1_attempt1/MANIFEST.json`
- `tmp/l20_extension1_passive_feedback_v1_attempt1_freeze.json`
- `logs/d168_qualification_v1.xml`
- `logs/l20_extension1_passive_feedback_v1_attempt1_saved_audit_v1.json`
- `outputs/l20_extension1_passive_feedback_v1_attempt1/geometry.npz`
- `outputs/l20_extension1_passive_feedback_v1_attempt1/summary.json`
- `outputs/l20_extension1_passive_feedback_v1_attempt1/verification.json`

SHA256:

- COMPLETE: `155f95991d4dc718ca6f0a16d0c7e0e8bd5d10de73670449bd363a689facd9e5`.
- Fresh audit: `a581f332021deb269ece4fc52cbd7486ec0a859c68d17b6b5a10eea8e870a23e`.
- Freeze: `30595a834c1264689e21f16417ae7fa1f0071eca6d5ef6a0c465952e95b151c8`.
- Summary: `1e6374db03784273363e789a7440f69d7543b39fc436949562005f3bea5930bd`.

[The documentation checker](check_report.py) separately verifies all nine
numeric tables (1,346 rows), local links, source/output hashes and the
arithmetic bridges, and can write a write-once receipt under
`logs/l20_extension1_passive_feedback_v1_attempt1_documentation_v1.json`.
The source protocol, implementation, independent checker, executor and
qualification tests remain frozen.

## Law status and a bounded next question

L20 remains **STRESS_TESTED / MIXED**. D141's original prospective comparison
and [D162's pilot](../confirmation/PILOT64_RESULTS.md) remain unresolved.
D162's challenge primary was 0.045281% worse than passive, with a gain interval
of [−0.399249, +0.322641]% of reference MSE; both beat starting-only by about
4%. D168 neither replaces that primary nor establishes a challenge benefit,
autonomous repair, complete shape preservation or real-biological heredity.
This tissue carrier is 2,048 bytes, not the earlier DoorKey 64-byte germ.

The useful next proposal is a matched address-swap replay of these diagnostic
writers, not another broad geometry search. For each existing copy, preserve
its read-end body and writer/fresh-reader random streams, but exchange U0/U1's
assigned feedback shifts. Include reproduction under the original addresses
and aligned-writer unused-address controls, retain both families and every
founder, and compare what follows the shifted address versus the fixed
body/noise history. This can isolate the address-assignment contribution in
this specific imbalance; it would not validate the original prediction claim.

That successor needs its own fixed scope, replay qualification and measured
budget before any main execution. It is only a proposal here: no replay,
new protocol, new forecast or successor job has been launched.
