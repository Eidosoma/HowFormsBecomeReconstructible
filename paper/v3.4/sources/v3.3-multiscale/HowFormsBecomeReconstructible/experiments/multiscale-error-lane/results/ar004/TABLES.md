# AR004 tables

Intervals: 95% t over the blocks with the block SD (the registration's SD is the larger of that and the case-level SD over sqrt 8; the lead's check uses it).

## Registered statements

| Id | Verdict | Part | Value | Threshold |
|---|---|---|---|---|
| G1 | HOLDS | G1 R1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vms, memory@1) | +0.095739 | ge 0.04 |
| G2 | HOLDS | G2 R0 = (1/3) sum over sizes of u(vpool, memory@0) - u(vms, memory@0) | -0.000051 | ge -0.005 |
| G3 | HOLDS | G3 (a) the trade-off: sheet cost under scattered cue damage, vpool less vms, cue@0 | +0.011842 | ge 0.008 |
| G3 | HOLDS | G3 (b) vpool's sheet cost under scattered cue damage: r_all(vote) - r_all(vpool), cue@0 | +0.017691 | le 0.029 |
| G3 | HOLDS | G3 (c) vpool's sheet cost with no event: r_all(vote) - r_all(vpool), none@0 (the confirmed bound) | -0.000009 | le 0.002 |
| G5 | HOLDS | G5 u(vpool) - u(vote) in the 4 x 4 patch, none@0 | +0.000000 | ge -0.005 |
| G5 | HOLDS | G5 u(vpool, none@1) - u(vote, none@0) in the 4 x 4 patch | -0.007874 | ge -0.03 |
| G6 | HOLDS | G6 p(vpool fires on the patch | memory@1, 4 x 4) | +0.520508 | ge 0.25 |
| G6 | HOLDS | G6 p(vpool fires on the patch | memory@1, 8 x 8) | +0.502930 | ge 0.3 |
| G6 | HOLDS | G6 p(on the patch | memory@1, 4 x 4): vpool - vms | +0.227539 | ge 0.04 |
| G7 | HOLDS | G7 W1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vote, memory@0) | +0.177846 | ge 0.09 |

## Contrasts

| Contrast | Value [95%] |
|---|---|
| G1 R1 (misread recovery over vms) | +0.0957 [+0.0819, +0.1096] |
| G2 R0 (sigma-0 hits against vms) | -0.0001 [-0.0005, +0.0004] |
| G3 (a) sham cue@0, vpool less vms | +0.0118 [+0.0087, +0.0150] |
| G3 (b) sham cue@0 vpool | +0.0177 [+0.0153, +0.0200] |
| G3 (c) sham none@0 vpool | -0.0000 [-0.0000, +0.0000] |
| sham none@1 vpool (the dropped G4) | +0.0078 [+0.0066, +0.0089] |
| G5 give none@0 | +0.0000 [+0.0000, +0.0000] |
| G5 give none@1 | -0.0079 [-0.0177, +0.0020] |
| give cue@0 vpool (reported: the trade-off inside the patch) | -0.0092 [-0.0163, -0.0021] |
| G6 located memory@1 L4 | +0.5205 [+0.4576, +0.5835] |
| G6 located memory@1 L8 | +0.5029 [+0.4288, +0.5771] |
| G6 located memory@1 L4 minus vms | +0.2275 [+0.1755, +0.2796] |
| G7 W1 vpool (worth over the vote under misreads) | +0.1778 [+0.1638, +0.1919] |
| W1 vms | +0.0821 [+0.0691, +0.0951] |
| vms misread loss (sigma 1 - sigma 0) | -0.3549 [-0.3757, -0.3341] |
| vpool misread loss (sigma 1 - sigma 0) | -0.2591 [-0.2812, -0.2371] |
| sham cue@0 vms | +0.0058 [+0.0044, +0.0073] |
| sham none@0 vms | -0.0000 [-0.0000, +0.0000] |
| sham none@1 vms | +0.0038 [+0.0031, +0.0045] |
| R1 at L2 | +0.0173 [-0.0014, +0.0361] |
| R0 at L2 | +0.0000 [+0.0000, +0.0000] |
| R1 at L4 | +0.1163 [+0.0925, +0.1400] |
| R0 at L4 | -0.0001 [-0.0016, +0.0013] |
| R1 at L8 | +0.1536 [+0.1210, +0.1862] |
| R0 at L8 | -0.0000 [-0.0002, +0.0002] |

The recovery fraction (R1 over vms's own misread loss, pooled over the sizes): 0.2698; by size: L2 1.1639, L4 0.374, L8 0.2079

## u by arm and run

| Arm / run | u |
|---|---|
| vote/memory@0-L2 | 0.6089 |
| vote/memory@0-L4 | 0.3071 |
| vote/memory@0-L8 | 0.0886 |
| vote/none@0-L4 | 0.9901 |
| vote/cue@0-L4 | 0.9901 |
| vms/memory@0-L2 | 0.6289 |
| vms/memory@0-L4 | 0.7346 |
| vms/memory@0-L8 | 0.9521 |
| vms/memory@1-L2 | 0.6140 |
| vms/memory@1-L4 | 0.4237 |
| vms/memory@1-L8 | 0.2132 |
| vms/none@0-L4 | 0.9901 |
| vms/cue@0-L4 | 0.9853 |
| vms/none@1-L4 | 0.9819 |
| vpool/memory@0-L2 | 0.6289 |
| vpool/memory@0-L4 | 0.7344 |
| vpool/memory@0-L8 | 0.9521 |
| vpool/memory@1-L2 | 0.6313 |
| vpool/memory@1-L4 | 0.5400 |
| vpool/memory@1-L8 | 0.3668 |
| vpool/none@0-L4 | 0.9901 |
| vpool/cue@0-L4 | 0.9808 |
| vpool/none@1-L4 | 0.9822 |

## The 6 x 6 side arm (reported)

| Quantity | Value |
|---|---|
| u vote/memory@0-L6 | 0.1528 |
| u vms/memory@0-L6 | 0.9130 |
| u vms/memory@1-L6 | 0.3576 |
| u vpool/memory@0-L6 | 0.9127 |
| u vpool/memory@1-L6 | 0.4944 |
| R1 at 6 x 6 | +0.1367 [+0.0967, +0.1768] |
| R0 at 6 x 6 | -0.0003 [-0.0008, +0.0002] |
| recovery fraction at 6 x 6 | 0.2462 |
| located vms/memory@0-L6 | 1.000 |
| located vms/memory@1-L6 | 0.320 |
| located vpool/memory@0-L6 | 1.000 |
| located vpool/memory@1-L6 | 0.572 |

## Detectors

| Run / arm | fired | on the patch | onset median | footprint cells | patch covered |
|---|---|---|---|---|---|
| memory@0-L2/vms | 0.098 | 0.059 | 1996.5 | 52.9 | 0.6 |
| memory@0-L2/vpool | 0.098 | 0.059 | 1996.5 | 52.9 | 0.6 |
| memory@0/vms | 0.842 | 0.842 | 1.0 | 70.8 | 1.0 |
| memory@0/vpool | 0.842 | 0.842 | 1.0 | 74.7 | 1.0 |
| memory@0-L8/vms | 1.000 | 1.000 | 1.0 | 145.0 | 1.0 |
| memory@0-L8/vpool | 1.000 | 1.000 | 1.0 | 148.0 | 1.0 |
| none@0/vms | 0.038 | 0.000 | 4673.0 | 56.9 | 0.0 |
| none@0/vpool | 0.038 | 0.000 | 4673.0 | 56.9 | 0.0 |
| cue@0/vms | 0.552 | 0.089 | 1.0 | 71.3 | 0.079 |
| cue@0/vpool | 0.928 | 0.152 | 1.0 | 100.2 | 0.092 |
| memory@1-L2/vms | 0.476 | 0.049 | 1.0 | 63.3 | 0.094 |
| memory@1-L2/vpool | 0.686 | 0.098 | 1.0 | 79.4 | 0.129 |
| memory@1/vms | 0.621 | 0.293 | 1.0 | 71.7 | 0.459 |
| memory@1/vpool | 0.860 | 0.521 | 1.0 | 92.5 | 0.59 |
| memory@1-L8/vms | 0.547 | 0.238 | 1.0 | 83.9 | 0.289 |
| memory@1-L8/vpool | 0.837 | 0.503 | 1.0 | 108.6 | 0.413 |
| none@1/vms | 0.471 | 0.051 | 1.0 | 64.4 | 0.059 |
| none@1/vpool | 0.668 | 0.066 | 1.0 | 79.2 | 0.054 |
| memory@0-L6/vms | 1.000 | 1.000 | 1.0 | 103.2 | 1.0 |
| memory@0-L6/vpool | 1.000 | 1.000 | 1.0 | 107.5 | 1.0 |
| memory@1-L6/vms | 0.623 | 0.320 | 1.0 | 84.1 | 0.454 |
| memory@1-L6/vpool | 0.871 | 0.572 | 1.0 | 104.8 | 0.569 |
