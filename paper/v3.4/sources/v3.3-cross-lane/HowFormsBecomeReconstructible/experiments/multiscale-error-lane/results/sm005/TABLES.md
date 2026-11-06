# SM005 tables: development

Per refined condition read at full resolution: F = E_cg - E_base, V_X = E_X - E_base (X: C the coupling length, E the erasure size, B the record's bond grain); A = V_C + V_E + V_B - F.

## The parts

| Id | Part | Value [95%] | SD | Halves | Narrowest | Threshold | |
|---|---|---|---|---|---|---|---|
| L1 | late (m 2): V_C = E_C - E_base, the coupling length's recovery | +0.0466 [+0.0413, +0.0519] | 0.0147 | +0.0471, +0.0461 | [0.02, 0.08] | [0.02, 0.1] | HOLDS |
| L2 | late: V_E = E_E - E_base, the erasure size's recovery | +0.1911 [+0.1795, +0.2028] | 0.0323 | +0.1825, +0.1998 | [0.13, 0.25] | [0.14, 0.32] | HOLDS |
| L3 | late: V_B = E_B - E_base, the bond grain's recovery | +0.0320 [+0.0126, +0.0513] | 0.0537 | +0.0279, +0.0360 | [-0.06, 0.13] | [-0.12, 0.24] | HOLDS |
| L4 | late: F = E_cg - E_base, the fully scaled reader's recovery | +0.1861 [+0.1715, +0.2006] | 0.0404 | +0.1766, +0.1955 | [0.11, 0.26] | [0.13, 0.33] | HOLDS |
| L5 | late: A = V_C + V_E + V_B - F, the additivity | +0.0836 [+0.0658, +0.1013] | 0.0492 | +0.0808, +0.0864 | [0.0, 0.17] | [-0.04, 0.28] | HOLDS |
| P1 | prompt (m 0): V_C | +0.0263 [+0.0224, +0.0303] | 0.0110 | +0.0255, +0.0271 | [0.0, 0.05] | [0.0, 0.07] | HOLDS |
| P2 | prompt: V_E | +0.1062 [+0.0963, +0.1161] | 0.0274 | +0.0975, +0.1148 | [0.06, 0.16] | [0.05, 0.22] | HOLDS |
| P3 | prompt: V_B | +0.0141 [+0.0005, +0.0278] | 0.0379 | +0.0122, +0.0161 | [-0.05, 0.08] | [-0.1, 0.17] | HOLDS |
| P4 | prompt: F | +0.1052 [+0.0948, +0.1157] | 0.0290 | +0.0969, +0.1136 | [0.05, 0.16] | [0.05, 0.22] | HOLDS |
| K1 | late: B - E = E_B - E_E, the bond grain's recovery beyond the erasure it brings | -0.1592 [-0.1794, -0.1390] | 0.0561 | -0.1545, -0.1638 | [-0.26, -0.06] |  |  |
| K1p | prompt: B - E, the contrast | -0.0920 [-0.1053, -0.0788] | 0.0367 | -0.0854, -0.0987 | [-0.16, -0.03] | [-0.2, -0.01] | HOLDS |
| K2 | late: F - (V_C + V_B), the additivity with the overlap removed (B already carries the erasure) | +0.1075 [+0.0936, +0.1215] | 0.0387 | +0.1017, +0.1134 | [0.04, 0.18] | [0.0, 0.21] | HOLDS |

## The shares of the late recovery, V_X / F (F +0.1861 [+0.1715, +0.2006]; read as ratios: True)

| Variant | Share [95%, whole-block bootstrap] |
|---|---|
| C | +0.250 [+0.228, +0.273] |
| E | +1.027 [+0.976, +1.088] |
| B | +0.172 [+0.076, +0.255] |

## The shares of the prompt recovery, V_X / F (F +0.1052 [+0.0948, +0.1157]; read as ratios: True)

| Variant | Share [95%, whole-block bootstrap] |
|---|---|
| C | +0.250 [+0.226, +0.274] |
| E | +1.009 [+0.954, +1.068] |
| B | +0.134 [+0.011, +0.240] |

The prompt additivity A: +0.0414 [+0.0270, +0.0559].

Late less prompt, V_X: C +0.0202 [+0.0177, +0.0228]; E +0.0849 [+0.0791, +0.0907]; B +0.0178 [+0.0109, +0.0247].

## Each reader's levels (mean E, generic recovery, phase E - generic)

| Reader | late E | late gen | late phase | prompt E | prompt gen | prompt phase |
|---|---|---|---|---|---|---|
| base | 0.5576 | 0.8814 | -0.3239 | 0.8067 | 0.9420 | -0.1354 |
| cg | 0.7436 | 0.9291 | -0.1854 | 0.9119 | 0.9776 | -0.0657 |
| C | 0.6041 | 0.8667 | -0.2625 | 0.8330 | 0.9363 | -0.1033 |
| E | 0.7487 | 0.9415 | -0.1928 | 0.9129 | 0.9824 | -0.0695 |
| B | 0.5895 | 0.8635 | -0.2740 | 0.8208 | 0.9355 | -0.1147 |

## The late parts by unit

| unit | L1 V_C | L2 V_E | L3 V_B | L4 F | L5 A |
|---|---|---|---|---|---|
| W8_x64_r2 | +0.0312 | +0.1465 | +0.0489 | +0.1594 | +0.0672 |
| W16_x64_r2 | +0.0488 | +0.2019 | +0.0266 | +0.1911 | +0.0862 |
| W32_x64_r2 | +0.0597 | +0.2250 | +0.0203 | +0.2077 | +0.0973 |

## The late parts by patch size

| patch size | L1 V_C | L2 V_E | L3 V_B | L4 F | L5 A |
|---|---|---|---|---|---|
| 4 | +0.0506 | +0.1864 | +0.0295 | +0.1749 | +0.0916 |
| 8 | +0.0642 | +0.2809 | +0.0372 | +0.2702 | +0.1122 |
| 16 | +0.0249 | +0.1061 | +0.0292 | +0.1131 | +0.0470 |
