# P5 results — Renewable E transmission through complete 2D carrier replacement

Recorded 2026-09-12. P5 finished on September 11 at **16:38:27 UTC**, about
1 hour 37 minutes after launch. All 28 cases and 804 native integrations
completed. The independent audit passes 42,065 checks and all twelve finer
comparisons. A read-only re-audit on September 12 exactly matches the saved
report, with all source, frozen-file and input provenance checks passing.

Run: `runs/paper-relay-20260911T150113Z-b8woml1d`.
Job: `runs/jobs/paper-relay-20260911T150113Z-07u06kcr`.
Primary evidence: the run's `independent_audit.json`, `summary.json`, raw NPZ
arrays and per-case identity/setup records. Design: [PAPER_RELAY_PROTOCOL.md](PAPER_RELAY_PROTOCOL.md).

## What was added

P4's first handover supplied the actual three newly written recipient cells.
P5 continued their full live 17-component states through eleven new handovers,
rounds 2-12. At each handover, three carriers contacted three fresh M cells in
a 2 x 3 grid. Every old carrier was removed. The three new recipients underwent
two fully isolated holds before becoming the next carriers, without resets,
winner selection or return of original cells. All new round endpoints were
carried onward even if transmission failed.

Round 1 is historical, not a newly simulated independent P5 replicate.
There were four historical exact replays and 24 continuations: four ancestries
x three communication routes x two numerical resolutions. Across the 24
continuations, 264 new handovers were executed. That number is NOT a count
of successful E transmissions or independent biological replicates.

## Audited outcomes

| Ancestry | Open route | RNA blocked | Carrier/recipient boundary cut |
| --- | --- | --- | --- |
| Ordinary E | All three recipients retain E at every round through 12 | First new handover fails at round 2; no later E renewal | Same |
| Restored E | All three recipients retain E at every round through 12 | First new handover fails at round 2; no later E renewal | Same |
| Ordinary M | Recipients remain M | Recipients remain M | Recipients remain M |
| Failed-restoration M | Recipients remain M | Recipients remain M | Recipients remain M |

The E outcomes meet the registered criterion: final label and >=95% E in the
late quarter of BOTH isolated holds, for every new recipient at every round.
All eight coarse blocked/cut control lineages have zero new all-E rounds.
The M-control recipients already started M: staying M is a negative control
for E writing, not new M acquisition.

All twelve finer continuations agree with their coarse partners in every
phase's endpoint labels and round-level outcomes. Continuous arrays are not
identical: the maximum absolute endpoint-component difference is approximately
0.04452 native concentration units. The maximum symmetric relative difference,
normalized by `max(1, abs(coarse), abs(fine))`, is approximately 0.000595.
Historical acquisition/restoration and round 1 were not independently refined.

## Meaning and limits

The actual regenerated carrier group can repeatedly write E into fresh M
cells and leave them retaining E after carrier removal. This extends prior
line-based PH-style relays to the paper-linked 2D assay. It is evidence for
finite renewable state transmission under an externally maintained protocol.

Ordinary-E and restored-E ancestries both succeed. There is no demonstrated
special advantage of the acquired-and-restored history. Simple state copying
and stable regulatory attractors remain sufficient alternatives; P5 did not
test a unique new memory mechanism or a new law of physics.

Fresh cells, baths, relocation and the contact/hold voltage schedule are
externally supplied. The contact setting is native hypol/power 1; hypol names
removal of the extra potassium gate, not a calibrated voltage clamp. No cell
division, migration, biological fitness, self-scheduling, autonomous heredity,
wet-lab effect, therapy or complete original-paper replication was demonstrated.

## Authorized next experiment

[P6 halfway rewriting](PAPER_REWRITE_PROTOCOL.md) branches from actual
round-6 carriers of both E ancestries. It tests whether a temporary opposing
M cue changes those carriers, and whether their actual descendants then write
M into fresh E recipients through six replacements. It uses matched controls,
ordinary E/M capacity diagnostics and a fixed simple-copy reference.
This is a deliberately new opposite-state readout, not unchanged P5 conditions.
No later stress campaign, return-to-E or autonomous extension is automatic.
