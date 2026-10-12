# E007 fresh compact-renewal confirmation

**COMPACT_RENEWAL_CONFIRMED**

All 128 founders retained; formation qualified 100/128. Mean within-block disagreement 18.66%.

| Bytes at every boundary | Terminal own minus foreign, points [95%] | Own agreement | Renewal minus same-budget copy, points [95%] |
| --- | --- | --- | --- |
| 2048 | +1.78 [+1.24, +2.36] | 71.29% | -5.57 [-6.18, -4.97] |
| 128 | +1.66 [+1.14, +2.17] | 67.35% | -1.29 [-1.82, -0.79] |

## 2048 bytes

Gates: `{"acquisition_readable": true, "early_specificity": true, "formation": true, "terminal_read_required": true, "terminal_specificity": true, "terminal_write_required": true}`.

- G1 own minus foreign: +2.60 [+2.10, +3.14] points.
- G2 own minus foreign: +2.25 [+1.70, +2.85] points.
- G3 own minus foreign: +2.05 [+1.53, +2.61] points.
- terminal own minus foreign: +1.78 [+1.24, +2.36] points.
- Terminal renewal minus full-field renewal: +0.00 [+0.00, +0.00] points.

## 128 bytes

Gates: `{"acquisition_readable": true, "early_specificity": true, "formation": true, "terminal_read_required": true, "terminal_specificity": true, "terminal_write_required": true}`.

- G1 own minus foreign: +1.82 [+1.32, +2.36] points.
- G2 own minus foreign: +1.82 [+1.28, +2.35] points.
- G3 own minus foreign: +1.74 [+1.26, +2.22] points.
- terminal own minus foreign: +1.66 [+1.14, +2.17] points.
- Terminal renewal minus full-field renewal: -3.94 [-4.70, -3.19] points.

This is a fresh-cohort confirmation in the same codebase. Three body-written replacements precede a fresh terminal reader. General writing/reading machinery and coordinates are supplied. Compression changes field amplitude and resolution together; the packet budget excludes shared machinery. The wider 97.5% intervals and all controls are retained in summary.json.
