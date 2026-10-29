# P4 — Corrective access across the patch boundary matters in the tested model

Completed **2026-09-10 at 18:54:45 UTC**, about 4 h 57 min after launch.
All 146 cases, 858 native integrations and 42,565 independent checks pass.
All sixteen selected finer continuations agree. A read-only re-audit on
September 11 exactly matches the saved report; prior artifacts remain unchanged.

## Main finding

The SAME genuinely acquired, retained M patches were placed at the edge and
centre. Unlike P3's never-acquired centre samples, all 96 main P4 conditions
therefore qualify as restoration tests. Seventy-eight achieve the full chain:
all patch cells retain E after helper/intervention withdrawal, and a fresh M
recipient subsequently retains E after removal of the three fixed carriers.

| Native voltage mode | Boundary expression power | Full restoration/onward chain |
| --- | --- | --- |
| depol | 60 | 24/24 conditions |
| depol | 1 | 6/24 |
| hypol | 60 | 24/24 |
| hypol | 1 | 24/24 |

Each denominator is three known-positive P3 edge acquisition histories x two
destinations x two patch sizes x two internal expression powers. Helper-helper
power stays 60. These are deterministic model conditions, not random
replicates or biological treatment response rates.

Increasing boundary power from 1 to 60 rescues 18 of 48 paired comparisons;
the other 30 already succeed at both settings. Changing internal power alone
changes none of the 48 matched success/failure outcomes (39 pairs succeed
at both values; nine fail at both). This supports boundary access as the
explanation of the tested low-expression failures, rather than weakening
internal reinforcement alone. It does NOT show that internal communication
never matters or that trajectory timing and concentrations are identical.

Switching depol to hypol also rescues the same 18 failing main conditions.
These controls are not literal calibrated voltage clamps: hypol removes the
source's additional potassium gate. Expression powers set the amplitude of
a continuously state-dependent native factor; they are not constant conductance
values. No net miRNA flux measurement or unique molecular-cause claim follows
from endpoint gate sums alone.

## Location and controls

Moving to the centre rescues six matched conditions: all three histories for
the smaller 2 x 2 patch under depol/low boundary power, at either internal power.
The corresponding larger 3 x 3 patches still fail. No location pairing changes
success to failure; 36 succeed at both positions and six fail at both.

The centre also has more donor/helper boundary edges (4 x patch side versus
3 x patch side). Position, contact count and surrounding topology are not
independently isolated, so this does not prove a special effect of centre
coordinates themselves or retrospectively explain P3's acquisition contrast.

All six miRNA-blocked and all six whole-boundary-cut controls fail restoration
and onward E while their corresponding open main conditions succeed. The
twelve helper-helper power controls do not change the matched binary outcome.
No main condition spreads M to the fresh helpers at the measured endpoint.
All six historical replay/assay cases reproduce their original raw arrays.

## A first three-to-three replacement capacity

The four fixed 2 x 3 capacity cases give:

- Ordinary E founders: all three fresh M recipients become and retain E.
- Actual acquired-then-restored E founders: all three become and retain E.
- Ordinary M founders and failed-restoration M founders: all three stay M.

All old carriers are removed before two fully isolated recipient holds.
This is a single handover, not a repeated relay. M controls started with M
recipients, so remaining M is not acquisition of a new state. Ordinary E
success means there is no demonstrated unique advantage of acquired/restored
ancestry in this readout. Capacity cases were not among P4's finer cases.

## Next bounded question

The authorized [P5 relay](PAPER_RELAY_PROTOCOL.md) uses the actual recipients
from those four capacity cases as carriers for eleven additional handovers.
Together with archived P4 round 1, this tests twelve rounds. It includes open,
RNA-blocked and boundary-cut routes and finer versions of all continuations.
No midway rewriting, stress campaign or automatic follow-on is included.

This remains a finite externally scheduled model experiment: no biological
division, self-managed reproduction, new attractor, special PH mechanism,
clinical treatment, wet-lab validation or full original-paper replication is
demonstrated.

## Provenance

Protocol: [PAPER_TOPOLOGY_PROTOCOL.md](PAPER_TOPOLOGY_PROTOCOL.md).
Run: `runs/paper-topology-20260910T135736Z-_g47fgl8`.
Job: `runs/jobs/paper-topology-20260910T135735Z-7x5pqejc`.
Audit: [independent_audit.json](runs/paper-topology-20260910T135736Z-_g47fgl8/independent_audit.json).
Native revision: `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

