# E044 — timing changes and saved rewriting histories

**TECHNICAL_ONLY**

1 reused blocks; 8 lineages. No new trajectories or causal repair claim.

Groups compare the original and delayed-extra-time normalized receivers. All intervals are exploratory, pointwise whole-block intervals, conditioned on the indicated outcome group.

| Horizon | Group | Cases | Original locked / reversed / other | Delayed locked / reversed / other | Current rebuilding body correct % | Earlier bodies failing % |
| --- | --- | --- | --- | --- | --- | --- |
| 24 | persistent_failure | 8 | 0 / 0 / 8 | 1 / 0 / 7 | 0.00 [0.00,0.00] | 100.00 [100.00,100.00] |
| 24 | rescued | 0 | 0 / 0 / 0 | 0 / 0 / 0 | n/a | n/a |
| 24 | lost | 0 | 0 / 0 / 0 | 0 / 0 / 0 | n/a | n/a |
| 24 | stable_success | 0 | 0 / 0 / 0 | 0 / 0 / 0 | n/a | n/a |
| 32 | persistent_failure | 8 | 1 / 0 / 7 | 0 / 0 / 8 | 0.00 [0.00,0.00] | 100.00 [100.00,100.00] |
| 32 | rescued | 0 | 0 / 0 / 0 | 0 / 0 / 0 | n/a | n/a |
| 32 | lost | 0 | 0 / 0 / 0 | 0 / 0 / 0 | n/a | n/a |
| 32 | stable_success | 0 | 0 / 0 / 0 | 0 / 0 / 0 | n/a | n/a |

| h32 scattered group | Strong edges | Strong before latest rewrite | Latest strong weakening | Latest weak-to-strong promotion | Physical strong loss | Last 8 bodies: failures | Last 8 rewrites: strong weakening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| persistent_failure | 62.00 [62.00,62.00] | 72.00 [72.00,72.00] | 11.38 [11.38,11.38] | 18.00 [18.00,18.00] | 16.62 [16.62,16.62] | 8.00 [8.00,8.00] | 99.12 [99.12,99.12] |
| rescued | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| lost | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| stable_success | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

| h32 scattered group | Original intact success % | Delayed intact success % | Strong injured graph connected % | Returning edges restored % | Young weak repairs promoted % |
| --- | --- | --- | --- | --- | --- |
| persistent_failure | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] | 98.93 [98.93,98.93] | 8.54 [8.54,8.54] |
| rescued | n/a | n/a | n/a | n/a | n/a |
| lost | n/a | n/a | n/a | n/a | n/a |
| stable_success | n/a | n/a | n/a | n/a | n/a |

All h24/h32 injuries, three schedules, four mutually exclusive output classes, full class-transition tables, 113 retained features, declared conditional repair ratios and per-block counts are available in summary.json. h32 next-body success is unobserved and has a null estimate, never zero success. E042 packet/body/graph measurements are reused as previously audited inputs; the new joins, output classification, history windows, totals and intervals are independently checked.

These groups are defined by outcomes on the same cohort. Small rescued/lost groups, nonrandom conditioning and repeated measurements prevent causal or fresh-confirmation claims. Output locking is a response label, not proof of an attractor. Unsigned connectivity omits weight signs and magnitudes. Associations between body failure and strong weakening do not identify which causes which. This diagnosis cannot overturn E043's failed timing criterion or E041's passed finite durability criterion. No additional reader or writing intervention ran.
