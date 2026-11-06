# SM006 phase B: the run record (fork H1, 2 November 2026)

The frozen reader wrote two outputs on the development:
- `predictions_scored.json`: the registered parts, S2 and S7 as reported, R1–R20, H1 beside every part, and the
  sensitivity U's values.
- `TABLES.md`.

The development rereads the saved records of the 32 TEST blocks with the gain variants, under the frozen J4. The block
order is SM003's 16 then SM004's 16, so the two halves are the two sources. Intervals are 95% t intervals over the 32
blocks, with SD = √(SD_T² + SD_F²).

## Commits and stages

- **The plan:** a284bd0bc0 (17:38:42Z). **Amendment 1:** b4fe068ad5 (17:39:52Z).
- **The model** was frozen with the package as ac03c6b500 (18:11:19Z), before P55 was run or read.
- **Phase A for review:** 576ba88b6d (18:34:51Z). **The lead's P55c:** c92ca1558a (pushed 18:37:37Z).
- **The freeze:** de81480388 (18:44:55Z, pushed 18:44:59Z).
  - The design was frozen at 18:44:07Z: digest 6300a7c7408f (186 source hashes), the digest of P55 and the debug run.
  - The predictions were frozen at 18:44:08Z.
  - The sensitivity U: model sha256 0ed6eea6dc925d01….
- **The preflight** reread SM004's preflight records 900470–900471, 18:45:13–18:52:00Z: 12 tasks on 12 workers, 3,803
  CPU-seconds, peak worker memory 463 MB, every bridge equal.
- **Q1–Q10:** PASS, all ten (18:52:37–18:57:17Z, 580 CPU-seconds). The re-price was 20.05 CPU-hours, within 35. The
  receipt commit is def76d3feb (18:57:42Z, pushed 18:57:48Z), and it names the freeze commit.
- **The development:**
  - 192 tasks (6 units × 32 blocks), 18:58:03–20:27:35Z on 12 workers (cores 37–66, nice 10). At the launch the 1-minute
    load was 55.9, with 325 GiB available.
  - 60,007 CPU-seconds (16.67 CPU-hours: 365 a transfer task, 260 a refined task). 5,372 s of wall; peak worker memory
    477 MB; 1.90 GB written.
  - Every task's base and E(6) bridges are equal. Nothing crashed, was resumed or was redone. No block was drawn.
- **The frozen reader** ran 20:28:48–20:29:37Z (14 CPU-seconds). It first checked that `sm006/predict.py`, every source
  and the digest are the frozen ones.

## The statements (32 blocks): 9 of 9 registered parts HOLD

The verdicts use the frozen thresholds from P55. S2 and S7 are reported with their intervals (the lead's ruling). H1
beside is H1 in the model's place; for S2 and S7, which compare the two, it is their first term, |H1's error|. U is the
reported sensitivity, value only.

| Id | Part | Value [95%] | Threshold | Halves (SM003's 16, SM004's 16) | Verdict | H1 beside [95%] | U |
|---|---|---|---|---|---|---|---|
| S1 | the late loss from FIT alone: refinement, base g 1, late: (E - E twin) - (the model - the model at the twin) | -0.0305 [-0.0544, -0.0066] | [-0.16, +0.08] | -0.0357, -0.0254 | HOLDS | -0.0654 [-0.0822, -0.0487] (R6) | +0.0228 |
| S2 | the late loss against H1: \|H1's loss error\| - \|the model's loss error\| | +0.0319 [+0.0236, +0.0402] | reported | +0.0366, +0.0272 | reported | +0.2775 [+0.2677, +0.2873] (R17) | +0.0240 |
| S3 | E(4), blind: every unit, g 1, gain x 1/2: E - the model | +0.0395 [+0.0244, +0.0547] | [-0.05, +0.11] | +0.0484, +0.0307 | HOLDS | +0.0762 [+0.0586, +0.0939] (R7) | +0.0450 |
| S4 | E(8), blind: every unit, g 1, gain x 1/4: E - the model | +0.0438 [+0.0277, +0.0598] | [-0.02, +0.15] | +0.0456, +0.0420 | HOLDS | +0.0627 [+0.0450, +0.0804] (R8) | +0.0431 |
| S5 | the erasure's recovery at eps 8, blind: refinement, late: (E(8) - E base) - (the model at 8 - at the base) | +0.0842 [+0.0538, +0.1146] | [-0.01, +0.28] | +0.0712, +0.0972 | HOLDS | +0.2205 [+0.2049, +0.2360] (R9) | +0.0243 |
| S6 | the same at eps 4 | +0.0660 [+0.0510, +0.0811] | [+0.01, +0.17] | +0.0617, +0.0704 | HOLDS | +0.1332 [+0.1230, +0.1435] (R12) | +0.0372 |
| S7 | closer than H1 at the blind targets: every unit, g 1, eps 4 and 8: \|E - H1\| - \|E - the model\| | +0.0416 [+0.0351, +0.0480] | reported | +0.0421, +0.0410 | reported | +0.2014 [+0.1912, +0.2117] (R19) | +0.0441 |
| S8 | the g-2 offset kept: refinement, g 2: E - the model | -0.0444 [-0.0577, -0.0310] | [-0.10, +0.02] | -0.0411, -0.0477 | HOLDS | -0.0293 [-0.0454, -0.0132] (R13) | -0.0518 |
| S9 | the g-4 shortfall kept: refinement, g 4: E - the model | +0.0473 [+0.0330, +0.0616] | [+0.00, +0.14] | +0.0559, +0.0387 | HOLDS | -0.0073 [-0.0212, +0.0066] (R14) | +0.0634 |
| S10 | the prompt loss kept: refinement, base g 1, prompt: as S1 | +0.0120 [-0.0050, +0.0289] | [-0.08, +0.09] | +0.0095, +0.0144 | HOLDS | +0.0047 [-0.0089, +0.0183] (R15) | +0.0520 |
| S11 | the larger sheet kept: transfer, base g 1, 2 and 4: E - the model | +0.0195 [+0.0068, +0.0321] | [-0.05, +0.08] | +0.0299, +0.0090 | HOLDS | +0.0040 [-0.0089, +0.0168] (R16) | +0.0245 |

**The margins on TEST** (in SD, for information; the rule applied at P55): S1 1.95, 1.67; S3 2.13, 1.67; S4 1.43,
2.39; S5 1.12, 2.32; S6 1.34, 2.49; S8 1.50, 1.74; S9 1.19, 2.33; S10 1.96, 1.66; S11 1.98, 1.72. Every half of every
registered part lies inside its band, with the sign of the whole.

## Reported (R1–R20)

| Id | Part | Value [95%] | Halves (SM003's 16, SM004's 16) |
|---|---|---|---|
| R1 | E(6), refinement (not blind): E - the model | +0.0436 [+0.0296, +0.0577] | +0.0470, +0.0403 |
| R2 | E(6), transfer (blind): E - the model | +0.0396 [+0.0222, +0.0569] | +0.0477, +0.0314 |
| R3 | the erasure's recovery at eps 6 (SM005's V_E): refinement, late | +0.0691 [+0.0446, +0.0936] | +0.0604, +0.0777 |
| R4 | the matched-reader gain at g 2: (E - E twin at g/2) - (the model - at the twin at g/2) | -0.0242 [-0.0393, -0.0091] | -0.0362, -0.0121 |
| R5 | the same at g 4 | +0.0332 [+0.0186, +0.0478] | +0.0330, +0.0334 |
| R6 | H1 on S1: the late loss | -0.0654 [-0.0822, -0.0487] | -0.0706, -0.0603 |
| R7 | H1 on S3: E(4) | +0.0762 [+0.0586, +0.0939] | +0.0851, +0.0674 |
| R8 | H1 on S4: E(8) | +0.0627 [+0.0450, +0.0804] | +0.0646, +0.0609 |
| R9 | H1 on S5: the recovery at eps 8 | +0.2205 [+0.2049, +0.2360] | +0.2075, +0.2335 |
| R10 | the observed late loss, base g 1: E - E twin | -0.1526 [-0.1629, -0.1423] | -0.1577, -0.1475 |
| R11 | the observed recovery at eps 8: E(8) - E base, refinement, late | +0.2205 [+0.2049, +0.2360] | +0.2075, +0.2335 |
| R12 | H1 on S6: the recovery at eps 4 | +0.1332 [+0.1230, +0.1435] | +0.1289, +0.1376 |
| R13 | H1 on S8: g 2, refinement | -0.0293 [-0.0454, -0.0132] | -0.0260, -0.0326 |
| R14 | H1 on S9: g 4, refinement | -0.0073 [-0.0212, +0.0066] | +0.0013, -0.0159 |
| R15 | H1 on S10: the prompt loss | +0.0047 [-0.0089, +0.0183] | +0.0023, +0.0071 |
| R16 | H1 on S11: the larger sheet | +0.0040 [-0.0089, +0.0168] | +0.0144, -0.0065 |
| R17 | S2's first term: \|H1's late-loss error\| | +0.2775 [+0.2677, +0.2873] | +0.2753, +0.2797 |
| R18 | S2's second term: \|the model's late-loss error\| | +0.2456 [+0.2367, +0.2546] | +0.2387, +0.2526 |
| R19 | S7's first term: \|E - H1\| at the blind targets | +0.2014 [+0.1912, +0.2117] | +0.2009, +0.2019 |
| R20 | S7's second term: \|E - the model\| at the blind targets | +0.1599 [+0.1538, +0.1659] | +0.1588, +0.1609 |

## The readings, by the frozen outcome table (the lead reads; these are the values)

- **The late loss.**
  - The observed late loss is −0.153 (R10). J4 predicts −0.122 and H1 −0.087.
  - J4's error is −0.031 [−0.054, −0.007] (S1). It holds in its band, but its interval excludes 0. H1's error is −0.065
    [−0.082, −0.049] (R6).
  - J4 closes 0.035 of H1's 0.065 shortfall (53%).
  - S2 is +0.032 [+0.024, +0.040], reported, with both halves positive (+0.037, +0.027). J4's late-loss error is smaller
    than H1's.
- **The blind erasure readers.**
  - The model's errors are +0.040 [+0.024, +0.055] at E(4) and +0.044 [+0.028, +0.060] at E(8) (S3, S4 hold). H1's are
    +0.076 and +0.063.
  - At E(6) on the transfer units (blind, R2) the error is +0.040 [+0.022, +0.057].
  - S7 is +0.042 [+0.035, +0.048], reported, and +0.042 and +0.041 in the halves. J4 is closer than H1 at the blind
    targets.
  - J4 under-reads every gain variant by about 0.04.
- **The erasure's own recovery.**
  - At ε 8 the observed recovery is +0.221 (R11), and J4 predicts +0.136 (62%); S5 is +0.084 [+0.054, +0.115].
  - At ε 4 it is +0.133, and J4 predicts +0.067 (50%). S6 is +0.066 [+0.051, +0.081] and holds with its band above 0,
    which is the added row: J4 under-predicts the erasure's own recovery at the doubled scale.
  - At ε 6 (R3, not blind) the shortfall is +0.069 [+0.045, +0.094].
- **SM004's successes** (S8–S11 hold):
  - The values are g 2 −0.044, g 4 +0.047, the prompt loss +0.012 and the larger sheet +0.020.
  - H1's values beside them are −0.029, −0.007, +0.005 and +0.004. On each of the four, H1 is nearer 0 than J4.
- **The matched-reader gains against the model** (reported; observed − predicted): −0.024 [−0.039, −0.009] at g 2
  (R4) and +0.033 [+0.019, +0.048] at g 4 (R5).

## The sensitivity U (reported, numbers only; never computed on P55)

U is J4's terms refitted on the 1,458 FIT means whose erasure size is not censored. It drops 378: g 4 and g 2 × 1/4 at
side 32. Model sha256 0ed6eea6dc925d01….

Its value on every part, with U in the model's place:

| Part | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | S11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U | +0.0228 | +0.0240 | +0.0450 | +0.0431 | +0.0243 | +0.0372 | +0.0441 | -0.0518 | +0.0634 | +0.0520 | +0.0245 |

Derived from these: U predicts the late loss at −0.175 (observed −0.153), the recovery at ε 8 at +0.196 (of +0.221),
and at ε 4 at +0.096 (of +0.133).

## The ledger

- **Phase B** (CPU-seconds):
  - the additions before the freeze (the U fit 3, the reader's dry run 9, the freeze writer and the tests about 5):
    about 17;
  - the preflight 3,803;
  - Q1–Q10 580;
  - the development 60,007;
  - the frozen reader 14.
  - **In all, about 64,420 (17.89 CPU-hours).**
- **The development's budget** (Amendment 1, with the FIT rereads inside it): FIT 2.91, plus about 0.23 lost to the
  stall, plus TEST 16.67, makes **19.82 CPU-hours against the cap of 35**. The preflight's re-price was 20.05.
- **Phase A:** about 3.17 CPU-hours against the cap of 6.

## Disclosures

- **Phase A's interruption** (the session stall at about 17:58Z) and the reread digest the FIT shards carry are disclosed
  in the registration.
- **In phase B** nothing crashed, was resumed or was redone. Every run and commit was launched detached (setsid nohup),
  with its PID recorded and kill -0 waiters.
- **TABLES.md** is written by the frozen `sm006/tables.py`. Its rows for S2, S7 and R17–R20 carry unescaped `|`
  characters from the part names, so they render with extra columns. Their values are the same as in this file and in
  `predictions_scored.json`.
- **The narrowest bands** the reader prints on TEST are for information. The verdicts use the frozen thresholds from P55.
