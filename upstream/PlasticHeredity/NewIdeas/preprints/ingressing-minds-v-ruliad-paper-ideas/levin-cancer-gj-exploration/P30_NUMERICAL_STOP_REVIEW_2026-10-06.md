# P30 numerical stop review — October 6, 2026

**P30 stopped at its registered parent-stage numerical gate on October 6
at 02:09:55 UTC**, after **12 hours 40 minutes 42 seconds**. All 24 reference
readouts and 208 parent trajectories executed successfully: **232/856 cases
and 5,480/7,352 integrations**. Three numerical comparisons failed, so none
of the 624 onward assays started and the final independent audit did not run.
No P30 process remains. The earlier completion ETA no longer applies.

## Exact stop reason

All three failures concern the heldout_17021 sequence with a 100-unit pause
starting at time 15. Joint preparation/downstream divisors 8 and 16 disagree
on the third cell's classification at the end of `challenge_15`, relative
time **175**. The lower resolution gives MMX; the higher gives MME. The
written history fails under both archived source bundles, and the ordinary
history fails under the fine source bundle. Ordinary/coarse gives MME at
both resolutions and passes.

The native classifier marks E when miR200 exceeds Zeb mRNA by more than 2.
These raw differences lie just to either side of that cutoff:

| History | Source bundle | Third-cell miR200 − Zeb at q8 | At q16 | Labels q8 → q16 |
| --- | --- | ---: | ---: | --- |
| Written | Coarse | 1.988471503 | 2.013485620 | MMX → MME |
| Written | Fine | 1.999666840 | 2.024674295 | MMX → MME |
| Ordinary | Coarse | 2.006528616 | 2.031533912 | MME → MME |
| Ordinary | Fine | 1.993108478 | 2.018119284 | MMX → MME |

**Every reconstructed final outcome and common-grid newcomer diagnostic
agrees across every registered comparison.** All eight parent variants for
this particular history/source/resolution set fail final E retention; none
shows newcomer recovery by time 300. The discrepancy concerns a different
cell at one intermediate endpoint. Every numerical error is below the 0.01
limit: the largest across all numerical pairs is 0.00346930023; the largest
finest-source error is 0.00121485706. Label agreement is a separate registered
requirement, so the small error and unchanged final outcome do not qualify
the failed stage. No acceptance rule was relaxed.

## Checks that passed

Both complete 54-test software suites passed: prelaunch 1640.894 seconds,
frozen verification 1629.585 seconds. Historical preflight and all 24
reference readouts passed. All 80 P26 retention anchors, all 576 exact shared
schedule prefixes and all 16 exact P29 replays passed.

The cumulative parent-stage audit contains **370,463 checks, with exactly
three failures**. Its numerical comparisons pass **113/116**; its source
comparisons at divisor 16 pass **58/58**. All nine saved source/input integrity
flags are true, both in that audit and in the terminal runner summary.
P29's previously repaired schedules remain consistent. The remaining failure
is at the start-15 schedule, outside P29's four-schedule numerical study.

## Recorded retention pattern, pending panel qualification

Immediate pauses lasting 5/10/15/20/25/100 and 100-unit pauses starting at
5 or 10 retain E in **16/16** variants per schedule. Pauses starting at
15/20/25, continuous communication and full blockade retain E in **0/16**.
Thus 128/208 parents retain E. Each schedule includes two histories, two
incoming sequences, two source bundles and two numerical settings; these
are deterministic model comparisons, not biological replicates.

This matches the earlier provisional boundary pattern. It does not establish
a qualified short-pause transmission chain or an exact timing threshold.
No new-parent transmission result exists for P30.

## Preservation and next decision

The [stop review](storage/p30-stop-review-20261006.json) freshly checks all
232 result records, 5,480 raw phase files, 416 assembly files and 283
current/frozen execution sources. It verifies software-log hashes, saved
audit consistency, the released lock and absent registered processes, and
reconstructs the disputed labels from all eight raw phase endpoints.
These checks preserve and explain the failed study; they do not turn it
into a successful panel. The 36,990 historical input paths were not all
rehashed during this status review. No scientific simulation or historical
mathematical audit was repeated.

Keep the protocol, source, settings, gates and raw outputs frozen. The next
lead is a separately registered, focused convergence test of start-15/
duration-100, retaining both histories/source bundles and matched controls,
with finer numerical settings and explicit tracking of the third cell near
time 175. Distinguish preparation and downstream contributions as needed
before qualifying further onward work. No replacement study or retry was
launched during this status review.

Job: `/mnt/workspaces/levin-cancer-gj-exploration/p30-refined-pause-boundary/jobs/p30-20261005T132855Z-oic4e3y0`.
Run: `/mnt/workspaces/levin-cancer-gj-exploration/p30-refined-pause-boundary/runs/p30-20261005T140222Z-shal5ynt`.
Protocol: [P30 registration](PAPER_REFINED_PAUSE_BOUNDARY_PROTOCOL.md).
