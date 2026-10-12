# E016 saved response dynamics

Post hoc, descriptive only. All 32 blocks and 128 founders retained; all regimes, controls and damage conditions are included in summary.json. No simulation, candidate, criterion or primary test was added.

Each checkpoint uses the preceding 32-step output mean and the original strict margin. Later observations are descriptive, not a longer-horizon test.

| Own-record regime | Damage | Accuracy at step 64 | Step 128 | Step 256 | Step 512 |
| --- | --- | --- | --- | --- | --- |
| ordinary | intact | 16.02% | 28.42% | 40.72% | 43.46% |
| ordinary | scattered | 14.36% | 19.92% | 27.25% | 32.42% |
| ordinary | square | 15.43% | 28.61% | 39.45% | 42.38% |
| consistent | intact | 29.69% | 48.44% | 65.72% | 67.87% |
| consistent | scattered | 26.46% | 35.64% | 45.61% | 53.42% |
| consistent | square | 27.83% | 45.80% | 63.96% | 68.95% |
| engineered | intact | 29.30% | 50.78% | 66.11% | 66.50% |
| engineered | scattered | 26.17% | 35.94% | 46.68% | 56.15% |
| engineered | square | 28.71% | 46.97% | 67.58% | 70.90% |

| Own-record regime | Damage | Final failures | Failures with a wrong sign | Failures strongly wrong and quiet late | Same strong output signs for both opposing cues |
| --- | --- | --- | --- | --- | --- |
| ordinary | intact | 56.54% | 86.53% | 60.97% | 35.94% |
| ordinary | scattered | 67.58% | 85.40% | 61.27% | 36.52% |
| ordinary | square | 57.62% | 88.64% | 62.71% | 35.55% |
| consistent | intact | 32.13% | 96.96% | 89.97% | 43.36% |
| consistent | scattered | 46.58% | 98.53% | 91.82% | 50.98% |
| consistent | square | 31.05% | 98.11% | 90.25% | 38.48% |
| engineered | intact | 33.50% | 93.59% | 84.84% | 43.16% |
| engineered | scattered | 43.85% | 99.33% | 91.31% | 48.83% |
| engineered | square | 29.10% | 96.31% | 86.91% | 37.50% |

The two failure-subtype columns use all final failures as their denominator. The last column instead uses all matched founder/recipient pairs. A strongly wrong response has at least one requested signed output below -0.25. 'Quiet late' additionally requires less than 0.05 change between the final two 32-step means at both ports, and no output sign change in the last 128 steps. These descriptive cutoffs were chosen after the main outcome was known, before this trace analysis.

Quiet wrong outputs during this finite window do not prove a stable whole-body attractor or show when/why commitment occurred. A longer run or a change in the timing of amplification would be a new experiment. Equal output signs do not imply exactly equal amplitudes or no causal input effect. All final scores reproduce the independently audited original block scores exactly; raw file hashes match the scientific COMPLETE receipt.
