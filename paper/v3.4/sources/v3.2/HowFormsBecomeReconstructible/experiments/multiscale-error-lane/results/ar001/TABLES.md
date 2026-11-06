# AR001 tables (development, blocks 910528-910543, design 051af4cc7450)

## Statements

| Id | Verdict | Part | Pooled | Threshold |
|---|---|---|---|---|
| A1 | HOLDS | A1 max over arms and cases of abs(u(new) + u(old) - 1), change@0 and change@1 | +0.000000 | le 1e-12 |
| A2 | HOLDS | A2 U_ctrl(h 1, f 0) - U(BEST) | +0.142044 | ge 0.04 |
| A3 | HOLDS | A3 U_ctrl(h 0.75, f 0.25) - U(BEST) | +0.067745 | ge 0 |
| A4 | HOLDS | A4 U_ctrl(h 0.5, f 0.5) - U(BEST) | -0.006554 | le 0.03 |
| A4 | HOLDS | A4 U_ctrl(h 1, f 0) - U_ctrl(h 1, f 1) | +0.087852 | ge 0.04 |
| A5 | HOLDS | A5 u(dial, correlated) - u(record, correlated) | +0.652161 | ge 0.3 |
| A5 | HOLDS | A5 u(dial, correlated) - u(body, correlated) | +0.418030 | ge 0.1 |
| A5 | HOLDS | A5 u(dial, correlated) - u(vote, correlated) | +0.394592 | ge 0.1 |
| A6 | HOLDS | A6 sham cost to the sheet, cue@0: r_all(rest) - r_all(dial) | +0.006059 | le 0.01 |
| A6 | HOLDS | A6 sham cost to the sheet, none@0: r_all(rest) - r_all(dial) | +0.000000 | le 0.002 |
| A7 | HOLDS | A7 cue@0 sheet: r_all(arbiter) - r_all(latch) | +0.159770 | ge 0.1 |
| A8 | HOLDS | A8 u(record, none) - u(body, none) | +0.046265 | ge 0.02 |
| A8 | HOLDS | A8 u(body, memory) - u(record, memory) | +0.302490 | ge 0.2 |
| A9 | HOLDS | A9 u(dial-m2, memory) - u(dial, memory) | -0.101501 | le 0 |
| A9 | HOLDS | A9 u(dial-m0.5, memory) - u(dial, memory) | +0.019836 | ge -0.02 |
| A10 | HOLDS | A10 u(dial-s6, memory) - u(rest, memory) | +0.022400 | le 0.05 |
| A10 | HOLDS | A10 u(dial-s4, memory) - u(dial, memory) | -0.361145 | le -0.15 |
| A10 | HOLDS | A10 sham(cue@0, dial-d8) - sham(cue@0, dial) | +0.037778 | ge 0.02 |
| A11 | HOLDS | A11 u(dial, change/new) misread - exact | -0.156433 | le 0 |
| A11 | HOLDS | A11 u(dial, none) misread - exact | -0.032471 | le 0 |

## The record inside the patch by scoring (pooled, t = 8,000), and the utility U

| Arm | none | body | memory | correlated | shared | cue | change/new | change/old | U |
|---|---|---|---|---|---|---|---|---|---|
| inactive | 0.8760 | 0.8760 | 0.1272 | 0.1272 | 0.6902 | 0.8760 | 0.1240 | 0.8760 | 0.5716 |
| record | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.7427 | 1.0000 | 0.0000 | 1.0000 | 0.5928 |
| body | 0.9537 | 0.9534 | 0.3025 | 0.2341 | 0.9134 | 0.9537 | 0.0463 | 0.9537 | 0.6639 |
| vote | 0.9908 | 0.9908 | 0.3378 | 0.2576 | 0.9466 | 0.9908 | 0.0092 | 0.9908 | 0.6893 |
| arbiter | 0.9712 | 0.9713 | 0.1147 | 0.0947 | 0.8596 | 0.9634 | 0.0632 | 0.9368 | 0.6218 |
| latch | 0.9712 | 0.9713 | 0.2758 | 0.2645 | 0.8571 | 0.8132 | 0.2328 | 0.7672 | 0.6441 |
| rest | 0.9712 | 0.9713 | 0.1152 | 0.0962 | 0.8596 | 0.9626 | 0.0649 | 0.9351 | 0.6220 |
| dial | 0.9712 | 0.9713 | 0.6526 | 0.6522 | 0.8596 | 0.8412 | 0.6463 | 0.3537 | 0.7435 |

Best fixed policy here: **vote** (U 0.6893); P41's (registered): **vote**.

## The controller over the declared reliability (U_ctrl(h, f) and its advantage)

| h | f | U_ctrl | minus U(best here) | minus U(P41's best) |
|---|---|---|---|---|
| 1 | 0 | 0.8314 | +0.1420 | +0.1420 |
| 0.9 | 0.1 | 0.8016 | +0.1123 | +0.1123 |
| 0.75 | 0.25 | 0.7571 | +0.0677 | +0.0677 |
| 0.5 | 0.5 | 0.6828 | -0.0066 | -0.0066 |
| 1 | 1 | 0.7435 | +0.0542 | +0.0542 |
| 0 | 0 | 0.6220 | -0.0673 | -0.0673 |
| 0.9 | 0.5 | 0.7665 | +0.0772 | +0.0772 |
| 0.5 | 0.1 | 0.7179 | +0.0286 | +0.0286 |

## A sham's cost to the sheet (r_all(rest) - r_all(arm), t = 8,000)

| Run | dial | dial-m0.5 | dial-m1 | dial-m2 | dial-s4 | dial-s6 | dial-d0 | dial-d8 |
|---|---|---|---|---|---|---|---|---|
| none@0 | 0.0000 |  |  |  |  |  |  |  |
| body@0 | 0.0000 |  |  |  |  |  |  |  |
| shared@0 | 0.0000 |  |  |  |  |  |  |  |
| cue@0 | 0.0061 | 0.0064 | 0.0067 | 0.0062 | 0.0064 | 0.0067 | 0.0014 | 0.0438 |
| change@0 | -0.0079 | -0.0079 | -0.0075 | -0.0071 | -0.0025 | -0.0004 | -0.0072 | -0.0079 |

## Side arms: the record inside the patch (pooled, t = 8,000)

| Scoring | rest | dial | dial-m0.5 | dial-m1 | dial-m2 | dial-s4 | dial-s6 | dial-d0 | dial-d8 |
|---|---|---|---|---|---|---|---|---|---|
| none | 0.9712 | 0.9712 |  |  |  |  |  |  |  |
| body | 0.9713 | 0.9713 |  |  |  |  |  |  |  |
| memory | 0.1152 | 0.6526 | 0.6724 | 0.6656 | 0.5511 | 0.2914 | 0.1376 | 0.5481 | 0.6606 |
| correlated | 0.0962 | 0.6522 | 0.6730 | 0.6700 | 0.5813 |  |  |  |  |
| shared | 0.8596 | 0.8596 |  |  |  |  |  |  |  |
| cue | 0.9626 | 0.8412 | 0.8301 | 0.8309 | 0.8381 | 0.9161 | 0.9605 | 0.8798 | 0.8377 |
| change/new | 0.0649 | 0.6463 | 0.6659 | 0.6692 | 0.6160 | 0.2551 | 0.0878 | 0.5396 | 0.6525 |
| change/old | 0.9351 | 0.3537 | 0.3341 | 0.3308 | 0.3840 | 0.7449 | 0.9122 | 0.4604 | 0.3475 |

## Misread cues (GC001, sigma 1): the cue readers inside the patch and over the sheet (t = 8,000)

| Scoring | arbiter σ0 / σ1 | latch σ0 / σ1 | rest σ0 / σ1 | dial σ0 / σ1 |
|---|---|---|---|---|
| none | 0.9712 / 0.9684 | 0.9712 / 0.9524 | 0.9712 / 0.9684 | 0.9712 / 0.9387 |
| memory | 0.1147 / 0.1062 | 0.2758 / 0.4417 | 0.1152 / 0.1141 | 0.6526 / 0.6671 |
| change/new | 0.0632 / 0.0486 | 0.2328 / 0.3253 | 0.0649 / 0.0527 | 0.6463 / 0.4899 |
| change/old | 0.9368 / 0.9514 | 0.7672 / 0.6747 | 0.9351 / 0.9473 | 0.3537 / 0.5101 |
| none: sheet | 0.9698 / 0.9680 | 0.9698 / 0.9350 | 0.9698 / 0.9680 | 0.9698 / 0.9659 |

## Per unit-body pair: U and the record inside the patch at memory and correlated (t = 8,000)

| Pair | U inactive | U record | U body | U vote | U arbiter | U latch | U rest | U dial |
|---|---|---|---|---|---|---|---|---|
| S4_t0/dw | 0.5706 | 0.5921 | 0.6788 | 0.7005 | 0.6262 | 0.6473 | 0.6261 | 0.7476 |
| S4_t0/li4 | 0.5706 | 0.5921 | 0.6627 | 0.6347 | 0.6312 | 0.6539 | 0.6313 | 0.7545 |
| S4_t1/dw | 0.5706 | 0.5921 | 0.6609 | 0.7213 | 0.6222 | 0.6424 | 0.6221 | 0.7421 |
| S4_t1/li4 | 0.5706 | 0.5921 | 0.6715 | 0.6850 | 0.6340 | 0.6512 | 0.6340 | 0.7462 |
| F0_t0/dw | 0.5725 | 0.5936 | 0.7308 | 0.7209 | 0.6461 | 0.6686 | 0.6464 | 0.7574 |
| F0_t0/li4 | 0.5725 | 0.5936 | 0.6329 | 0.6693 | 0.5858 | 0.6111 | 0.5861 | 0.7229 |
| F0_t1/dw | 0.5725 | 0.5936 | 0.7260 | 0.7220 | 0.6395 | 0.6618 | 0.6399 | 0.7529 |
| F0_t1/li4 | 0.5725 | 0.5936 | 0.5474 | 0.6607 | 0.5898 | 0.6165 | 0.5901 | 0.7243 |
