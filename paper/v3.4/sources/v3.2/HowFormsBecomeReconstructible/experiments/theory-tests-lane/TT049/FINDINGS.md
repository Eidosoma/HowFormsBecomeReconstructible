# TT049 — the screening benefit carries to fresh sources, with limits

TT049 completed on **31 October 2026 at 14:40:47 UTC**. Production took
2 h 36 m 21 s on two CPUs, after 10 m 22 s of excluded qualification. The
independent saved-evidence review passed on 1 November. All 35 recorded
controller/worker processes have exited. No successor has been launched.

This was the frozen one-read test proposed after TT048 development. It enrolled
**32 new source blocks, eight per writing history, all 512 generation-14 records,
and four new matched receiving futures per record**. All 417 initially passing
and 95 initially failing records remain. Each arm/regime contains 2,048 paired
receiving contexts; population inference uses the 32 independent source blocks.
These are fresh in-domain records, not a new physical model or noise-pairing test.

## Mixed unmarked damage: primary panel

| Arm | Edited records | Intended-task success | Opposite-task success | Mean intended margin |
|---|---:|---:|---:|---:|
| Preserve | 0/512 | 20/2048 — 0.98% | 7/2048 — 0.34% | -0.8070 |
| Forest repair | 512/512 | 332/2048 — 16.21% | 242/2048 — 11.82% | -0.4220 |
| Screened forest | 170/512 | 344/2048 — 16.80% | 247/2048 — 12.06% | -0.5576 |

The screen avoids 342/512 edits (**66.80%**) and preserves every observed
intended rescue from unconditional forest repair. Relative to preservation,
both methods rescue **329** receiving contexts. Unconditional repair harms 17
previously successful contexts; screening harms five. The screen's 12 extra
intended successes therefore come entirely from preserving existing success.
Eleven records have a higher four-future success mean than under unconditional
repair; 501 tie and none have a lower mean. Nine block means improve and 23 tie.

There are still five paired harms versus preservation, affecting five record
means, and no guarantee that rescue retention holds outside this finite test.
All record gains/harms and all three paired arm tables remain in the outputs.

Screening also preserves five opposite-task successes that unconditional repair
had removed. Both methods create 240 opposite-task successes where preservation
fails that opposite-task criterion. Thus opposite success rises from 242 to
247 contexts. This is not correction of the intended historical identity.

Average intended margin falls by **.1355** compared with unconditional repair,
in 31 of the 32 blocks. It remains above preservation: the margin improvement
over preservation is +.38495 for unconditional repair and +.24940 for screening.
Some skipped edits help below the binary success threshold. Fewer edits and
higher threshold success do not establish uniform improvement across endpoints.
Every record still pays for forest inference; edited-record counts are not a
measurement of energy, total CPU saving, or later serial reliability.

![Mixed-damage findings](FINDINGS.png)

## The other regimes and wrong-history controls

With sign flips, screening reduces edits from 512 to 194, retains all 359
intended rescues, and reduces paired harms from 34 to 10. Intended success rises
from 369/2048 (18.02%) to 393/2048 (19.19%). Opposite success also rises from
353/2048 (17.24%) to 361/2048 (17.63%), and intended margin falls by .0790 relative
to unconditional repair. These remain separate outcomes.

For original packets, both repairs achieve 1789/2048 (87.35%) intended success,
versus 1670/2048 (81.54%) for preservation. Both retain 10 paired harms against
preservation. With added missing edges, screening gives 1766/2048 (86.23%)
intended success versus 1765/2048 (86.18%) for unconditional repair and 1374/2048
(67.09%) for preservation; paired harms are 13 and 14, respectively. The screen
has no observed rescue loss in any input regime, but this is an empirical result,
not an equivalence or noninferiority claim.

The screen accepts **all 512 records in both wrong-history panels**:

| Control | Intended success, all arms | Opposite success, all arms | Screen edits |
|---|---:|---:|---:|
| Actual opposite founder's learned packet | 0/2048 | 2048/2048 — 100% | 16/512 |
| Balanced wrong-task construction | 0/2048 | 1892/2048 — 92.38% | 0/512 |

Acceptance is distinct from editing: 496 of the learned wrong-history packets
and all balanced wrong packets are accepted unchanged. The balanced aligned
control also receives no edits and achieves 1892/2048 intended successes. All
arms fail on complete erasure. Control labels occur only in construction and
scoring; the screen receives no historical orientation. Every algorithm output
still marks history **UNVERIFIED**.

## Uncertainty and scope

The preregistered all-record S-minus-G quantities for mixed damage are below.
The intervals are **pointwise**, not simultaneous across all endpoints/regimes.
The Welch–Satterthwaite estimates and the much wider distribution-free bounds
must not be presented as equally strong claims.

| Quantity | Estimate | Stratified 95% interval | Bounded 95% interval |
|---|---:|---:|---:|
| Intended success change (pp) | 0.586 | [0.192, 0.980] | [-47.430, 48.602] |
| Opposite success change (pp) | 0.244 | [0.030, 0.459] | [-47.772, 48.260] |
| Intended margin change | -0.136 | [-0.168, -0.103] | [-2.056, 1.785] |
| Edited records avoided (pp) | 66.797 | [62.650, 70.943] | [42.789, 90.805] |

The bounded interval supports a reduction in edit frequency; it does not resolve
the signs of the modest success changes or margin change. When estimated
variance is zero, the frozen method uses a nonzero bounded interval. For example,
zero observed intended rescues lost has a [0, .2401] bounded interval for the
population-average rate, rather than a zero-width certainty claim. No composite
positive verdict or equivalence claim was specified. Four futures still give
coarse estimates for each particular record.

The [production report](runs/fresh_one_read_v1/REPORT.md),
[all summary arrays](runs/fresh_one_read_v1/SUMMARY.npz) and
[all population intervals](runs/fresh_one_read_v1/INFERENCE.json) retain all
regimes, source histories, original pass/fail strata, selected-case denominators,
paired harms and separate margins. Conditional receiving Monte Carlo errors are
kept distinct from source-population intervals.

## Verification and decision

[The completion review](completion_review_v1/REVIEW.json) verified all 48 frozen
inputs, 1,310 production files and 109 qualification files. It checked 480 fresh
source stream births and all 448 source packet-chain links, independently
reconstructed endpoints from 196,608 retained port-window means, independently
reduced 896 block arrays and 62 global arrays, and checked all 104 population
intervals. Screen packet, state and endpoint identities passed. The maximum
compensated-mean discrepancy was 6.66e-16 with no threshold-flag disagreement.
Native source and receiving dynamics were independently replayed during
production; this completion review generated no new physical futures.

The scientific inputs and frozen rule are unchanged. Production retained about
312 MB, below the two-GiB study cap, and finished before its 16:15 UTC conservative
forecast. The closeout and original launch handoff are retained locally.

The supported contribution is a fixed, simple screen that substantially reduces
edits and avoids some harms while retaining the observed binary rescues on new
records. It still accepts coherent wrong history and gives up continuous-margin
improvement. Any attempt to verify or recover historical identity needs a
separate information design, with an explicit historical reference and absent
or misleading-reference controls. These results do not establish serial safety
and do not trigger a large serial confirmation. No new run is active.
