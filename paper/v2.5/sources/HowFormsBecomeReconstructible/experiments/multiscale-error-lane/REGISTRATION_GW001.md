# GW001 registration: geometry and wound kind on a sheet of any size

**Frozen 25 October 2026 at 21:53:54Z, before any development outcome. Development study, not confirmation.** The design is `gw001/design.py`, digest `aada308c3f76dda01fc089df489f5d6d59d2bf547cdd3484be6ef894c446d702`. Source hashes and the registered statements are in `gw001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

The model-limits study (MODEL_LIMITS_AND_EXPANSION.md, 25 October) found that the lane's repair results mixed four things the 16 × 16 torus could not separate:
- wound size;
- contact with the pattern's own walls;
- the sign of the wound: every BR001 and BR002 lesion inverted cells into a stable wrong state, while lost cells regrow undecided;
- sheet size.

Its probes, and the lead's independent check with BR002's simulator, showed that this changes conclusions:
- **Reset wounds heal.** Consensus alone heals reset wounds that clear the walls (a centred 6 × 6 kept 1.000 reset, 0.000 flipped).
- **Closed flips heal given time.** On larger sheets closed flipped wounds heal too (a centred 8 × 8 kept 0.92 by t = 2000 on a 32 × 32 sheet).

GW001 registers these questions on fresh blocks with an engine that runs on any sheet size:
- which record designs repair which wounds;
- how fast;
- what the coarse code really adds;
- whether the conserved body's limits survive a larger sheet.

## The engine

`msegrid/` holds side-agnostic restatements of:
- the lane's draws, births and threshold fields;
- the full acquisition (birth, settle, teach and release on the native routes);
- the block projection;
- the pattern families;
- BR001's record step and BR002's bonds.

At side 16 each equals its original bit for bit (`tests/test_msegrid.py`), and GW001's two simulators equal `br002.sim.simulate` bit for bit (`tests/test_gw001.py`). `mse/`, `br001/` and `br002/` are untouched, because their sources are hashed into frozen studies.

## Panels

**R, the record alone.**
- **No regime needed.** With writing off the record never reads the body (MODEL_LIMITS §2.4). Records are acquired in the conserved body at σ = 0.1.
- **Geometries:**
  - F0 half-planes at sides 16, 32 and 64 (domains 8, 16 and 32 sites thick);
  - stripes 8 thick at side 32 (S8);
  - fresh multi-scale blobs per block at side 16 (BL), at side 32 with the same feature size (BL_32), drawn twice as coarse at side 32 (BLx2) and four times as coarse at side 64 (BLx4).
- **Wounds:**
  - flip (r → −r);
  - reset (r → 0, the record's unstable point; bonds kept);
  - kill (reset, and the bonds between two dead cells lost).
- **Placement** (F0 and S8): at a declared distance d from the nearest wall, centred in the domain ("mid"), or straddling a wall ("cross"); random for BL. Every size and wound kind at one placement shares the same draws, so contrasts across them are paired.
- **Arms:**
  - consensus (self, k_r = 1);
  - stronger consensus (k_r = 2);
  - the coarse code alone;
  - consensus + code (multi);
  - relational (rel);
  - relational + code.
- **Window and reads.** 8,000 updates, read at 2,000 (BR001's window), 4,000 and 8,000, with snapshots every 250 for the time to keep 95% (t95).

**B, the body.**
- **Regimes:** F0 at sides 16 and 32, conserved and open bodies, σ = 0.1, with the native acquisition.
- **Wounds:** body and record wounded together, flipped or reset (body cells newborn), 4 × 4 centred, 8 × 8 touching a wall, and 8 × 8 straddling one.
- **Arms:** static record, multi, relational + code, protected copy.
- **Window and endpoints:** 4,000 updates. Endpoints are the body's agreement overall (v_qual), outside the patch (v_out) and inside it (les_v), and the record's inside the patch (les_r).

Units are 16 development blocks (910500–910515) × 8 cases. The contrasts in `design.CONTRASTS` are paired within case, with 95% t intervals over block means, as BR001 and BR002.

## Registered statements

Every threshold was set from probe P10 (below, 16 engineering cases) and the limits study's probes, with margins. Several statements are therefore replications on fresh blocks.

| Id | Kind | Claim | Rule |
|---|---|---|---|
| G1 | replication (T1, P10) | Consensus alone heals closed flipped wounds of every size tested once they have room; it cannot heal a large flipped wound that touches a wall, at any sheet size | HOLDS if self kept@8000 >= 0.95 for f4-, f6-, f8- and f10-mid at side 32 and f4-, f8- and f12-mid at side 64, and self kept@8000 <= 0.7 for f8-d0 at sides 16, 32 and 64 (block means), else FAILS |
| G2 | replication (T1b, P10) | Reset wounds (cells lost, record at its unstable point) heal fast under consensus alone wherever they clear the walls | HOLDS if self kept@2000 >= 0.95 for every reset wound at mid and d2 placements at sides 32 and 64, and the median t95 of each is <= 1000 updates, else FAILS |
| G3 | scaling (T1c, P10) | The healing time of a closed flipped wound grows faster than its area | HOLDS if the least-squares slope of ln(median t95) on ln(side) for self is >= 2.0 over f4/f6/f8/f10-mid at side 32 and over f4/f8/f12-mid at side 64 (FAILS if any of these medians is censored), and self kept@8000 <= 0.7 for f16-mid at side 64, else FAILS |
| G4 | mechanism | The coarse code's job is wounds at walls, and speed: its gain over consensus is large where a wound touches a wall, and for a large closed wound it is gained time, not a different end state | HOLDS if at side 32 (multi - self) kept@2000 averaged over f4-d0 and f8-d0 exceeds the same average over f4-mid and f8-mid by >= 0.3, and for f12-mid at sides 32 and 64 (multi - self) is >= 0.5 at t = 2000 and <= 0.1 at t = 8000 (block means), else FAILS |
| G5 | mechanism | Stronger consensus heals closed wounds faster when they have room, but pins them when the margin is thin | HOLDS if for f12-mid self_kr2's median t95 at side 64 is at most half of self's, and self_kr2 kept@8000 <= 0.1 at side 32 while self kept@8000 >= 0.9 there, else FAILS |
| G6 | geometry | Domain thickness, not sheet size, decides consensus repair: 8-thick stripes on a 32-site sheet repair flipped wounds as 8-thick half-planes on a 16-site sheet do | HOLDS if \|self kept@2000 on S8_32 - on F0_16\| <= 0.08 for every flipped condition the two share, else FAILS |
| G7 | geometry | Consensus's loss of multi-scale detail is set by feature size on the lattice, not by sheet size, and differs between patterns more than between replicates | HOLDS if for self's undamaged record at t = 2000 \|BL_32 - BL_16\| <= 0.03 and BLx2_32 - BL_32 >= 0.08, and on BL_16 the SD of block means (fresh patterns) is >= 2.5 x the replicate SD between the two births of a pattern, else FAILS |
| G8 | replication (P8, BR002) at scale | A relational record with the coarse code repairs every flipped and reset wound at every size and placement, and a relational record keeps multi-scale detail at every resolution | HOLDS if rel+code kept@8000 >= 0.98 for every flipped and reset wound on F0_16, F0_32, F0_64 and S8_32, and rel's undamaged record agreement at t = 8000 is >= 0.98 on every BL geometry, else FAILS |
| G9 | physics | The conserved body's failure to heal a wound that touches a wall is diluted on a larger sheet, as the mean shift scales with wound area over sheet area | HOLDS if with the protected record, for f8-d0, (conserved - open) les_v is <= -0.3 at side 16 and >= -0.15 at side 32, and (conserved - open) v_out is <= -0.05 at side 16 and >= -0.04 at side 32 (block means), else FAILS |
| G10 | mechanism | With a record that cannot repair itself, the body heals a reset wound but not a flipped one | HOLDS if at side 32 static les_v under r8-d0 exceeds that under f8-d0 by >= 0.4 in both bodies (block means), else FAILS |

## Information boundary

As BR002. The record's dynamics see local record values and, for the relational arms, their bonds (written once when the record was taught). The coarse code is 16 values per 16 × 16 area of privileged storage, and the protected copy is privileged. Wound placement uses the template's geometry: it is the experimenter's choice of where to wound, not information given to the tissue. Targets and scores reach only the evaluator.

## Qualification

Fixed in `gw001/checks.py` before their results, on preflight blocks 900860–900861 at the full shape:
- **Q1** complete and finite;
- **Q2** serial equals parallel;
- **Q3** engine equivalence with BR002 at side 16, bit for bit (acquisition, panel B, panel R's record);
- **Q4** an independent per-site replay of six branches at sides 16, 32 and 64 (its own placement, wounds, bonds, record step and body step), within 1e-9;
- **Q5** exact aliases (kill equals reset for arms without bonds; the protected copy never changes; the static record keeps its wounded state);
- **Q6** reanalysis from saved final states;
- **Q7** a placement audit of every F0 and S8 patch;
- **Q8** efficacy;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities.
- **The model-limits study** (blocks 900832–900847, tag `mse-expansion`) and the lead's check of it (blocks 900850–900851, BR002's tag); MODEL_LIMITS_AND_EXPANSION.md and `probes/expansion/`.
- **Unit tests** on blocks 900862–900863.
- **Probe P10** (`probes/p10_gw001_design_inputs.py`, blocks 900852–900853 under GW001's tag). It ran GW001's worker with this design on every panel. Its levels were read, and the thresholds were set from them. One threshold was then loosened before the freeze: G2's reset healing time went from 750 to 1,000 updates, because P10's slowest reset wound sat exactly at 750.
- **A debug run of the whole pipeline** (blocks 900862–900863) and its checks. The debug run (21:46Z) and its checks passed Q1–Q10 at the first attempt. The independent per-site replay agreed to 9 × 10⁻¹⁵, the difference being summation order in independent code. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **G1–G3.** If closed flipped wounds heal given room and time while wall-touching ones do not, and reset wounds heal fast, BR001's "consensus for small wounds, a code for large ones" is replaced by a sharper rule. Consensus repairs anything that does not fuse with an opposite domain, in a time that grows faster than the wound's area.
- **G4–G5.** If the code's gain is concentrated at walls and in speed, a coarse positional code is chiefly a boundary and speed device. If stronger consensus pins thin margins, faster repair costs robustness at the pattern's walls.
- **G6–G7.** If domain thickness and feature size, not sheet size, decide repair and detail loss, the lane's earlier numbers transfer to any tissue with the same feature-to-cell ratio. The pattern-to-pattern spread then has to be reported beside every pattern-specific number.
- **G8.** If the relational record with the code repairs everything at every size, BR002's design result is not a small-sheet artefact.
- **G9–G10.** If the conserved body's penalty shrinks with sheet size and the body heals reset but not flipped wounds, BR001's body-physics result (RL4) is a small-sheet effect, and the wound's kind matters for the body as it does for the record.
