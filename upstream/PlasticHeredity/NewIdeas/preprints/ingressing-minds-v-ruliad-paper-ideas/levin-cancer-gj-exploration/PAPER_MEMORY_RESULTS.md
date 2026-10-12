# P1 — Population-induced state persists and transfers after source removal

Completed 2026-09-09 at 13:30:16 UTC, approximately 3 h 42 min after launch.
All 42 cases, 372 native integrations and 16,815 independent checks passed.
This is an extension using unmodified native BITSEY, not an independent
implementation, full paper replication, wet-lab result or cancer treatment.

## Main result

In 16/24 main settings all originally E neighbours became M. They retained M
through both follow-up holds after original M donors were removed, including
when all intercellular transport and neighbour-voltage reading were disabled.
Two fixed originally E cells from each isolated branch then converted all
14 fresh E recipients, which retained M through both donor-free isolated holds.

In the other eight main settings no originally E neighbours converted. None
showed onward M memory. There were no partial-conversion main outcomes in
this particular panel, and no endpoint-label difference between continued
contact, source removal with neighbours connected, and individual isolation.
This does not establish that these distinctions never matter near a boundary.

| Native voltage algorithm | Power 1 | Power 8 | Power 60 | Power 100 |
| --- | --- | --- | --- | --- |
| depol | No conversion | No conversion | Full sequence | Full sequence |
| nbrDepol | No conversion | Full sequence | Full sequence | Full sequence |
| hypol | No conversion | Full sequence | Full sequence | Full sequence |

The table holds for both initial M sizes (6 and 11 in a 25-cell line).
“Full sequence” means all 19 or 14 original E neighbours converted and
retained M, followed by retained M in all 14 fresh onward recipients.
These are deterministic parameter conditions, not independent biological
replicates or an estimated population success probability.

## Controls and relationship to the paper

- All six archived source endpoints reproduced: initial 11 M cells remain
  11 at power 1, versus 25 final M at power 100, in all three native modes.
- All six miRNA-blocked cases showed neither neighbour conversion nor onward
  M memory. Their small-ion communication and native voltage rules remained.
  This implicates the specified molecular communication route in these cases.
- All six finer whole-protocol runs agreed with their baseline endpoint
  labels and outcome counts. The largest absolute endpoint concentration
  difference across the reported comparisons was about 0.00465 model units.
- Source, frozen files, copied inputs, identities, full-state carryover,
  actual voltage and gate calculations passed the independent audit. A
  subsequent read-only P1 audit again passed all 16,815 checks before P2 work.

The narrow result is that, under these native population conditions,
communication can install a state which the recipient's own dynamics retain
after disconnection, and the recipient can then carry it to other cells.
This goes beyond a continuing response to the original population.

P1 does NOT demonstrate a new attractor, superior acquired versus ordinary
M carriers, molecular-turnover-tagged renewal, actual cell division,
autonomous heredity, a complete malignancy phenotype or therapeutic benefit.
The 25-cell line is not the paper's full 3D field. Source hypol is a native
mode name, not a literal calibrated hyperpolarization; table-label/geometry
questions remain as recorded in PAPER_OUTPUT_MAP.md.

## Artifacts and next question

Protocol: [PAPER_MEMORY_PROTOCOL.md](PAPER_MEMORY_PROTOCOL.md).
Job: `runs/jobs/paper-memory-20260909T094808Z-13b5435c`.
Run: `runs/paper-memory-20260909T094809Z-yna2d02r`.
Audit: [independent_audit.json](runs/paper-memory-20260909T094809Z-yna2d02r/independent_audit.json).
Source revision: `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

The next authorized bounded question is durable restoration: can E neighbours
restore actual P1-exposed M cells, and does the restored state persist after
the helpers AND intervention are withdrawn and transmit in a common assay?
See [PAPER_RESTORATION_PROTOCOL.md](PAPER_RESTORATION_PROTOCOL.md) for P2;
P1's historical files and executed code remain unchanged.
