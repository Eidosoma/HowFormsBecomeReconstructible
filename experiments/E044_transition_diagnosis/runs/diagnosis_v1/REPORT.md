# E044 — timing changes and saved rewriting histories

**EXPLORATORY_DIAGNOSIS_COMPLETE**

32 reused blocks; 512 lineages. No new trajectories or causal repair claim.

Groups compare the original and delayed-extra-time normalized receivers. All intervals are exploratory, pointwise whole-block intervals, conditioned on the indicated outcome group.

| Horizon | Group | Cases | Original locked / reversed / other | Delayed locked / reversed / other | Current rebuilding body correct % | Earlier bodies failing % |
| --- | --- | --- | --- | --- | --- | --- |
| 24 | persistent_failure | 44 | 11 / 3 / 30 | 14 / 2 / 28 | 4.55 [0.00,12.50] | 30.53 [23.13,39.37] |
| 24 | rescued | 8 | 8 / 0 / 0 | 0 / 0 / 0 | 87.50 [60.00,100.00] | 4.89 [0.00,13.04] |
| 24 | lost | 14 | 0 / 0 / 0 | 14 / 0 / 0 | 85.71 [55.56,100.00] | 4.35 [2.61,6.35] |
| 24 | stable_success | 446 | 0 / 0 / 0 | 0 / 0 / 0 | 94.62 [92.24,96.84] | 3.61 [2.99,4.23] |
| 32 | persistent_failure | 67 | 20 / 3 / 44 | 24 / 3 / 40 | 10.45 [1.67,21.16] | 31.49 [23.22,40.10] |
| 32 | rescued | 17 | 14 / 0 / 3 | 0 / 0 / 0 | 88.24 [70.00,100.00] | 3.23 [1.29,5.81] |
| 32 | lost | 14 | 0 / 0 / 0 | 13 / 0 / 1 | 92.86 [75.00,100.00] | 2.76 [0.95,5.57] |
| 32 | stable_success | 414 | 0 / 0 / 0 | 0 / 0 / 0 | 97.34 [95.49,98.82] | 4.32 [3.67,4.99] |

| h32 scattered group | Strong edges | Strong before latest rewrite | Latest strong weakening | Latest weak-to-strong promotion | Physical strong loss | Last 8 bodies: failures | Last 8 rewrites: strong weakening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| persistent_failure | 290.85 [270.25,308.64] | 296.15 [281.29,309.59] | 12.97 [4.08,26.11] | 59.55 [54.77,64.52] | 51.88 [48.72,54.96] | 5.42 [4.31,6.49] | 72.04 [46.43,99.09] |
| rescued | 306.88 [296.06,318.10] | 312.06 [301.94,321.06] | 7.76 [2.58,14.50] | 57.35 [51.36,63.47] | 54.76 [50.95,58.31] | 0.53 [0.12,1.07] | 48.65 [26.18,77.85] |
| lost | 308.86 [281.08,324.57] | 312.29 [300.93,323.67] | 9.29 [1.38,24.14] | 60.79 [50.78,69.24] | 54.93 [49.20,61.00] | 0.57 [0.20,1.17] | 47.21 [18.00,92.80] |
| stable_success | 316.38 [313.88,318.77] | 314.15 [311.88,316.30] | 2.98 [2.14,3.89] | 59.89 [58.11,61.73] | 54.69 [53.66,55.70] | 0.39 [0.29,0.49] | 30.33 [25.90,35.00] |

| h32 scattered group | Original intact success % | Delayed intact success % | Strong injured graph connected % | Returning edges restored % | Young weak repairs promoted % |
| --- | --- | --- | --- | --- | --- |
| persistent_failure | 19.40 [5.36,35.59] | 17.91 [5.36,31.82] | 62.69 [44.78,79.69] | 99.28 [99.00,99.53] | 60.47 [53.74,67.14] |
| rescued | 100.00 [100.00,100.00] | 100.00 [100.00,100.00] | 88.24 [70.00,100.00] | 98.87 [98.40,99.34] | 58.61 [52.26,65.95] |
| lost | 100.00 [100.00,100.00] | 92.86 [75.00,100.00] | 92.86 [75.00,100.00] | 99.23 [98.60,99.68] | 64.09 [49.04,74.84] |
| stable_success | 100.00 [100.00,100.00] | 99.28 [98.36,100.00] | 97.34 [95.49,98.82] | 99.12 [99.00,99.23] | 67.07 [65.09,68.99] |

All h24/h32 injuries, three schedules, four mutually exclusive output classes, full class-transition tables, 113 retained features, declared conditional repair ratios and per-block counts are available in summary.json. h32 next-body success is unobserved and has a null estimate, never zero success. E042 packet/body/graph measurements are reused as previously audited inputs; the new joins, output classification, history windows, totals and intervals are independently checked.

These groups are defined by outcomes on the same cohort. Small rescued/lost groups, nonrandom conditioning and repeated measurements prevent causal or fresh-confirmation claims. Output locking is a response label, not proof of an attractor. Unsigned connectivity omits weight signs and magnitudes. Associations between body failure and strong weakening do not identify which causes which. This diagnosis cannot overturn E043's failed timing criterion or E041's passed finite durability criterion. No additional reader or writing intervention ran.
