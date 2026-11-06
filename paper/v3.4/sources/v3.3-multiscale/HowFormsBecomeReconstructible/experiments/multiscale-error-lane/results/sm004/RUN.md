# SM004 phase B: the run record (fork H1, 2 November 2026)

The frozen reader's outputs on TEST are `predictions_scored.json` (the registered parts N1–N8, the reported candidates
N9 and N10, the reported parts R1–R22, the contrasts predicted from FIT alone, and the two reported sensitivities H2 and
H5 on N1–N10) and `TABLES.md` (the selection on FIT, every predictor's condition-level error by set, grain and signal,
and the parts). Units: the reader's agreement E with the acquired template inside the patch; 95% t intervals over the 16
TEST blocks. "The model" is SM004's frozen H1 (F4's terms + G = log2 g); "F4" is SM003's frozen model.

## Commits and stages

- **The plan:** 3cc6c78454 (23:34:03Z on 1 November), before any fit, probe value or run.
- **The model,** selected on FIT and frozen before P52 was read: 09dd6bb059 (23:45:10Z).
- **Phase A for review** (P52 read, the two sensitivities frozen, the debug run's Q1–Q10, the draft): 88b6d65759
  (00:09:04Z on 2 November). The lead's P52c: 75fd9b2ae2 (00:14:55Z).
- **The freeze:** 97f9983481 (00:17:45Z, pushed 00:17:48Z). Design frozen 00:17:05Z, digest 33a8a24747b0 (168 source
  hashes, the digest the phase-A model carries); predictions frozen 00:17:07Z.
- **The preflight:** 900470–900471, 00:18:18–00:28:56Z, 12 tasks on 12 workers, 7,518 CPU-seconds, peak worker memory
  1,364 MB, under the frozen digest.
- **Q1–Q10:** PASS, all ten (00:29:23–00:38:42Z, 1,705 CPU-seconds). Receipt commit 8d391a10b0 (00:39:42Z, pushed
  00:39:50Z), which names the freeze commit.
- **TEST:** 910617–910627, 910859–910861 and 910890–910891 (16 blocks x 6 units = 96 tasks), 00:40:11–02:01:18Z on 12
  workers (cores 37–71, nice 10; the 1-minute load 23.8 and 124.5 GiB available at the launch): 57,582 CPU-seconds
  (16.00 CPU-hours, 600 a task), 4,868 s of wall, peak worker memory 1,655 MB, 1.04 GB written. Each block was drawn once;
  nothing crashed, was resumed or was redrawn.
- **The frozen reader:** about 13 CPU-seconds.
- **In all:** the development (TEST and the g-4 FIT rereads) 16.05 CPU-hours, against the cap of 35 (Q9's forecast
  16.76). Phase A 1.65; the preflight and its Q1–Q10 2.56.

## Registered statements (16 TEST blocks): 8 of 8 HOLD

| Id | Part | Value [95%] | Threshold | |
|---|---|---|---|---|
| N1 | the g-2 offset: refinement at g 2, E − the model | −0.0326 [−0.0566, −0.0086] | within [−0.10, +0.05] | holds |
| N2 | the g-4 shortfall: refinement at g 4, E − the model | −0.0159 [−0.0361, +0.0043] | within [−0.05, +0.08] | holds |
| N3 | the late loss: refinement read at g 1, late: (E − E twin) − (the model − the model at the twin) | −0.0603 [−0.0857, −0.0349] | within [−0.16, +0.01] | holds |
| N4 | the prompt loss: the same at m 0 | +0.0071 [−0.0134, +0.0277] | within [−0.07, +0.06] | holds |
| N5 | the larger sheet: transfer at g 1, 2 and 4, E − the model | −0.0065 [−0.0264, +0.0135] | within [−0.07, +0.06] | holds |
| N6 | the matched-reader gain at g 2: (E − E twin at g/2) − (the model − the model at the twin at g/2) | −0.0212 [−0.0471, +0.0047] | within [−0.10, +0.08] | holds |
| N7 | the same at g 4 | −0.0063 [−0.0278, +0.0152] | within [−0.05, +0.09] | holds |
| N8 | closer than F4 at g 4: \|E − F4\| − \|E − the model\| | +0.0455 [+0.0351, +0.0558] | at least +0.02 | holds |

- **The margins on TEST** (in SD; for information, since the rule applied at P52): N2's lower side 0.90, N7's lower 1.08,
  N8 1.31, N4's upper 1.37, N3's upper 1.48, N1's lower 1.50; every other side 1.62 or more.
- **The reported candidates:** N9, closer than F4 at g 2, **+0.0165 [+0.0096, +0.0235]**; N10, the late loss kept against
  F4, **−0.0150 [−0.0201, −0.0099]**.

## The answer to the question

**Does naming the grain remove the g-2 offset and the g-4 shortfall without giving up M2's prediction of the late loss?**
It removes them, and it gives up part of M2's prediction.
- **The offsets go.**
  - At g 2, E less the model is −0.033 [−0.057, −0.009], against F4's +0.041 [+0.018, +0.064] (R7).
  - At g 4 it is −0.016 [−0.036, +0.004], against F4's +0.072 [+0.052, +0.093] (R8).
  - The model is closer than F4 at g 4 by 0.046 (N8) and at g 2 by 0.017 (N9).
  - At g 2 the interval lies below 0: the grain term slightly overcorrects there.
- **The grain's own gain is predicted** from FIT alone. At equal ratios the model predicts the matched reader's gain at
  +0.095 (g 2) and +0.061 (g 4), against +0.074 and +0.055 observed (N6 −0.021, N7 −0.006). F4 predicts 0.
- **The larger sheet and the prompt loss are predicted** (N5 −0.007; N4 +0.007; transfer at g 4 +0.006 against F4's +0.054).
- **But part of M2's late-loss prediction is given up.** From FIT alone the model predicts a late loss at g 1 of −0.087,
  where F4 predicted −0.143 and TEST observed −0.147 (R16).
  - N3 is −0.060 [−0.086, −0.035]: inside its band, which also covers 0, so its holding does not decide the question.
  - N10 says the model's late-loss error is larger than F4's, by 0.015 [0.010, 0.020].
  - By the registration's reading (N10 near −0.02, N3 near −0.08), naming the grain cost part of M2's prediction, a
    little less than P52 showed.
- **Where the new error sits** (`TABLES.md`, the model's bias by signal):
  - under the late signal at the coarse grains it now reads too high: E less the model −0.086 at g 2 and −0.056 at g 4;
  - the prompt signal is close there: −0.006 and +0.004.
  - F4's biases were +0.014 and +0.055 (late), and +0.054 and +0.081 (prompt).
- **The comparators at g 4:** the parametric is still closer than the model, by 0.007 [0.004, 0.010] (R11), and the 4-NN
  by 0.007 [0.002, 0.012] (R13). At g 2 the model is closer than the 4-NN (R12 +0.006).

## The reported sensitivities (fixed by FIT alone; computed only here)

N1–N10 under each, as numbers, no thresholds:

| Id | H1 (registered) | H2 = H1 + G·c (lobo 0.065940) | H5, the lobo best (0.065297) |
|---|---|---|---|
| N1 | −0.033 [−0.057, −0.009] | −0.048 [−0.072, −0.025] | −0.038 [−0.067, −0.009] |
| N2 | −0.016 [−0.036, +0.004] | −0.030 [−0.049, −0.010] | −0.035 [−0.056, −0.014] |
| N3 | −0.060 [−0.086, −0.035] | −0.059 [−0.085, −0.033] | −0.051 [−0.089, −0.013] |
| N4 | +0.007 [−0.013, +0.028] | −0.027 [−0.048, −0.005] | −0.012 [−0.041, +0.018] |
| N5 | −0.006 [−0.026, +0.014] | −0.007 [−0.027, +0.013] | −0.007 [−0.027, +0.013] |
| N6 | −0.021 [−0.047, +0.005] | −0.043 [−0.068, −0.019] | −0.033 [−0.065, −0.000] |
| N7 | −0.006 [−0.028, +0.015] | −0.016 [−0.036, +0.005] | −0.025 [−0.049, −0.000] |
| N8 | +0.045 [+0.035, +0.056] | +0.053 [+0.042, +0.063] | +0.052 [+0.041, +0.064] |
| N9 | +0.017 [+0.010, +0.023] | +0.022 [+0.013, +0.030] | +0.019 [+0.012, +0.026] |
| N10 | −0.015 [−0.020, −0.010] | −0.015 [−0.020, −0.010] | −0.025 [−0.040, −0.011] |

- Neither sensitivity recovers the late loss (N3 −0.059 and −0.051, against H1's −0.060).
- Both move further from F4 at the coarse grains (N8, N9 larger), and both overcorrect more there (N1, N2, N6 further
  below 0). H1 is as close or closer on N1, N2, N4, N6 and N7.

## Reported parts (TEST)

| Id | Part | Value [95%] |
|---|---|---|
| R1–R3 | refinement at g 1, E − the model: all, late, prompt | −0.027 [−0.061, +0.008]; −0.067 [−0.107, −0.027]; −0.007 [−0.039, +0.026] |
| R4–R6 | transfer, E − the model: g 1, g 2, g 4 | −0.011 [−0.040, +0.017]; −0.010 [−0.035, +0.016]; +0.006 [−0.008, +0.019] |
| R7, R8 | refinement, E − F4: g 2 (SM003's R1), g 4 (SM003's M7) | +0.041 [+0.018, +0.064]; +0.072 [+0.052, +0.093] |
| R9–R11 | \|E − the parametric\| − \|E − the model\|: g 1, 2, 4 | −0.003 [−0.009, +0.003]; −0.003 [−0.005, +0.000]; −0.007 [−0.010, −0.004] |
| R12, R13 | \|E − the 4-NN\| − \|E − the model\|: g 2, 4 | +0.006 [+0.002, +0.010]; −0.007 [−0.012, −0.002] |
| R14 | \|E − SM001's model\| − \|E − the model\|, refinement g 1 | +0.010 [+0.001, +0.020] |
| R15 | \|E − the parametric with (log2 g)²\| − \|E − the model\|, g 4 | −0.007 [−0.010, −0.004] |
| R16 | the observed late loss at g 1, E − E twin | −0.147 [−0.164, −0.131] |
| R17, R18 | E − E twin at g/2: g 2 (SM003's M4), g 4 (M5) | +0.074 [+0.056, +0.091]; +0.055 [+0.036, +0.074] |
| R19–R22 | the same by signal: g 2 late, prompt; g 4 late, prompt | +0.048 [+0.026, +0.070]; +0.086 [+0.070, +0.103]; +0.036 [+0.014, +0.058]; +0.064 [+0.046, +0.083] |

The contrasts predicted from FIT alone (the model; F4): late loss at g 1 −0.0871 (−0.1427); prompt loss −0.0344
(−0.0681); matched-reader gains +0.0947 at g 2 and +0.0613 at g 4 (0 and 0).

## Slips (disclosed)

- **The freeze commit** ran as a shell background job inside one tool call, not as a tracked background command. It
  finished in 5 s, and nothing was harmed.
- **The preflight's values were seen.** Testing the run-record printer after the receipt, fork H1 ran the frozen reader on
  the preflight (two engineering blocks) and read its N1–N10 values. They play no part in anything frozen. H2 and H5 were
  not computed there.
- **Phase A's slips** are in the registration: the identity scan's first run, the side arm's price corrected, the debug
  run launched beside the P45 bridge, and Q10's fix on the one-block debug run.

## Files

- **In git** (each 256 KiB or less): this record; `predictions_scored.json`; `TABLES.md`.
- **On scratch** (`/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm004/`): the TEST, preflight and debug roots
  (shards, raw records, done files, manifests), the g-4 FIT rereads, the P45 bridge, `progress.md`, the launchers
  (`tools/`).
