# TT036 — fresh-cohort stopped writing


[TT036 fresh-cohort stopped-writing confirmation](README.md) is **complete
and reviewed**. All 64 fresh blocks finished at 2026-10-21T15:20:11.363336+00:00
in **5 hours 18 minutes 43 seconds**, using two single-thread CPUs. All frozen
checks passed: 362,944 native arrays independently replayed, 512 new paired
receiving environments, 303,104 physical recipient assays, and all 196,608
labelled paired rows retained. Both job and controller have exited.

The registered joint criterion **CONFIRMED_JOINT_STOPPING_BENEFIT** passed.
For residual-family own-source all-mask original-target recognition:

| Writing updates | Terminal body credit | Fresh-recipient packet credit |
|---|---:|---:|
| 0: preservation | 43.09% | 25.00% |
| 100: stop writing, continue body | 40.16% | 40.70% |
| 1,000: continuous writing | 32.43% | 31.32% |

Stopping at 100 increases body credit by **7.7271 percentage points** and
packet credit by **9.3811 points** versus continuous writing. The respective
one-sided alpha .025 lower bounds are **6.9333 and 8.6488 points**; pointwise
95% intervals are **[6.9333, 8.5208]** and **[8.6488, 10.1134]**. All 64 block
means are positive for both endpoints. These are approximate paired-block
Student-t results with Bonferroni family alpha .05. Conservative bounded
Hoeffding sensitivity lower bounds remain negative (-26.23 / -24.57 points).

Paired harms remain: body record means have **474 gains / 82 harms / 468 ties**;
packet record means have **725 / 209 / 90**. Of 1,024 record means, **384**
improve on both endpoints, **39** decline on both, **48** improve the body while
harming the packet, **32** improve the packet while harming the body, and
**521** have at least one tied endpoint. These counts are descriptive.

Preservation remains a tradeoff: 100 writes gain **15.6982 packet points** but
lose **2.9297 body points** versus no writing. The common family shows the same
mean ordering (100 versus 1,000: +6.1890 body / +7.0160 packet points).
Residual negative-half and mixed-half retention benefit on both endpoints;
positive-half retention loses **2.2461 body / 12.5122 packet points**.

This fresh-cohort result supports the fixed stopping rule's average benefit
under uniform memory reset, fully replaced incoming packets and the stated
source/recipient distribution. It does not establish 100 updates as optimal,
universal benefit, uninterrupted body performance, or serial heredity.
Four recipient draws per fixed packet remain coarse conditional evidence.
TT028 primary and joint classifications remain NOT_CONFIRMED.

The review independently reduced the primary saved rows and reconciled all
block aggregates, weights, count denominators, joint tables, registered
inference and the report. Full physical replay and complete source/output
checks passed during acquisition and were not repeated in this review.
No successor has been started. See [report](runs/confirmation_v1/REPORT.md),
[registered inference](runs/confirmation_v1/INFERENCE.json),
[findings](FINDINGS.json) and [review scope](CLOSEOUT.json).

Prior handoff documents are preserved in [the completion archive](completion_handoff_inputs/MANIFEST.json).

Authorized successor TT037 is qualified and queued for an equal-budget early-versus-late writing diagnosis on these now-exposed cases, retaining both endpoints and all controls and harms. See [TT037 execution](../TT037/CURRENT_EXECUTION.json). Prior completion-bound documents are preserved in [the TT037 intake archive](../TT037/intake_inputs/MANIFEST.json).

TT037 is complete and reviewed. At equal 100-write budgets, early minus late changes residual own-source all-mask body credit by -3.2593 points and packet credit by +1.0742 points. This is descriptive timing development on exposed TT036 cases; the TT036 confirmation is unchanged. See [TT037 findings](../TT037/README.md). No successor is running.
