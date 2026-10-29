# E112 — Fresh-source component-sensitivity prediction

**Complete and verified.** Finished **28 October 2026 at 16:26:22 UTC**, in
**2 h 23 min 49.17 s**, including independent replay. Closeout passed at
**20:54:33 UTC**: **2,913 outputs / 114 frozen inputs** verified, figure
inspected, **2.46 GB** retained. All 32 sources and 4,096 comparisons remain.

The sole mixture primary is **UNRESOLVED**: gross shared-minus-cue sensitivity
is **+0.551 points [0.000, 1.460]**. Its lower bound is exactly zero and fails
the frozen requirement to exceed zero. The excess comes from three comparisons
in two source histories. Native excess is +1.418 [0.181, 3.167], a secondary
pointwise result; continuous endpoints also retain an exploratory lead.

The earlier tradeoff repeats: mixture pruning improves immediate success by
**7.227 points** but harms success after paired writing by **4.199 points**.
After independent writing the mean pruning effect is unresolved, with **109
individual gains and 108 harms** retained. See the [interpretation and
manuscript wording](INTERPRETATION.md), [report](runs/prediction_v1/REPORT.md),
[figure](runs/prediction_v1/endpoints.png) and [closeout](analysis/closeout_v1.json).

The run used four workers / one numerical thread each, finishing within the
original 4h00m forecast and 10.10 GB reserve. No retry, extension or successor.

E111 suggested that exchanging the shared halfway activity changes the sign-flip
effect more than exchanging the cue-dependent component. E112 tested that ordering
on 32 new source histories, with one mixture primary fixed before generation.

- [Protocol](PROTOCOL.md): prediction, cohort, structural eligibility, endpoints,
  uncertainty, interpretation limits and bounded runtime.
- [Data dictionary](DATA_DICTIONARY.md): all raw fields, source boundaries,
  individual harms and provenance.
- [Predecessor interpretation](../E111_halfway_component_cross/INTERPRETATION.md).

The full original genealogy and both earlier functional endpoints are preserved.
Unneeded intermediate terminal comparisons are omitted. Excluded cases verify
that this combined pipeline exactly reproduces the existing separate experiments.

The [technical checks](analysis/tests_attempt_001.json) passed in **5.27 s**.
The two excluded histories and their complete endpoint/component pipeline passed
in **127.30 s**, with **300 output hashes** verified and the figure inspected.
All numerical fields in **112 ancestry/endpoint archives** matched, followed by
the static donors, interventions, phase histories and all eight E111 outcomes.
See the [excluded report](runs/benchmark_v1/REPORT.md).

The initial runtime projection scaled small batches with only five/two
eligible contexts. A separate [capacity probe](analysis/capacity_v1.py) measured
the full 64-context, four-recipient width using excluded donor weights and a
short schedule. It forces allocation only for timing, with C=F, and produces no
scientific inference. The scientific sample, genealogy and outcome rules remain
unchanged; the qualified forecast retains a 3× timing allowance. That check
passed in **227.12 s**, with **150 outputs** verified.

[Qualification](analysis/qualification_v1.json), [forecast](analysis/forecast_v1.json),
[sample freeze](SAMPLE_FREEZE.json), [startup receipt](jobs/prediction_v1/startup.json),
[launch/log directory](jobs/prediction_v1), [durable status](runs/prediction_v1/STATUS.json).

One bounded startup check and user-requested status checks were performed under
the [execution policy](../RUN_POLICY.md). The process has exited.

No automatic extension, restart or successor. Integration remains with the
separate manuscript agent.

Subsequent user-authorized follow-up: [E113](../E113_component_threshold_diagnosis/README.md)
completed in **97.39 s**, closeout **28 October 21:54 UTC** passed. It found m
swaps about 17× larger than d and 88–89% cancellation of m success movement
in C−F. It used saved data without new dynamics and leaves this completed
primary unchanged. A matched-amplitude intervention remains a candidate.
