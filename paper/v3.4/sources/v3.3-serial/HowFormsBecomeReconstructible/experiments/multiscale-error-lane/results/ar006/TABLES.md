# AR006 tables

Intervals: 95% t over the blocks with the lane's SD, the larger of the block SD and the case-level SD over sqrt 8. Size means over 4 x 4 and 8 x 8.

## Registered statements

| Id | Verdict | Part | Value | Threshold |
|---|---|---|---|---|
| K2 | HOLDS | K2 (a) sheet cost with no event: r_all(vote) - r_all(vtol), none@0 | -0.000026 | le 0.002 |
| K2 | HOLDS | K2 (b) sheet cost under misreads with no event: r_all(vote, none@0) - r_all(vtol, none@1) | +0.004172 | le 0.01 |
| K3 | HOLDS | K3 (a) R1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vms, memory@1) | +0.092422 | ge 0.04 |
| K3 | HOLDS | K3 (b) the share kept: R1(vtol) - k R1(vpool) | +0.036629 | ge 0.0 |
| K4 | HOLDS | K4 R0 = (1/2) sum over sizes 4, 8 of u(vtol, memory@0) - u(vms, memory@0) | +0.000298 | ge -0.005 |
| K5 | HOLDS | K5 (a) u(vtol) - u(vms) in correlated damage, 4 x 4, sigma 0 | +0.000366 | ge -0.005 |
| K5 | HOLDS | K5 (b) u(vtol) - u(vguard) in correlated damage, 4 x 4, sigma 0 | +0.326233 | ge 0.25 |
| K5 | HOLDS | K5 (c) u(vtol) - u(vms) in correlated damage, 4 x 4, sigma 1 | +0.013916 | ge -0.03 |
| K5 | HOLDS | K5 (d) u(vtol) - u(vguard) in correlated damage, 4 x 4, sigma 1 | +0.137390 | ge 0.0 |
| K6 | HOLDS | K6 W1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vote, memory@0) | +0.240372 | ge 0.12 |
| K7 | HOLDS | K7 u(vtol) - u(vote) in the 4 x 4 patch, none@0 | +0.000000 | ge -0.005 |
| K7 | HOLDS | K7 u(vtol, none@1) - u(vote, none@0) in the 4 x 4 patch | -0.001770 | ge -0.005 |

## Contrasts

| Contrast | Value [95%] |
|---|---|
| K3 R1 vtol (misread recovery over vms, sizes 4 and 8) | +0.0924 [+0.0707, +0.1141] |
| R1 vpool (sizes 4 and 8) | +0.1116 [+0.0897, +0.1334] |
| R1 vtol less vpool | -0.0192 [-0.0272, -0.0111] |
| R1 vguard (sizes 4 and 8) | +0.0899 [+0.0681, +0.1118] |
| R1 vtol less vguard | +0.0025 [-0.0018, +0.0067] |
| K4 R0 vtol (sigma-0 hits against vms) | +0.0003 [-0.0001, +0.0007] |
| vms misread loss (sigma 1 - sigma 0) | -0.4806 [-0.5180, -0.4433] |
| K6 W1 vtol (worth over the vote under misreads) | +0.2404 [+0.2074, +0.2734] |
| W1 vms | +0.1479 [+0.1200, +0.1759] |
| W1 vpool | +0.2595 [+0.2257, +0.2934] |
| W1 vguard | +0.2379 [+0.2052, +0.2705] |
| sham cue@0 vms | +0.0067 [+0.0052, +0.0083] |
| sham cue@0 vpool | +0.0195 [+0.0167, +0.0222] |
| K1 (not registered: beside the confirmed 0.01) sham cue@0 vtol | +0.0077 [+0.0062, +0.0093] |
| sham cue@0: vtol less vms (the extra false-alarm cost) | +0.0010 [+0.0005, +0.0015] |
| sham none@0 vms | -0.0000 [-0.0001, +0.0000] |
| K2a sham none@0 vtol | -0.0000 [-0.0001, +0.0000] |
| sham none@0: vtol less vms (the extra false-alarm cost) | +0.0000 [-0.0000, +0.0000] |
| sham none@1 vms | +0.0038 [+0.0029, +0.0048] |
| K2b sham none@1 vtol | +0.0042 [+0.0033, +0.0050] |
| sham none@1: vtol less vms (the extra false-alarm cost) | +0.0003 [+0.0001, +0.0006] |
| K7a give none@0 vtol | +0.0000 [+0.0000, +0.0000] |
| K7b give none@1 vtol | -0.0018 [-0.0040, +0.0004] |
| give cue@0 (reported: inside the patch) vtol | -0.0069 [-0.0172, +0.0034] |
| K5a corr@0: u(vtol) - u(vms) | +0.0004 [-0.0004, +0.0011] |
| K5b corr@0: u(vtol) - u(vguard) | +0.3262 [+0.2684, +0.3841] |
| corr@0: u(vtol) - u(vpool) | -0.0007 [-0.0020, +0.0007] |
| K5c corr@1: u(vtol) - u(vms) | +0.0139 [+0.0065, +0.0214] |
| K5d corr@1: u(vtol) - u(vguard) | +0.1374 [+0.1049, +0.1699] |
| corr@1: u(vtol) - u(vpool) | -0.0908 [-0.1224, -0.0592] |
| u(vtol) - u(vms), memory@0 L4 | +0.0004 [-0.0004, +0.0012] |
| u(vtol) - u(vms), memory@1 L4 | +0.0927 [+0.0625, +0.1229] |
| u(vtol) - u(vpool), memory@1 L4 | -0.0067 [-0.0150, +0.0017] |
| u(vtol) - u(vguard), memory@1 L4 | +0.0049 [-0.0022, +0.0120] |
| u(vtol) - u(vms), memory@0 L8 | +0.0002 [-0.0002, +0.0005] |
| u(vtol) - u(vms), memory@1 L8 | +0.0921 [+0.0624, +0.1219] |
| u(vtol) - u(vpool), memory@1 L8 | -0.0317 [-0.0456, -0.0178] |
| u(vtol) - u(vguard), memory@1 L8 | +0.0001 [-0.0043, +0.0045] |

The recovery fraction (R1 over vms's own misread loss, sizes 4 and 8): vpool 0.2322, vguard 0.1871, vtol 0.1923

## u by arm and run

| Arm / run | u |
|---|---|
| vote/memory@0 | 0.3326 |
| vms/memory@0 | 0.7310 |
| vtol/memory@0 | 0.7314 |
| vote/memory@0-L8 | 0.0911 |
| vms/memory@0-L8 | 0.9499 |
| vtol/memory@0-L8 | 0.9501 |
| vms/memory@1 | 0.4677 |
| vpool/memory@1 | 0.5671 |
| vguard/memory@1 | 0.5555 |
| vtol/memory@1 | 0.5604 |
| vms/memory@1-L8 | 0.2519 |
| vpool/memory@1-L8 | 0.3757 |
| vguard/memory@1-L8 | 0.3439 |
| vtol/memory@1-L8 | 0.3440 |
| vote/none@0 | 0.9892 |
| vms/none@0 | 0.9892 |
| vtol/none@0 | 0.9892 |
| vms/none@1 | 0.9875 |
| vtol/none@1 | 0.9874 |
| vote/cue@0 | 0.9892 |
| vms/cue@0 | 0.9848 |
| vpool/cue@0 | 0.9727 |
| vtol/cue@0 | 0.9823 |
| vote/correlated@0 | 0.2421 |
| vms/correlated@0 | 0.7040 |
| vpool/correlated@0 | 0.7050 |
| vguard/correlated@0 | 0.3781 |
| vtol/correlated@0 | 0.7043 |
| vms/correlated@1 | 0.4301 |
| vpool/correlated@1 | 0.5348 |
| vguard/correlated@1 | 0.3066 |
| vtol/correlated@1 | 0.4440 |

## vtol's branch per lineage-case (PLAN_AR006.md's derivation)

| Run | lineage-cases | the vote's | vms's | vguard's | another (union) | not compared |
|---|---|---|---|---|---|---|
| memory@0 | 1024 | 202 | 781 | 0 | 41 | 0 |
| memory@0-L8 | 1024 | 0 | 965 | 0 | 59 | 0 |
| memory@1 | 1024 | 243 | 510 | 187 | 84 | 0 |
| memory@1-L8 | 1024 | 336 | 410 | 222 | 56 | 0 |
| none@0 | 1024 | 990 | 33 | 0 | 1 | 0 |
| none@1 | 1024 | 537 | 444 | 0 | 43 | 0 |
| cue@0 | 1024 | 358 | 555 | 0 | 111 | 0 |
| correlated@0 | 1024 | 203 | 820 | 1 | 0 | 0 |
| correlated@1 | 1024 | 305 | 656 | 63 | 0 | 0 |

## Detectors

| Run / arm | fired | on the patch | onset median | footprint cells | patch covered |
|---|---|---|---|---|---|
| memory@0/vms | 0.802 | 0.795 | 1.0 | 71.2 | 0.991 |
| memory@0/vtol | 0.803 | 0.796 | 1.0 | 73.9 | 0.991 |
| memory@0-L8/vms | 1.000 | 1.000 | 1.0 | 145.7 | 1.0 |
| memory@0-L8/vtol | 1.000 | 1.000 | 1.0 | 148.3 | 1.0 |
| memory@1/vms | 0.654 | 0.355 | 1.0 | 72.7 | 0.526 |
| memory@1/vpool | 0.873 | 0.535 | 1.0 | 91.6 | 0.587 |
| memory@1/vguard | 0.556 | 0.504 | 1.0 | 69.9 | 0.893 |
| memory@1/vtol | 0.763 | 0.512 | 1.0 | 79.6 | 0.661 |
| memory@1-L8/vms | 0.547 | 0.210 | 1.0 | 90.0 | 0.343 |
| memory@1-L8/vpool | 0.834 | 0.475 | 1.0 | 106.1 | 0.422 |
| memory@1-L8/vguard | 0.463 | 0.400 | 1.0 | 104.1 | 0.669 |
| memory@1-L8/vtol | 0.672 | 0.396 | 1.0 | 98.9 | 0.461 |
| none@0/vms | 0.032 | 0.009 | 5638.0 | 52.8 | 0.083 |
| none@0/vtol | 0.033 | 0.009 | 5638.0 | 52.7 | 0.081 |
| none@1/vms | 0.445 | 0.047 | 1.0 | 65.2 | 0.058 |
| none@1/vtol | 0.476 | 0.051 | 1.0 | 64.3 | 0.058 |
| cue@0/vms | 0.575 | 0.048 | 1.0 | 70.8 | 0.042 |
| cue@0/vpool | 0.913 | 0.141 | 1.0 | 115.6 | 0.1 |
| cue@0/vtol | 0.650 | 0.058 | 1.0 | 69.7 | 0.047 |
| correlated@0/vms | 0.801 | 0.794 | 1.0 | 71.2 | 0.991 |
| correlated@0/vpool | 0.805 | 0.798 | 1.0 | 73.8 | 0.991 |
| correlated@0/vguard | 0.286 | 0.271 | 886.0 | 68.3 | 0.935 |
| correlated@0/vtol | 0.802 | 0.795 | 1.0 | 71.2 | 0.991 |
| correlated@1/vms | 0.653 | 0.351 | 1.0 | 72.8 | 0.523 |
| correlated@1/vpool | 0.870 | 0.532 | 1.0 | 91.7 | 0.585 |
| correlated@1/vguard | 0.238 | 0.161 | 2766.0 | 63.3 | 0.637 |
| correlated@1/vtol | 0.702 | 0.385 | 1.0 | 71.9 | 0.534 |
