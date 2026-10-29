# TT018: restored records across repeated serial futures

The registered practical primary passes. Repeated repair increases success in a
fresh recipient reading the actual generation-32 outgoing record from **87.52%
to 91.72%**, a gain of **4.20 percentage points**. The one-sided approximate 95%
lower bound is **2.61 points**, above the fixed two-point requirement; the
two-sided interval is **2.29–6.11 points**. This supports a population-average
benefit under the supplied simulator and disturbance law.

The scientific run finished on 13 October 2026 at 21:28:13 UTC, in 16 hours
16 minutes 39 seconds from the original launch, including the operational pause.
All 64 preassigned records and 192 unchanged model forecasts were sealed before
continuation. Each record supplied 64 independent future environments, paired
across the three policies. Population inference uses **64 independent acquisition
blocks**, with sixteen per history. The 4,096 futures per policy improve estimates
for those fixed records; they do not provide 4,096 independent population units.
See the [registered protocol](PROTOCOL.md) and [complete report](runs/validation_two_cpu_v1/REPORT.md).

## The endpoints answer different questions

| Endpoint | Untreated | One-time repair | Repeated repair |
|---|---:|---:|---:|
| Fresh-recipient record success | 3,585/4,096 (87.52%) | 3,688/4,096 (90.04%) | 3,757/4,096 (91.72%) |
| All eighteen bodies pass | 3,191/4,096 (77.91%) | 3,415/4,096 (83.37%) | 3,692/4,096 (90.14%) |
| Generation-32 body passes | 3,587/4,096 (87.57%) | 3,688/4,096 (90.04%) | 3,757/4,096 (91.72%) |

Every branch continues after a failed body and transmits its actual written
successor. The terminal recipient receives a separate injury, reset and forcing
draw, with no additional repair or writing. Last-body and terminal outcomes
disagree in 22 untreated futures and 26 one-time-repair futures; equal aggregate
counts in the latter condition conceal those individual disagreements. They
agree in all repeated-repair futures in this sample, without making the two
endpoints interchangeable.

Uninterrupted body performance improves by 12.23 points with repeated repair
(descriptive two-sided 95% interval 9.85–14.61). Among futures with an earlier
body failure, 406 untreated, 284 one-time and 65 repeated-repair branches still
pass the terminal assay. Conversely, 12 untreated and 11 one-time branches pass
all eighteen bodies but fail the terminal assay. These separate observations
remain in the analysis; they do not alter the primary decision.

## Benefits, harms and record-level uncertainty

For terminal success, the paired comparison retains **213 repeated-only successes
and 41 untreated-only successes**, alongside 3,544 successes under both policies
and 298 failures under both. The estimated record-level difference is positive
for 51 records, negative for three and tied for ten. For uninterrupted performance,
there are 539 repeated-only and 38 untreated-only successes. An average repair
benefit does not imply that every record or future benefits.

Repeated restoration now permits a conditional serial probability estimate for
each fixed starting record and policy. Untreated terminal outcomes vary across
futures for 53 records; eight score 64/64 and three score 0/64. With repeated
repair, 53 score 64/64, three score 0/64 and eight have intermediate counts.
Neither boundary count establishes a true probability of one or zero. For 64/64,
the pointwise exact 95% interval is approximately **[94.40%, 100%]**; the registered
simultaneous interval over the 384 record/policy/endpoint combinations is
**[86.02%, 100%]**. All estimates and intervals are retained in
[record_probabilities.csv](runs/validation_two_cpu_v1/record_probabilities.csv).

Enrollment retained nine currently failing and 55 currently passing bodies.
Here are all nine failing bodies' outgoing records, with terminal successes out
of 64 serial futures per policy. These are descriptive results, without a new
subgroup gate or outcome-based enrollment.

| Record suffix | Untreated | One-time | Repeated |
|---|---:|---:|---:|
| 18000004 | 62 | 64 | 64 |
| 18000007 | 48 | 43 | 46 |
| 18000019 | 34 | 14 | 14 |
| 18000038 | 1 | 1 | 0 |
| 18000039 | 0 | 0 | 0 |
| 18000045 | 30 | 52 | 54 |
| 18000059 | 0 | 8 | 9 |
| 18000060 | 0 | 1 | 0 |
| 18000063 | 51 | 60 | 61 |

This measures repeated futures from particular failed bodies' outgoing records,
going beyond a cross-tabulation of past body histories and one later outcome.
For example, 18000004 has an untreated estimate of 62/64 with a pointwise exact
95% interval of 89.16–99.62%; 18000019 instead loses twenty terminal successes
with either repair policy. The table retains both patterns. Estimates remain
conditional on the fixed record, task, reader, writer, numerical channel, policy
and specified disturbance distribution. One terminal read per descendant still
does not estimate each descendant packet's own repeated-read reliability.

The prespecified split halves show positive within-history covariance for both
endpoints under all policies. Overall correlations for untreated and repeated
terminal success are 0.973 and 0.995. These are descriptive indications of
resolvable differences between starting records, not a newly declared
confirmation of a heterogeneity threshold.

## Forecast transport and computational cost

The unchanged candidate has mean Brier loss **0.054810**, compared with **0.065100**
for expression/history and **0.067711** for expression/history/unsigned. The
secondary gains are 0.010291 (two-sided interval 0.000060–0.020521) and 0.012901
(−0.000268–0.026071). The latter two-sided interval includes zero. These secondary
comparisons do not inherit TT008's separate primary margin or become new primary
gates for TT018.

Descriptive AUCs are 0.8792, 0.8737 and 0.8700. All three models underpredict
average untreated terminal success by about 2.1–2.3 points. Fixed-bin absolute
calibration errors are 0.03558, 0.03886 and 0.03596. No models were fitted or
recalibrated here. All retain their supplied task orientation and original
expression/history access. The candidate uses 64 signed plus 64 unsigned
operator iterations; its unsigned rival uses 64 unsigned iterations.

One-time repair uses **4,096** optimizer calls; repeated repair uses **73,728**.
The extra repeated-versus-one-time terminal gain is 1.68 points (descriptive
interval 1.23–2.13). Measured production repair CPU time is approximately 118.46
and 2,177.63 seconds, with separate audit costs of 222.33 and 4,089.44 seconds.
These are optimizer costs, not the total simulation cost. This unequal-budget
comparison does not show superior repair efficiency or identify when repair
should be scheduled.

## Provenance and scope

The user's two-CPU request changed execution scheduling after acquisition began.
The [amendment](EXECUTION_TWO_CPU_AMENDMENT.json) preserves the same registered
cohort, original 43 scientific/runtime inputs, six registration/context inputs,
random streams, models, policies, endpoints, analysis and absolute deadline.
All 513 inherited checkpoint files were retained. The qualified scheduling
extension passed 1,603 byte-exact array comparisons. A delayed startup receipt
required a disclosed administrative recovery, with no restart of the new job.
The [execution record](EXECUTION.md) retains this history.

Full independent dynamics and optimizer replay ran alongside the scientific
computation. The completed run retains 14,336 preliminary, 221,184 serial and
12,288 fresh-terminal contexts, plus 77,824 independent optimizer checks.
The post-completion [closeout](CLOSEOUT.json) verifies all 6,800 committed output
files, the handover and original input commitments, 62,400 native array receipts,
retained endpoint scores and exact regeneration of the analysis and report.
The closeout verifier was prepared after completed-result inspection; it does
not supply a second prospective cohort or rerun trajectories.

This is prospective evidence within the declared apparatus. The population
confidence bounds use an approximate stratified method, and record-level
intervals remain limited by 64 futures. The study does not isolate message-specific
corrective information supplied by a surviving body, establish autonomous
heredity, or establish a uniquely necessary theoretical explanation. An equal-budget
scheduling comparison and the separate body-source causal experiment remain
different questions. No successor has been launched.
