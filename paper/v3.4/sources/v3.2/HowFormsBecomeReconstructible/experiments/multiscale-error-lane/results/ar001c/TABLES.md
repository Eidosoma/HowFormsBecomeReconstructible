# AR001C tables (confirmation, blocks 920000-920015, design a78866e1421d)

**Verdict: CONFIRMED**

| Criterion | Bound | Rule | Pass |
|---|---|---|---|
| C1 (a) U_ctrl(0.9, 0.1) - U(vote) | lower +0.0673 | > 0 | True |
| C2 (b) U_ctrl(0.9, 0.1) - U_ctrl(1, 1) | lower +0.0470 | > 0 | True |
| C3 sham cost, cue@0 | upper +0.0079 | <= 0.01 | True |
| C3 sham cost, none@0 | upper +0.0000 | <= 0.002 | True |

## The contrasts (95% t intervals over the blocks)

| Contrast | Mean | Interval | Half-width | SD_block | Case SD / sqrt 8 |
|---|---|---|---|---|---|
| (a) U_ctrl(0.9, 0.1) - U(vote) | +0.0906 | [+0.0673, +0.1139] | 0.0233 | 0.0437 | 0.0314 |
| (b) U_ctrl(0.9, 0.1) - U_ctrl(1, 1) | +0.0520 | [+0.0470, +0.0570] | 0.0050 | 0.0094 | 0.0100 |
| sham cost, cue@0 | +0.0066 | [+0.0053, +0.0079] | 0.0013 | 0.0024 | 0.0022 |
| sham cost, none@0 | -0.0000 | [-0.0000, +0.0000] | 0.0000 | 0.0000 | 0.0000 |
| location alone, U_ctrl(1, 1) - U(vote) | +0.0386 | [+0.0187, +0.0586] | 0.0199 | 0.0374 | 0.0266 |

Half-widths against their targets (a third of the development values): (a) 0.0233 against 0.0374; (b) 0.0050 against 0.0194

## The three arms by scoring (pooled, t = 8,000)

| Arm | none | body | memory | correlated | shared | cue | change/new | change/old | U |
|---|---|---|---|---|---|---|---|---|---|
| vote | 0.9926 | 0.9926 | 0.3171 | 0.2325 | 0.9448 | 0.9926 | 0.0074 | 0.9926 | 0.6840 |
| rest | 0.9743 | 0.9743 | 0.0933 | 0.0753 | 0.8657 | 0.9670 | 0.0512 | 0.9488 | 0.6187 |
| dial | 0.9743 | 0.9743 | 0.5588 | 0.5588 | 0.8657 | 0.8491 | 0.5570 | 0.4430 | 0.7226 |

U_ctrl(h, f) = 0.6187 + 0.1819 h -0.0780 f
