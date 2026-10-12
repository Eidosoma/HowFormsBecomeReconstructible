# E007 fresh compact-renewal confirmation

**TECHNICAL_ONLY**

All 4 founders retained; formation qualified 2/4. Mean within-block disagreement 18.95%.

| Bytes at every boundary | Terminal own minus foreign, points [95%] | Own agreement | Renewal minus same-budget copy, points [95%] |
| --- | --- | --- | --- |
| 2048 | +1.12 [+1.12, +1.12] | 73.05% | -4.88 [-4.88, -4.88] |
| 128 | +0.78 [+0.78, +0.78] | 71.39% | +0.20 [+0.20, +0.20] |

## 2048 bytes

Gates: `{"acquisition_readable": true, "early_specificity": true, "formation": false, "terminal_read_required": true, "terminal_specificity": true, "terminal_write_required": true}`.

- G1 own minus foreign: +1.90 [+1.90, +1.90] points.
- G2 own minus foreign: +2.25 [+2.25, +2.25] points.
- G3 own minus foreign: +0.98 [+0.98, +0.98] points.
- terminal own minus foreign: +1.12 [+1.12, +1.12] points.
- Terminal renewal minus full-field renewal: +0.00 [+0.00, +0.00] points.

## 128 bytes

Gates: `{"acquisition_readable": true, "early_specificity": true, "formation": false, "terminal_read_required": true, "terminal_specificity": true, "terminal_write_required": true}`.

- G1 own minus foreign: +1.76 [+1.76, +1.76] points.
- G2 own minus foreign: +0.59 [+0.59, +0.59] points.
- G3 own minus foreign: +0.44 [+0.44, +0.44] points.
- terminal own minus foreign: +0.78 [+0.78, +0.78] points.
- Terminal renewal minus full-field renewal: -1.66 [-1.66, -1.66] points.

This is a fresh-cohort confirmation in the same codebase. Three body-written replacements precede a fresh terminal reader. General writing/reading machinery and coordinates are supplied. Compression changes field amplitude and resolution together; the packet budget excludes shared machinery. The wider 97.5% intervals and all controls are retained in summary.json.
