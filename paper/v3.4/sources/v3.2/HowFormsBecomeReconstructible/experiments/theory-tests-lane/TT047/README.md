# TT047 — stopped at the disk-space reserve


TT047 stopped at the shared-disk 4 GiB free-space guard on **29 October 2026
at 14:01 UTC**, after 1 hour 2 minutes of production. Qualification passed in
3 minutes 28 seconds, including exact serial/parallel agreement. Two of four
blocks completed; the other two retained partial work. In total, 2,936 of
4,608 planned new read packages are saved. All seven controller/worker processes
have exited. The saved status review verified frozen inputs, qualification,
completed-block outputs and partial-package hashes without reading scientific
effects. There is no complete TT047 result or new scientific conclusion.

Local free space has since recovered, but the proposed recovery first archives
the completed TT046 production run (about 12.6 GB) to the previously authorized
dataset archive with full checksum checks and original paths preserved. Then
the same fixed TT047 cases can be recovered under a recorded execution plan,
reusing verified retained work. The original failure and all partial data remain.
No archive, scientific retry, cohort change or successor has been launched.
See [failure review](status_reviews/storage_stop_v1/REVIEW.json).

# TT047 — voltage and slow memory at writing onset

TT047's authorized detached sequence is launched on two single-thread CPUs.
The one startup observation passed at 2026-10-29T12:55:41.730623+00:00, phase
**QUALIFICATION_RUNNING**. Excluded preflight passed in 18.1 seconds.
Full qualification is forecast at 4.9
minutes. The controller will freeze a measured production forecast only after
qualification passes; that forecast must be below eight hours. Current machine
state is recorded in [CURRENT_EXECUTION.json](CURRENT_EXECUTION.json).

The question is which stored body state influences the outgoing message during
late writing. At update 900, cross voltage (with its EMA companion) and slow
memory R from the original or orthogonal-message donor body. Keep the original
incoming packet fixed. Continue the same 100 writing updates, then test every
actual output in matched fresh recipients. Preservation and unchanged own-body
writing remain controls. This is a four-cell physical intervention, not a new
repair policy.

Four exposed TT046 blocks are selected at cohort positions 0, 8, 16 and 24.
All three damage levels, masks, messages and histories remain. Four saved fresh
births are crossed with the same eight TT046 futures per block. The untouched
P/OO reads are inherited evidence. New DO/OD/DD reads use those exact starts
and forcing streams, retaining both 900- and 1000-update readouts, absolute
performance, all pairwise effects, margins, paired harms and separate writer
body outcomes. These are development results; no fresh population confirmation
or serial-inheritance claim is planned.

The untouched writer and no-writing controls must reproduce TT046 exactly.
Full-replacement donor swaps must also reproduce the permuted original writer
and recipient trajectories. That identity follows task-coupled randomness and
is a control, not another independent replication. Hybrid voltage/memory states
may not arise naturally. Intact and half-mixed donor states previously evolved
with their own informative packets, limiting their history interpretation.

Preflight passed the original writer/reader bridges, independent dynamics,
both donor-permutation checks, all 168 condition reductions, eleven contrasts,
scalar sign/timing tables, paired errors, unequal weights and mutation checks.
Full excluded qualification must also pass exact serial/parallel comparison.
Production then runs once with every physical continuation independently replayed.
No scientific production outcomes have been inspected.

The 6 GiB study cap and 4 GiB free reserve are enforced before each phase.
This study requires no new archival move. CPU/disk guards stop on failure;
there is no automatic retry, extension, successor or result polling. Long work
is left detached until the user requests status. TT046's confirmation remains
unchanged. See the [protocol](PROTOCOL.md), [source bindings](SOURCE_MANIFEST.json)
and [launch receipt](QUEUE_LAUNCH.json).


The user requested a substantial storage move. A detached, checksum-verified
archive of eight completed runs (63.04 GB) is underway at
`/mnt/datasets/theory-tests-lane-archive/2026-10-30_completed-runs_v1`. Original paths are preserved, and each local run is released only
after complete destination verification. TT047's partial work stays local and
its scientific recovery has not started. One startup check passed; no automatic
polling follows. See [archive status](../storage_archives/2026-10-30_completed-runs_v1/README.md).
