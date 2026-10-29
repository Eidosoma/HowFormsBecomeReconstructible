# E099 interpretation — noise benefit survives ordinary selected capture

23 October 2026. Scientific run `capture_v1` completed all 32 blocks at
**17:58:45 UTC**, in **1 h 24 min 42.40 s**. Verification and visual inspection
passed. The primary conjunction was **not met**: the noise benefit repeated,
but the proposed contribution of hybrid versus ordinary capture on the same
independently noisy pruned body was not established.

## Primary result

| Pooled-mixture contrast | Difference (percentage points) | Adjusted 97.5% whole-block interval |
| --- | ---: | --- |
| Same independent-noise pruned body: hybrid H minus ordinary selected capture O | −0.146 | [−0.928, 0.488] |
| Pruned hybrid records: independent minus paired supplying-body noise | +6.396 | [3.955, 8.984] |

Both lower bounds had to exceed zero. The first interval spans zero and lies
entirely below the prespecified +3-point practical reference; the second lies
above that reference. This gives no established positive average contribution
of the selected H/O switch under these conditions. It is not an equivalence
test, and small effects and individual harms remain.

The paired-pruned H and O records are byte-identical: their selected connections
use ordinary fallback already. On the independently noisy body, changing just
those selected weights to ordinary capture retains a **+6.543-point** noise
benefit, secondary 95% interval **[4.346, 8.789]**. Thus the selected hybrid rule
is not required for the observed average noise gain in this intervention.
The exact path identity is **6.396 = −0.146 + 6.543** points. It does not assign
a unique or exclusive mediation fraction.

## Absolute outcomes and sign/magnitude separation

H is the archived hybrid capture. O substitutes ordinary coactivity at the
originally selected connections only. S combines H signs with O magnitudes;
M combines O signs with H magnitudes. Within each body, outside record bytes,
connection support and terminal reader conditions remain fixed. Natural reader
normalization remains in effect.

| Pruned-record success, pooled histories | Paired body H=O | Independent body O | Independent body S | Independent body M | Independent body H |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mixture | 52.441% | 58.984% | 58.838% | 59.082% | 58.838% |
| Native | 72.754% | 81.348% | 81.641% | 81.885% | 81.836% |

All four mixture component comparisons are unresolved at their secondary,
pointwise 95% intervals:

| Mixture component contrast | Difference (points) | 95% interval |
| --- | ---: | --- |
| H signs at O magnitudes: S−O | −0.146 | [−0.830, 0.439] |
| H signs at H magnitudes: H−M | −0.244 | [−0.635, 0.049] |
| H magnitudes at O signs: M−O | +0.098 | [−0.488, 0.586] |
| H magnitudes at H signs: H−S | 0.000 | [−0.342, 0.342] |

These comparisons concern two captures of the **same independently noisy body**.
They do not test whether signs or magnitudes generally matter, or whether
differences between paired- and independent-noise bodies matter. Native M−O
has a small positive secondary effect, **+0.537 [0.049, 1.172]** points; native
H−O is **+0.488 [0.000, 1.074]**, with the interval touching zero. Native noise
benefits are **+9.082 [6.786, 11.426]** points under H and
**+8.594 [6.445, 10.791]** under O, both secondary.

The intact paired-body control is also informative: mixture H−O is
**+3.223 [2.051, 4.590]** points, secondary. The selected capture rule can matter
in another background. E099 does not establish that hybrid capture or exact
fallback is generally irrelevant, nor does it replace the whole writer with
ordinary coactivity.

## Individual gains and harms

Each row below contains **2,048 dependent case/draw comparisons** across 32
independent source blocks. These are not 2,048 independent replications.

| Contrast | Mixture gains / harms | Native gains / harms |
| --- | ---: | ---: |
| Same-body selected H−O | 10 / 13 | 10 / 0 |
| Noise change under H | 176 / 45 | 191 / 5 |
| Noise change under O | 182 / 48 | 184 / 8 |
| S−O | 8 / 11 | 6 / 0 |
| H−M | 1 / 6 | 0 / 1 |
| M−O | 10 / 8 | 11 / 0 |
| H−S | 4 / 4 | 4 / 0 |

For mixture H−O, gains occur in nine blocks and harms in seven; four exact
source contexts are harmed under both terminal draws. For the H noise change,
gains occur in 30 blocks and harms in 20; 28 contexts gain under both draws and
15 are harmed under both. The average noise benefit does not imply universal
benefit. All sixteen O/S/M/H outcome configurations, zero effects, history and
draw splits, and old and new pruning/noise endpoint tables are retained.

## What remains to explain

The independent-noise pruned H/O intervention is small on average. For mixtures,
the selected support is identical (mean **60.113** connections), mean selected
absolute weight mass is **3.006 under H versus 3.173 under O**, and a mean
**2.493** selected signs change. The mean uninjured normalized-coupling L1
change per cell is **0.02435**. By comparison, ordinary selected weight mass
changes from **0.374 on paired bodies to 3.173 on independent-noise bodies**.
These are structural descriptions, not causal mediation estimates.

The remaining noise benefit can therefore involve noise-altered content at the
selected connections even with the same ordinary capture rule, changes in the
outside record, or their interaction. E099 does not localize it solely outside
the selected connections or solely to supplying-body dynamics.

The next candidate is a reciprocal swap of selected content between the saved
paired- and independent-noise **ordinary-selected-capture** records, crossed
with each record's outside background. That 2×2 comparison would test selected
content, outside background and their interaction without regenerating ancestry
or supplying bodies. Preserve native/mixture and sham/pulse conditions, both
original endpoints and individual harms. A concrete protocol, frozen prediction
and runtime qualification would precede any new reader outcomes. No successor
has been implemented or launched as part of this closeout.

## Scope and evidence

All **32 known E098 sources 980000–980031** were retained. E098 informed this
hypothesis; E099 froze its primary rule before two new matched terminal draws.
This is a mechanism study on reused sources, not fresh-source validation. Old
E098 scores use different terminal nuisances and remain historical context:
they never enter the new intervals, and their absolute rates must not be read
as a matched before/after comparison with E099.

All 2,048 source contexts, 4,096 new context/draw rows, 77,824 terminal cue
observations, 2,048 erased-control rows, 4,383 event rows and 134,016 block means
passed independent checks. Capture and interventions, reader states, scores,
diagnostics and endpoint tables were independently replayed or recounted.
Closeout **PASS at 18:50:30 UTC** verified **606 outputs / 49 frozen inputs**,
job snapshots and qualification, with the final figure inspected. Retained run
size **1,284,631,687 bytes**. No supplying writer dynamics were repeated.

[Frozen protocol](PROTOCOL.md), [original report](runs/capture_v1/REPORT.md),
[complete statistics](runs/capture_v1/summary.json),
[individual cases](runs/capture_v1/cases.csv), [events](runs/capture_v1/events.csv),
[figure](runs/capture_v1/capture.png), [checks](runs/capture_v1/CHECKS.json),
[closeout](analysis/closeout_v1.json).
