# D169 — exchanging feedback locations reverses the development copy gap

Completed and freshly audited; write-up 2026-09-23.
[Fixed protocol](PROTOCOL_V1.md), [complete tables](TABLES.md),
[execution record](WORKLOG.md), [documentation checker](check_report.py).

## Plain-language result

We can now go beyond saying that two diagnostic copies happened to receive
different feedback locations. We exchanged those locations while keeping
each copy's starting body and random disturbances unchanged.

In the development B-pattern/ordinary-writer group, the second copy's
exported shape originally scored **0.064221 higher** than the first.
After the exchange, it scored **0.051300 lower**. Giving the first copy the
second copy's feedback location improved its score; giving the second copy
the first location worsened its score. This is a controlled causal result
inside the simulated reconstruction mechanism, conditional on these saved
bodies, random streams and fixed guide.

The larger pilot does not have the same average imbalance: its matched
address effect is −0.004903, with a pointwise 95% founder interval from
−0.021431 to +0.011262. That is unresolved, not proof of no effect.
The development result is also not universal: its address effect is
positive in 11 of 16 founders and negative in five.

This closes a specific explanatory gap in the diagnostic apparatus. It
does **not** show that a challenged observer predicts long-term survival
better. No new predictor or actual three-replacement outcome was used.

## What changed and what stayed fixed

This is the intervention proposed after
[D167's stage localization](../passive-stages/RESULTS.md) and
[D168's feedback-geometry accounting](../passive-feedback/RESULTS.md).
The earlier [D143 geometry audit](../reviews/CROSSED_ADDRESS_GEOMETRY_2026-09-17.md)
already showed a general feedback-placement mechanism. D169's contribution
is to test that explanation for these particular undisturbed-copy imbalances.

All 16 development founders 90000–90015 and 64 pilot founders
100000–100063 were retained, with four lives, both target families and
ordinary/aligned writers. No favorable-copy selection, new founders,
challenge changes or outcome-based exclusions. The carrier is the existing
2,048-byte tissue record, not the separate DoorKey 64-byte germ.

For each life/group, Y[c,a] uses saved body/noise background c and the
writer-feedback shift assigned to donor a. The four cells are:

- Y00: original U0 body/noise with U0's shift.
- Y01: that same U0 body/noise with U1's shift.
- Y10: original U1 body/noise with U0's shift.
- Y11: that same U1 body/noise with U1's shift.

Each arm starts from its body's saved read-end V, ema and R, with zero
writer theta. It reuses that body's original writer noise and fresh-reader
birth/read streams, for 1,000 writer steps and 300 fresh-reader steps.
No initial reader is rerun. Only the assigned feedback displacement changes
within a background. Incoming records, writer rules and guide are unchanged;
the guide routes each changed outgoing packet normally, so its downstream
routing decision is allowed to change. The writer itself has no access to
the target, guide or incoming packet; targets enter only the observer metrics.

Every diagonal arm reproduced its original saved checkpoints, packets,
routing scores and metadata. Aligned writers ignore assigned displacement:
their full paths and outputs must be identical across donors. All arms
within one background also share writer0/1 and the final reader's birth
state. All equal-shift and equal-q cases remain included.

## Primary mechanistic contrast: development B ordinary

The focus was fixed before the new main counterfactuals, after seeing the
earlier studies. It is therefore a post-test mechanistic follow-up, not a
new prospectively selected prediction result. The pilot counterpart is
reported separately, without pooling the two cohorts.

The following are exported-record best-own shape correlations. They are
correlation units, not success percentages or a claim of complete fidelity.

<!-- d169-table:result-b-cells -->
| Cohort | Group | Response | Y00 | Y01 | Y10 | Y11 |
| --- | --- | --- | --- | --- | --- | --- |
| development | B_ordinary | outgoing_own | 0.704699363 | 0.763979699 | 0.712679897 | 0.768919970 |
| pilot | B_ordinary | outgoing_own | 0.775451487 | 0.771514194 | 0.778148349 | 0.772280401 |
<!-- d169-end -->

Development U0 improves by +0.059280 when given U1's shift; U1 worsens
by −0.056240 when given U0's shift. Thus this cohort's U1-assigned shifts
help both fixed backgrounds on average. Neither the U1 label nor its
shifts are intrinsically better: the donor labels identify finite draws.

Define original gap G=Y11−Y00 and swapped gap S=Y10−Y01.
The matched address contrast A=((Y01−Y00)+(Y11−Y10))/2 and bundled
background contrast B=((Y10−Y00)+(Y11−Y01))/2 give exact identities
G=A+B and S=B−A. The interaction is I=(Y11−Y10)−(Y01−Y00).
E0 and E1 are the two within-background donor1-minus-donor0 effects;
actual swap effects are E0 and −E1.

<!-- d169-table:result-b-contrasts -->
| Cohort | Group | Response | Contrast | Mean | 95% low | 95% high | Positive | Negative | Zero | Omit min | Omit max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | B_ordinary | outgoing_own | original_gap | 0.064220607 | 0.025942374 | 0.105880373 | 11 | 5 | 0 | 0.049349970 | 0.071497088 |
| development | B_ordinary | outgoing_own | swapped_gap | -0.051299802 | -0.093661042 | -0.012138470 | 6 | 10 | 0 | -0.059117623 | -0.036850589 |
| development | B_ordinary | outgoing_own | address | 0.057760205 | 0.019884937 | 0.099184495 | 11 | 5 | 0 | 0.043100280 | 0.064179622 |
| development | B_ordinary | outgoing_own | background | 0.006460402 | -0.000934901 | 0.013522782 | 11 | 5 | 0 | 0.005061999 | 0.008315731 |
| development | B_ordinary | outgoing_own | interaction | -0.003040263 | -0.010889706 | 0.004759157 | 7 | 9 | 0 | -0.005193448 | -0.001232847 |
| development | B_ordinary | outgoing_own | address_at_U0 | 0.059280336 | 0.022298445 | 0.099087863 | 11 | 5 | 0 | 0.045697004 | 0.065935762 |
| development | B_ordinary | outgoing_own | address_at_U1 | 0.056240073 | 0.017258203 | 0.099984558 | 11 | 5 | 0 | 0.040503556 | 0.063209590 |
| pilot | B_ordinary | outgoing_own | original_gap | -0.003171086 | -0.020848659 | 0.013960885 | 30 | 34 | 0 | -0.005443224 | 0.000345101 |
| pilot | B_ordinary | outgoing_own | swapped_gap | 0.006634156 | -0.009284573 | 0.022613266 | 35 | 29 | 0 | 0.003822305 | 0.009160105 |
| pilot | B_ordinary | outgoing_own | address | -0.004902621 | -0.021430730 | 0.011262495 | 31 | 33 | 0 | -0.007301665 | -0.001738602 |
| pilot | B_ordinary | outgoing_own | background | 0.001731535 | -0.001697967 | 0.005271009 | 32 | 32 | 0 | 0.001086755 | 0.002144340 |
| pilot | B_ordinary | outgoing_own | interaction | -0.001930655 | -0.006099670 | 0.002316496 | 28 | 36 | 0 | -0.002687700 | -0.001341001 |
| pilot | B_ordinary | outgoing_own | address_at_U0 | -0.003937293 | -0.020292488 | 0.012145392 | 30 | 34 | 0 | -0.006281595 | -0.000811217 |
| pilot | B_ordinary | outgoing_own | address_at_U1 | -0.005867948 | -0.022607756 | 0.010558372 | 30 | 34 | 0 | -0.008321735 | -0.002665987 |
<!-- d169-end -->

For development, G=+0.064221 decomposes into matched A=+0.057760 and
B=+0.006460. The address interval [+0.019885,+0.099184] excludes zero;
the background and interaction intervals include zero. This does not
prove that background or interaction effects are absent in individual
cases. B combines the starting body and all retained copy-specific noise;
it does not isolate record quality or one noise phase. No ratio A/G or
“percentage of causation explained” is reported.

The address mean stays positive under every single-founder omission
(+0.043100 to +0.064180); both original and reversed swapped gap signs
also survive these omissions. That rules out dependence on just one
founder for the observed sign, not all sampling or modeling uncertainty.

In the pilot, A=−0.004903 and B=+0.001732 sum to the small original gap
−0.003171. Address effects are positive in 31 of 64 founders and negative
in 33. Its address mean stays negative in all single-founder omissions
(−0.007302 to −0.001739), yet its bootstrap interval includes zero.
Omission robustness and an unresolved interval are compatible; neither
establishes equivalence or a universal negative effect.

Uncertainty uses 20,000 whole-founder bootstrap resamples after averaging
four lives within a founder, with frozen seeds 16920260922/16920260923.
Intervals are pointwise, not multiplicity-adjusted. The 64 or 256 lives
per group are not independent founder replications. Shared group shift
assignments are not extra independent address draws.

## Where the effect appears, and whether it survives a fresh reading

The seven fixed responses remain visible below. The four writer responses
are changes from each background's own writer0 correlation, not D167's
raw checkpoint-shape gaps. outgoing_guide is the outgoing packet's
own-minus-alternative guide margin. final_preference means the fresh
*diagnostic* reader's qualified own-minus-alternative preference.

<!-- d169-table:result-b-stages -->
| Cohort | Response | Original gap | Swapped gap | Address | Address low | Address high | Background | Interaction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | write_R_change:0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| development | write_R_change:1 | -0.000071914 | -0.000071914 | 0 | 0 | 0 | -0.000071914 | 0 |
| development | write_R_change:300 | 0.084093394 | -0.094247869 | 0.089170631 | 0.037129285 | 0.149614081 | -0.005077238 | 0.005754362 |
| development | write_R_change:1000 | 0.058204767 | -0.057603874 | 0.057904320 | 0.020680322 | 0.099046605 | 0.000300446 | -0.002885356 |
| development | outgoing_own | 0.064220607 | -0.051299802 | 0.057760205 | 0.019884937 | 0.099184495 | 0.006460402 | -0.003040263 |
| development | outgoing_guide | 0.075310593 | -0.066942164 | 0.071126378 | 0.024885627 | 0.121885432 | 0.004184215 | -0.006072880 |
| development | final_preference | 0.032287598 | -0.046447754 | 0.039367676 | 0.017395020 | 0.064300537 | -0.007080078 | -0.007080078 |
| pilot | write_R_change:0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| pilot | write_R_change:1 | -0.000015701 | -0.000015701 | 0 | 0 | 0 | -0.000015701 | 0 |
| pilot | write_R_change:300 | -0.008769919 | 0.005238743 | -0.007004331 | -0.037673402 | 0.023025608 | -0.001765588 | 0.001482983 |
| pilot | write_R_change:1000 | -0.004082521 | 0.003707502 | -0.003895011 | -0.020542093 | 0.012306364 | -0.000187509 | -0.002197319 |
| pilot | outgoing_own | -0.003171086 | 0.006634156 | -0.004902621 | -0.021430730 | 0.011262495 | 0.001731535 | -0.001930655 |
| pilot | outgoing_guide | -0.000293137 | 0.008870805 | -0.004581971 | -0.025385566 | 0.015663237 | 0.004288834 | -0.005571245 |
| pilot | final_preference | -0.000396729 | 0.008621216 | -0.004508972 | -0.014923096 | 0.005699158 | 0.004112244 | 0.002182007 |
<!-- d169-end -->

At writer0 all change scores are zero by definition. At writer1 the
address effect is exactly zero because initial feedback is zero; the
small background difference need not be zero. By the saved writer300
checkpoint, development B-ordinary's address effect on shape change is
+0.089171, falling to +0.057904 at writer1000. These snapshots do not
locate the first onset between saved checkpoints.

The development effect continues through export and fresh reading:
outgoing guide-margin A=+0.071126, interval [+0.024886,+0.121885];
diagnostic preference A=+0.039368, interval [+0.017395,+0.064301].
The latter is about 3.94 preference points, not an increase in three-
replacement lineage success. Its original preference gap +0.032288
reverses to −0.046448 under the swap.

Pilot B-ordinary address intervals include zero at both later writer
checkpoints, export, guide margin and final diagnostic preference. This
prevents treating the development average as a generally better donor
identity or as evidence of a new reliable forecast.

## Other groups, engineered controls and complete support

Every group's exported-own comparison is retained:

<!-- d169-table:result-own-controls -->
| Cohort | Group | Original gap | Swapped gap | Address | Address low | Address high | Background | Background low | Background high | Interaction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | A_ordinary | 0.001787617 | -0.001351255 | 0.001569436 | -0.007157139 | 0.010576343 | 0.000218181 | -0.001405153 | 0.001996841 | -0.001054822 |
| development | A_aligned | 0.000695108 | 0.000695108 | 0 | 0 | 0 | 0.000695108 | -0.002082984 | 0.003611072 | 0 |
| development | B_ordinary | 0.064220607 | -0.051299802 | 0.057760205 | 0.019884937 | 0.099184495 | 0.006460402 | -0.000934901 | 0.013522782 | -0.003040263 |
| development | B_aligned | 0.000548166 | 0.000548166 | 0 | 0 | 0 | 0.000548166 | -0.008020308 | 0.008416242 | 0 |
| pilot | A_ordinary | -0.000415223 | 0.006280509 | -0.003347866 | -0.007558485 | 0.000733676 | 0.002932643 | 0.001413646 | 0.004498070 | 0.000980545 |
| pilot | A_aligned | -0.000118778 | -0.000118778 | 0 | 0 | 0 | -0.000118778 | -0.002277785 | 0.002116917 | 0 |
| pilot | B_ordinary | -0.003171086 | 0.006634156 | -0.004902621 | -0.021430730 | 0.011262495 | 0.001731535 | -0.001697967 | 0.005271009 | -0.001930655 |
| pilot | B_aligned | 0.003061743 | 0.003061743 | 0 | 0 | 0 | 0.003061743 | -0.000482634 | 0.006757344 | 0 |
<!-- d169-end -->

Aligned address and interaction contrasts are exactly zero because the
assigned displacement is unused. This is a successful engineered invariance
check, not a statistical equivalence result or evidence that spatial
feedback never matters. Original-path reproductions likewise check the
apparatus rather than adding independent scientific replications.

A-ordinary does not reproduce development B's large address contrast.
In the pilot A-ordinary background contrast is +0.002933, with interval
[+0.001414,+0.004498]; its swapped gap also has a positive pointwise
interval. Thus the complete panel does not justify claiming all background
differences are irrelevant. All responses, interactions, founder signs and
omissions appear in the [complete tables](TABLES.md).

Every pair of the nine A q levels and five B q levels is retained:
424 cohort/group/q-pair rows, including 92 empty pairs. Development has
44/81 occupied A pairs and 20/25 B pairs per writer condition; the pilot
has 77/81 and 25/25. Conditional means retain unequal support and
founder clustering; empty means are undefined, not zero.

q describes ideal-template compatibility, not the entire spatial operation.
Equal q need not mean equal shifts; q=−1 sign reversal need not destroy
best-translated shape, and q=+1 may be physically nonzero. The individual
within-background interventions are controlled, but observed q categories
are not independently randomized, balanced strata. No preferred pair,
new q threshold or monotonic “higher q is always better” claim is added.

## What changes from D168, and what does not

D168 described the development B exported-shape gap as mixture +0.044129
plus residual +0.020091. D169 instead gives intervention address +0.057760
plus bundled background +0.006460, for the same +0.064221 original gap.
These are different estimands: D168 pooled observed category means; D169
crossed actual shifts within fixed backgrounds. Its mixture term is not
the new address effect, and its residual is not the new background effect.

The original seven responses on both diagonals bridge back to D168:
four response arrays and 17,920 values checked. No earlier result is
replaced or silently relabeled.

The extension's original question remains whether a small diagnostic
challenge predicts later reconstruction better than equally costly passive
observation. [D162's fixed pilot](../confirmation/PILOT64_RESULTS.md) remains
unresolved: primary challenge MSE was about 0.0453% worse, with a gain
interval from −0.3992% to +0.3226% of reference MSE; both diagnostic observers
beat starting-only by about 4%. D169 neither refits these models nor joins
actual lineage outcomes to its counterfactuals. It cannot establish how
much this mechanism explains that prediction result.

The [L20 case](../../laws/L20_self_written_genome.md) remains
STRESS_TESTED / MIXED. The narrower supported statement is that, in this
engineered tissue system, where writer feedback lands can causally alter
the organization exported to a fresh reader. It is not autonomous interface
repair, learned addressing, full shape preservation, biological heredity
or confirmation of the broad self-written-genome law.

## Verification, chronology, costs and provenance

Qualification retained its initial failure history. The smoke passed one
test (47 deselected) in 9.15s. Qualification v1 had 43 passes and five
failures in 142.93s: the same unit assertion compared a NumPy array to a
Python list before numeric comparison. Values agreed. Container handling
was corrected; numeric-list checking was batched with shape/finite/type/
tolerance checks retained and five adverse tests added. No physics, metric
or estimand changed; failed reports and fixtures were preserved.

Qualification v2 passed all 53 tests in 30.29s. The protocol, three new
modules, tests and passing qualification were among 327 frozen inputs at
2026-09-22 17:40:02 UTC. No frozen scientific file was edited afterwards.

The complete disposable block passed in 31.177248s, including independent
physics replay, original reproduction, aligned controls and saved-output
checks. Its 64 writers and 64 fresh readers had zero replay discrepancy.
It is a cost/qualification block, excluded from scientific evidence.

The frozen full-stage budget was 65.40 minutes without parallel-speedup
credit; the measured main took 640.039s (10m40s), completing all 80 blocks
at 2026-09-22 17:52:51 UTC. The separately authorized fresh full-physics audit
passed at 2026-09-23 11:51:40 UTC in 330.019s (5m30s). Both ran detached
because their conservative stage budget exceeded ten minutes, with at most
six workers, one numerical-library thread each, CPU affinity 0–5.
No automatic polling, retry or successor was used.

The fresh audit checked all 333 main input hashes and 163 output hashes,
all 5,120 writer and 5,120 fresh-reader paths, 2,560 original-path
reproductions, 1,280 aligned swap aliases and every fixed summary/support
row. Writer/reader replay discrepancies were zero. The 333-input closure
adds the freeze, benchmark receipt and four benchmark files to the 327
frozen inputs. The independent checker reconstructs physics, stream
assignment, metrics, factorial algebra and bootstrap summaries separately
from the production calculations.

Scientific outputs occupy 295,531,020 bytes (281.840 MiB), below the
737.164 MiB measured storage allowance and fixed 1 GiB cap with 4 GiB
reserve. Benchmark files add 4.864 MiB; preserved qualification fixtures
add 38.861 MiB, plus logs/receipts. All numerical artifacts, caches and
fixtures remain external. This write-up adds only code/documentation here.
No new simulation, prediction fit or job was launched during closeout.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.

Run: `l20_extension1_address_swap_v1_attempt1`. Relative artifacts:

- `runs/l20_extension1_address_swap_v1_attempt1/COMPLETE.json`
- `runs/l20_extension1_address_swap_v1_attempt1/MANIFEST.json`
- `tmp/l20_extension1_address_swap_v1_attempt1_freeze.json`
- `tmp/l20_extension1_address_swap_v1_attempt1_benchmark.json`
- `logs/d169_qualification_v1.xml` and `logs/d169_qualification_v2.xml`
- `logs/l20_extension1_address_swap_v1_attempt1_saved_audit_v1.json`
- `outputs/l20_extension1_address_swap_v1_attempt1/responses.npz`
- `outputs/l20_extension1_address_swap_v1_attempt1/summary.json`
- `outputs/l20_extension1_address_swap_v1_attempt1/verification.json`
- `logs/l20_extension1_address_swap_v1_attempt1_documentation_v1.json`

SHA256 bindings:

- Freeze: `6fce26496ac263c73f2b2c58f38c3f9ce596bf49960efc2db99ec1e79632073b`.
- COMPLETE: `898fd26329f89d8123abf6561ded22876e258612195d1b748d18e5df79e8dcd2`.
- Fresh audit: `f6a78b24b80bb5b1c953b234315e1457dc9cb54ca79da90565dcafafe28505fa`.
- Summary: `8f59572303047e279a9e3f0a0589d5327212e1f02cd4ad245e5de78f0223350b`.
- Responses: `a9f181830ad3528b2fb1c120f5562b1514c727d2d6f69fb886607f8e63fd0689`.

The separate documentation checker rehashes the existing closure,
independently rechecks summary arithmetic, bridges the original responses
and checks all nine tables (6,118 numeric rows) and local links against the
saved output. Eight synthetic transcription checks also pass, including
rejection of changed numbers, undefined-to-zero substitutions, wrong labels,
nonfinite entries and malformed/duplicate table markers. Its receipt binds
this report, TABLES.md and checker. It
does not rerun tissue dynamics and is not a new scientific experiment.

## Decision and possible next step

Close this matched-swap test without changing D141, D162 or the law verdict.
The specific development copy imbalance now has controlled mechanistic
support; continuing to redescribe the same gap is not itself a new
prediction test.

A useful next step is a small, design-only review of how this mechanism
could be addressed in a future equally budgeted prediction comparison,
keeping starting-only and passive baselines prominent. First check what
the existing diagnostic pairing already controls, then specify any new
balancing and development/test separation before generating outcomes.
Do not assume this swap explains the entire plus/minus forecasting
difference or tune the challenge against the observed pilot. No such
follow-up is registered or launched here; it needs separate approval.
