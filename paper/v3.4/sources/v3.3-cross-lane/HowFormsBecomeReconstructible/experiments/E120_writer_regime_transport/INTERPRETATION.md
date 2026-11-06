# E120 — the clear successor penalty does not survive independent writer noise

Reviewed 2 November 2026. All 32 archived E077 blocks were restored to the same
intact/pruned starting records. Only the next writer's ongoing cue-noise pairing
and fallback tolerance changed. Initial activity remained shared; assessment
readers and original acquisition retained the matched apparatus.

## Primary result

The independent-noise, 1e−4-tolerant primary meets **nine of ten gates**. Immediate
benefit, all four useful-performance bounds and all four five-point retention
requirements pass. The required successor cost fails: its estimated direction
is positive and its interval includes zero. The generic-regime reversal is
therefore **not established**.

Immediate success is 55.713% intact and 62.891% pruned in every writer regime:
**+7.178 points [5.566, 8.740]**. Successor results are:

| Next writer | Intact success | Pruned success | Pruned minus intact, points [pointwise 95%] |
| --- | ---: | ---: | ---: |
| Matched noise, exact fallback | 63.184% | 57.275% | −5.908 [−7.764, −4.053] |
| Matched noise, tolerant fallback | 57.031% | 55.127% | −1.904 [−4.102, 0.391] |
| Independent noise, exact fallback | 65.967% | 66.113% | +0.146 [−1.904, 2.197] |
| Independent noise, tolerant fallback | 61.719% | 63.623% | +1.904 [−0.439, 4.199] |

Intervals here are the pointwise whole-source bootstrap intervals used by the
primary gates. The frozen automated report additionally displays simultaneous
bands within each profile. Do not mix the two interval conventions.

Changing noise alone shifts the successor pruning contrast by **+6.055 points
[3.711, 8.301]** under exact fallback and +3.809 [1.807, 5.566] under tolerance.
These are paired, prespecified secondary factorial comparisons, not separate
fresh-source confirmations. Tolerance also changes the contrast; its effect is
not interchangeable with changing the noise stream.

## What the result establishes

The matched-exact reversal repeats, while changing the next writing operation
weakens or removes the resolved successor cost. An unresolved independent-noise
contrast is not proof of no effect or absence of individual harms. The primary
independent-tolerant successor has **135 gains and 96 harms** among 2,048 paired
assessment contexts; the matched-exact successor has 81 gains and 202 harms.
These contexts contain 32 independent blocks, not 2,048 independent replicates.

The fixed starting intervention is identical across these conditions. Its
selection came from the original matched apparatus; no claim is made that a
new independent-noise history would select the same connections. That is the
distinct E121 test. Cue resets stay shared, precision is float64 and the
normalization floor is zero throughout. This is not a combined finite-storage
test or a second-substrate result.

Completed 1 November at 17:18:26 UTC in **3h48m25s**. All new states were
independently replayed; 73,728 case rows and 18,432 mechanism rows remain.
The figure was inspected. Artifact verification is recorded in the closeout
linked below. No manuscript change or new simulation was made for this review.

[Protocol](PROTOCOL.md), [frozen report](runs/transport_v1/REPORT.md),
[complete estimates and gates](runs/transport_v1/summary.json),
[closeout](analysis/closeout_v1.json).
