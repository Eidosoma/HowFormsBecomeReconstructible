# E118 — finite formation does not rescue the tested formulation

`formation_v1` completed **31 October 2026, 19:07:30 UTC**, in **5h34m48.97s**
on four workers, close to the 5h21m forecast. Closeout passed **1 November,
10:46:57 UTC**: **2,777 outputs / 48 frozen inputs** verified and the figure
inspected. All 32 fresh sources, 20,480 condition rows, 4,096 context/draw
identities, 12,288 erased controls and 11,646 event rows remain. Every new
trajectory was independently replayed; 499,529,728 record-steps were checked.
Retained run size is **5,758,606,025 bytes**.

The result is a clear robustness limit for this recipe. Starting with finite
records and applying the finite rules throughout their histories does not
produce useful mixture performance at the tested settings. The original
formulation repeats the immediate-benefit/later-harm pruning pattern on fresh
sources. Thus the supplied original mechanism remains reproducible, while
formation under these finite rules does not repair its numerical fragility.

## Primary result

The combined T1F1Q1 mixture arm passes **one of ten** requirements: later
pruning harm remains. Its immediate effect is unresolved and every absolute
success and retention requirement fails.

| Endpoint | Original success (%) | Combined finite success (%) | Finite minus original (points) |
| --- | --- | --- | --- |
| Intact, immediate I0 | 49.023 | 7.178 [5.518, 8.936] | −41.846 [−46.973, −37.109] |
| Pruned, immediate P0 | 54.736 | 6.836 [5.176, 8.643] | −47.900 [−52.637, −43.457] |
| Intact, after writing I1 | 54.443 | 6.836 [5.176, 8.643] | −47.607 [−52.734, −42.871] |
| Pruned, after writing P1 | 49.805 | 4.932 [3.418, 6.592] | −44.873 [−48.975, −40.771] |

Brackets are pointwise 95% whole-source bootstrap intervals, with 10,000 paired
resamples of 32 independent sources. Each formulation/class has 2,048 dependent
context/draw observations; these are not 2,048 independent experiments.

Original-rule pruning is **+5.713 [4.053, 7.471] points immediately**, then
**−4.639 [−7.275, −2.100] points after writing**. Under combined finite rules
it is **−0.342 [−0.879, 0.244]** immediately and **−1.904 [−2.686, −1.172]**
later. The remaining later cost occurs in a system with very little absolute
success; it does not qualify as a useful finite version of the reversal.

All four finite success upper bounds are below 9%, far below the user-selected
50% usefulness threshold. All retention upper bounds are below −37 points,
far beyond the five-point allowance. This is not merely insufficient precision
around a passing result. Some original reference intervals themselves cross
50%; the paired finite losses remain large and the gates were not relaxed.

## Separate numerical changes

These are prespecified secondary comparisons, not alternative primaries.

| Formulation | I0 / P0 success (%) | I1 / P1 success (%) | Immediate pruning (points) | Later pruning (points) |
| --- | --- | --- | --- | --- |
| Original | 49.02 / 54.74 | 54.44 / 49.80 | +5.713 [4.053, 7.471] | −4.639 [−7.275, −2.100] |
| Tolerance only | 5.42 / 4.98 | 6.45 / 4.59 | −0.439 [−0.879, −0.049] | −1.855 [−2.637, −1.172] |
| Floor only | 28.13 / 29.15 | 34.72 / 29.83 | +1.025 [−0.049, 2.197] | −4.883 [−7.178, −2.393] |
| Grid only | 3.91 / 4.20 | 3.66 / 2.98 | +0.293 [−0.049, 0.635] | −0.684 [−1.221, −0.195] |
| Combined | 7.18 / 6.84 | 6.84 / 4.93 | −0.342 [−0.879, 0.244] | −1.904 [−2.686, −1.172] |

Tolerance 1e−4 and the 2^-16 storage grid each strongly degrade these complete
histories. The 1e−4 denominator floor is less damaging but still leaves mixture
performance well below the required floor. The five-condition design does not
estimate the omitted two-factor interactions or a critical numerical threshold.
Changing levels after this result would be development, not confirmation.

Both sham and pulse histories have poor combined finite performance: the four
mixture endpoints span **4.88–8.30%** under sham and **4.98–6.15%** under pulse.
The failure therefore also occurs without the pulse intervention.

## Native records and the final-reader control

Native records also lose substantial function under combined finite histories:
I0/P0 **8.84/8.69%**, I1/P1 **8.45/5.22%**, versus original-rule
**82.23/83.01%** and **81.05/71.58%**. This failure is broader than the mixture
construction. It does not establish that every finite formulation must fail.

The floor-only native arm remains functional at **64.84/65.09%** immediately
and **63.13/55.27%** later. Its four absolute lower bounds clear 50%, but it
loses **16–18 points** relative to its original reference; every retention
interval's upper bound is below −11 points. This secondary result cannot
rescue the combined mixture primary or justify dropping retention requirements.
Its pruning directions also persist: **+0.244 [0.049, 0.537] points** immediately
and **−7.861 [−9.814, −5.957]** later. This arm still uses exact-zero fallback
and unquantized storage; it does not demonstrate robustness to all three changes.

For floor-only mixture packets, removing the floor only at the terminal reader
raises intact/pruned rewritten success from **34.72/29.83%** to
**37.99/32.13%**. The paired improvements are **3.271 [2.002, 4.590]** and
**2.295 [1.416, 3.271] points**. Some loss is therefore due to terminal
interpretation, but this control still leaves low absolute performance.

For combined finite packets, the common zero-floor reader changes **no
individual both-cue success classification** at either rewritten endpoint,
in either record class: zero changes in each of four 2,048-observation sets.
The final floor alone cannot explain the combined failure. This does not
separate earlier storage, writing and ancestry effects or imply identical
continuous activity under the two readers.

## Individual consequences and scope

Original mixture records have **129 immediate gains / 12 harms**, and
**84 later gains / 179 harms** from pruning. Combined finite records have
**9 / 16** immediately and **4 / 43** later. Zero combined observations both
gain immediately and are harmed later, versus eight under the original rules.
Keep the full event tables: aggregate effects need not describe the same
individuals, and fewer pruning harms in a mostly unsuccessful population do
not establish improved rebuilding. No complete pruning intervention was a
no-op in these sources, although grid-erased individual tags remain recorded.

Each formulation prunes its own pre-channel repair tags. Finite and original
pruned endpoints can remove different coordinates; their retention comparison
therefore concerns the full formulation and its pruning policy. Intact endpoints
also fail strongly, so changed pruning coordinates alone cannot explain the
overall loss. No common-coordinate or unique mediation claim follows.

E118 supplies a new cohort. Its results should not be subtracted from E116's
old-history challenge as a paired estimate of adding finite ancestry. Teaching
also remains the original fixed-scaffold rule, with no learned-weight feedback:
the grid acts on its first reusable record, while tolerance/floor act only in
later phases where those operators exist. This is not an optimized learning
rule designed to compensate for finite storage.

## Next lead

Use the saved acquired packets and 32-generation lineage to locate **when
function and normalized coupling first diverge** across formulations. Retain
every source, both cue outcomes, continuous signed transfer, physical masks,
raw versus delivered captures, fallback use, weak denominators and all later
pruning harms. Separate acquisition, ancestry, pulse/continuations and recovery.
Declare the saved-data measures before extraction; the analysis is post hoc.
Saved body outcomes describe those histories, rather than fresh-reader
qualification at every intermediate boundary.

This bounded diagnosis needs no new long trajectories. It can identify a
specific transition for a later controlled replay instead of launching another
full lineage experiment or searching numerical levels until a result passes.
The E118 primary remains failed. No successor launched at closeout.

[Frozen report](runs/formation_v1/REPORT.md),
[statistics](runs/formation_v1/summary.json),
[all cases](runs/formation_v1/cases.csv),
[individual events](runs/formation_v1/events.csv),
[figure](runs/formation_v1/finite_formation.png),
[closeout](analysis/closeout_v1.json).
