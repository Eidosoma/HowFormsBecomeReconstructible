# SM005 phase B: the run record (fork H1, 2 November 2026)

The frozen reader's outputs on the development are `predictions_scored.json` (the registered parts, K1 reported, the
shares, the levels, the parts by unit and size) and `TABLES.md`. The development rereads the refined units' saved final
records of the 32 TEST blocks (SM003's 16 then SM004's 16, the block order, so the two halves are the two sources) with
five readers. F = E_cg − E_base, V_X = E_X − E_base; 95% t intervals over the 32 blocks.

## Commits and stages

- **The plan:** 81e5a26049 (12:14:47Z). **Amendment 1**, the engineering and the package: 976191f0bd (15:17:35Z), before
  P54. **Phase A for review:** a554bfd439 (15:43:53Z). **The lead's P54c:** 22ab6561fe (pushed 15:44:39Z).
- **The freeze:** cd2ab608eb (15:46:56Z, pushed 15:47:00Z); design frozen 15:46:17Z, digest 8b759268ac24 (177 source
  hashes, the debug run's digest); predictions frozen 15:46:18Z.
- **The preflight:** SM004's preflight records 900470–900471 reread, 15:47:15–15:53:34Z, 6 tasks on 6 workers, 2,259
  CPU-seconds, peak worker memory 459 MB, every bridge equal.
- **Q1–Q10:** PASS, all ten (15:53:51–15:59:39Z, 615 CPU-seconds). Receipt commit da74c92969 (16:00:09Z, pushed 16:00:18Z),
  which names the freeze commit.
- **The development:** 96 tasks (3 refined units x 32 blocks), 16:00:35–17:04:41Z on 12 workers (cores 37–71, nice 10;
  the 1-minute load 20.7 and 354 GiB available at the launch): 45,826 CPU-seconds (12.73 CPU-hours, 477 a task), 3,846 s of
  wall, peak worker memory 478 MB, 1.61 GB written. Every task's base and cg rereads equal the saved reads; nothing
  crashed, was resumed or redone. No block was drawn.
- **The frozen reader:** about 3 CPU-seconds.
- **The ledger:** the development 12.73 CPU-hours against the cap of 35 (Q9 forecast 10.04); phase B in all (the
  preflight, Q1–Q10, the development, the reader) 13.53; phase A about 2.61.

## Registered statements (32 blocks): 11 of 11 HOLD

| Id | Part | Value [95%] | Band | Halves (SM003's 16, SM004's 16) | |
|---|---|---|---|---|---|
| L1 | late: V_C, the coupling length's recovery | +0.0466 [+0.0413, +0.0519] | [+0.02, +0.10] | +0.0471, +0.0461 | holds |
| L2 | late: V_E, the erasure size's | +0.1911 [+0.1795, +0.2028] | [+0.14, +0.32] | +0.1825, +0.1998 | holds |
| L3 | late: V_B, the bond grain's (with the record's own erasure) | +0.0320 [+0.0126, +0.0513] | [−0.12, +0.24] | +0.0279, +0.0360 | holds |
| L4 | late: F, the fully scaled reader's | +0.1861 [+0.1715, +0.2006] | [+0.13, +0.33] | +0.1766, +0.1955 | holds |
| L5 | late: A = V_C + V_E + V_B − F | +0.0836 [+0.0658, +0.1013] | [−0.04, +0.28] | +0.0808, +0.0864 | holds |
| P1 | prompt: V_C | +0.0263 [+0.0224, +0.0303] | [+0.00, +0.07] | +0.0255, +0.0271 | holds |
| P2 | prompt: V_E | +0.1062 [+0.0963, +0.1161] | [+0.05, +0.22] | +0.0975, +0.1148 | holds |
| P3 | prompt: V_B | +0.0141 [+0.0005, +0.0278] | [−0.10, +0.17] | +0.0122, +0.0161 | holds |
| P4 | prompt: F | +0.1052 [+0.0948, +0.1157] | [+0.05, +0.22] | +0.0969, +0.1136 | holds |
| K1p | prompt: B − E | −0.0920 [−0.1053, −0.0788] | [−0.20, −0.01] | −0.0854, −0.0987 | holds |
| K2 | late: F − (V_C + V_B), the overlap removed | +0.1075 [+0.0936, +0.1215] | [+0.00, +0.21] | +0.1017, +0.1134 | holds |

**K1, reported** (B − E under the late signal; not supported by P54): **−0.1592 [−0.1794, −0.1390]**, halves −0.1545 and
−0.1638.

**The margins on TEST** (in SD, for information; the rule applied at P54): L4's lower side 1.39, L2's lower 1.58; every
other side 1.81 or more.

## The shares of the recovery (reported; read as ratios: F's lower bound is above half F under both signals)

| | F | C | E | B |
|---|---|---|---|---|
| late | +0.1861 [+0.1715, +0.2006] | 0.250 [0.228, 0.273] | **1.027 [0.976, 1.088]** | 0.172 [0.076, 0.255] |
| prompt | +0.1052 [+0.0948, +0.1157] | 0.250 [0.226, 0.274] | 1.009 [0.954, 1.068] | 0.134 [0.011, 0.240] |

Whole-block bootstrap, 10,000 resamples, seed 20261102. The prompt additivity: +0.0414 [+0.0270, +0.0559]. Late less
prompt: C +0.0202 [+0.0177, +0.0228]; E +0.0849 [+0.0791, +0.0907]; B +0.0178 [+0.0109, +0.0247].

## The readings, by the frozen outcome table

- **The reader's erasure size alone recovers the whole late loss the scaled reader recovers.** E's recovery is +0.191
  against the scaled reader's +0.186: its share is 1.03 [0.98, 1.09]. Under the prompt signal the same: 1.01.
- **By the declared rule no single length "carries most".** The rule needs each other share below 0.25, and C's late share
  is 0.2503 (0.2501 under the prompt signal), at the line. E's share and its lower bound pass by far (1.03, 0.98); B's
  (0.17) passes.
- **The coupling length,** isolated at the base's erasure, recovers a quarter (C 0.25 under both signals).
- **The bond grain recovers least, and less than the reader's erasure of the same island size:** B − E is −0.159 late
  (reported) and −0.092 prompt (K1p holds, a band wholly below 0). This is the row "B below E": the record's erasure and
  the reader's are not interchangeable.
- **The additivity:** the three-way sum exceeds the scaled reader's recovery (A +0.084), as expected with the erasure
  counted twice. With the overlap removed, K2 is +0.108: C and B together account for well under the full recovery, and
  the rest (about 0.11) is carried by what the scaled reader doubles beyond them, here the reader body's erasure size.
- **Every part is concordant across the two sources** (SM003's 16 blocks and SM004's 16).
- **By patch size and unit:** E tracks F everywhere (L 4: 0.19 against 0.17; L 8: 0.28 against 0.27; L 16: 0.11 against
  0.11).

## Each reader's levels (mean E; generic recovery; phase)

| Reader | late E | late generic | late phase | prompt E | prompt generic | prompt phase |
|---|---|---|---|---|---|---|
| base | 0.5576 | 0.8814 | −0.3239 | 0.8067 | 0.9420 | −0.1354 |
| cg | 0.7436 | 0.9291 | −0.1854 | 0.9119 | 0.9776 | −0.0657 |
| C | 0.6041 | 0.8667 | −0.2625 | 0.8330 | 0.9363 | −0.1033 |
| E | 0.7487 | 0.9415 | −0.1928 | 0.9129 | 0.9824 | −0.0695 |
| B | 0.5895 | 0.8635 | −0.2740 | 0.8208 | 0.9355 | −0.1147 |

E reaches the scaled reader's level (0.749 against 0.744 late), mostly by recovering the acquired phase (its phase −0.19
against the base's −0.32), as cg does.

## Disclosed

- **The crash and the reboot** (about 12:21Z and 13:54Z): the first erasure run was killed (about 220 CPU-seconds lost)
  and rerun alone; nothing else was lost, and the package on disk was the one written.
- **B's own erasure** (Amendment 1): B doubles the erasure size (6) through the record, and the gain cannot hold it back.
- **The outcome row "B below E"** was added on the lead's ruling after P54's values and before any development value.
- **F is not blind:** the base's and cg's values on these records were read in SM003 and SM004; the variants' never were
  before SM005.

## Files

- **In git** (each at most 256 KiB): this record; `predictions_scored.json` (24,844 B); `TABLES.md`.
- **On scratch** (`/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm005/`): the development, preflight, debug
  and P54 roots (shards, bodies, done records, manifests), `progress.md`, the launchers (`tools/`).
