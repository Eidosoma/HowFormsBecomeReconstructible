# E114 — matched-amplitude result and interpretation

Completed **28 October 2026 at 22:59:35 UTC**, in **17 min 14.75 s**, within
the 22-minute forecast. User-triggered closeout passed at **29 October
11:56:49 UTC**: **845 output hashes / 87 frozen inputs** verified, figure
inspected, **519,261,658 bytes** retained. All **32 sources / 4,096 identities /
554 eligible rows / 4,432 matched comparisons** remain. Every one of 8,864
variant continuations and 9,076,736 later variant updates was independently
replayed. No retry, sample extension or new writer dynamics.

## The shared-component ordering did not persist in the point estimates

After matching change sizes, gross sensitivity of the C−F success contrast was
smaller for shared activity m than for cue-specific activity d in both groups.
The sole mixture primary remains **UNRESOLVED**, with an interval ending at
exactly zero. Neither greater shared sensitivity nor reversed ordering meets
the declared strict interval rule. This is not evidence of equivalence.

| Eligible group | Gross matched m sensitivity, points | Gross matched d sensitivity, points | m−d, points (95% interval) | Status |
| --- | ---: | ---: | ---: | --- |
| Mixture, 272 rows | 0.276 | 0.460 | **−0.184 [−0.547, 0.000]** | Sole primary: **UNRESOLVED** |
| Native, 282 rows | 0.709 | 1.418 | −0.709 [−1.678, 0.000] | Secondary, pointwise |

These are mean absolute changes in the difference between C and F, averaged
over the other component and both later streams. They are not absolute success
rates or improvements from a generally better noise stream. C/F share
connectivity, magnitudes and local signed budgets; F flips the selected cycle.

Only one mixture row has nonzero m−d excess:
`1120024/2/1/3/1`, with raw excess **−0.5**. It supplies the entire −0.5 sum over
272 eligible rows and the only nonzero source sum. The other 31 source sums
are zero; zero-excess rows may still respond equally to both components.
Native excess comes from four rows in three sources, each −0.5:
`1120005/1/1/3/1`, `1120014/1/0/2/1`, `1120026/0/1/1/0`,
`1120026/1/1/1/0`. Identity order is source/arm/founder/recipient/injury.
All other cases and zero-eligible sources remain in the analysis.

E112's original primary is preserved exactly: **+0.551 [0.000, 1.460]** points,
also unresolved. The paired matched-minus-full-size excess is **−0.735
[−1.626, 0.000]** mixture and **−2.128 [−4.167, −0.565]** native points.
These are secondary pointwise comparisons. The native result does not replace
the selected mixture primary, and no old primary has been recalculated or
reclassified.

## What the manipulation actually changed

The shared range was reduced to about **5.7%** of its original size: mean scale
0.05744 mixture / 0.05776 native. The cue-component scale was exactly **1.0 in
every eligible case**. The common mean absolute target was 0.002845 mixture /
0.002780 native. There were no zero targets in this cohort; their handling was
validated in synthetic tests. The seven erased-witness no-ops remained.

Each component's lower/upper levels were centered on its original O/N midpoint.
One scale was applied to both C/F records, matching their pair-averaged L1 norm;
their individual norms need not be identical. Actual size matching agreed to
**2.60e−18**, unintended component change was at most **1.11e−16**, and maximum
absolute injected activity was 1.0. No initial clipping occurred. All later
noise owners, offsets, injuries, weights and reader equations remained fixed.

E113's larger natural m changes therefore cannot be interpreted as an intrinsic
shared-component priority. E114's matched point estimates supply no support for
that stronger claim. However, attenuation also moves the shared levels toward
their midpoint. The present experiment does not separately identify the role
of smaller amplitude and the role of that changed starting context. Equal-size
priority would additionally remain specific to the norm, direction and dose.

Continuous-score point estimates have the same ordering, without a new paired
interval test being added at closeout:

| Eligible group / score | Gross matched m C−F sensitivity | Gross matched d C−F sensitivity |
| --- | ---: | ---: |
| Mixture / minimum margin | 0.005832 | 0.010424 |
| Mixture / aligned transfer | 0.003574 | 0.005793 |
| Native / minimum margin | 0.013958 | 0.026144 |
| Native / aligned transfer | 0.004815 | 0.009575 |

These are secondary descriptive means in native score units. The complete
pointwise intervals for each component remain in the saved summary; they do
not establish a confidence interval for their difference.

## All gains, losses and earlier endpoints remain

There are **58/4,432 comparisons** with any absolute success change: 26 joint
changes and 32 single-record changes, no opposite-direction changes. They
produce **84 dependent record-level transitions: 50 gains and 34 losses**.

| Group/component | C gains/losses | F gains/losses | Wrong-sign / weak-positive failing sides |
| --- | ---: | ---: | ---: |
| Native/m | 3 / 6 | 5 / 4 | 18 / 0 |
| Native/d | 11 / 6 | 7 / 6 | 30 / 0 |
| Mixture/m | 3 / 4 | 6 / 4 | 17 / 0 |
| Mixture/d | 7 / 2 | 8 / 2 | 15 / 4 |

In total, **80/84** involve a wrong-sign output on the failing side; four have
correct signs but insufficient amplitude. These transitions are correlated
conditions within histories, not 84 independent replicates. The direction is
the declared lower-to-upper component comparison; it is not a universal benefit
of one random stream.

Cancellation of total absolute success movement in C−F is 55.56% m / 46.67% d
native and 82.35% m / 73.68% d mixture, with broad pointwise intervals. The
individual absolute outcomes, joint patterns and all gains/harms remain in
the cases/comparison/event ledgers. All seven original E112 endpoint, summary
and event tables were preserved byte-for-byte, including the immediate pruning
benefit and later paired-rewrite harm. Those earlier endpoints are unchanged.

## Next candidate: match sizes around the original starting states

A bounded control can distinguish midpoint placement from attenuation. Use
both original OO and NN states as anchors, perturb m or d toward the other
source by the same existing smaller norm, and hold the other component at its
anchor value. Pair and average both anchor directions and both later streams
so an arbitrary O/N label is not favored. Preserve exact archived baseline
outcomes, all sources, both earlier endpoints and every individual harm.

For example, from OO use (m_O+α_mΔm,d_O) or (m_O,d_O+α_dΔd); from NN use
(m_N−α_mΔm,d_N) or (m_N,d_N−α_dΔd). C/F receive the same declared scale rule.
Since α_d=1 in every current case, cue interventions and unperturbed anchors
correspond to existing full-size conditions and may be reusable after exact
validation. Only newly required continuations should be run, with benchmarked
runtime and one frozen contrast before outcomes. Do not select the one source
contributing to the current mixture excess or add a dose sweep.

This is a candidate, not a launched successor. E114 has exited. A fresh-source
confirmation should follow a clearer controlled effect rather than extending
the present sparse primary. Paired-cue noise, reset, normalization and numerical
precision remain features of the supplied apparatus.

## Suggested manuscript wording

> Matching the mean absolute size of halfway shared- and cue-component changes
> did not confirm greater shared-component sensitivity of the C−F success
> contrast. In eligible mixture records, gross sensitivities were 0.276 and
> 0.460 percentage points, respectively, giving −0.184 points with a whole-source
> 95% interval of [−0.547, 0.000]. The nonzero excess came from one source
> history. Shared changes were attenuated to about 5.7% of their original
> range, whereas cue changes retained their original size. Because attenuation
> also centered component levels near the original midpoint, the result limits
> an intrinsic-priority interpretation without separating amplitude from starting
> context. All absolute outcomes, earlier endpoints and individual harms were
> retained; the original E112 primary remains unresolved.

[Report](runs/matched_v1/REPORT.md), [statistics](runs/matched_v1/summary.json),
[all cases](runs/matched_v1/cases.csv), [comparisons](runs/matched_v1/comparisons.csv),
[crossings](runs/matched_v1/crossings.csv), [figure](runs/matched_v1/matched.png),
[closeout](analysis/closeout_v1.json).
