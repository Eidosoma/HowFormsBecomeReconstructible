# E051 interim evidence: theory-tests assessment

The first eight blocks provide encouraging evidence that the original writer can retain high terminal performance after rebuilding cue noise is decorrelated. They also show that its advantage over simpler alternatives can shrink or disappear. These are separate findings. The original E051 robustness decision remains pending.

This review uses the user-supplied excerpt, the saved [early report](source/REPORT.md), its [snapshot](source/snapshot.json) and the [native protocol](source/PROTOCOL.md). Copies and hashes are retained in [SOURCE_RECEIPT.json](SOURCE_RECEIPT.json). This lane reviewed the fixed snapshot; it did not poll the live experiment, rerun trajectories or verify the original dynamics independently.

The cohort is blocks 34000–34007: eight of 32 planned independent blocks, with 128 of 512 planned lineages per condition. Counts below are both-cue successes in the normalized scattered-damage terminal assay after 32 rebuilds. They do not mean that all 32 preceding bodies passed.

| Rebuilding cue noise | Original writer | Ordinary rewrite | Pure contrast | Bridge preservation |
| --- | ---: | ---: | ---: | ---: |
| Matched | 120/128 | 31/128 | 0/128 | 99/128 |
| Correlation .999 | 126/128 | 120/128 | 126/128 | 122/128 |
| Independent | 126/128 | 127/128 | 126/128 | 128/128 |

Here “bridge preservation” is E051's `exact_preserve`: retain available incoming weights with absolute magnitude above .5 and otherwise use the original bridge rule. It is not the fully protected copying reference from earlier experiments.

For the original writer, the saved returning-edge fallback fraction changes from 100% under matched rebuilding noise to 0% in each noise-mismatch condition, while terminal success remains high. This weakens the specific concern that disabling the exact-zero fallback necessarily causes functional collapse. It does not show that the same repair mechanism operated in both conditions. Pure contrast's change from 0/128 to 126/128, together with the improvements of ordinary rewriting and preservation, makes that mechanistic distinction especially important.

The original-minus-ordinary differences are +69.53 percentage points under matched noise, +4.69 points at correlation .999 and −0.78 points with independent noise. Its differences from bridge preservation are +16.41, +3.13 and −1.56 points. These are arithmetic descriptions of the same eight blocks, not superiority or equivalence decisions. The controls must remain in the final account: robustness of absolute performance alone would not establish a distinctive writer advantage across these conditions.

The fixed tolerance has 3/128 successes under matched cues, 80/128 at noise correlation .999 and 122/128 under independent noise. This particular threshold is unfavorable relative to the original rule in the observed conditions. The threshold changes the writing branch on every available edge satisfying `0 < abs(q) <= 1e-4`; it does more than replace an exact-zero test on returning edges. Its failure therefore does not establish that every finite tolerance fails or that exact equality is the only workable implementation. No replacement threshold should be selected from these interim outcomes and inserted into E051.

Initial-state perturbations need their own interpretation. With update noise still matched, the original writer scores 119/128 at reset correlation .99 and 118/128 with independent resets; the returning-edge fallback remains at 100% in this subset. Those rows do not provide another intervention that turns off the same branch.

The numerical mechanism remains unresolved. The original writer's mean absolute returning-edge contrast is approximately 0.001635 at noise correlation .999 and 0.052564 with independent noise, compared with exactly zero in the paired condition. Means do not determine the small-weight tail or identify which connections carry the task. Noise-created connections, normalized reading, changes in functional activity and other ordinary mechanisms remain candidates. E052 already proposes finite precision, quantization, record-noise and denominator-floor challenges; it addresses a different question and should preserve its own exposure and version history.

E051 changes rebuilding trials only. Teaching, holding-phase noise and terminal assays retain their original definitions, and teaching and assay cue randomness remain paired. There is no joint reset-plus-noise condition. These results therefore cannot establish robustness of the entire acquisition-to-test procedure to independent cue randomness, arbitrary numerical changes, full machinery turnover or indefinite inheritance.

The source early-look script reports agreement between saved mean-port arrays and exported scores at all five assay horizons in the eight blocks. That is useful scoring evidence, while the independent trajectory audit and full cohort remain outstanding in this snapshot. The frozen primary rule requires five simultaneous conditions: absolute lower bounds above .75 for the paired and two mild-perturbation arms, plus lower bounds above −.05 for both perturbed-minus-paired contrasts. This review computes no interim interval or primary gate, changes no stopping rule and makes no sample-size adjustment.

For RDT, this is now development evidence. A later explanation must distinguish quantitative prediction of performance from a retrospective account of the branch used. TT001 was already scored and sealed before this numerical excerpt was received, includes no E051 records and makes no transfer claim to these noise regimes. The next prospective theory test still needs its own frozen predictor and eligible new conditions.
