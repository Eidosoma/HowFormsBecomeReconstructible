# TT025 execution

The user authorized implementing and running the paired receiving experiment.
Qualification passes all 23 checks in 25.731 seconds on excluded cases.
All 56 serial/two-worker array files agree exactly. The full-update excluded
benchmark precedes production freeze and determines the runtime/storage bound.

Production uses two single-thread workers, no automatic retry or extension,
and one detached startup acknowledgment. Subsequent progress checks occur
only when the user asks. The unique execution record is [current status](CURRENT_EXECUTION.json).
The exact input/evidence hashes and fixed budget are in [freeze](FREEZE.json).

The 64 new production recipient addresses are disjoint from qualification,
benchmark and the checked prior reader streams. New conditional draws do not
make the four historical source blocks prospectively fresh. No production
receiving outcome is interpreted at launch.

TT025 is **complete and verified**. Production ended at **2026-10-16 18:43:05 UTC**, in **2 hours 3 minutes 36 seconds** on two CPUs. All 51,200 receiving evaluations passed independent replay. The user-authorized saved closeout passed in **52.504 seconds** before effect inspection; all 65,536 paired comparisons and the original run verify. See [interpretation](INTERPRETATION.md), [full report](runs/paired_v1/REPORT.md), [closeout](CLOSEOUT.json) and [next proposal](NEXT_STEP.md).

There was no automatic production polling. The user's subsequent “lets go” authorized the first completion check. Closeout code was written after acquisition and before effects were inspected; it integrated no trajectories. The 445 frozen inputs, 2,415 evidence files and 6,441 original run files remain unchanged. All summaries, conditional pairs and the report reproduce exactly. No automatic retry, extension or successor occurred.
