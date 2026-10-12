# P27 numerical stop review — October 3, 2026

**Stopped at the registered renewal precision gate; no completed P27
transmission result.** The supervisor stopped October 3 at 00:45:11 UTC,
3 hours 16 minutes 46 seconds after launch. It completed 116 of 428 cases
and 2,740 of 3,676 integrations: all 12 reference assays and 104 renewal
parents. All 116 individual executions were valid. None of the 312 new-parent
onward assays started; the final independent audit did not run. Nothing is
currently running for P27, and no retry or replacement experiment was launched.

## Passed checks and exact stop reason

Both complete software suites passed 47 tests: prelaunch 1058.661 seconds,
frozen verification 1061.084 seconds. Historical preflight and all reference
assays passed. All 40 P26 renewal anchors and 288 exact shared-schedule-prefix
comparisons passed. Saved source/input integrity checks were true at the stop.

The renewal audit contains 207,129 checks, with four failures. Of its 58
cumulative coarse/fine pairs, 54 pass and four fail. The four failures are
phase-end label disagreements in the heldout_17021 sequence:

| Schedule | Histories | Relative time | Coarse labels | Fine labels |
|---|---|---:|---|---|
| Immediate 5-unit pause | Written and ordinary | 120 | XEE | EEE |
| 100-unit pause starting at 10 | Written and ordinary | 225 | MXE | XXE |

The first cell crosses a classifier boundary between resolutions. The native
classifier uses miR200 minus Zeb mRNA: above +2 is E, below −2 is M, and the
intervening range is X. For written history, the immediate-five values are
1.973285 / 2.041804; the delayed-ten values are −2.263745 / −1.295589.
Ordinary history shows the same label discrepancies. Exact raw values,
phase hashes and common-grid trajectories are in the saved review JSON.

All reconstructed outcome dictionaries agree within these four pairs,
including final retention and the sampled recovery category. Every other
phase-end label comparison passes. Nevertheless, the registered criterion
requires phase-end labels to agree as well, so this is a genuine failed
acceptance check. The 5-unit pause also shifts the sampled first-return-E
bracket from 120–135 to 105–120 between resolutions. Treat recovery timing
as numerically unresolved; do not relax the gate after seeing results.

## Recorded observations, pending qualification

The saved renewal outputs show retention for immediate 5/10/15/20/25/100
pauses and 100-unit pauses starting at 5 or 10, each 8/8 across histories,
sequences and resolutions. Delays 15/20/25, baseline and full blockade show
0/8 retention. This totals 64/104 retained parents. These are descriptive
outputs from a panel that failed its numerical gate; they do not establish
qualified transmission chains or a timing threshold. New-parent onward
transmission was never tested.

## Preservation and next step

The status review freshly verified all 116 result records, 2,740 raw phase
files, 208 assembly files and 257 current/frozen execution sources, plus
software-log hashes and saved stage-report consistency. All 16 stop-review
checks pass; these verify diagnosis and preservation, not experimental
success. Historical input hashes were not all re-read during this status
review, and no historical mathematics or scientific simulation was rerun.

Keep P27's protocol, sources, acceptance rules and outputs frozen. The next
lead is a separately registered numerical-convergence diagnosis of the two
affected schedules, including both histories and appropriate shared-source
controls. Tighter numerical resolutions should establish whether the
transition classifications and recovery timing stabilize before any onward
assays are attempted. No new protocol or run was created at this status check.
The former 18–28-hour completion estimate no longer applies to the stopped run.

Evidence: [stop review](storage/p27-stop-review-20261003.json),
[registered protocol](PAPER_PAUSE_BOUNDARY_PROTOCOL.md),
[active-job pointer](storage/p27-active.json).
