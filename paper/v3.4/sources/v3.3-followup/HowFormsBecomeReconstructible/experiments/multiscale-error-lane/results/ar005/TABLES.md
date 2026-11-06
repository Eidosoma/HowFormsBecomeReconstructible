# AR005 tables

Intervals: 95% t over the blocks with the lane's SD, the larger of the block SD and the case-level SD over sqrt 8. Size means over 4 x 4 and 8 x 8.

## Registered statements

| Id | Verdict | Part | Value | Threshold |
|---|---|---|---|---|
| K1 | HOLDS | K1 sheet cost under scattered cue damage: r_all(vote) - r_all(vguard), cue@0 | +0.002479 | le 0.01 |
| K2 | HOLDS | K2 (a) sheet cost with no event: r_all(vote) - r_all(vguard), none@0 | -0.000008 | le 0.002 |
| K2 | HOLDS | K2 (b) sheet cost under misreads with no event: r_all(vote, none@0) - r_all(vguard, none@1) | +0.001024 | le 0.01 |
| K3 | HOLDS | K3 (a) R1 = (1/2) sum over sizes 4, 8 of u(vguard, memory@1) - u(vms, memory@1) | +0.098778 | ge 0.01 |
| K3 | HOLDS | K3 (b) the share kept: R1(vguard) - k R1(vpool) | +0.070091 | ge 0.0 |
| K4 | HOLDS | K4 R0 = (1/2) sum over sizes 4, 8 of u(vguard, memory@0) - u(vms, memory@0) | -0.005188 | ge -0.01 |
| K5 | HOLDS | K5 W1 = (1/2) sum over sizes 4, 8 of u(vguard, memory@1) - u(vote, memory@0) | +0.217888 | ge 0.12 |
| K6 | HOLDS | K6 (a) u(vpool) - u(vguard) in correlated damage, 4 x 4, sigma 0 | +0.331909 | le 0.4 |
| K6 | HOLDS | K6 (b) u(vpool) - u(vguard) in correlated damage, 4 x 4, sigma 1 | +0.212585 | le 0.37 |
| K6 | HOLDS | K6 (c) u(vguard) - u(vote) in correlated damage, 4 x 4, sigma 0 | +0.129578 | ge 0.08 |
| K6 | HOLDS | K6 (c) u(vguard, correlated@1) - u(vote, correlated@0), 4 x 4 | +0.050354 | ge 0.02 |
| K7 | HOLDS | K7 u(vguard) - u(vote) in the 4 x 4 patch, none@0 | +0.000000 | ge -0.005 |
| K7 | HOLDS | K7 u(vguard, none@1) - u(vote, none@0) in the 4 x 4 patch | -0.000183 | ge -0.005 |

## Contrasts

| Contrast | Value [95%] |
|---|---|
| K3 R1 vguard (misread recovery over vms, sizes 4 and 8) | +0.0988 [+0.0756, +0.1220] |
| R1 vpool (sizes 4 and 8) | +0.1147 [+0.0911, +0.1384] |
| R1 vguard less vpool | -0.0160 [-0.0245, -0.0075] |
| vms misread loss (sigma 1 - sigma 0) | -0.5069 [-0.5426, -0.4712] |
| K4 R0 vguard (sigma-0 hits against vms) | -0.0052 [-0.0098, -0.0006] |
| K5 W1 vguard (worth over the vote under misreads) | +0.2179 [+0.1827, +0.2531] |
| W1 vpool | +0.2339 [+0.1991, +0.2686] |
| W1 vms | +0.1191 [+0.0916, +0.1466] |
| sham cue@0 vms | +0.0056 [+0.0042, +0.0069] |
| sham cue@0 vpool | +0.0193 [+0.0165, +0.0221] |
| K1 sham cue@0 vguard | +0.0025 [+0.0019, +0.0031] |
| sham none@0 vms | -0.0000 [-0.0001, +0.0001] |
| sham none@0 vpool | -0.0000 [-0.0001, +0.0001] |
| K2a sham none@0 vguard | -0.0000 [-0.0001, +0.0000] |
| sham none@1 vms | +0.0040 [+0.0031, +0.0048] |
| sham none@1 vpool | +0.0089 [+0.0076, +0.0102] |
| K2b sham none@1 vguard | +0.0010 [+0.0006, +0.0014] |
| K7a give none@0 vguard | +0.0000 [+0.0000, +0.0000] |
| K7b give none@1 vguard | -0.0002 [-0.0013, +0.0009] |
| give cue@0 (reported: inside the patch) vguard | -0.0016 [-0.0036, +0.0003] |
| give body@0 (reported) vguard | +0.0000 [+0.0000, +0.0000] |
| K6a corr@0 cost: u(vpool) - u(vguard) | +0.3319 [+0.2825, +0.3813] |
| K6c corr@0: u(vguard) - u(vote) | +0.1296 [+0.1030, +0.1562] |
| corr@0: u(vguard) - u(vms) | -0.3307 [-0.3803, -0.2811] |
| K6b corr@1 cost: u(vpool) - u(vguard) | +0.2126 [+0.1763, +0.2489] |
| K6c corr@1: u(vguard) - u(vote) | +0.0504 [+0.0316, +0.0691] |
| corr@1: u(vguard) - u(vms) | -0.1087 [-0.1399, -0.0775] |
| u(vguard) - u(vms), memory@0 L2 | -0.0005 [-0.0022, +0.0012] |
| u(vguard) - u(vpool), memory@0 L2 | -0.0005 [-0.0022, +0.0012] |
| u(vguard) - u(vms), memory@1 L2 | +0.0085 [-0.0051, +0.0222] |
| u(vguard) - u(vpool), memory@1 L2 | -0.0054 [-0.0173, +0.0065] |
| u(vguard) - u(vms), memory@0 L4 | -0.0100 [-0.0193, -0.0007] |
| u(vguard) - u(vpool), memory@0 L4 | -0.0109 [-0.0206, -0.0012] |
| u(vguard) - u(vms), memory@1 L4 | +0.0718 [+0.0416, +0.1020] |
| u(vguard) - u(vpool), memory@1 L4 | -0.0186 [-0.0315, -0.0056] |
| u(vguard) - u(vms), memory@0 L8 | -0.0004 [-0.0011, +0.0004] |
| u(vguard) - u(vpool), memory@0 L8 | +0.0000 [+0.0000, +0.0000] |
| u(vguard) - u(vms), memory@1 L8 | +0.1258 [+0.0819, +0.1697] |
| u(vguard) - u(vpool), memory@1 L8 | -0.0134 [-0.0228, -0.0039] |

The recovery fraction (R1 over vms's own misread loss, sizes 4 and 8): vpool 0.2264, vguard 0.1949

## u by arm and run

| Arm / run | u |
|---|---|
| vote/memory@0-L2 | 0.6252 |
| vms/memory@0-L2 | 0.6375 |
| vpool/memory@0-L2 | 0.6375 |
| vguard/memory@0-L2 | 0.6370 |
| vote/memory@0 | 0.3375 |
| vms/memory@0 | 0.7375 |
| vpool/memory@0 | 0.7383 |
| vguard/memory@0 | 0.7275 |
| vote/memory@0-L8 | 0.0947 |
| vms/memory@0-L8 | 0.9467 |
| vpool/memory@0-L8 | 0.9463 |
| vguard/memory@0-L8 | 0.9463 |
| vms/memory@1-L2 | 0.6343 |
| vpool/memory@1-L2 | 0.6482 |
| vguard/memory@1-L2 | 0.6428 |
| vms/memory@1 | 0.4503 |
| vpool/memory@1 | 0.5406 |
| vguard/memory@1 | 0.5220 |
| vms/memory@1-L8 | 0.2201 |
| vpool/memory@1-L8 | 0.3593 |
| vguard/memory@1-L8 | 0.3459 |
| vote/none@0 | 0.9899 |
| vms/none@0 | 0.9899 |
| vpool/none@0 | 0.9899 |
| vguard/none@0 | 0.9899 |
| vms/none@1 | 0.9887 |
| vpool/none@1 | 0.9797 |
| vguard/none@1 | 0.9897 |
| vote/cue@0 | 0.9899 |
| vms/cue@0 | 0.9888 |
| vpool/cue@0 | 0.9635 |
| vguard/cue@0 | 0.9883 |
| vote/correlated@0 | 0.2505 |
| vms/correlated@0 | 0.7108 |
| vpool/correlated@0 | 0.7120 |
| vguard/correlated@0 | 0.3801 |
| vms/correlated@1 | 0.4095 |
| vpool/correlated@1 | 0.5134 |
| vguard/correlated@1 | 0.3008 |
| vote/body@0 | 0.9900 |
| vms/body@0 | 0.9900 |
| vpool/body@0 | 0.9900 |
| vguard/body@0 | 0.9900 |

## Detectors

| Run / arm | fired | on the patch | onset median | footprint cells | patch covered |
|---|---|---|---|---|---|
| memory@0-L2/vms | 0.090 | 0.049 | 2764.0 | 50.2 | 0.527 |
| memory@0-L2/vpool | 0.090 | 0.049 | 2764.0 | 50.2 | 0.527 |
| memory@0-L2/vguard | 0.071 | 0.045 | 1.0 | 48.6 | 0.623 |
| memory@0/vms | 0.784 | 0.782 | 1.0 | 69.6 | 0.996 |
| memory@0/vpool | 0.785 | 0.783 | 1.0 | 72.3 | 0.997 |
| memory@0/vguard | 0.762 | 0.762 | 1.0 | 72.3 | 1.0 |
| memory@0-L8/vms | 1.000 | 1.000 | 1.0 | 145.4 | 1.0 |
| memory@0-L8/vpool | 1.000 | 1.000 | 1.0 | 149.5 | 1.0 |
| memory@0-L8/vguard | 1.000 | 1.000 | 1.0 | 149.4 | 1.0 |
| memory@1-L2/vms | 0.496 | 0.056 | 1.0 | 64.7 | 0.104 |
| memory@1-L2/vpool | 0.697 | 0.133 | 1.0 | 84.9 | 0.168 |
| memory@1-L2/vguard | 0.199 | 0.068 | 2257.0 | 56.7 | 0.338 |
| memory@1/vms | 0.646 | 0.296 | 1.0 | 70.8 | 0.436 |
| memory@1/vpool | 0.877 | 0.481 | 1.0 | 91.5 | 0.525 |
| memory@1/vguard | 0.529 | 0.431 | 1.0 | 67.5 | 0.805 |
| memory@1-L8/vms | 0.584 | 0.211 | 1.0 | 81.1 | 0.257 |
| memory@1-L8/vpool | 0.878 | 0.470 | 1.0 | 105.1 | 0.364 |
| memory@1-L8/vguard | 0.499 | 0.412 | 1.0 | 98.2 | 0.596 |
| none@0/vms | 0.045 | 0.001 | 4608.0 | 55.9 | 0.005 |
| none@0/vpool | 0.045 | 0.001 | 4608.0 | 56.1 | 0.005 |
| none@0/vguard | 0.028 | 0.000 | 4608.0 | 55.2 | 0.0 |
| none@1/vms | 0.474 | 0.037 | 1.0 | 66.0 | 0.031 |
| none@1/vpool | 0.688 | 0.095 | 1.0 | 82.3 | 0.077 |
| none@1/vguard | 0.141 | 0.014 | 3449.5 | 59.5 | 0.043 |
| cue@0/vms | 0.508 | 0.047 | 1.0 | 69.8 | 0.032 |
| cue@0/vpool | 0.935 | 0.148 | 1.0 | 106.9 | 0.099 |
| cue@0/vguard | 0.235 | 0.021 | 1447.0 | 57.6 | 0.048 |
| correlated@0/vms | 0.785 | 0.783 | 1.0 | 69.5 | 0.996 |
| correlated@0/vpool | 0.786 | 0.784 | 1.0 | 72.2 | 0.997 |
| correlated@0/vguard | 0.287 | 0.268 | 1065.0 | 66.6 | 0.929 |
| correlated@1/vms | 0.644 | 0.293 | 1.0 | 70.8 | 0.432 |
| correlated@1/vpool | 0.880 | 0.484 | 1.0 | 91.4 | 0.526 |
| correlated@1/vguard | 0.242 | 0.124 | 2650.0 | 61.8 | 0.494 |
| body@0/vms | 0.045 | 0.001 | 4608.0 | 55.9 | 0.005 |
| body@0/vpool | 0.045 | 0.001 | 4608.0 | 56.1 | 0.005 |
| body@0/vguard | 0.028 | 0.000 | 4608.0 | 55.2 | 0.0 |
