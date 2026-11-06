# PLAN_SM005: the reader's lengths, one at a time

**Written by fork H1 at the start of phase A, 2 November 2026 (about 12:20Z), before any variant value, for the lead's
review.** The PI's word: "lets start the two next one in parallel" (about 12:00Z on 2 November), after the lead's AR004
and SM004 reports; the two next are AR005 (fork A3, cores 2–36) and SM005 (fork H1, cores 37–71). The lead's constraint
(about 12:12Z): SM005 claims no development blocks and no engineering blocks for new simulation; it rereads saved
records only.

## The question

- **SM002:** a reader scaled with the tissue (the half-scale reader seen at twice the grain, `cg`) reads the doubled
  tissue as well as the small reader reads the half-scale one.
- **SM004:** with the reader's grain named, the late loss under a FIXED reader at the doubled scale is under-predicted:
  the model gives −0.087, TEST observed −0.147 (SM003's F4 gave −0.143). A length of the reader that the model does not
  name carries the rest.
- **SM005** (SM003's next step 2, SM004's next step 1): double ONE of the reader's lengths at a time to match the doubled
  tissue, keeping the others at the base. The lengths are its coupling, its erasure size and the record's bond grain.
  **Which carries the late loss, and do the parts add up to the fully scaled reader's recovery?**

## The design: rereads of saved records

No episode is run and no block is drawn. Every stage rereads the refined units' saved final records (SM001's W8_x64_r2,
W16_x64_r2, W32_x64_r2: `r`, `H`, `W` at side 64, float32 and int8; 9 arms and the no-record control, 8 cases, patch
sizes L 4, 8, 16), each under its own study's tag and case set, with five readers:

| Reader | What it is | Its lengths against the base |
|---|---|---|
| **base** | SM001's successor (`sm001.sim.successor`, stream `dw`): SM003's g 1 | — |
| **cg** | SM002's cg reader (`sm002.coarse.read_cg`, stream `dw-cg`): SM003's g 2, the fully scaled reader | every length x 2 (coupling, erasure, the record's value grain, reach and bond grain) |
| **C** | the base with the body's coupling x 4 (its coupling length x 2) at dt 0.1 over 4,000 updates, and the gain x g_C | the coupling length only |
| **E** | the base with the gain x g_E | the erasure size only |
| **B** | the base on the record with its bonds coarse-grained 2 x 2 by SM002's declared rule and lifted back (bonds inside a block +1, across blocks the coarse bond), its values unchanged | the record's bond grain only |

- **C in full:** the body's coupling 4.0 (base 1.0), dt 0.1 (base 0.2), 4,000 updates (the same time, 400), the body's
  noise per update σ/√2 (the same per unit time); the record's step at the same rate per unit time (EPS/2 = 0.025,
  KR unchanged at 1.0, SIGMA_R/√2), so the record's own reach is not scaled; the gain per unit time x g_C.
  - SM002's candidate 1′ (coupling x 4 at dt 0.1, gain unchanged, KR x 4) doubled the erasure size with the coupling
    (it cleared islands up to 6, against the base's 3). The gain x g_C holds the erasure size at the base's, so C
    doubles the coupling length alone. In a double well with a linear pull g toward the record, the smallest held island
    scales as √(coupling)/g: so g_C = 2 is expected, and the measurement decides (below).
- **E in full:** the base reader (coupling, dt, window, record step unchanged) with the gain x g_E: by the same scaling
  g_E = 1/2 doubles the erasure size. It also halves the body's pull toward the record per unit time; that is how this
  reader's erasure size is set, and it is disclosed as the variant's nature.
- **B in full:** the base reader unchanged; only the bonds it reads through are coarse-grained, so the record relaxes at a
  2-site grain while its values and the body stay at the base.
- **Draws:** C, E and B draw from the base's stream (`dw`) under the record's tag, so each is paired with the base
  (common random numbers), and at the base setting each equals the base bit for bit. cg keeps its own stream (`dw-cg`),
  as it was read.
- **The endpoints:** E (the agreement with the acquired template inside the patch), the generic recovery and the phase,
  at the reader's last read (2,000 updates; C's 4,000), and the final bodies (float32).

## The engineering, before any variant value on the records

1. **The reader loop:** SM002's smoke loop (`probes/p43s_sm002_smoke.py`'s `reader`, `sm001.sim.successor`'s
   arithmetic with the parameters as arguments), extended with the gain factor and the bond map. At the base parameters
   it must equal `sm001.sim.successor` bit for bit on a real record (every branch).
2. **C's stability at dt 0.1:** the checkerboard multiplier inside a domain, (1 + dt (f′(V*) − 2 × coupling))
   (1 − dt × gain), at the domain's fixed point, must lie in (−0.5, 1); and on a stripe record (W16, side 64, 8 cases) no
   site clipped, no sign checkerboard, and the checkerboard mode's rms at most 1.5 times the base's.
3. **The erasure sizes** (SM002's island test): a uniform record (+1.2, every bond +1) with one flipped ℓ x ℓ island,
   bonds consistent, ℓ in 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 24, 8 cases, read for the full window; the erasure size is
   the largest ℓ whose island reads with the background (agreement >= 0.5). Measured for base, cg, B, C at gain factors
   1, √2, 2, 2√2, and E at 1/√2, 1/2, 1/(2√2), 1/4. **The calibration, fixed here:** g_C is the smallest factor at
   which C's erasure size equals the base's; g_E the factor nearest 1 at which E's erasure size is at least twice the
   base's. If no factor does it, STOP and report.
4. **Exactness bridges at the base setting:** C at coupling 1, dt 0.2, 2,000 updates, gain x 1 and the base record step,
   and E at gain x 1, each equal `sm001.sim.successor` bit for bit; B's bond map returns a 2x upsampled record's bonds
   exactly, so on an upsampled record B equals the base bit for bit.
5. **The base bridge:** the base reread equals the saved g 1 reads at every read, every sign-based endpoint bit for bit
   (in, in_gen, align, r_align, shape, agree); the final body (float32-stored records read in float64) and the spacing are
   recorded, not gated (SM003's FIT-reread criterion). **The cg bridge:** the cg reread equals the saved cg reads in the
   same sense; and cg's own bridge to SM002's definitions (on 2x upsampled side-32 records, cg at side 64 equals SM001's
   reader at side 32 bit for bit). Both run in every task.

## The stages (no draw)

| Stage | Records | Tag | Tasks (refined units) |
|---|---|---|---|
| smoke | P45's W8_x64_r2 on 900476 (one task) | mse-p45 | 1 |
| P54, the probe | SM003's P45, 900476–900479 | mse-p45 | 12 |
| debug | SM004's debug, 900472 | mse-sm004 | 3 |
| preflight (phase B) | SM004's preflight, 900470–900471 | mse-sm004 | 6 |
| development | SM003's TEST 910879–910888, 910894–910899 (16) and SM004's TEST 910617–910627, 910859–910861, 910890–910891 (16) | mse-sm003, mse-sm004 | 96 |

- Every input file is checked by sha256 against its stage's manifest, and its case set enrolled as its study did.
- **The records scan** (12:12Z; `runs/.../sm005/scan_records.txt`): the 39 record blocks are named only by SM003's and
  SM004's files and run roots (and ENGINE.md's account of them). None is in AR005's holds (its progress.md).
- **Disclosed:** the base reader's and cg's values on these records were read in SM003 and SM004 (P45, the debug and
  preflight runs, TEST). The variants' never were. So F (below) is not blind; V_C, V_E and V_B are.

## Statement candidates (declared before any variant value)

Per refined condition (unit, L, arm) read at full resolution, per case: **F = E_cg − E_base**, the fully scaled reader's
recovery, and **V_X = E_X − E_base** for X in C, E, B. Every part is linear in the case values: per case the mean over
its conditions, a block's value the mean of its 8 cases, the part the mean over the blocks. **Granularity: 0.01.**

| Id | Signal (conditions a block) | Per-case value | Kind |
|---|---|---|---|
| L1 | late, m 2 (27) | V_C, the coupling's recovery | band |
| L2 | late (27) | V_E, the erasure size's | band |
| L3 | late (27) | V_B, the bond grain's | band |
| L4 | late (27) | F, the full recovery | band |
| L5 | late (27) | A = V_C + V_E + V_B − F, the additivity | band |
| P1–P4 | prompt, m 0 (54) | V_C, V_E, V_B, F | band |

- **The rule** (BE002's): on P54 (4 blocks x 8 cases) each part sits at least 1.68 SD inside its threshold (the
  lead's figure, 3√(1/4 + 1/16); with 32 development blocks the formula gives 1.59, so 1.68 is conservative) and passes
  in both halves of P54 (900476–77, 900478–79). The thresholds are the narrowest round values the rule allows on P54.
- **The SD:** the max rule on the case values (the larger of the block SD and the case SD over √8). No fitted model
  enters, so there is no SD_F. Intervals on the development: mean ± t(0.975, 31) x SD / √32.
- **Every band part registers at its narrowest band;** none is dropped for its P54 value.
- **Reported:** each variant's share of the late loss recovered, V_X / F, with a whole-block bootstrap interval (10,000
  resamples), read as a ratio only if F's 95% lower bound is at least half its estimate (HS001's ratio rule); the same
  under the prompt signal; the prompt additivity; the late less prompt contrasts; every part by unit, by patch size and
  by source study (SM003's 16 blocks, SM004's 16); each reader's E, generic recovery and phase; the erasure sizes and
  the stability figures.

## What each outcome would mean (fixed before any value)

"One length carries most of the late loss": its late share V_X / F is at least 0.5, its share's lower bound at least
0.25, and each other single-length share below 0.25.

| Outcome | Reading |
|---|---|
| C carries most | The late loss under a fixed reader is the body's coupling length not keeping pace with the doubled tissue: the reader's own interaction range. |
| E carries most | It is the reader's erasure size: what a reader of the base's reach erases or holds in a record repaired at the doubled scale. |
| B carries most | It is the record's bond grain: the record relaxing at the base's 1-site grain while its features have doubled. |
| No length carries most, A's band covers 0 | The lengths share the recovery and add up to the scaled reader's: each carries part. |
| A below 0 | The three single lengths fall short of the scaled reader: cg's other scalings (the record's value grain and reach) or the lengths' interactions carry the rest. |
| A above 0 | The single-length recoveries overlap: the lengths act on the same part of the loss. |
| A length recovers late but not prompt (P near 0) | It acts on the late signal's damage specifically, as the scale loss does (SM001–SM004). |

No confirmation is declared.

## Qualification (Q1–Q10, fixed in `sm005/checks.py` before their results)

Q1 every endpoint at its shape, finite; Q2 one task rerun in-process bit for bit; Q3 the bridges (the base and cg
rereads against the saved reads in every task of the stage; cg against SM002's definitions; every variant at its base
setting; the inputs' sha256); Q4 an independent replay of one C, one E and one B branch from the definitions (explicit
loops) within 1e-8, E exact; Q5 the no-record control alike under base, E and B (gain 0 makes them the same read); Q6 E
recomputed from the saved final bodies within 1/64; Q7 the erasure sizes and C's multiplier re-measured as declared,
the calibrated factors in force, the units refined, every condition present, no block drawn; Q8 a branch listed twice
gives identical outputs and reordering changes none; Q9 the development within 35 CPU-hours and 12 h of wall on 12
workers, memory within 2 GB, disk; Q10 the reader's dry run (predict and tables complete, every candidate scored,
every output at most 256 KiB).

## Price

From SM003's and SM004's TEST timing, the base read of a refined task (three patch sizes) costs 140–200 CPU-seconds.
A task reads base 1, cg 0.25, C 2, E 1 and B 1: about 5.25 reads, 735–1,050 CPU-seconds. The smoke measures it.
- **Phase A** (cap 6): the smoke and the engineering about 0.5; P54 (12 tasks) 2.5–3.5; the debug run (3 tasks)
  0.6–0.9; Q1–Q10 about 0.6. **About 4.2–5.5 CPU-hours.** If the smoke prices P54 and the debug run over the cap, STOP
  and report before P54.
- **The development** (cap 35): 96 tasks, **about 20–28 CPU-hours**; the preflight 6 tasks, about 1.5.
- **The node:** cores 37–71, nice 10; at most 8 workers in phase A, 12 in the development; at every launch, STOP if the
  1-minute load passes 100 or available memory is under 20 GiB beyond the workers' need (1.6 GiB each).

## Not run

- **SM002's candidate 1′ itself** (coupling x 4 with KR x 4, gain unchanged): it doubles the coupling and the erasure size
  together, and the record's reach. About +2 reads a task.
- **The record's value grain and reach** (SM002's avg-u reread; KR x 4) as single lengths: they are cg's other scalings,
  and A says whether they are needed.
- **Fresh episodes, geometry, the 128 x 128 refinement:** none; SM005 rereads saved records only.

## Files (to be written)

`sm005/` (design, readers, worker, run, analyze, predict, tables, checks); `tests/test_sm005.py`;
`probes/p54s_sm005_smoke.py`, `probes/p54b_sm005_margins.py` and their results; the run root
`/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm005/` (progress.md, the smoke, P54, the debug run). No REPORT
file: the lead writes it.

## Amendment 1 (2 November 2026, about 15:17Z): the engineering read, B's erasure, two added candidates (the lead's ruling)

Written after the engineering was read and before P54, the first variant value. A session crash at about 12:21Z and a
login-node reboot at about 13:54Z killed the first erasure run; it was rerun alone (15:06–15:12Z).

- **The engineering** (`probes/results/p54s_sm005_identity.json`, `_stability.json`, `_erasure.json`, `_erasure_b.json`):
  - every base-setting bridge holds bit for bit (the loop at the base, C at its base setting, E at gain x 1, B on a
    2-grain record);
  - C is stable at every gain factor (multipliers −0.011 to −0.025; no clipping, no checkerboard);
  - erasure sizes: base 3 and cg 8, both rows equal to SM002's smoke exactly; C 6, 6, 4, 3 at gain x 1, √2, 2, 2√2; E 3,
    4, 6, 8 at x 1/√2, 1/2, 1/(2√2), 1/4.
- **The calibration by the declared rule** (approved): **G_C = 2√2 = 2.83** (C erases 3, the base's) and **G_E = 1/(2√2) =
  0.354** (E erases 6). The √(coupling)/gain scaling predicted 2 and 1/2; the lattice needs the next grid point each way.
- **B's erasure (disclosed):** B erases 6 at gain x 1, and 5 at x √2, 2 and 2√2. With 2-site bonds the record itself does
  not hold islands under about 5 sites, so the reader's gain cannot hold B's erasure back. **B is the bond grain together
  with the record's own erasure; E is the reader body's erasure at the base grain.** B stays as declared.
- **Two added statement candidates** (granularity 0.01; bands by the same rule on P54):
  - **K1, B − E** (late), with **K1p** its prompt contrast: per case E_B − E_E, the bond grain's recovery beyond the
    erasure it brings. B and E erase islands of the same size (6), so B − E isolates the bond grain **provided the bond
    grain and the erasure it brings act additively** in B.
  - **K2, F − (V_C + V_B)** (late): the additivity with the overlap removed. B already carries the erasure, so E is not
    added a second time. It stands beside the declared L5 (A = V_C + V_E + V_B − F).
  - **They register only if P54 supports them:** their narrowest band's half-width is at most half of P54's |L4| (the full
    late recovery), so that the band is informative against what is to be split. Otherwise they are reported.
- **The outcome table, added before any value:**

  | Outcome | Reading |
  |---|---|
  | **L5: A above 0, as expected** | The three-way sum counts the erasure twice (in E and in B), so it exceeds the scaled reader's recovery. |
  | K2 near 0 | C and B (with the erasure B brings) account for the scaled reader's recovery between them. |
  | K2 above 0 | Something else the scaled reader doubles (the record's value grain or reach) carries the rest. |
  | K2 below 0 | C and B overlap. |
  | **B about E** (K1's band covers 0) | The erasure, not the bond grain, carries B's recovery. |
  | **B clearly above E** (K1's band above 0) | The bond grain matters beyond its erasure. |
  | **C** (L1) | The coupling length isolated at the base's erasure (C erases 3): what the body's interaction range alone recovers. |

  **A row added under this table** (Added 2 November 2026, about 15:47Z, on the lead's ruling, after P54's values were read and before any development value. K1p registers by Amendment 1's support condition with a band wholly below 0, so its reading is named before the development.):

  | Outcome | Reading |
  |---|---|
  | **B below E** (K1p's registered band, and K1's reported value, below 0) | The record's bond grain at 2 sites, with the record's own erasure of the same island size, recovers less than the reader body's erasure at the base grain. Coarsening the record's bonds costs part of what erasing islands of that size recovers: the record's erasure and the reader's are not interchangeable. |

- **The price** (approved): one task about 440 CPU-seconds at today's load (the identity run's reads); P54 about 1.5
  CPU-hours, phase A about 2.6, the development about 12. The separate smoke stage is not run: the identity run's timing
  priced the tasks.
