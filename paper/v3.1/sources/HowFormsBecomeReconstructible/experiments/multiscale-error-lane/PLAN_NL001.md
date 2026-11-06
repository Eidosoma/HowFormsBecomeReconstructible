# NL001 plan: nested levels

**Plan, 29 October 2026 (fork H, phase A).** Written before any development run. The registered statements are in REGISTRATION_NL001.md (draft until frozen); this plan and the draft registration are the design record.

## Why

The lane's first principle is "correct at every scale the body cannot regenerate, and no finer" (THEORY §§4–7; SYNTHESIS step 1). It was tested two levels at a time:
- cell consensus or the record's relations, plus one coarse code over 4 × 4 regions (BR001, BR002, GW001, LR001);
- BR002's code fought fine minorities, and LR001's gauge-covariant code, in the frame of the record's relations, fixed that;
- the theory note says the general construction needs a hierarchy that corrects at every scale.

NL001 runs three nested levels at once, with damage at three scales together, and the traffic between levels: top-down re-specification, bottom-up leakage, and conflicts.

## The tissue

**Scope.** LR001's record of relations alone, with no body dynamics: the levels are stores, and the body's own physics (DL001–NP002) is not in this study.

LR001's record of relations alone (writing off, no body), on a 64 × 64 sheet:
- r ← r + EPS [r (1 − (r/R*)²) + KR (Σ_j J_ij r_j / 4 − r)] + SIGMA_R ξ, with the bonds J holding the template's relations (lr001.sim.step's arithmetic and constants: EPS 0.05, KR 1, SIGMA_R 0.02, R* 1.2);
- then each level's code, one clip to [−2, 2].

**The levels.** Each is a store held by the cells of its unit:
- **L1** — the per-cell record and its relations (always present).
- **L2** — a region code, one value per 4 × 4 region: the region's sign in the record's gauge frame (LR001's gauge code, gain k2, default KC = 0.02).
- **L3** — a block code, one value per 16 × 16 block: the block's mean, restored by an even shift (BR002's plain code at the block scale, gain k3, default KC).

**Two ways to store L2:**
- **absolute** — each region's own sign (its identity; redundant with L3's mean);
- **relative** — each region's sign relative to its block's sign, read through L3's store (a pure hierarchy, no redundancy).

**A derived L3** — the block mean implied by the region codes, with no store of its own.

**The template**, the same scheme for every case, drawn fresh per case:
- 16 blocks with balanced signs (8 and 8);
- in each block, 4 of its 16 regions with the block's opposite sign (minority regions);
- in each region, 2 of its 16 cells with the region's opposite sign (minority cells).

Every scale carries information the others do not: the template has error-free content in the fine (cells within regions), regional (regions within blocks) and block bands (Q7 checks it).

**No body was used** (a design change from the sketch, which allowed BR001's or LR001's record): the record of relations alone holds fine detail exactly, so the three levels' roles are clean. The record starts exact (R0 = T) rather than acquired through a body.

## Events

Each case's units are addressed by the case. Events are applied to a branch's state before its window.

| Event | What changes | What it tests |
|---|---|---|
| none | nothing | the cost of a level where nothing is damaged |
| F | 5% of cells (205) flipped, everything else intact | fine errors |
| R | 4 regions (outside B's block) flipped, with their boundary bonds | coherent regional errors: the record of relations holds no trace |
| B | one block flipped, with its boundary bonds and its 16 absolute region codes | a coherent block error that also corrupted absolute L2; relative L2 keeps its relations by construction |
| FRB | F, R and B together | damage at three scales at once |
| C3 | the block store of B's block flipped | top-down: a corrupted block store |
| C2 | the region stores of R's first region flipped | top-down: a corrupted region store |
| K | a 2 × 2 square of regions (8 × 8 cells) killed, chosen to hold a minority region: records 0, the bonds between two dead cells 0, the killed regions' codes 0; the block store kept | shared damage: every copy at the region scale and below lost |

## Arms

**Base (gains at KC):**
- L1;
- L1L2 (absolute L2);
- L1L3 (block code alone);
- L1L2L3 (absolute L2 and L3);
- L1L2rL3 (relative L2, L3);
- L1L2L3d (absolute L2, derived L3).

**Gain variants, run where they matter (nl001.design.RUNS):**
- the absolute block code at k3 = 2, 3, 4, 5, 6 and 8 KC (events none, B, FRB, C3);
- the block code alone at 4 and 8 KC (none, R, B, FRB);
- the relative hierarchy with k3 = 0.25 KC (B, C3);
- the region code at k2 = 0.25, 0.5 and 0.75 KC (R, C2).

88 branches a block; window 2,000 updates; reads at 250, 1,000 and 2,000.

**Endpoints:**
- cell, region and block error;
- minority cells and minority regions right;
- the event's units right: fine sites, R's regions, B's block, B's block's minority regions, C2's region, K's killed cells, regions and minority regions;
- the error field's energy by band (reported).

## Changes from the lead's sketch

- **No body;** the record of relations alone (above).
- **The kill event** is one event (K) with L3's store kept, not a separate panel.
- **L3 is a plain block code,** not gauge-covariant in L2's frame. L2's frame is a single sign per region, so a block-scale frame would be the block's sign relative to its regions: what the relative storage of L2 already expresses. The relative arm is the gauge-covariant hierarchy.
- **Gain variants** were added after P34 version 1 located the turns, as version 2.

## Probe P34 (engineering, 900560–900563, tag mse-p34)

- **Version 1:** 74 branches, 702 CPU-seconds.
- **Version 2:** 88 branches with the finer gains, 1,167 CPU-seconds. It reproduced version 1's 4,736 values bit for bit.
- **The smoke** (block 900560, 42 branches) set the scheme.

**What P34 showed** (block means over 4 blocks, t = 2,000):
- **Fine flips** are repaired by every arm.
- **Coherent regional errors** are repaired by every arm with L2 and by none without, block codes of up to 8 KC included.
- **Damage at three scales at once:**
  - the relative hierarchy repairs everything (cell error 0.0014);
  - the absolute and derived hierarchies leave the block (0.0625);
  - the record alone leaves the regions and the block (0.0781).
- **A level overrides the levels below by its gain, whether it is right or wrong.**
  - The region code at ≥ 0.75 KC repairs coherent regional errors and imposes a corrupted store; at ≤ 0.5 KC it does neither.
  - The absolute block code at ≤ 3 KC neither repairs a coherent block error nor imposes a corrupted store; at ≥ 5 KC it does both (4 KC partial).
  - In the relative hierarchy the block store dictates at every gain tested (0.25 and 1 KC).
- **When the absolute block code wins,** it restores the block's sign but not its minority regions.
- **A derived block code** neither repairs nor imposes.
- **In a kill wound,** a block code fills the killed regions with the block's majority. Killed minority regions come back 0.44–0.46 less often than without one.

## Development

- 16 blocks, 910380–910395 (128 cases), tag mse-nl001.
- One task per (event, block): 128 tasks.
- Forecast about 1.3 CPU-hours from P34 version 2 (Q9 gives the debug run's figure).
