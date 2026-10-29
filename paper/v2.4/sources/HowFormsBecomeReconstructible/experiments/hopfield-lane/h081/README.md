# H081 — selective response feedback

Completed **23 October 2026 at 23:51:46 UTC** as
[h081_selective_v2](../runs/h081_selective_v2), on **64 fresh development
networks**. Controller **3340595** has exited. The selective rule reduces new
final bit errors from **688 to 252 (63.37%)**, but retains only **88.49%** of
delayed feedback's repairs. Complete tasks fall from **128/256 (50.00%)** to
**84/256 (32.81%)**. Both simpler controls also complete 84 tasks; quadratic LS
and nearest-history complete all 256. All three predeclared screens fail:

- **SELECTIVE_FEEDBACK_MECHANISM_SCREEN_FAILED**: less new harm, insufficient
  repair retention and a task loss.
- **SELECTIVITY_OVER_SIMPLE_CONTROLS_SCREEN_FAILED**: no task gain over either
  half-strength feedback or a barrier on all bits.
- **ITERATIVE_READER_CAPABILITY_SCREEN_FAILED**: below 75% completion and the
  four required source-control gaps.

All **22 frozen fixtures, 192,124 synthetic checks and 10,589,504 main numerical
checks pass**. The 24 October closeout verifies **558 sealed artifacts, 194
frozen files, 190 current source/context files, 1,033 parent artifacts and all
201 preserved failed-run files**. Main took **24m51s** with four workers, chosen
after a **2.64x** engineering speedup with exact arrays, audits and tables. The
controller took **40m19s**, including **6m18s** of capacity waiting.
[Interpretation](INTERPRETATION.md), [sealed report](../runs/h081_selective_v2/main/REPORT.md),
[integrity](../.cache/h081_completion_verification_v2.json),
[protocol](PROTOCOL.md), [status](../runs/h081_selective_v2/STATUS.json).

Version two restarted at **23:11:25 UTC**. The propagation preflight,
report preflight and early engineering handoff remain preserved:
[propagation](../.cache/h081_preflight_v1/PASS.json),
[report](../.cache/h081_report_preflight_v2/PASS.json),
[handoff](../.cache/h081_handoff_v2.json).

Version one stopped in the synthetic report fixture at **23:06:36 UTC**.
A column starting with the integer sentinel -1 was incorrectly parsed as
integer-only, rejecting a later decimal energy value. The parser now infers
numeric types across the column, with an explicit regression fixture. All
**201 failed-run files** and synthetic arrays remain preserved. Dynamics,
audits, scores, thresholds and cohort are unchanged; no engineering or main
network had started. [Failure seal](../.cache/h081_failed_v1_seal.json).

One fixed candidate raises the flip threshold for response bits that agree
with their current context/query field. After a shared feedback-off cue sweep,
such a bit needs response feedback stronger than twice the input-field
magnitude to flip; input-opposed bits keep the ordinary rule. The reader
receives no target or correctness label. The multiplier is fixed at one,
without fitting or a parameter search.

Two controls test whether any benefit comes from selectivity: response feedback
at half strength, and the same threshold on all response flips. All three
interventions share the original delayed/off first sweep. Always-on retains
its different first sweep. Original source/context controls, zero/one/eight
update endpoints and linear/quadratic/nearest-history comparators remain.

The campaign uses **64 fresh development networks**, four births each,
with root seed **81081** and four separate engineering networks. It propagates
new policy paths, audits them independently in extended precision, and saves
the accepted and vetoed response decisions. A policy-fixed state is reported
separately from a fixed point of the ordinary full-feedback reader.

Three development screens remain distinct: fewer new final errors while
retaining repairs and gaining tasks; benefit beyond both simpler feedback
controls; and the unchanged seven-gate capability screen. Whole-network
bootstrap intervals are descriptive. No secondary panel or winning control
replaces the primary, and no superiority, inheritance or RDT forecast result
follows from a point-screen pass.

The durable controller ran full fixtures and benchmarked the same four
engineering networks with one/four workers before main. One numerical thread
per worker and the shared twelve-slot ceiling were retained. The measured
forecast and capacity waits required a detached handoff under the
[run policy](../RUN_POLICY.md).

H079's timing benefit and capability failure, H080's local diagnosis and the
earlier H031/H033/H071/H076/H077/H078 results remain intact. Richer inherited
tasks remain a separate priority. No private quotation, public-manuscript edit
or automatic successor is included.

Restart freeze: `f686c99268f0b15293f2e32f8eff645a537e94122abe34fe0824e2994af6fed9`.
Completed manifest: `004bce5848dbbefe377b8dcdd0b536ba3c3c828c047f3717dded9ed0f07217c9`.
Preserved initial freeze: `35d2814ecd5611a9b158216df30ad7d4220e39e9a961a0c511ca727d167c2c5c`.
Context manifest: `277355cf92e5ede881afb9af09c3e189f34164ec2480431a837309a574bd2330`.
