# Leads on rebuilding from E025's saved packets

Implementation update: the four-packet intervention below is complete and
audited as [E026](../../E026_restoration_intervention/README.md). Adding restored
connections raised scattered-terminal success from 62.1% to 83.0%; removing
them from the rebuilt record lowered 80.1% to 60.9%. E026 records the post hoc
effects and limits; this note retains the original exploratory rationale.

21 September 2026. This is an **exploratory description after seeing E025's
outcomes**, not a new confirmation or causal mechanism test. Both short
analyses retained all 32 blocks and all three boundaries. They read selected
members of saved arrays and verified all 96 boundary-file hashes against the
completed cohort. No new trajectories were simulated and no earlier result
or frozen scientific input was changed.

Rebuilding can write at a coordinate missing in an earlier body because
each replacement starts on a fresh lattice before its new injury. Cumulative-
erasure copying cannot restore those coordinates. Actual saved packets show:

| Renewal | Candidate nonzero connections | Copy nonzero connections | Candidate nonzero connections at previously erased, currently available coordinates | Of those, strong connections |
| --- | --- | --- | --- | --- |
| 1 | 420.45 | 420.45 | 0 | 0 |
| 2 | 419.78 | 345.90 | 73.88 | 0 |
| 3 | 419.56 | 285.24 | 134.32 | 47.46 |

Entries are mean counts per 512-edge packet across all 512 lineages. A
coordinate is "previously erased" if a renewal mask removed it at least
once; "strong" means absolute weight >0.5, declared before computing these
descriptions. Numerical nonzero alone does not establish useful connectivity.

The number of reappearing connections does not explain the whole result.
After three renewals, baseline, degree-compensated and strength-compensated
rewriting each retain approximately 419.6 nonzero connections. Their mean
numbers of **strong restored connections** are **0.12, 0.16 and 47.46**,
respectively. Their already-audited scattered-terminal both-cue success with
the same normalized reader is **26.8%, 33.2% and 80.1%**. These comparisons
motivate a mechanism test; they do not identify which packet differences
caused the performance differences.

The scale check suggests a possible two-step process. At generation two,
candidate weights at previously erased, currently available coordinates
have median magnitude **0.0000261** and mean **0.000612**; none exceeds .5.
At generation three, **35.15%** of weights in that coordinate category exceed
.5. The coordinate sets differ across generations, so these aggregate
descriptions do not establish a paired maturation rate for individual links.
Shared coordinates that survived every injury remain much stronger (mean
magnitude **0.98975** at generation two and **0.98509** at generation three).

Local normalization can give weak inputs a larger relative influence where
little incident strength remains. One hypothesis is that weak reappearing
connections influence the next body's activity and then become stronger
when activity is written again. The observed sequence is consistent with
that hypothesis; its causal contribution to the 18-point advantage is untested.
A sensitivity test should distinguish useful weak signals from noise-driven
effects. In the saved third renewal, positive live-cell denominators were
above 1e-12; the present descriptions do not establish a floating-point artifact.

Rebuilding does not simply reproduce every original sign. On restored
coordinates, the candidate's sign agrees with the protected original on
about **49.8%** of nonzero connections at generation three; agreement on
coordinates surviving every injury is **99.97%**. These are mean within-lineage
fractions. Original sign agreement is not a functional correctness test.

The recommended first intervention separates two changes in the final
packet. Let C be the coordinates surviving every renewal injury, and T the
coordinates erased earlier but physically present at generation three.
The existing copied packet M is zero outside C; rebuilt packet R can write
on both C and T. Compare four packets in otherwise paired terminal assays:

| Diagnostic packet | Values on C | Values on T |
| --- | --- | --- |
| Existing cumulative-erasure copy | Copied | Zero |
| Copy plus restored connections | Copied | Rebuilt |
| Rebuilding with restoration removed | Rebuilt | Zero |
| Existing rebuilt packet | Rebuilt | Rebuilt |

Keep terminal births, noise and injury paired, use the frozen scoring rule,
and recompute the receiving denominator after each intervention. Replay the
two existing endpoints against their saved assays as a technical check.
The new contrasts would test necessity and contribution of restored
connections separately from changed values on surviving connections,
including an interaction between the two. They identify contributions of
the final packet, not the entire history of rebuilding. This would be a
post hoc causal diagnostic; a fresh cohort would be needed for a new
prospective confirmation.

If restored connections matter, the next intervention can suppress or alter
only their weak generation-two precursors before the third renewal, testing
the proposed weak-connection-to-strong-connection sequence. No such functional
intervention, new cohort, or long run has been started.

The first description took **12.35 seconds** on one CPU and saved **6144
lineage-condition-generation rows**. The follow-up scale check took **11.72
seconds** on one CPU. All descendants and edges are nested within blocks;
no inferential test or independent-edge sample claim is made.

[Count-analysis code](rebuilding_leads.py),
[count summary](rebuilding_leads_v1/summary.json),
[lineage rows](rebuilding_leads_v1/lineages.csv),
[count-analysis completion](rebuilding_leads_v1/COMPLETE.json),
[scale-analysis code](rebuilding_link_scale.py),
[scale summary](rebuilding_link_scale_v1/summary.json),
[scale-analysis completion](rebuilding_link_scale_v1/COMPLETE.json).
