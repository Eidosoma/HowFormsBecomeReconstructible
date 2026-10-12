# P14 — Tissue persistence, relapse and controlled turnover

Registered 2026-09-18 before new biological integrations. This is one bounded
model-extension screen connecting P13 lineage carriers to the paper's spatial
communication mechanism; not an exact replication of its tables or 3D results.

## Question and fixed design

Can temporary regional communication changes correct an actual M-state lineage
patch in a competing tissue, persist after withdrawal, and survive replacement
of every original patch cell? Does the surrounding initially E tissue instead
develop M states?

One preselected P13 challenge seed (301, the first registered seed) supplies
the actual final r09 isolated trios for both written-origin and ordinary-origin
histories. Both carry the full M→E→M, nine-handover ancestry and end at logical
time 1,020,000. They are not three independent replicates and are not freshly
reset or cloned. Each source's complete 17-variable state and three IDs are
transferred unchanged. Each resolution uses its own historical source.

A third comparison uses three fresh ordinary-M stock cells. It is matched for
initial M classification, geometry and all subsequent treatment, but NOT prior
age, state vector or lineage history. Do not infer a history advantage from a
difference against this benchmark. Earlier ordinary-origin lineages are not
unwritten controls: they too have undergone both rewrites.

There are 36 cases: three source backgrounds × six arms × two resolutions.
Counterfactual arms fork the same saved source; they are not new biological
replicates. No outcome-based selection, retries, extra seeds or follow-on runs.

## Geometry, interventions and time

Every sheet is 13×13, orthogonal, nonperiodic. Zero-based row-major central
positions 83,84,85 form a 1×3 lineage patch. A separate 3×3 ordinary-M patch
occupies 28,29,30,41,42,43,54,55,56. The remaining 157 positions start E.
The competing patch evolves normally; it is not clamped or replenished.
All 169 cells evolve in every connected phase.

Native depol voltage feedback and miRNA Kd=1.25e-14 remain the baseline.
Helper-helper expression power is 60, central-patch internal power 60,
central-patch boundary power 1. Powers multiply the native state-dependent
expression rule; they are NOT constant physical conductances.

The first 20,000 units apply:

| Arm | Patch internal power | Boundary power | Other temporary change |
| --- | ---: | ---: | --- |
| sham | 60 | 1 | None |
| internal | 1 | 1 | None |
| boundary | 60 | 60 | None |
| both | 1 | 60 | None |
| rna | 1 | 60 | Whole-sheet miRNA transport Kd=0 |
| cut | 1 | 60 | Only central-patch boundary edges unavailable |

RNA and cut are mechanism controls matched to BOTH, not individually matched
mechanism controls for every other arm. RNA blockade does not block ion
transport. In all arms, all settings then return to the identical baseline.

Two 10,000-unit withdrawal phases follow in the SAME live mixed tissue.
At relative times 40,000, 60,000 and 80,000, replace central positions 83,84,85
respectively with one fresh M-state cell, integrating the ENTIRE sheet for
20,000 units after each replacement. Only that one column and ID change;
no other cells reset, freeze, disappear or get pooled. The source cell being
replaced is removed, not retained as a helper. New cells share three registered
SHA-256 draws from seed 401 across histories, arms and resolutions, changing
only ZEB protein by an integer within ±25%; initial M classification is required.
This challenge is deliberate M-cell introduction, not spontaneous relapse.

At relative time 100,000, remove all surrounding cells and take the three
actual replacement cells through two completely isolated 10,000-unit holds.
Isolation removes both miRNA and ion junctional transport, with default power
1. Exactly eight integrations per case, 288 total; no scientific early stopping.
Every phase advances its own interval exactly. Fresh stock uses logical base
0, historical carriers 1,020,000; subsequent exposure duration is matched.

## Prespecified observations and comparisons

Report all phase endpoints: central E/M/other labels, competitor E/M counts,
initially-E background cells now M, and maximum such background-M count across
stored samples. Background spread cannot uniquely be attributed to the central
lineage, because a second M patch is deliberately present.

Correction-at-treatment-end requires all three central cells E. Persistence
without intervention requires all three E at each withdrawal endpoint AND
at least 95% E occupancy in each cell's final quarter of BOTH withdrawal holds.
Loss of this stability and return of any M cells are reported separately.
Transient E appearance is not stable correction.

Each replacement window requires all three central cells E at its endpoint
and at least 95% E occupancy per cell over its last quarter. Replacement cells
must have entered as M. All three windows must pass; no successful subset.
Final isolation requires endpoint and late-quarter E stability in both holds.
The composite tissue-correction outcome requires withdrawal persistence,
all replacement windows and final isolated retention.

For each source, report the four intervention arms and paired sham comparisons
at both resolutions. A provisional BOTH-mechanism-supported contrast additionally
requires BOTH's composite outcome at both resolutions, and absence of withdrawal
persistence in sham, RNA and cut. Also report each control's actual outcome:
controls may become E after transport is restored, which is scientifically valid
and limits attribution to the original intervention. No blanket expectation of
negative controls is used as an execution gate.

Positive tissue turnover is NOT a new isolated PH handover: surrounding E cells
may instruct every incoming M cell. Isolation checks later short-term retention,
not where that memory originated. No cell division, autonomous scheduling,
new attractor, therapeutic efficacy or human cancer result is claimed.
E/M labels are regulatory-state proxies, not complete cancer phenotypes.

## Numerical verification and bounds

Use the frozen native BITSEY equations, source revision
b2cb370aaecbc8299f259bc4251d5396c81f19a6, and our explicitly changed bounded
Euler clock: 100-unit coarse / 50-unit fine maximum step, 100-unit sampling,
with fine base step and adaptive increment limits halved. Native voltage gates
remain active; no hypol intervention, synthetic voltage clamp or GRN retuning.
All 18 coarse/fine pairs must match phase-endpoint labels and discrete outcomes;
continuous endpoint differences are reported, not a proof of numerical convergence.

Before biology: full software regression, frozen manifests, original and archived
P13 independent re-audits matching its saved 63,744 checks. Stage/final auditing
independently reconstructs geometry, exact state transfers, clocks, native gate
equations, intervention withdrawal, each single-cell replacement and outcomes.
Raw NPZ hashes, IDs, all 17 initial variables, environments and inventories
are checked. Negative biological results are valid; technical failures stop.

Two single-threaded workers, six-hour per-case ceiling, 36-hour science ceiling,
50-minute regression ceiling, 45-minute final audit ceiling, five-GiB minimum
free disk. Detached supervisor has an overall 38-hour ceiling. These are
safety caps, not an ETA. No automatic retry or downstream launch.
