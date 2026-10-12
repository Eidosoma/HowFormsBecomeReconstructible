# Prospective repair call efficiency

The frozen criterion is UNRESOLVED. All 2112 records in 132 fresh blocks remain enrolled, including failures at the common first repair. All three schedules continue after failure.

| Repairs | Uninterrupted success | Terminal success | Later losses after first success |
|---:|---:|---:|---:|
| 1 | 1761/2112 (83.38%) | 1884/2112 (89.20%) | 118 |
| 6 | 1833/2112 (86.79%) | 1911/2112 (90.48%) | 46 |
| 18 | 1879/2112 (88.97%) | 1925/2112 (91.15%) | 0 |

The primary prediction requires both continual repair to improve uninterrupted success over one initial repair, and six repairs to supply more than twice the added benefit per additional repair call of eighteen repairs. Additional calls are five and seventeen. Equivalently, G = p18 - p1 > 0 and D = p6 - (10/17)p18 - (7/17)p1 > 0. Both one-sided 95% lower bounds must be strictly positive. This is a conjunction; terminal recovery cannot rescue it. A negative verdict requires either one-sided 97.5% upper bound below zero, guarding the two possible negative components. Otherwise the verdict is unresolved.

| Frozen contrast | Estimate in percentage points | One sided 95% lower bound |
|---|---:|---:|
| continual_benefit | 5.587 | 4.782 |
| double_call_efficiency | 0.123 | -0.395 |

The observed ratio of added benefit per additional repair call is 2.0745762711864417; it is undefined when the continual-minus-once benefit is not positive. All history strata, direct schedule contrasts and paired rescue/harm counts are retained in analysis.json.

| Repairs | Total calls | Added edge events | Added absolute weight | Repair CPU seconds |
|---:|---:|---:|---:|---:|
| 1 | 2112 | 194916 | 176402.958 | 21.103 |
| 6 | 12672 | 1161786 | 1132607.264 | 130.705 |
| 18 | 38016 | 3481916 | 3428938.905 | 391.988 |

The fresh cohort contains 1879 common-first-pass records and 233 common-first-fail records. Conditional maintenance is secondary and retains its own pooled denominator. Inference resamples whole paired blocks within four equally weighted history strata. Bootstrap coverage is approximate, and all secondary intervals are descriptive.

The schedules and doubled-efficiency target were chosen after a five-budget development curve on separate exposed blocks. The target gives a concrete resource criterion without declaring an acceptable absolute loss in performance: six calls must preserve more than 10/17 of the added benefit at 5/17 of the additional calls. This is not noninferiority, a minimum budget or proof of an optimal schedule. Call counts do not measure total CPU, added weight or sensing cost.

Teaching, the first fourteen renewals, every continuation and every control are newly generated under reserved namespaces. Ongoing cue noise is independent; teaching and reset pairing remain matched. The ordinary sign-graph repair, reader, writer, ports and resources remain supplied. No unique RDT mechanism or autonomous maintenance follows from this comparison.

All optimizer results, preparations, captures, injury/noise streams, schedules, quotas, endpoints and tables receive separate checks. Independent flat dynamics cover teaching, one generation-14 case, and all three schedules at cases 0 and 14 at generations 15 and 32 in every block. These are same-lane internal checks, with selected rather than exhaustive continuation dynamics replay. The cohort is fixed; no optional extension, interim scientific verdict or automatic successor is used.
