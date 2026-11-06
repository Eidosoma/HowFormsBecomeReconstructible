# E116 — finite-resolution pruning result

The all-finite mixture condition **did not establish the prespecified
conjunction**. Of ten required gates, only later pruning harm passed.
The immediate benefit is unresolved, and all four absolute-success and
five-point-retention requirements failed. This is a material robustness limit
for the tested settings on records acquired under the original apparatus.
It does not establish that every finite formulation fails or invalidate the
original declared-apparatus result.

`finite_v1` completed **30 October 2026 at 21:24:43 UTC**, in **3h14m40.70s**
on four workers, below the 5h09m expected forecast. Closeout passed **31 October
at 11:00:59 UTC**: **1,283 output hashes / 35 frozen inputs** verified, source
and qualification bindings intact, figure inspected. Retained data total
**2,919,681,126 bytes**. All 32 sources, 4,096 context/draw rows, 32,768 condition
rows, 16,384 erased-control rows and every individual event remain. Independent
replay covers 118,814 new continuations and 243,331,072 record steps. The
reference arm exactly reproduces E112; this reuse is not another replication.

## Primary result: mixture records, all three numerical changes

T = fallback tolerance 1e−4, F = positive-denominator floor 1e−4,
Q = stored-weight grid spacing 2^-16. Computation remains float64.
I/P mean intact/pruned; 0/1 mean immediate/after one paired writer.

| Outcome | Reference | T+F+Q | Finite minus reference, points (95% CI) |
| --- | ---: | ---: | ---: |
| I0 success | 52.54% | 41.41% | −11.13 [−13.28, −9.03] |
| P0 success | 59.77% | 41.80% | −17.97 [−20.85, −15.14] |
| I1 success | 58.84% | 40.43% | −18.41 [−21.39, −15.48] |
| P1 success | 54.64% | 36.04% | −18.60 [−21.73, −15.58] |

The immediate pruning contrast changes from **+7.227 [5.273, 9.375]** to
**+0.391 [−0.537, 1.270] points**. The later contrast is **−4.395
[−6.689, −2.295]**, compared with the original −4.199. Thus later harm
survives while the complete immediate-benefit/later-harm pattern does not
qualify under this finite condition. Similar later point estimates do not
establish equivalence between numerical regimes.

All four finite success intervals have upper bounds below 50%, and all four
finite-minus-reference intervals have upper bounds below −5 points. Failure
is therefore not solely an inability to certify a lower bound. For context,
the original immediate intact success interval itself crosses 50%; the user
chose the strict lower-bound gate before these finite outcomes, and it was
not relaxed. The finite losses are directly apparent in paired comparisons.

## What the separate interventions identify

These are prespecified secondary, pointwise comparisons on known sources.

- **Rounding alone:** immediate pruning becomes −0.098 [−0.928, 0.635]
  points. Its change from reference is −7.324 [−9.473, −5.371]. Immediate
  intact/pruned success falls to 42.04/41.94%; later success is 39.55/34.18%.
- **Normalization floor alone:** immediate pruning becomes +0.586
  [−0.586, 1.709], a change of −6.641 [−8.691, −4.785]. Immediate success
  is 42.09/42.68%; later success is 48.49/41.06%, with −7.422 points of
  later pruning harm.
- **Tolerance alone:** immediate outcomes are unchanged because tolerance
  acts at the later capture. Later pruning becomes −0.098 [−2.734, 2.637],
  an interaction of +4.102 [2.881, 5.322] points. However, intact success
  falls by **5.713 [4.346, 7.178] points** and pruned success by **1.611
  [0.586, 2.588]**. A smaller intact/pruned gap here is not improved pruned
  reconstruction, and an interval crossing zero is not equivalence.

The current experiment therefore separates sensitivities: the immediate
mixture benefit is sensitive to the tested storage grid and normalization
floor; the later gap is sensitive to the tested writer tolerance. It does
not isolate a universal mechanism or prove that exact zero is indispensable.
Only one finite level of each intervention was tested.

## The effect is not a collapse of every record class

The native group is secondary and remains substantially functional under
T+F+Q: I0/P0 **85.64/85.50%**, I1/P1 **83.15/72.31%**. Its later pruning
cost is **−10.840 [−13.623, −8.252] points**. All four native absolute and
retention bounds would clear the same numerical limits, but this does not
rescue the mixture primary: native records never showed a clear immediate
benefit in the reference comparison. Native performance is evidence against
describing the result as universal failure of finite reading or rewriting.

The common-reader controls also narrow the interpretation. Removing the
terminal floor from the **same floor-only rewritten packets** raises mixture
intact/pruned success from 48.49/41.06% to 52.98/44.43%. Native-minus-common
effects are −4.492 [−5.811, −3.271] and −3.369 [−4.834, −2.148] points.
Some loss is therefore in their terminal interpretation. But the all-finite
packets still score only **40.33/36.04%** under the common zero-floor reader.
Changing the final reader alone does not restore their performance; the
inherited starting records and changes during writing/storage remain relevant.
This control does not separate every earlier stage.

## Individual gains and harms remain visible

Each mixture arm has 2,048 dependent context/draw observations across 32
independent sources. The reference has **167 immediate gains / 19 harms**
and **91 later gains / 177 harms**. T+F+Q has **30 / 22** immediately and
**49 / 139** later. Tolerance alone has **143 later gains / 145 harms**.
Those nearly cancelling totals are not an absence of individual consequences.

The complete 3×3 immediate/later event tables remain in `summary.json`.
Only **one** all-finite observation both gains immediately and is harmed later,
compared with 15 in the reference. Opposite aggregate effects need not describe
the same individuals. All prunings still change at least one selected weight;
rounding did not make an entire selected intervention a no-op in these sources.
The ledger also retains finite-minus-reference losses, not just pruning losses.

## Next lead

First use the retained arrays for a bounded diagnosis: locate the small
denominators and rounded-away weights in selected versus outside edges, and
relate those changes to lost immediate gains and persistent later harms.
Keep every case and the original two endpoints. This is cheaper and more
informative than extending the horizon or changing thresholds until a pass
appears; it remains a post hoc diagnosis, not a causal mediation claim.

Then separately freeze acquisition and renewal under the finite formulation
from the beginning. E116 challenged records formed under the original
apparatus; it cannot determine whether finite formation avoids relying on
fragile structure. Any revised numerical level or writer chosen using E116
is development and needs untouched validation sources. The original primary
remains failed, and no successor is launched by this closeout.

[Original report](runs/finite_v1/REPORT.md), [statistics](runs/finite_v1/summary.json),
[all cases](runs/finite_v1/cases.csv), [individual events](runs/finite_v1/events.csv),
[figure](runs/finite_v1/finite_pruning.png), [closeout](analysis/closeout_v1.json).
