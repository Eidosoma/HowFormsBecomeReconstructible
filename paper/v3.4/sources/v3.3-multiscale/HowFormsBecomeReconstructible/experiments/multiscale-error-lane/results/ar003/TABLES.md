# AR003 tables

Intervals: 95% t over the blocks with the block SD (the registration's SD is the larger of that and the case-level SD over sqrt 8; the lead's check uses it).

## Registered statements

| Id | Verdict | Part | Value | Threshold |
|---|---|---|---|---|
| E1 | HOLDS | E1 max over arms and cases of abs(u(new) + u(old) - 1), change@0 | +0.000000 | le 1e-12 |
| E2 | HOLDS | E2 U_mix(vms) - U_mix(vote) | +0.108527 | ge 0.09 |
| E3 | HOLDS | E3 U_2(vms) - U_2(det) | +0.123932 | ge 0.06 |
| E3 | HOLDS | E3 U_4(vms) - U_4(det) | +0.050934 | ge 0.03 |
| E3 | HOLDS | E3 U_8(vms) - U_8(det) | +0.149961 | ge 0.11 |
| E4 | HOLDS | E4 four scorings at 4 (none, body, shared, cue): (1/8) sum u(vms) - u(ms) | +0.018211 | ge 0.005 |
| E4 | HOLDS | E4 U_2(vms) - U_2(ms) | +0.127625 | ge 0.08 |
| E5 | HOLDS | E5 kept at 4: (u(vms) - u(vote)) - k (u(vdial) - u(vote)), memory + correlated | +0.048175 | ge 0.0 |
| E5 | HOLDS | E5 kept at 8: (u(vms) - u(vote)) - k (u(vdial) - u(vote)), memory + correlated | +0.172929 | ge 0.0 |
| E6 | HOLDS | E6 sheet cost under scattered cue damage: r_all(vote) - r_all(vms), cue@0 | +0.005635 | le 0.01 |
| E6 | HOLDS | E6 sheet cost with no event: r_all(vote) - r_all(vms), none@0 | -0.000035 | le 0.002 |
| E7 | HOLDS | E7 p(vms fires on the patch | memory, 4 x 4) | +0.819336 | ge 0.6 |
| E7 | HOLDS | E7 p(vms fires on the patch | correlated, 4 x 4) | +0.820312 | ge 0.6 |
| E7 | HOLDS | E7 p(vms fires on the patch | memory, 8 x 8) | +1.000000 | ge 0.95 |
| E7 | HOLDS | E7 p(vms fires on the patch | correlated, 8 x 8) | +1.000000 | ge 0.95 |
| E7 | HOLDS | E7 p(vms fires at all | none) | +0.048828 | le 0.05 |
| E8 | HOLDS | E8 four scorings at 4: (1/8) sum u(vms) - u(vote) | -0.000244 | ge -0.005 |
| E8 | HOLDS | E8 U_2(vms) - U_2(vote) | +0.001434 | ge -0.01 |
| E9 | HOLDS | E9 under misread cues (sigma 1), memory damage: u(vms) - u(det), memory@1 | +0.193542 | ge 0.05 |
| E9 | HOLDS | E9 under misread cues with no event: r_all(vote) - r_all(vms), none@1 (the vote's none@0) | +0.002879 | le 0.01 |
| E10 | HOLDS | E10 price at 4 x 4 over memory and correlated: (1/8) sum u(vms) - (fire u(vdial) + (1 - fire) u(vote)) | +0.001755 | ge -0.005 |

## Utilities by size

| Arm | U_2 | U_4 | U_8 | U_mix |
|---|---|---|---|---|
| vote | +0.7728 [+0.7641, +0.7814] | +0.6848 [+0.6786, +0.6911] | +0.6212 [+0.6183, +0.6241] | +0.6929 [+0.6886, +0.6972] |
| det | +0.6503 [+0.6398, +0.6607] | +0.7421 [+0.7280, +0.7562] | +0.6872 [+0.6746, +0.6998] | +0.6932 [+0.6840, +0.7024] |
| ms | +0.6466 [+0.6381, +0.6550] | +0.7376 [+0.7203, +0.7548] | not run | n/a |
| vms | +0.7742 [+0.7651, +0.7833] | +0.7930 [+0.7781, +0.8079] | +0.8372 [+0.8336, +0.8408] | +0.8015 [+0.7957, +0.8072] |

## Contrasts

| Contrast | Value [95%] |
|---|---|
| a: U_mix(vms) - U_mix(vote) | +0.1085 [+0.1026, +0.1145] |
| U_mix(vms) - U_mix(det) | +0.1083 [+0.1012, +0.1153] |
| U_mix(det) - U_mix(vote) | +0.0003 [-0.0106, +0.0111] |
| b: U_2(vms) - U_2(det) | +0.1239 [+0.1124, +0.1354] |
| U_2(vms) - U_2(vote) | +0.0014 [-0.0004, +0.0033] |
| U_2(det) - U_2(vote) | -0.1225 [-0.1349, -0.1101] |
| b: U_4(vms) - U_4(det) | +0.0509 [+0.0447, +0.0571] |
| U_4(vms) - U_4(vote) | +0.1082 [+0.0915, +0.1249] |
| U_4(det) - U_4(vote) | +0.0572 [+0.0415, +0.0730] |
| b: U_8(vms) - U_8(det) | +0.1500 [+0.1382, +0.1617] |
| U_8(vms) - U_8(vote) | +0.2160 [+0.2130, +0.2190] |
| U_8(det) - U_8(vote) | +0.0660 [+0.0536, +0.0784] |
| c: four at 4: vms - ms | +0.0182 [+0.0157, +0.0208] |
| c: U_2(vms) - U_2(ms) | +0.1276 [+0.1176, +0.1376] |
| c: hits at 2: vms - ms | +0.1160 [+0.1058, +0.1263] |
| four at 4: vms - vote (non-inferiority) | -0.0002 [-0.0008, +0.0003] |
| four at 4: ms - det | +0.0004 [-0.0004, +0.0011] |
| U_4(ms) - U_4(det) | -0.0045 [-0.0100, +0.0009] |
| U_2(ms) - U_2(det) | -0.0037 [-0.0069, -0.0005] |
| d: kept at 4 over 0.5 (memory + correlated) | +0.4123 [+0.3304, +0.4941] |
| d: kept at 4 over 0.8 (memory + correlated) | +0.1392 [+0.0833, +0.1951] |
| d: kept at 4 over 0.9 (memory + correlated) | +0.0482 [-0.0014, +0.0977] |
| d: kept at 8 over 0.5 (memory + correlated) | +0.8659 [+0.8541, +0.8777] |
| d: kept at 8 over 0.8 (memory + correlated) | +0.3462 [+0.3414, +0.3510] |
| d: kept at 8 over 0.9 (memory + correlated) | +0.1729 [+0.1704, +0.1755] |
| e: sham cue@0 vms | +0.0056 [+0.0043, +0.0069] |
| e: sham none@0 vms | -0.0000 [-0.0001, +0.0000] |
| price at 4 (hits) | +0.0018 [-0.0008, +0.0043] |
| price at 8 (hits) | -0.0000 [-0.0001, +0.0000] |

Shares of the declared signal's worth (vms, memory + correlated): L4 0.9529, L8 0.9998; by situation: L4/memory 0.9589, L4/correlated 0.9478, L8/memory 0.9998, L8/correlated 0.9998; det (rest default) against the same: L4 0.6685, L8 0.4124

## u by scoring

| Arm / size | none | body | memory | correlated | shared | cue | change/new | change/old |
|---|---|---|---|---|---|---|---|---|
| vote/L2 | 0.987 | 0.987 | 0.617 | 0.613 | 0.990 | 0.987 | - | - |
| det/L2 | 0.967 | 0.967 | 0.172 | 0.171 | 0.965 | 0.960 | - | - |
| ms/L2 | 0.967 | 0.967 | 0.157 | 0.156 | 0.965 | 0.960 | - | - |
| vms/L2 | 0.987 | 0.987 | 0.622 | 0.619 | 0.990 | 0.988 | - | - |
| vote/L4 | 0.993 | 0.993 | 0.321 | 0.235 | 0.944 | 0.993 | 0.007 | 0.993 |
| det/L4 | 0.976 | 0.976 | 0.583 | 0.582 | 0.856 | 0.965 | 0.575 | 0.425 |
| ms/L4 | 0.976 | 0.976 | 0.563 | 0.563 | 0.856 | 0.967 | - | - |
| vms/L4 | 0.993 | 0.993 | 0.722 | 0.702 | 0.944 | 0.991 | 0.535 | 0.465 |
| vote/L8 | 0.990 | 0.990 | 0.084 | 0.078 | 0.838 | 0.990 | - | - |
| det/L8 | 0.969 | 0.969 | 0.440 | 0.437 | 0.725 | 0.957 | - | - |
| vms/L8 | 0.990 | 0.990 | 0.948 | 0.946 | 0.838 | 0.985 | - | - |

vdial: vdial/L4/memory 0.739, vdial/L4/correlated 0.728, vdial/L8/memory 0.948, vdial/L8/correlated 0.947

## Detectors

| Run / arm | fired | on the patch | onset median | footprint cells | patch covered |
|---|---|---|---|---|---|
| none@0/det | 0.164 | 0.017 | 5447.0 | 68.9 | 0.054 |
| none@0/ms | 0.050 | 0.000 | 6031.0 | 59.2 | 0.0 |
| none@0/vms | 0.049 | 0.001 | 6031.0 | 59.8 | 0.01 |
| body@0/det | 0.164 | 0.017 | 5447.0 | 68.9 | 0.054 |
| body@0/ms | 0.050 | 0.000 | 6031.0 | 59.2 | 0.0 |
| body@0/vms | 0.051 | 0.001 | 6031.0 | 60.3 | 0.01 |
| memory@0/det | 0.969 | 0.959 | 1.0 | 68.3 | 0.989 |
| memory@0/ms | 0.806 | 0.803 | 1.0 | 71.6 | 0.996 |
| memory@0/vms | 0.823 | 0.819 | 1.0 | 71.8 | 0.995 |
| correlated@0/det | 0.970 | 0.960 | 1.0 | 68.3 | 0.989 |
| correlated@0/ms | 0.808 | 0.805 | 1.0 | 71.6 | 0.996 |
| correlated@0/vms | 0.824 | 0.820 | 1.0 | 71.8 | 0.995 |
| shared@0/det | 0.178 | 0.029 | 5584.0 | 69.0 | 0.121 |
| shared@0/ms | 0.050 | 0.000 | 6031.0 | 58.9 | 0.0 |
| shared@0/vms | 0.051 | 0.001 | 6031.0 | 60.3 | 0.01 |
| cue@0/det | 0.620 | 0.105 | 1.0 | 76.8 | 0.097 |
| cue@0/ms | 0.608 | 0.072 | 1.0 | 64.2 | 0.046 |
| cue@0/vms | 0.560 | 0.070 | 1.0 | 64.7 | 0.046 |
| change@0/det | 0.968 | 0.958 | 1.0 | 68.3 | 0.989 |
| change@0/vms | 0.810 | 0.806 | 1.0 | 71.6 | 0.995 |
| memory@0-L2/det | 0.213 | 0.061 | 4728.5 | 70.8 | 0.266 |
| memory@0-L2/ms | 0.073 | 0.023 | 5521.0 | 58.2 | 0.32 |
| memory@0-L2/vms | 0.074 | 0.025 | 4149.0 | 58.8 | 0.342 |
| correlated@0-L2/det | 0.213 | 0.061 | 4728.5 | 70.8 | 0.266 |
| correlated@0-L2/ms | 0.073 | 0.023 | 5521.0 | 58.2 | 0.32 |
| correlated@0-L2/vms | 0.075 | 0.026 | 4153.0 | 59.1 | 0.351 |
| body@0-L2/det | 0.164 | 0.009 | 5447.0 | 68.9 | 0.03 |
| body@0-L2/ms | 0.050 | 0.000 | 6031.0 | 59.2 | 0.0 |
| body@0-L2/vms | 0.050 | 0.001 | 6031.0 | 60.5 | 0.02 |
| shared@0-L2/det | 0.166 | 0.011 | 5447.0 | 69.0 | 0.041 |
| shared@0-L2/ms | 0.050 | 0.000 | 6031.0 | 59.2 | 0.0 |
| shared@0-L2/vms | 0.050 | 0.001 | 6031.0 | 60.5 | 0.02 |
| memory@0-L8/det | 0.713 | 0.636 | 15.0 | 75.7 | 0.52 |
| memory@0-L8/vms | 1.000 | 1.000 | 1.0 | 145.9 | 1.0 |
| correlated@0-L8/det | 0.707 | 0.629 | 15.0 | 75.8 | 0.518 |
| correlated@0-L8/vms | 1.000 | 1.000 | 1.0 | 145.9 | 1.0 |
| body@0-L8/det | 0.164 | 0.037 | 5447.0 | 68.9 | 0.079 |
| body@0-L8/vms | 0.049 | 0.007 | 6031.0 | 59.8 | 0.021 |
| shared@0-L8/det | 0.182 | 0.045 | 5380.5 | 70.3 | 0.09 |
| shared@0-L8/vms | 0.049 | 0.007 | 6031.0 | 59.8 | 0.021 |
| none@1/det | 0.554 | 0.084 | 1.0 | 74.6 | 0.08 |
| none@1/vms | 0.426 | 0.036 | 1.0 | 58.2 | 0.041 |
| memory@1/det | 0.701 | 0.368 | 1.0 | 81.5 | 0.505 |
| memory@1/vms | 0.653 | 0.380 | 1.0 | 70.3 | 0.564 |

## Sheet costs against the vote

| Run / arm | r_all(vote) - r_all(arm) |
|---|---|
| cue@0/det | +0.03206 [+0.03070, +0.03342] |
| cue@0/ms | +0.03307 [+0.03155, +0.03459] |
| cue@0/vms | +0.00564 [+0.00434, +0.00693] |
| none@0/det | +0.01955 [+0.01891, +0.02018] |
| none@0/ms | +0.01961 [+0.01894, +0.02027] |
| none@0/vms | -0.00004 [-0.00009, +0.00001] |

## The misread side arm (sigma 1)

| Quantity | Value [95%] |
|---|---|
| none@1/r_in/det-sigma0 | -0.0043 [-0.0071, -0.0015] |
| none@1/r_all/det-sigma0 | -0.0049 [-0.0057, -0.0041] |
| none@1/sham/det | +0.0244 [+0.0235, +0.0253] |
| none@1/rate/det | +0.5537 [+0.4884, +0.6190] |
| none@1/located/det | +0.0840 [+0.0414, +0.1265] |
| none@1/u/det | +0.9714 [+0.9644, +0.9784] |
| none@1/r_in/vms-sigma0 | -0.0021 [-0.0046, +0.0004] |
| none@1/r_all/vms-sigma0 | -0.0029 [-0.0034, -0.0025] |
| none@1/sham/vms | +0.0029 [+0.0024, +0.0033] |
| none@1/rate/vms | +0.4258 [+0.3827, +0.4688] |
| none@1/located/vms | +0.0361 [+0.0107, +0.0615] |
| none@1/u/vms | +0.9905 [+0.9861, +0.9950] |
| none@1/vms-det misread loss difference | +0.0022 [-0.0009, +0.0053] |
| none@1/u(vms) - u(det) | +0.0192 [+0.0131, +0.0252] |
| memory@1/r_in/det-sigma0 | -0.3131 [-0.3562, -0.2700] |
| memory@1/r_all/det-sigma0 | -0.0087 [-0.0098, -0.0077] |
| memory@1/sham/det | +0.0245 [+0.0237, +0.0253] |
| memory@1/rate/det | +0.7012 [+0.6402, +0.7621] |
| memory@1/located/det | +0.3682 [+0.3171, +0.4192] |
| memory@1/u/det | +0.2694 [+0.2385, +0.3003] |
| memory@1/r_in/vms-sigma0 | -0.2587 [-0.3164, -0.2011] |
| memory@1/r_all/vms-sigma0 | -0.0065 [-0.0075, -0.0055] |
| memory@1/sham/vms | +0.0007 [+0.0002, +0.0012] |
| memory@1/rate/vms | +0.6533 [+0.6059, +0.7007] |
| memory@1/located/vms | +0.3799 [+0.3225, +0.4372] |
| memory@1/u/vms | +0.4630 [+0.4282, +0.4977] |
| memory@1/vms-det misread loss difference | +0.0544 [+0.0260, +0.0828] |
| memory@1/u(vms) - u(det) | +0.1935 [+0.1672, +0.2199] |

## U_4(vms) - U_4(vote), decomposed

| Term | Value [95%] |
|---|---|
| hits | +0.1084 [+0.0917, +0.1251] |
| four | -0.0002 [-0.0008, +0.0003] |
| pair | +0.0000 [+0.0000, +0.0000] |
| total | +0.1082 [+0.0915, +0.1249] |
