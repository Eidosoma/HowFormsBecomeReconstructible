# TT018 serial reliability from restored records

TT018 is **complete**, with its registered practical primary and retained-evidence
closeout both passing. Repeated repair yields **3,757/4,096 (91.72%)** fresh-recipient
successes, versus **3,585/4,096 (87.52%)** untreated. The gain is **4.20 percentage
points**, with a one-sided 95% lower bound of **2.61**, above the fixed two-point
margin. The two-sided interval is **2.29–6.11** points. Population inference uses
64 independent acquisition blocks; each fixed record has 64 future environments.
See the [interpretation](INTERPRETATION.md), [full report](runs/validation_two_cpu_v1/REPORT.md)
and [closeout](CLOSEOUT.json).

Uninterrupted performance across all eighteen bodies is **90.14%** with repeated
repair versus **77.91%** untreated. This is a separate endpoint. Terminal paired
outcomes retain 213 repeated-only successes and **41 untreated-only successes**.
Three records have a negative estimated repair effect. All nine initially failing
bodies remain enrolled, with each outgoing record assessed across 64 serial futures.
Individual probability estimates and pointwise/simultaneous uncertainty remain in
[record_probabilities.csv](runs/validation_two_cpu_v1/record_probabilities.csv).

The unchanged forecast candidate has lower mean Brier loss in this secondary
transport test. All models underpredict average untreated terminal success;
the candidate's two-sided improvement interval against the unsigned rival includes
zero. Repeated repair uses eighteen calls per chain, versus one for one-time
repair. No equal-budget efficiency or body-source causal claim follows.

The run finished on **13 October 2026 at 21:28:13 UTC**, after **16 hours 16 minutes
39 seconds** from the original start, including the operational pause. At the
user's request, a qualified extension moved the same cohort to two CPU cores,
preserving 513 checkpoint files and all 43 original runtime plus six registration/context
inputs. The original absolute 48-hour deadline remained fixed and was met.
The initial 43.47-hour and later 33.87-hour estimates were conservative forecasts;
they are not a controlled measurement of the realized speedup.

Full native replay ran during execution. Post-completion closeout verifies all
6,800 committed outputs, 62,400 native array receipts, actual successor chains,
registered random-input construction, retained repair construction, raw endpoint
scoring and exact regeneration of analysis/report files. The closeout verifier
was prepared after completed-result inspection and generates no new trajectories.
See [execution](EXECUTION.md), [current execution](CURRENT_EXECUTION.json),
[registration](REGISTRATION.json), [protocol](PROTOCOL.md) and
[execution amendment](EXECUTION_TWO_CPU_AMENDMENT.json).

Preparation history remains preserved: [source review](EVIDENCE_REVIEW.md),
[source bindings](SOURCE_REVIEW.json), [design checks](checks/design_v1/RESULTS.json),
[original draft](DRAFT_PROTOCOL.md), [prelaunch protocol](launch_inputs/TT018/PROTOCOL.md),
[registration-search correction](REGISTRATION_SEARCH_REVIEW.json),
[original qualification](runs/native_v3/qualification.json) and
[two-worker qualification](two_cpu_v1/checks/qualification_v2/COMPLETE.json).
The original launch and prior handoffs retain their historical status fields.
All TT018 test blocks are now exposed. No successor is running.
