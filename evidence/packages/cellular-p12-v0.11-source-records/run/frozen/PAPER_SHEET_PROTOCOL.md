# P3: acquisition and restoration in a two-dimensional sheet

Registered 2026-09-09 before any P3 native integration. This is the bounded
2D extension authorized by “let's go”; no 3D or autonomous-lineage campaign.
Configuration: `configs/paper_sheet_v1.json`. Native BITSEY remains unchanged
at `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

## Question and scope

Can cells that start E acquire and retain M in a sheet, then regain and retain E
after rehoming, and pass that restored influence to a new cell? P2 used one
successful 1D acquisition history. Here acquisition itself occurs in 2D.
Three deterministic native voltage conditions are distinct exposure histories,
not independent random replicates. This panel tests conditional robustness,
not statistical population prevalence or a universal PH mechanism.

## Geometry and fixed identities

The field is a 1 x 13 x 13 native grid: orthogonal nearest neighbours, no
diagonals, wraparound, motion, division or artificial target schedule. Coordinates
below are zero-based (row, column). The original 4 x 4 M block begins at (0,1)
for edge exposure and (4,1) for centre exposure. The fixed, initially E, 3 x 3
sample begins at (0,5) or (4,5), respectively. These are vertical translations
with identical orientation, not outcome-selected cells.

Native `nbrDepol` reads the preceding row/column neighbours directionally;
we retain and audit that asymmetry, not silently symmetrize it. Location is
a boundary/contact-geometry contrast, not a pure coordinate effect with
neighbour counts held equal.

A separate common reference preparation uses the edge arrangement, `depol`,
power 1, and 1,000 model-time units with miRNA transfer off. Its last returned
snapshot supplies fresh E at (12,12) and fresh M at (0,1). These fixed stocks
are shared by all ordinary and finer continuations. They are not selected by
acquisition or restoration outcome.

## Acquisition banks

Six banks cross `depol`, `nbrDepol`, `hypol` with edge/centre. Each begins with
16 native M cells and 153 native E cells. Prepare for 1,000 units with power 1
and miRNA transfer off (small-ion junctions remain on); restore the native
last returned preparation snapshot, as in the earlier source workflow.
Then expose for 20,000 units at power 60, miRNA Kd
8.801117367933935e-16, OiET 0.5 and tness 1.

Remove every cell except the nine preassigned sample cells. Preserve all 17
concentrations, not just an E/M label. Hold twice for 10,000 units in a 3 x 3
grid with ALL junction transport and neighbour voltage reading off, common
`depol`/power 1. From exposure onward, carry the native LIVE endpoint, never
the last returned snapshot or a freshly assigned regulator state.

Six matched acquisition-blocked banks disable only miRNA transfer during
exposure. Three finer banks repeat preparation, acquisition and both holds
for depol/edge, nbrDepol/centre and hypol/edge. No positive acquisition result
is required to continue; negatives are scientific outcomes, not software errors.

## Restoration branches

Main panel: six ordinary banks x two patch sides x four strategies = 48.
The 2 x 2 patch uses sample indices [0,1,3,4]; the 3 x 3 patch uses all nine.
Place these actual held cells in a fresh 13 x 13 E sheet, patch origin (0,5)
at the edge or (5,5) at the centre. The rest are common fresh E helpers.
Restoration contact lasts 20,000 units at Kd 1.25e-14:

| Strategy | Native voltage mode | M-associated expression multiplier |
| --- | --- | --- |
| Neither | depol | 60 |
| Voltage only | hypol | 60 |
| Expression only | depol | 1 |
| Both | hypol | 1 |

Expression treatment removes the M-associated overexpression advantage; it
does not increase every connection. `hypol` is a source identifier: it removes
the extra state-dependent potassium gate, not a calibrated voltage clamp.
Actual Vm and all gate factors are saved and independently checked.

Remove ALL helpers and BOTH interventions. Keep only the original patch
state and identities in a fully isolated patch-sized grid, common depol/power 1,
for two 10,000-unit holds. Six blocked-restoration controls use the 3 x 3 patch
and “both” but zero miRNA transfer during restoration only; small ions remain
connected. Six helper-free controls instead spend the 20,000-unit restoration
interval fully isolated under the common depol/power-1 rule. These distinguish
helper-assisted change from age-matched spontaneous change.

Six finer continuations use both patch sizes and “both” for the three finer
banks. Every bank/branch trajectory phase is refined, while the external
common E/M reference stocks are held fixed. Halve initial time step and both
adaptive delta limits. Require agreement of phase endpoint labels, acquisition
qualification and reported discrete outcomes; disclose numeric differences.

## Small 2D onward assay

After withdrawal take exactly the patch's top-left, top-right-adjacent and
bottom-left-adjacent cells: local indices [0,1,side]. Even if they failed, never
substitute a successful cell. Place them at indices [0,1,2] of a 2 x 2 grid;
one fresh common M recipient occupies index 3. Run 20,000 units in hypol,
power 1, Kd 1.25e-14. Remove all carriers and isolate the recipient under the
common depol/power-1 rule for two 10,000-unit holds.

This is a new **three-carrier/one-recipient 2D capability assay**, not P2's
two-to-one line or P1's two-to-14 invasion assay. Ordinary E-carrier and
M-carrier controls must first respectively leave a stably E and stably M
recipient. It is not a proliferating tissue or an autonomous hereditary cycle.

## Outcomes and evidence gates

E/M/X labels use the native two-unit miR200/Zeb mRNA difference. “Stable” means
the final label plus at least 95% of late-quarter samples in BOTH isolated
holds. A sampled cell qualifies as acquired M only if E both before preparation
and at exposure start, M at exposure end, and stably M through both holds.

Report every bank and branch, including partial/non-acquisition, helper M
spread, restoration without onward transfer, and unsuccessful restoration.
Primary full-patch chain requires ALL patch cells to qualify as acquired M,
ALL to retain restored E, and the fresh recipient to retain E. A secondary
fixed-three-carrier chain requires those three to qualify and retain E plus
recipient E; it must not be presented as whole-patch success. An E patch that
never acquired M is NEVER a restoration success, even if it converts the probe.
No outcome-dependent eligibility filtering removes rows or changes denominators.

Before new biology: read-only P2 re-audit must equal its saved audit and pass
10,886 checks/270 integrations. Replay the unchanged original pilot's 625-cell
ungated benchmark using the same pilot worker and compare all stored trajectory
arrays exactly, alongside reference identity checks and the two onward controls.
This is a software/source anchor, not a full original-paper table replication.
Audit source-bank shapes, topology, physics, gates and identity flow before
restoration branches; failure of a technical gate stops the panel. Absence of
M acquisition does not. Final independent audit checks all 85 cases/465 calls,
full fixed-case enumeration, frozen inputs/code and selected finer comparisons.

## Runtime and preservation

85 cases: one reference preparation; one historical replay; two onward controls;
15 banks (6 ordinary, 6 miRNA-blocked, 3 finer); 66 continuations (48 main,
6 restoration-blocked, 6 helper-free, 6 finer). 465 native integrations.
Two fresh single-threaded worker processes concurrently; no parameter search,
retry, hidden pilot, deletion or follow-on launch. Per-case cap 7,200 seconds;
panel cap 57,600 seconds (16 hours). Supervisor caps: runner 57,900, final
audit 1,800, overall 60,300 seconds. Require at least 5 GiB free before each
new worker and recorded native phase. Stop incomplete rather than silently
truncate the scientific design. All files/config/input hashes are frozen before
native integration. A later advancing heartbeat confirms persistent detachment.

E/M states are model regulatory states, not diagnoses. This work neither tests
wet-lab safety nor measures proliferation, migration, survival, fitness,
lifespan, clinical therapy or autonomous reproduction. Old runs remain immutable.
