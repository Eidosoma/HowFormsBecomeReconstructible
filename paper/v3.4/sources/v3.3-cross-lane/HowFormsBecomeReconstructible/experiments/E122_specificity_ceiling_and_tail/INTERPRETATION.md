# E122 — history remains distinguishable through 256 rewrites

**Complete and verified, 2 November 2026.** The original own-versus-foreign
history distinction remains detectable after 256 actual rewrites at both record
budgets. The prespecified 128→256 change intervals fit inside ±0.25 percentage
points for both budgets. This establishes practical stability over that last
doubling, not an infinite-horizon asymptote or multiple stable basins.

All 64 E014 backgrounds, 256 founders and both recipients remain, including
failed formations. This is a frozen continuation of a known cohort, not a new
independent formation cohort. All four routes use the same own-founder target
and matched terminal draws. Protected foreign is an actual matched reader of
foreign acquisition bytes, not a relabelled own reader.

## Native agreement and historical specificity are separate

At 256 rewrites, in percentage points except the ratio:

| Budget | Own agreement | Foreign agreement | Protected own | Protected foreign | Renewed own−foreign [95%] | Protected gap [95%] | Renewed/protected gap [Fieller 95%] |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 128 bytes | 64.256% | 62.744% | 68.266% | 66.502% | 1.511 [0.956, 2.091] | 1.765 [1.370, 2.182] | 0.856 [0.585, 1.125] |
| 2,048 bytes | 63.392% | 62.405% | 76.553% | 73.935% | 0.987 [0.514, 1.472] | 2.618 [2.197, 3.065] | 0.377 [0.201, 0.546] |

The compact estimate is about **86% of the protected-copy history gap**, not
86% of the founder's total information or shape. Its 64.256% own agreement is
also not a founder-specific information estimate. Protected copying supplies
an operational reference under the same acquisition, codec and reader; it is
not a theorem about the largest historical gap that the record format allows.
Ratio intervals were not clipped to [0,1].

The compact-minus-full *raw* history-gap difference at 256 is **+0.524 points
[−0.075, 1.130]**. Its positive point estimate does not establish superiority.
The two normalized ratios also use different protected denominators.

## Duration: a supported finite-window result

| Budget | History gap after 1 | After 16 | After 256 | Change 128→256, points [95%] | Within ±0.25 points? |
| --- | ---: | ---: | ---: | --- | --- |
| 128 bytes | 1.482 | 1.387 | 1.511 | −0.001 [−0.039, 0.037] | Yes |
| 2,048 bytes | 2.103 | 1.402 | 0.987 | −0.008 [−0.195, 0.168] | Yes |

The compact trajectory is nonmonotonic at early checkpoints. No monotone decay
was imposed on the plateau model. The larger record loses more of its initial
history gap before entering a much slower-changing segment. Equivalence here
uses a frozen practical margin and paired whole-block uncertainty; it is not
inferred from a nonsignificant difference.

The model comparisons leave the mathematical asymptote unresolved. For compact
records, both zero-asymptote alternatives can approximate a positive flat
segment by pushing toward very slow decay: the fitted exponential time constant
hits 65,536, and the power-law fit also reaches its slow-decay boundaries.
Late prediction does not distinguish either alternative from the plateau model.
The plateau-model fitted C is 1.524 points [0.938, 2.117], conditional on that
model; 130 of 2,000 bootstrap fits hit a parameter boundary.

For the 2,048-byte record, the plateau model predicts horizons 128/256 better
than the simple zero-asymptote exponential in the frozen comparison. Its
advantage over the zero-asymptote power law is unresolved. The plateau-model C
is 1.024 points [0.584, 1.486]. These are comparisons of later horizons within
the same cohort, not fresh independent tissues. No indefinite-memory or
multiple-basin claim follows.

## Sign and amplitude decomposition

| Budget | Own sign agreement, 1→256 | Own amplitude-qualified fraction, 1→256 | Own qualified agreement, 1→256 |
| --- | --- | --- | --- |
| 128 bytes | 71.324% → 66.463% | 94.039% → 95.912% | 68.091% → 64.256% |
| 2,048 bytes | 77.261% → 65.633% | 94.217% → 95.808% | 74.010% → 63.392% |

The aggregate amplitude-qualified fraction increases while sign agreement
falls. Thus a falling overall amplitude-qualified fraction cannot by itself
explain the loss of qualified agreement. Sign/amplitude events are correlated;
these marginal changes do not allocate independent causal contributions.
All four joint categories remain available per case and candidate.

At 256, the compact sign-only own-history gap is 1.510 points [0.947, 2.093],
while its amplitude-only gap is 0.012 [−0.082, 0.105]. The corresponding larger-
record gaps are 0.893 [0.426, 1.378] and 0.113 [0.011, 0.220].

## Verification and next analysis

`continuation_v1` completed **16:44:25 UTC**, runtime **10,013.84 seconds
(2h46m54s)** on four workers. Verified **418 outputs and 22 frozen inputs**;
inspected the actual scientific figure. Closeout passed **17:22:35 UTC**.
Stored output is 941,255,249 bytes. Every checkpoint reader was independently
replayed (1,024 reads), as were new renewal generations 17/32/64/128/256.
All boundary packets were saved and continuity checked. Exhaustive stepwise
replay of every generation is not claimed. No failed founder was removed.

[Native-scale figure](runs/continuation_v1/specificity.png),
[complete report](runs/continuation_v1/REPORT.md),
[full estimates](runs/continuation_v1/summary.json),
[verified closeout](analysis/closeout_v1.json).

E123 now asks whether an external observer can identify the acquisition donor
among four matched candidates from the record, the rebuilt body, or both. That
separately frozen post hoc analysis reuses these fields. It does not reinterpret
the native agreement percentages as bits. The manuscript hold remains in effect.
