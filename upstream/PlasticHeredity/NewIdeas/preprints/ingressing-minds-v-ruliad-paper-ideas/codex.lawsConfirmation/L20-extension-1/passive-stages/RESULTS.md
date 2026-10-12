# D167 — most of the persistent passive-copy imbalance grows during rewriting

Completed and freshly audited 2026-09-22. User-authorized follow-up to
[D166](../feature-support/RESULTS.md). [Protocol](PROTOCOL_V1.md),
[all tables](TABLES.md), [execution record](WORKLOG.md),
[documentation checker](check_report.py).

## Result in plain language

The two undisturbed copies start with the same inherited record. In the
development sample's B-family ordinary-writer condition, they finish the
initial read fairly close in shape quality. During rewriting, the first copy
loses substantially more of the target shape. Some of that difference recovers,
but a sizable gap remains in the exported record and its fresh diagnostic
reader. Exporting/normalizing the record does not create the large gap.

This is not just one bad founder: 11 of 16 development founders favor the
second copy on exported shape correlation, and the mean gap stays positive
after every single-founder score-only omission. But it is not universal:
five founders favor the first copy, and the 64-founder pilot has no comparable
average gap. Individual pilot copy differences remain substantial.

Aligned writing begins from exactly the same reader states but has a much
smaller development copy gap. The useful lead is therefore the ordinary
writer's dynamics and spatially shifted feedback. This audit locates where
the sample imbalance grows; it does not yet establish why particular copies
degrade, or that a challenge improves prediction.

## Scope and measurement

All 16 development founders 90000–90015 and 64 pilot founders 100000–100063,
all four lives and four family/writer groups. U0 and U1 are the two
undisturbed diagnostic copies, with identical incoming bytes and different
diagnostic random streams. Ordinary means the source's translated writer.

48 saved fields per copy: input/routed packets; every saved V, ema, R and
writer theta checkpoint; tanh(final writer R); outgoing/routed outgoing
packets; and the fresh reader's checkpoints. Five fixed measurements per
field, plus final-reader qualified preference at all four saved times.
No cherry-picked checkpoint or newly chosen survival threshold.

Own-best is continuous target-shape correlation after the best translation,
not a success rate. The guide margin and canonical margin are distinct;
canonical measurements stay in the current field's coordinates. The export
is centered, SD-0.3-scaled tanh(final writer R), not the stored writer theta.

Actual three-replacement outcomes, prediction errors and predictor coefficients
were not used. No challenge copies are analyzed. No new model, forecast,
simulation, founder or diagnostic cycle. Earlier outcome-containing files
were hash-checked for provenance only; their outcome members were not read.

## Exported-record comparison, all groups

Gap = U1 minus U0; positive means the second copy has higher correlation.
Gap change = pilot gap minus development gap. All values below are raw
correlations, not percentages of successful reconstruction.

<!-- d167-table:result-endpoints -->
| Group | Stage / transition | Measurement | Dev U0 | Dev U1 | Dev gap | Pilot U0 | Pilot U1 | Pilot gap | Gap change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_ordinary | outgoing | own_best | 0.936719110 | 0.938506728 | 0.001787617 | 0.938495019 | 0.938079795 | -0.000415223 | -0.002202841 |
| A_aligned | outgoing | own_best | 0.937727853 | 0.938422961 | 0.000695108 | 0.943148082 | 0.943029303 | -0.000118778 | -0.000813886 |
| B_ordinary | outgoing | own_best | 0.704699363 | 0.768919970 | 0.064220607 | 0.775451487 | 0.772280401 | -0.003171086 | -0.067391693 |
| B_aligned | outgoing | own_best | 0.771679422 | 0.772227588 | 0.000548166 | 0.805059413 | 0.808121156 | 0.003061743 | 0.002513577 |
<!-- d167-end -->

The distinctive persistent development gap is B ordinary: **0.064221**,
versus **0.000548** for B aligned. In the pilot those gaps are **−0.003171**
and **+0.003062**. Small cohort means are not equivalence: the B-ordinary
pilot mean absolute founder gap is **0.053868**, with founder gaps ranging
from **−0.224691 to +0.139974**.

## Where the B-ordinary gap grows

The complete packet/reference path is below; all other body and feedback
fields are retained in the [full tables](TABLES.md).

<!-- d167-table:result-reference-path -->
| Group | Stage / transition | Measurement | Dev U0 | Dev U1 | Dev gap | Pilot U0 | Pilot U1 | Pilot gap | Gap change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B_ordinary | input | own_best | 0.823529598 | 0.823529598 | 0 | 0.852278540 | 0.852278540 | 0 | 0 |
| B_ordinary | routed | own_best | 0.823529598 | 0.823529598 | 0 | 0.852278540 | 0.852278540 | 0 | 0 |
| B_ordinary | read:0:R | own_best | 0.086800565 | 0.084345527 | -0.002455038 | 0.083591287 | 0.087546737 | 0.003955451 | 0.006410488 |
| B_ordinary | read:1:R | own_best | 0.086823368 | 0.084530445 | -0.002292923 | 0.083588630 | 0.087624996 | 0.004036365 | 0.006329288 |
| B_ordinary | read:100:R | own_best | 0.496071261 | 0.520217772 | 0.024146511 | 0.523323040 | 0.528529288 | 0.005206248 | -0.018940264 |
| B_ordinary | read:101:R | own_best | 0.499606026 | 0.523609774 | 0.024003748 | 0.527005271 | 0.532200931 | 0.005195660 | -0.018808088 |
| B_ordinary | read:300:R | own_best | 0.760946443 | 0.767127018 | 0.006180575 | 0.792083828 | 0.794186046 | 0.002102219 | -0.004078356 |
| B_ordinary | write:0:R | own_best | 0.760946443 | 0.767127018 | 0.006180575 | 0.792083828 | 0.794186046 | 0.002102219 | -0.004078356 |
| B_ordinary | write:1:R | own_best | 0.761263463 | 0.767372123 | 0.006108661 | 0.792365519 | 0.794452037 | 0.002086518 | -0.004022143 |
| B_ordinary | write:300:R | own_best | 0.618733669 | 0.709007637 | 0.090273968 | 0.705992932 | 0.699325233 | -0.006667700 | -0.096941668 |
| B_ordinary | write:1000:R | own_best | 0.700754636 | 0.765139977 | 0.064385341 | 0.770595499 | 0.768615198 | -0.001980302 | -0.066365643 |
| B_ordinary | tanh_write_R | own_best | 0.704699363 | 0.768919970 | 0.064220607 | 0.775451487 | 0.772280401 | -0.003171086 | -0.067391693 |
| B_ordinary | outgoing | own_best | 0.704699363 | 0.768919970 | 0.064220607 | 0.775451487 | 0.772280401 | -0.003171086 | -0.067391693 |
| B_ordinary | terminal_packet | own_best | 0.704699363 | 0.768919970 | 0.064220607 | 0.775451487 | 0.772280401 | -0.003171086 | -0.067391693 |
<!-- d167-end -->

There is already a transient first-reader difference: the development gap
reaches 0.024147 at read step 100, then shrinks to **0.006181** by read
step 300. Read-end R and writer-start R are exactly the same stored field.

The much larger persistent imbalance emerges during ordinary writing:
gap **0.006109** at writer step 1, **0.090274** at step 300, then **0.064385**
at step 1000. The first copy falls from own correlation 0.760946 at writer
start to 0.618734 at step 300; the second falls from 0.767127 to 0.709008.
Both later recover partly. Sparse checkpoints do not identify an exact onset.

Applying tanh changes the gap only to **0.064221**. Centering, positive
rescaling and final guide routing leave these best-correlation and best-guide
measurements unchanged to numerical precision. The final guide-margin gap
is **0.075311**, already **0.075787** in the final writer R. The large endpoint
difference is thus present before the export normalization/routing.

The pilot's corresponding reference gaps are **0.002102** after reading,
**−0.006668** at writer step 300, **−0.001980** at writer step 1000, and
**−0.003171** in the outgoing record. It does not reproduce the same average
first-copy disadvantage; that does not establish equality of the cohorts.

## How widespread is it?

Founder gaps average all four lives. Numerical-zero means abs(gap)<=1e-12;
that tolerance is not a biological or survival threshold. Omission values
are sensitivity calculations only: every founder remains in the reported
mean. The largest absolute share uses the sum of absolute founder gaps,
not the canceling net gap.

<!-- d167-table:result-concentration -->
| Cohort | Group | Positive | Negative | Numerical zero | Largest abs founder | Share of absolute gap | Omission minimum | Omission maximum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | A_ordinary | 6 | 10 | 0 | 90005 | 0.160954525 | -0.000583686 | 0.003530165 |
| development | A_aligned | 8 | 8 | 0 | 90013 | 0.162350413 | -0.000101722 | 0.001227615 |
| development | B_ordinary | 11 | 5 | 0 | 90001 | 0.224034244 | 0.049349970 | 0.071497088 |
| development | B_aligned | 10 | 6 | 0 | 90014 | 0.145372481 | -0.000859135 | 0.002741181 |
| pilot | A_ordinary | 37 | 27 | 0 | 100032 | 0.058640681 | -0.001165183 | 0.000356919 |
| pilot | A_aligned | 33 | 31 | 0 | 100025 | 0.056499025 | -0.000512871 | 0.000207575 |
| pilot | B_ordinary | 30 | 34 | 0 | 100050 | 0.065174282 | -0.005443224 | 0.000345101 |
| pilot | B_aligned | 36 | 28 | 0 | 100057 | 0.062499296 | 0.002388833 | 0.003704968 |
<!-- d167-end -->

For development B ordinary, 11 founders favor U1 and five favor U0.
Founder 90001 contributes the largest absolute gap, **22.40% of the sum of
absolute gaps**, but dropping it from the score calculation still leaves
a **0.049350** mean gap. Across every single-founder omission the mean spans
**0.049350–0.071497**, always positive. This rules out a *single-founder-only*
description of this sample; it is not a population significance test.

For pilot B ordinary, 30 founders favor U1 and 34 favor U0. Single-founder
omission means span **−0.005443 to +0.000345**, crossing zero. Neither cohort
is treated as a collection of independent lives or diagnostic copies.
[Every founder/group row](TABLES.md) is available, with no exclusions.

## Important cross-checks and limits

Aligned and ordinary writers share identical initial reader traces, writer
starting bodies, and writer step-1 states within each family/copy. The large
development B-ordinary gap is not inherited from a different aligned-reader
input: aligned B's writer-step-300 gap is **0.003147**, ending at **0.000548**
after export. That localizes the divergence to the subsequent writer paths.
It does not separate the effects of feedback address, evolving state and
particular random fluctuations.

A ordinary also has a temporary writer imbalance: development gap **0.021541**
at step 300, shrinking to **0.001788** after export. Its pilot values are
**−0.011028** and **−0.000415**. Thus the observation is not that only B can
diverge during writing; B ordinary retains a much larger development gap.

The fresh diagnostic reader reflects some of the B-ordinary difference:
development preference **0.260803 versus 0.293091** (U1–U0 **0.032288**),
with 13/16 positive founder gaps. Pilot preference is **0.296295 versus
0.295898** (gap **−0.000397**), 32/64 positive. These are diagnostic readers,
not the actual later lineages. There is no outcome/error join in this audit.

No confidence intervals, equivalence claims or new prospective evidence.
No causal decomposition follows from telescoping stage differences. Shared
guide, supplied families/addresses, fixed tissue model and finite cohorts
remain limitations. D141/D162 remain unresolved and L20 remains
**STRESS_TESTED / MIXED**. In particular, this does not demonstrate autonomous
repair, learned ontology, complete shape preservation or a challenge advantage.

## Verification and cost

38 synthetic qualification tests passed in 79.70 seconds; the complete
16/64-panel extraction/check/save/summary roundtrip took 63.373747 seconds.
The fixed 337.532081-second conservative budget was below ten minutes, so
both real stages ran attached, one numerical thread, affinity CPUs 0–5.

The main run finished at 16:11:53 UTC in **67.782153 seconds**.
A separate saved-output audit finished at 16:14:04 UTC in **37.695723 seconds**.
All **291 input hashes and three output hashes** pass, including 160 raw
diagnostic archives bound to D162's earlier full physical audit. The raw
archives total 338,093,200 bytes; they were not duplicated.

Independent direct translated-template products checked production FFT
measurements: **122,880 fields / 614,400 measurements**, maximum discrepancy
**1.6653345369377348e-15**. Also checked **10,240 preference measurements**,
**5,120 packet routes**, writer-start continuity, record construction,
every saved initial/endpoint value, and **128 D166 aggregate means**.
All **960 field rows, 260 transition rows and 16 preference rows** and their
founder/omission accounting pass. This is saved algebra, not a new physics run.

The separate documentation check verifies seven tables / 1,582 numeric rows
and 11 local links, with fresh mean/gap arithmetic and source/output hashes.

Main outputs: **19,913,334 bytes / 18.990835 MiB** on the external drive.
The preserved full qualification fixtures add **19,286,626 bytes** there.
Code and Markdown only here. No background job or automatic successor.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.

Run: `l20_extension1_passive_stages_v1_attempt1`.
Outputs are `outputs/<run>/stages.npz`, `summary.json`, `verification.json`;
receipts are `runs/<run>/COMPLETE.json`, `MANIFEST.json`,
`logs/<run>_saved_audit_v1.json`, and `tmp/<run>_freeze.json`.

- COMPLETE SHA256: `f77af997a198b1fae48ca9cbce96dfa64eb746ce635de08d8f777d7737a2aa99`.
- Saved audit SHA256: `5e652602b46f3d84cacf6cc32d485387b95e6eb3610b82f222b9ccc9ce972d0d`.
- Freeze SHA256: `adc17fc2d7e5c63ef26328f51187f9e557b3429962bd1ed9b332811911a6a6a1`.
- Summary SHA256: `96dca17eb647e96361e827b79c86891de304caf2ba571fe1cdaf5168a78863cd`.

## Recommended next lead — not launched

Audit how the ordinary writer's **applied, spatially shifted feedback** aligns
with the current body/reference at the saved checkpoints. Retain both copies,
all founders/groups and all declared checkpoints, including negative cases;
compare the aligned condition without selecting a favorable shift subset.

That would test a specific descriptive lead for the amplification before
considering a separately frozen, matched-state/noise intervention. A causal
replay would need its own scope and qualification. Do not change the existing
predictors, replace the first copy, tune a new challenge or discard founders.
