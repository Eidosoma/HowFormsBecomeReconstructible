# TT040 — informative-record tradeoffs


[TT040 packet-integrity timing development](README.md) is **complete and
reviewed**. The four fixed exposed source blocks finished at 11:57:53 UTC on
24 October 2026 in **1 hour 17 seconds**, on two single-thread CPUs. All new
physical checks passed. The result is a tradeoff, not a confirmation of repair
without cost.

In the prespecified residual-family, own-source, all-mask comparison, late
writing minus preservation changes fractional original-target recognition by:

| Incoming packet | Body at 1900 (pp) | Fresh recipient (pp) |
|---|---:|---:|
| Intact | -3.9063 | -1.6602 |
| Half-mixed with noise: primary | -1.1719 | +1.5625 |
| Fully replaced | +6.6406 | +13.1836 |

For half-mixed packets, recipient credit rises from 76.1719% to 77.7344%, while
body credit falls from 76.9531% to 75.7813%. Recipient block effects are -0.7813,
+3.9063, 0 and +3.1250 points; body effects are -3.1250, 0, -1.5625 and 0.
Among 64 source-position means, recipient changes retain **15 gains / 10 harms /
39 ties**, and body changes retain **2 gains / 6 harms / 56 ties**. These 64
positions are dependent within the four source blocks.

Intact residual packets decline from 86.7188% to 85.0586% recipient credit.
Their changes retain 6 record gains, 15 harms and 43 ties; body changes retain
3 gains, 11 harms and 50 ties. Fully replaced packets improve on both endpoints
on average, but those gains cannot rescue the informative-record losses.
The common-family half-mixed averages also favor preservation: -0.7813 body
and -0.6836 recipient points.

This is a small development experiment on exposed sources, with one corruption
realization and four new receiving conditions per block. Mixture weight .5 is
an amplitude weight, not a fraction of information erased. No significance,
noninferiority, absence-of-harm or fresh-confirmation claim is made. All cases,
controls and paired harms remain. TT028 primary/joint and TT036/TT039
confirmation classifications are unchanged; no serial inheritance was tested.

Completion review rehashed all **7,964 retained outputs**, checked source and
frozen-input bindings, reconciled all three mixture panels and five body
checkpoints, and independently reduced the primary saved rows for all four
arms, four credits and six contrasts. The run replayed 68,800 native arrays,
performed 41,984 new receiving assays and used 16 new receiving conditions
shared across damage levels. Source states were reused from TT039. All
processes have exited, and no successor has started.

See [report](runs/damage_v1/REPORT.md), [findings](FINDINGS.json)
and [review scope](CLOSEOUT.json).


The four source identities are 39010000, 39010016, 39010032 and 39010048,
selected by position in the prior ordered cohort rather than outcomes.
All four schedules were retained: preservation, early 1-100, late 901-1000 and
full 1-1000. Every body continued to 1900 with writing off after 1000. Fresh
receiving conditions paired birth and forcing across every mixture, schedule,
family, physical mask and own/foreign/neutral body source. Intact preservation
equals the original packet byte for byte, with the same physical receiving assay.

Residual own-source record-mean joint tables retain opposing outcomes. For
half mixing, one record improves on both endpoints, two decline on both,
three change in opposing directions and 58 tie on at least one endpoint.
Recipient improvements therefore do not imply simultaneous body improvements.
The positive-half-retained primary stratum has +8.9844 recipient and +3.1250
body points; the negative-half stratum has -2.7344 and -1.5625. Mixed halves
have zero mean recipient change and -3.1250 body points, while retaining
10 recipient gains and 10 harms. Geometry is descriptive and task-aligned;
it does not supply an autonomous repair policy.

Early writing also harms intact residual inputs (-8.4961 recipient and -8.5938
body points) and half-mixed inputs (-2.0508 recipient and -4.2969 body points)
relative to preservation. Full writing has larger residual mean losses in
both informative-packet panels. These secondary comparisons do not establish
optimal timing or a safe schedule. A positive complete-replacement result
does not establish benefit for every damage level or individual record.

The frozen run and all outputs are unchanged. Closeout independently verifies
saved-row arithmetic and all retained hashes; it does not rerun the physical
trajectories. Independent physical replay passed during acquisition. The
original qualified input snapshots and the prior handoff remain retained in
[the completion archive](completion_handoff_inputs/MANIFEST.json).


TT041 now supersedes the no-successor status above. The authorized saved-state
diagnosis is complete and reviewed; see [TT041](../TT041/README.md). TT040
scientific results and frozen artifacts are unchanged. No TT042 run is active.
