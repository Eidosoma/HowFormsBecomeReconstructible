# E115 — equal component changes from original states

**Complete and verified.** `anchor_v2` finished **30 October 2026 at 14:23:48 UTC**
in **7m17.87s**. Closeout at **17:26:49 UTC** passed: **626 output hashes /
97 scientific inputs**, figure inspected, **502.97 MB** retained.

The sole mixture primary remains **UNRESOLVED**: shared-minus-cue sensitivity
**−0.184 [−0.859, 0.437] points**. Keeping original anchors does not establish
either ordering. The paired anchor-minus-midpoint difference is **0.000
[−0.775, 0.714]**, secondary, not equivalence. All **57 gains / 36 losses**
across 93 dependent transitions remain. See [interpretation](INTERPRETATION.md),
[report](runs/anchor_v2/REPORT.md) and [closeout](analysis/closeout_v1.json).

The original `anchor_v1` stopped on **29 October at 13:06:07 UTC**, after
**7.20 seconds**, when the execution-time shared CPU check rejected capacity.
It completed **zero blocks and zero new readers**. Its startup receipt was
premature: it accepted the initial RUNNING status before the resource check.
The 30 October user-triggered status review found the failure, verified all
frozen inputs unchanged and preserved the failed run. The administrative
[relaunch](admin/relaunch_v2.py) executes the unchanged scientific engine and
requires the reader stage before declaring startup successful. Exact processes
causing the earlier capacity rejection were not recorded.
[Failure](runs/anchor_v1/FAILED.json), [review](analysis/resource_recovery_v1.json).

E114 made shared and cue-dependent changes equally small, but also moved
the starting levels toward their midpoints. E115 instead keeps each original
OO/NN halfway state intact and makes the same small change from that state.
Both anchors and both later noise streams receive equal weight.

All 32 E112 sources, 4,096 identity/draw rows, 554 eligible rows and 4,432
comparisons remain. The sole primary is eligible-mixture gross shared-minus-cue
sensitivity of C−F success. E112 and E114 primaries remain unresolved and
unchanged. Original reconstruction endpoints, absolute outcomes and individual
gains/harms are retained; this is a controlled intervention on known sources.

Exact state matching permits reuse of 8,864 original variant outcomes. Only
4,432 continuations require new updates, half E114's reader work, plus independent
replay. The code verifies reused starts and ports, scalar scores, unchanged
sizes, noise ownership and offsets. Zero targets and empty batches are retained.
No writer is rerun and no source or dose is selected from the outcome.

[Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[source registry](SOURCE_DATA.json), [decisions](DECISIONS.md).
Analytic and excluded replay [tests](analysis/tests_attempt_001.json) passed
in **23.28 seconds**. The [excluded benchmark](runs/benchmark_v1/REPORT.md)
passed in **42.95 seconds**, with 112 new continuations / 28,672 steps
independently replayed, 224 exact reused outcomes, 336 scalar-port checks,
8,064 comparison checks and 37,296 block sums. All 153 output hashes verified;
figure inspected. Maximum size mismatch 1.30e−18, component leakage 5.55e−17;
no initial clipping. Excluded outcomes are not scientific evidence.

The scientific run retains the same **97 inputs / 748 scientific source files**.
The new job also snapshots the administrative launcher and failure review
(99 job inputs). Storage reserve **2.37 GB**, free at relaunch **8.49 GB**.
Both launch and execution checks found one other busy worker slot; three new
workers stay within the shared twelve-CPU ceiling.
[Qualification](analysis/qualification_v1.json), [forecast](analysis/forecast_v1.json),
[sample freeze](SAMPLE_FREEZE.json), [startup](jobs/anchor_v2/startup.json),
[launch/log directory](jobs/anchor_v2), [durable status](runs/anchor_v2/STATUS.json).
Following [RUN_POLICY.md](../RUN_POLICY.md), subsequent checks are user-driven.
No automatic extension, retry or successor.

The user subsequently prioritised [E116 finite-resolution pruning](../E116_finite_resolution_pruning/README.md).
Its design draft separates tolerance, denominator floor and record resolution
and uses the user-chosen 50% absolute floor plus five-point retention allowance.
No E116 scientific run has started.
