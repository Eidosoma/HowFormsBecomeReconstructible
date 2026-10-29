# TT039 — fresh confirmation of late writing


[TT039 fresh late-writing confirmation](README.md) is **complete and
reviewed: CONFIRMED_JOINT_LATE_WRITING_BENEFIT**. All 64 newly reserved blocks
finished on 23 October 2026 at 23:51:57 UTC, in **11 hours 40 minutes 17 seconds**
on two CPUs. Both co-primary endpoints pass the frozen late-minus-preservation
comparison in the residual family, own source, averaged over all four masks:

| Mean original-target recognition credit | Preservation | Late writing | Difference | Registered lower bound |
|---|---:|---:|---:|---:|
| Body at update 1900 | 39.16% | 43.21% | +4.0527 pp | +3.2630 pp |
| Fresh recipient after 1000 updates | 25.00% | 39.44% | +14.4379 pp | +13.6252 pp |

These are fractional recognition scores, not binary success rates. The decision
uses 64 paired block means, approximate Student-t bounds, one-sided alpha .025
per endpoint, Bonferroni family alpha .05 and margin zero. Both bounds exceed
zero. The conservative Hoeffding sensitivity bounds do not; no minimum practical
gain or distribution-free positive result is established.

All harms remain: body record means have **389 gains / 163 harms / 472 ties**;
recipient record means have **853 gains / 91 harms / 80 ties**. Negative-half
retention favors preservation by 3.0273 body and 4.0527 recipient points.
The later body advantage mainly reflects preservation declining after update
1000; the late-writing mean changes by -0.2197 points versus -4.3213 for
preservation. This does not establish stability of every body.

The run independently replayed 719,808 native arrays and performed 442,368 new
receiving assays across 512 new receiving conditions. Completion review checked
715 saved artifacts, all five checkpoint summaries, paired harms, and independent
primary-row and confidence-bound calculations. No interim scientific inspection
occurred. The initial validation-only timing failure and correction remain
preserved. All processes have exited. This fixed-schedule result does not establish
optimal timing, uninterrupted performance, indefinite stability, independent
teaching cues, general damage robustness or serial heredity. TT028 primary/joint
and TT036's confirmation classifications are unchanged. No successor has started.

See [report](runs/confirmation_v1/REPORT.md), [findings](FINDINGS.json)
and [review scope](CLOSEOUT.json).


The prespecified writing windows were preservation (no writing), early (1–100),
late (901–1000), and full (1–1000). All bodies continued to update 1900, with
writing off after 1000. Every outgoing packet was tested in four fresh receiving
conditions per corruption, with matched recipient birth and forcing across arms.
No production source states or recipient outcomes were inherited from TT038.

| Schedule | Body at 1000 | Body at 1900 | Fresh-recipient credit |
|---|---:|---:|---:|
| Preservation | 43.48% | 39.16% | 25.00% |
| Early | 39.70% | 40.47% | 40.19% |
| Late | 43.43% | 43.21% | 39.44% |
| Full, then hold | 31.62% | 32.47% | 31.60% |

The pointwise two-sided 95% intervals are **+3.2630 to +4.8425 body points**
and **+13.6252 to +15.2505 recipient points**. The conservative distribution-free
Hoeffding lower sensitivities are -29.8998 and -19.5147 points, respectively.
The frozen gate uses the approximate Student-t rule. No secondary result can
rescue that gate. Blocks are the independent population units; record means,
physical masks, corruption draws and receiving draws are dependent observations.

Among 1,024 primary record means, 336 improve on both endpoints, 22 decline on
both, 153 move in opposing directions, and 513 tie on at least one endpoint.
Body block means improve in 55 blocks, decline in five and tie in four;
recipient block means improve in all 64. The late body's own 1900-minus-1000
change still has 354 record gains, 352 harms and 318 ties.

The common family has the same average direction: +3.8696 body and +14.7064
recipient points. Source and damage geometry matter: residual foreign-source
late-minus-preservation averages are -1.2939 body and -1.4648 recipient points.
Early writing gives 0.7538 more recipient points than late writing, while late
gives 2.7466 more body points. These are descriptive secondary comparisons.
All original histories, four credits and six arm contrasts are retained.

Freshness is supported by the reserved identities, declared random-seed inventory
and preproduction freeze. The identity search was bounded locally and is not
independent custody or global proof of non-use. Teaching and repair cues retain
their declared coupling. The finite channel is 256 binary64 values (2048 bytes).
No descendant chains were tested, and each packet's four receiving conditions
per corruption provide only a coarse estimate of its individual reliability.

The completion review reconciled all block receipts, all five checkpoint
aggregates, global weights/counts/joint marginals, within-arm changes, independent
integer reductions of primary saved rows, and the frozen decision. Full physical
replay and raw output checks passed during acquisition; closeout did not repeat
every physical trajectory or rehash every raw output. Review scope is explicit
in CLOSEOUT.json. The failed qualification v1 and its validation-only correction
are retained; v2 qualification and benchmark passed before the production freeze.

The prior handoff is preserved in
[the completion archive](completion_handoff_inputs/MANIFEST.json). The recorded
correction is in [CORRECTION.json](corrections/metadata_timer_v1/CORRECTION.json).

Authorized successor TT040 is preflight checked and queued for detached qualification: four exposed source blocks, three packet mixtures, all four writing schedules, matched fresh recipients and retained harms. TT039 confirmation is unchanged. See [TT040 current state](../TT040/CURRENT_EXECUTION.json). Prior handoff-bound documents are preserved in the TT040 intake archive.

TT040 is complete and reviewed on four exposed source blocks. For half-mixed residual records, late writing gives +1.5625 recipient points with -1.1719 body points; intact records lose 1.6602 recipient and 3.9063 body points. This bounded development result does not change TT039's full-replacement confirmation. See [TT040 findings](../TT040/README.md). No successor is running.
