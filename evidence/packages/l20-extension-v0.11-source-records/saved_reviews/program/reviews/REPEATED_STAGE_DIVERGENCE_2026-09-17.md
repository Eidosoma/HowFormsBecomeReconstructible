# D142 — where the saved futures diverge

Status: COMPLETE, independently audited. Post-result saved-state review, not
a new experiment. All 16 founder blocks, four lives, both families/writers
and four futures retained: 256 record–host–writer cases, 1024 futures.
[Declared scope](../repeated-futures/analysis/SCOPE_V1.md),
[original D142 results](../repeated-futures/RESULTS.md).

## Finding in plain terms

The large ordinary-B spread opens during rewriting. The first ordinary and
aligned writers begin with exactly the same read states and matched noise;
their results have separated strongly by the saved writing checkpoint at 300.
Alignment avoids much of that extra variability. It does not, on average,
reduce variation in reference-shape scores below the amount present when
writing began. Avoiding instability is not the same as removing existing noise.

The remaining aligned-B fidelity loss has a different profile. The reader
builds an internal reference that resembles the incoming pattern but does not
fully match its shape. Writing improves this reference a little, insufficient
to recover the incoming record's fidelity. Thus reconstruction can be much
more repeatable while still losing detail at each replacement.

Important qualification: each future redraws the ordinary writer's spatial
feedback displacement as well as births and dynamical noise. These are all
included in D142's within-pair future variance. The aligned writer applies
feedback without that displacement. This review does **not** identify how
much variation comes from changing addresses versus other randomness, or from
their interaction. It does not measure a causal percentage attributable to
each stage. No claim of autonomous repair or complete preservation follows.

## Matched start: the contrast appears during the first rewrite

All G1 read states, writer-start states and writer states after one update
match exactly between writers. The table is B's mean best translated R-shape
correlation and mean within-pair variance across four futures. Variance uses
divisor three within each case, then equal averaging over 64 cases.

| G1 writing step | Ordinary mean shape | Aligned mean shape | Ordinary within variance | Aligned within variance |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0.763370 | 0.763370 | 0.000291173 | 0.000291173 |
| 1 | 0.763638 | 0.763638 | 0.000289937 | 0.000289937 |
| 300 | 0.677447 | 0.777496 | 0.031990324 | 0.000341289 |
| 1000 | 0.742336 | 0.772872 | 0.011795906 | 0.000435684 |

The exact onset between steps 1 and 300 was not saved. Ordinary writing also
recovers substantially between 300 and 1000; it is not a monotonic collapse.
Aligned B's modest late mean decline was also seen in the earlier
[D138 persistence audit](../../reviews/L20_HANDOFF_PERSISTENCE_2026-09-16.md).
It is not a reason to select a new stopping time from these outcomes.
Later generations no longer have identical writer inputs: their differences
include the consequences of earlier rewrites.

## Mean fidelity path: every group and generation

The guide only rolls the record, so best translated shape is unchanged by
routing to numerical precision. The table combines incoming and routed
columns for readability. R is the internal reference, not the transmitted
record. Reading does not edit the incoming record: the reported drop is
between that record's fidelity and the fidelity of the reference reconstructed
from it. During reading itself, R starts random and builds toward the pattern.

| Group | Generation | Incoming/routed record | Read-end R | Write-end R | Outgoing record |
| --- | ---: | ---: | ---: | ---: | ---: |
| A ordinary | 1 | 0.930348 | 0.900364 | 0.932567 | 0.938155 |
| A ordinary | 2 | 0.938155 | 0.910640 | 0.929046 | 0.934548 |
| A ordinary | 3 | 0.934548 | 0.906851 | 0.931109 | 0.936926 |
| A aligned | 1 | 0.930348 | 0.900364 | 0.937455 | 0.938405 |
| A aligned | 2 | 0.938405 | 0.904417 | 0.940389 | 0.941353 |
| A aligned | 3 | 0.941353 | 0.907936 | 0.943749 | 0.944929 |
| B ordinary | 1 | 0.823530 | 0.763370 | 0.742336 | 0.745754 |
| B ordinary | 2 | 0.745754 | 0.690951 | 0.653754 | 0.656799 |
| B ordinary | 3 | 0.656799 | 0.604897 | 0.585204 | 0.588463 |
| B aligned | 1 | 0.823530 | 0.763370 | 0.772872 | 0.772960 |
| B aligned | 2 | 0.772960 | 0.721242 | 0.732966 | 0.733813 |
| B aligned | 3 | 0.733813 | 0.686109 | 0.699532 | 0.701259 |

Every group's mean record-to-reference change is negative in all 16 blocks
at each generation. Aligned B's mean read-transfer changes are -0.060160,
-0.051719 and -0.047704; its mean writing gains are +0.009502, +0.011724
and +0.013423. Those writing gains are not universal: 82/256, 90/256 and
87/256 individual futures lose shape during the corresponding writing phases;
12/16 block means improve at each generation. Record construction makes only
small mean adjustments. A behaves differently: writing more than recovers
the mean read-transfer loss, especially under alignment. Do not generalize
B's progressive erosion to both families.

## Where within-pair shape-score spread grows

Entries below are **within-pair variance multiplied by 10,000**, not shape
percentages or survival rates. All cells use the same scalar shape metric.
The first incoming record is fixed across futures, so its variance is zero.

| Group | Generation | Incoming/routed | Read-end R | Write-end R | Outgoing |
| --- | ---: | ---: | ---: | ---: | ---: |
| A ordinary | 1 | 0.0000 | 0.7165 | 8.1741 | 9.0192 |
| A ordinary | 2 | 9.0192 | 6.4977 | 16.8243 | 17.7665 |
| A ordinary | 3 | 17.7665 | 12.3860 | 16.7476 | 18.1521 |
| A aligned | 1 | 0.0000 | 0.7165 | 0.7296 | 0.9141 |
| A aligned | 2 | 0.9141 | 1.2481 | 1.3539 | 1.6944 |
| A aligned | 3 | 1.6944 | 1.6946 | 1.8281 | 2.3033 |
| B ordinary | 1 | 0.0000 | 2.9117 | 117.9591 | 118.4825 |
| B ordinary | 2 | 118.4825 | 136.3619 | 312.3928 | 312.1732 |
| B ordinary | 3 | 312.1732 | 333.2864 | 487.3734 | 488.1571 |
| B aligned | 1 | 0.0000 | 2.9117 | 4.3568 | 4.6255 |
| B aligned | 2 | 4.6255 | 7.4443 | 9.9583 | 10.3788 |
| B aligned | 3 | 10.3788 | 15.5715 | 18.0799 | 18.1785 |

Ordinary B's largest mean increase occurs across writing at every generation.
Aligned B's writing increases are much smaller, but still positive on average
in each generation. Individual pairs can contract: 28/64, 35/64 and 34/64 do
so during aligned writing. This does not establish an average shape-noise
removal mechanism. Body preference can behave differently from shape scores.

For every adjacent phase X→Y, the checked accounting is
`W(Y)-W(X) = W(Y-X) + 2 mean_cov(X,Y-X)`.
The increments are not independent. For example, ordinary-B generation-2
writing adds 0.01760309 to W: increment variance 0.01306487 plus covariance
term 0.00453822. Omitting covariance would misdescribe the change. In ordinary
A's generation-2 read transfer, W decreases by 0.00025216 despite positive
increment variance 0.00012342, because its covariance term is -0.00037558.
All four phase means and variance differences telescope; no causal fractions
are assigned. Full covariance, case moments and block summaries are retained.

## Consequences in fresh readers

The following are square roots of mean within-pair variances, multiplied by
100: preference-point standard deviations for G1–G4 read endpoints. These
reproduce the final D142 within-pair variance estimates.

| Group | G1 | G2 | G3 | G4 | Negative endpoint counts, G1→G4 |
| --- | ---: | ---: | ---: | ---: | --- |
| A ordinary | 1.98 | 2.55 | 2.83 | 2.74 | 0 → 0 → 0 → 0 |
| A aligned | 1.98 | 1.81 | 1.79 | 1.88 | 0 → 0 → 0 → 0 |
| B ordinary | 2.75 | 7.65 | 10.88 | 13.85 | 0 → 10 → 26 → 39 |
| B aligned | 2.75 | 3.45 | 3.83 | 4.24 | 0 → 2 → 3 → 4 |

Each count has denominator 256; zero preferences are separately retained.
Unrouted writer-body preference is also saved, but must not be substituted
for this fresh-reader outcome. An ordinary writer can have negative canonical
preference while retaining strong translated shape, because spatial position
matters to the former. Translation-invariant shape is used above to avoid
mistaking a mere roll for loss of organization.

All retained checkpoints are in the external measurements and summary, not
only the illustrated G1 comparison. Independent units remain 16 founder
blocks. These additional stage descriptions have no new confidence intervals,
significance labels, fitted forecasts or changed thresholds. D141's original
challenge result stays unresolved; D142's primary estimates are unchanged;
L20 remains **STRESS_TESTED / MIXED**.

## Next causal question — proposal only

Separate changing feedback addresses from the other random streams. A
separately specified crossed comparison could hold a writer-displacement
sequence fixed while varying birth/read/write noise, then hold those noise
streams fixed while changing displacements. Retain all records, both families
and both writers, the same guide/carrier, and the full address-by-noise panel;
do not select favorable shifts or pool aliases as independent futures.

That would ask whether instability chiefly reflects different spatial
addresses, sensitivity to noisy dynamics, or their interaction. This review
cannot answer it. No successor protocol, executor or simulation was launched.
It would be a mechanism experiment, not a rescue of challenge forecasting.

Do not simply repeat the earlier hand-off cleanup or theta substitution:
[D137](../../reviews/L20_REFERENCE_HANDOFF_2026-09-16.md) and
[D139](../../reviews/L20_RECORD_HANDOFF_2026-09-16.md) already retain unresolved
primary effects. Likewise [D119](../../reviews/L20_WRITE_DURATION_2026-09-14.md)
found a small late-writing benefit in an earlier context; these saved B
checkpoints do not reverse that experiment or establish a better duration.

## Qualification, audit and provenance

37 synthetic tests passed in 1.18s. Earlier report: 35 passed/two failures
from demanding exact FFT equality to 1.0; discrepancy 1.11e-16. Corrected the
test assertion to the already specified 1e-12 tolerance, retaining both
reports. No scientific or numerical production rule was changed.

Scope, both implementations, tests, passing report and source seals frozen
16:07:34.137609 UTC. Checked saved-block benchmark 0.571744s, hash check
2.348300s; conservative full extraction/audit forecast 147.689s / 2.46min.
Below ten minutes, so this analysis ran in foreground with one worker and one
numerical thread, CPU affinity at most 0–5. No simulation calls/imports.

COMPLETE **16:08:42.455742 UTC**, extraction plus in-run checking **11.692768s**.
Output **1,142,361 bytes / 1.09MiB**, excluding the small completion receipt,
all external. Source hashes verified before/after extraction. Fresh-process
independent saved audit passes 31,744 body-preference and 40,960 FFT shape
evaluations (maximum discrepancy 8.88e-16), all pair/block/group statistics,
phase identities and original D142 endpoint checks. It verifies 1265 source
inputs, 36 source outputs and seven analysis artifacts. Zero new dynamics,
excluded cases, fitted models, retry or automatic successor.

External directory:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/analyses/d142_saved_divergence_v1/`.
`measurements.npz` axes begin block, life, future, condition; conditions are
A ordinary, A aligned, B ordinary, B aligned. `pair_moments.npz` stores each
case's means and four-future sample variances; `summary.json` stores all group
and block descriptions. `FREEZE.json`, `benchmark.json`, `STARTED.json`,
`verification.json` and `COMPLETE.json` retain provenance. No arrays/logs/cache
were written into the repository.

- Source D142 COMPLETE: `a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72`.
- Analysis FREEZE: `e7022aff533351cd4f72fbef5a86b55a9668019f2f1385d2eececdae038f9762`.
- Analysis COMPLETE: `e7893b713dce4796bfe16fffa820f1df060941c0dcd86b92db4a9e389f47533a`.
- Analysis summary: `a35d789282f8f115589f4c29494ec2f5235042a574bd3d28bf97e62def9dda9d`.
- Analysis measurements: `3fe2649a85377e78141ed816626e94cfcb458d65a47028445e22e087e5c18ed5`.

Read-only audit, using the existing external Python environment and the
documented one-thread/CPU-affinity environment:
`L20-extension-1/repeated-futures/analysis/audit_divergence.py`.
