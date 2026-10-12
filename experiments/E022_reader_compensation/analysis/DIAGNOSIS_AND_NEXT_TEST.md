# E022 transmission diagnosis and next causal test

20 September 2026. The authorized saved-state lead is complete and independently
verified. It retains all 32 blocks and every condition. This descriptive review
leaves E022's positive primary improvement and failed full qualification intact.
No new trajectories were part of this diagnosis. The user subsequently
authorized the test below as [E023](../../E023_receiver_compensation/README.md).
Its fresh cohort is now complete and independently audited: primary and full
qualification passed after one damaged renewal boundary. E023 changes the
receiving apparatus; it does not revise E022's original-reader result.

## Correct activity is captured exactly

| Renewal reader | Correct at capture, both cues | Fresh intact body | Fresh scattered-loss body |
| --- | --- | --- | --- |
| Unchanged | 399/512 | 345/512 | 97/512 |
| Degree compensated | 507/512 | 433/512 | 125/512 |
| Strength compensated | 512/512 | 444/512 | 130/512 |
| Intact renewal reference | 512/512 | 512/512 | 448/512 |

Instantaneous and final-32-update body classifications agree for **every
individual cue in every body branch**, including blocked controls. Thus the
512/512 compensated body result is not an averaging artifact. All **3072
computed capture packets** rebuild byte-for-byte from saved activity. Incoming
record erasure, copying, physical zeros and transmitted records also match.
The protected packet is unaffected by later holding dynamics.

## The surviving record is strong and sign-compatible

Damaged renewal leaves **91.70 of 512 edges zero on average (17.91%)**. In
baseline, degree and strength conditions, every zero edge is incident to a
missing renewal cell; no additional zero appears on a surviving edge. Masked
copying has exactly the same support. Strength compensation increases mean
absolute surviving weight to **0.989964**, versus **0.969440** in the original
record on those same edges. It changes only **0.02094%** of surviving nonzero
edge signs relative to the original, on average.

For the strength candidate, all eight output cells remain reachable from an
input through nonzero edges in **every lineage and every terminal injury
panel**. The mean weakest-output widest-path capacity is approximately
**0.9900** in all three panels. These paths ignore signs, so we additionally
checked the signed graph: all **512/512** candidate records in each panel
admit consistent node signs in the input-connected component, with all four
input cells constrained to +1 and all eight output cells matching their rule.
No candidate failure belongs to the disconnection, signed-conflict or
output-cell-sign-mismatch categories.

These are static consistency checks. They show that a task-compatible sign
pattern remains available, not that the reader must reach it. Signed
consistency is also not necessary for empirical success: protected copying
succeeds in all 512 intact assays even though 44 records have at least one
exact-nonzero sign conflict in their input-connected component. Neither path
strength nor graph consistency replaces a functional endpoint.

## Failure appears in reconstruction dynamics

The strength candidate fails in **68 intact**, **382 scattered-loss**, and
**106 square-lesion** fresh bodies, despite their compatible signed graphs.
Most incorrect individual-cue responses have substantial output amplitude
with incorrect polarities:

| Terminal injury | Incorrect cues | Weak-output cases | Substantial amplitude, wrong polarity |
| --- | --- | --- | --- |
| Intact | 68 | 12 | 56 |
| Scattered | 428 | 32 | 396 |
| Square | 106 | 15 | 91 |

These cue counts are nested within 512 lineages. The strict 0.25 criterion and
original port averages are unchanged. Simply lowering that threshold would
not correct the wrong-polarity cases.

Recorded cue opposition covers **99.99495%** of surviving cells at capture.
In fresh bodies, mean endpoint cue opposition among cells with nonzero
incident weight is **95.26% intact**, **67.05% scattered** and **92.42% square**.
This describes the reconstructed states; it is not an additional task score.

No simple deficit in weight immediately around output cells separates the
failures. For example, mean total absolute incident weight at outputs is
3.807 in failed intact assays versus 3.764 in successful ones; weakest-output
path capacities are approximately 0.990 in both subsets. These conditional
descriptions neither establish a causal mechanism nor rule out effects of
distributed missing edges.

Masked copying provides a useful control. In the scattered panel, both
candidate and copy fail for 350 lineages, both succeed for 103, the candidate
alone succeeds for 27 and the copy alone succeeds for 32. Improving surviving
record values has not removed the large shared deficit under this injury.

The terminal injury panels are separate fresh-body assays, with different
birth/noise realizations between injury panels. Their paired lineage tables
do not describe successive injury and recovery of one living body. Reader
and packet conditions share the appropriate realizations within each panel.

## Next test: compensation in the receiving body

The next prospective intervention should change only the fresh body's reader
for a fixed incoming packet. Compare denominator four against the sum of
absolute effective incident weights, with zero incoming contribution when
that denominator is zero. Use compensation in both reading stages while
keeping the staged clock, gain, noise, packet, writer and injury severity
unchanged. Pair packet, birth, noise and mask across the two receiving readers.

The frozen baseline coupling is `2*(S_i/4 - v_i)`. Removing incident record
edges reduces the incoming term while leaving the subtraction unchanged.
Local normalization changes that balance throughout the network. This follows
from the update rule and motivates an intervention; the saved-state findings
do not uniquely establish it as the cause. Normalization also changes effective
coupling symmetry despite reciprocal stored edges.

Use a fresh cohort and retain E022's packet conditions: baseline, degree and
strength compensated renewal, intact renewal, protected and masked copying,
and reading/writing blocked. Apply both receiving readers to all seven
record/communication controls and all three terminal injury panels. No output
teaching, labels or assay feedback may enter development or capture.

A suitable single primary is the paired improvement in **scattered-terminal
both-cue success** for the strength-compensated renewal packet, normalized
receiver minus unchanged receiver, with the whole-block 95% lower bound above
10 percentage points. Preserve the existing absolute reliability and
reading/writing-control requirements when freezing the full protocol; report
every panel and the primary/full conjunction separately. The intervention
changes the receiving apparatus, so a positive result would not retroactively
qualify E022's original-reader packets or establish three-generation renewal.

This design was implemented as E023 and qualified on its fresh 32-block
cohort. Receiver compensation raised candidate scattered-terminal both-cue
success from **141/512 (27.54%)** to **510/512 (99.61%)**, a paired improvement
of **72.07 points [95% whole-block bootstrap: 68.16, 75.98]**. Both primary
and full qualification passed. Intact and square-lesion success were each
512/512, observed. The paired intervention supports a role for receiving
dynamics in expressing surviving packet information.

Matched-erasure copying also reached 99.61% scattered success with the new
receiver. The candidate-minus-copy difference in receiver benefit was 0.78
points [-2.15, 3.71], a secondary comparison. No unique rewriting advantage
or prespecified equivalence claim follows. The next lead is to test three
successive damaged renewal boundaries with compensation in renewal and
terminal receivers, retaining copying and dependence controls. This is now
authorized as [E024](../../E024_serial_compensation/README.md), whose fresh
cohort has now passed primary and full qualification: 93.95% intact and
80.66% scattered-terminal both-cue success after three damaged renewals.
Its secondary scattered advantage over cumulative-erasure copying was
22.85 points [18.95, 26.95]; serial decline remains. These later prospective
results leave E022's original-reader verdict unchanged.
[E023 report](../../E023_receiver_compensation/runs/receiver_v1/REPORT.md)
and [closeout](../../E023_receiver_compensation/analysis/closeout_v1.json)
record the prospective evidence separately from this saved-state diagnosis.

## Evidence and verification

Analysis retained **4096 boundary rows** and **12288 terminal rows**, verified
99 consumed source-file hashes and reproduced all body and own-record terminal
CSV scores and block means. The analysis took **29.48 seconds**; independent
verification took **40.69 seconds**, within the retained **411.21-second**
forecast. The figure was visually inspected.

Unsigned graph results were independently checked with adjacency-matrix
closure at zero, the reported bottleneck and its preceding float. Signed
constraints were checked with parity union-find, independently of the
diagnostic traversal. Every terminal graph and capture was checked, along with
summary counts and paired transitions. The first excluded benchmark verifier
had a signed-zero byte discrepancy with no numerical weight difference; its
code and failed receipt remain. Separate v2 files corrected the accumulator,
and both benchmark CSVs and report remained byte-identical. The scientific
cohort diagnosis and its verifier passed on their first execution.

[Full diagnostic report](transmission_diagnosis_v1/REPORT.md),
[boundary rows](transmission_diagnosis_v1/boundaries.csv),
[terminal rows](transmission_diagnosis_v1/terminal.csv),
[statistics](transmission_diagnosis_v1/summary.json),
[figure](transmission_diagnosis_v1/diagnosis.png),
[independent verification](transmission_diagnosis_verification_v1.json),
[closeout](transmission_closeout_v1.json),
[analysis plan](TRANSMISSION_DIAGNOSIS.md),
[benchmark correction](transmission_verifier_correction_v2.json).
