# TT005 — repeated readout of fixed E051 packets

Status: authorized development pilot v1, informed by completed E051 and TT003–TT004. The user accepted implementation and launch on 9 October 2026. Freeze this protocol, code, analysis and all prepared inputs together before technical qualification and new native assays. This is not a confirmatory registration or a new forecasting claim.

## Question and scope

How does the distribution of observed function from an unchanged packet depend on fresh-recipient variation and pairing between its two cue trials? E051 changed rebuilding randomness while preserving terminal pairing. TT003 showed variable readouts from unchanged packets; TT004 showed why such variation and rare losses matter for interpretation and forecast uncertainty. This pilot tests the measurement contract before fitting another long-horizon model.

Select h32 packets by fixed identifiers: E051 blocks 34000–34003, founders 0 and 1, recipient 0; rebuilding conditions matched, noise correlation .999 and independent noise; writing policies original exact, ordinary and pure contrast. This gives eight lineage contexts across four blocks and 72 archived packets. Selection is by identifiers, not success or packet divergence. These outcomes and source blocks are already development exposure, and the design is outcome-informed. The pilot is conditional on this small packet panel; it cannot establish fleet-wide robustness.

The tolerance intervention is omitted because the theory lane already has sign/magnitude and pulse protocols. E052's proposed precision/normalization experiment retains its own identity. No source experiment is modified and no 32-generation trajectory is rerun.

## Assays and controls

For each context draw four fresh scattered-damage masks, each removing 24 non-port cells. For each mask draw two independent recipient realizations. Cross terminal initial-state correlation {1,0} with terminal update-noise correlation {1,0}, giving four assay conditions. Within each condition both cues use the same physical damage mask. Use common base and innovation arrays across conditions and packets; preserve each cue's marginal initial-state and noise distributions. The first cue always uses the base arrays. The second either copies them or uses the independent innovation, separately for reset and update noise. Duplicates share the mask but have independent reset/noise arrays, so they are not independent draws of physical damage.

Read a fresh immutable copy of each packet for every assay. Keep the native normalized reader, 2,048 read steps, 1,024 settling steps, last-32-step observation, noise .02, birth SD .05, dt .2, port geometry and strict margin >.25. Do not capture or pass an assay body forward. Preserve labels only for scoring; they must not enter dynamics or stream selection.

Add a shared erased-packet control and an opposite-founder acquired-packet control in each context, with the same draws and four assay conditions. Keep the foreign rule identity explicit so an opposite-rule response is not confused with unreadability. The proposed count is 2,304 paired-cue assays on study packets plus 512 control assays, for 2,816 paired-cue assays total. Retain all cases, including duplicate packets and poor readouts; duplicates are not new independent source records.

## Analysis fixed before execution

The main descriptive contrast is fully independent terminal reset/noise minus fully matched terminal reset/noise, separately for each of the nine rebuilding/writer combinations. Retain the two singly perturbed conditions to distinguish the factors. Average within context and block before comparing blocks; four blocks do not support a population precision claim.

Report per-cue success and continuous signed port margins, strict both-cue success, ancestral/opposite/neither categories, and duplicate disagreement under each condition. Keep raw cue-level margins, masks, packet identities and random-stream identifiers. The paired design distinguishes condition contrasts from accidental changes in input draws.

Changing dependence between two binary cue outcomes can change their joint success while leaving both marginal probabilities unchanged. Therefore a change in both-cue success alone must not be labeled loss of stored rule identity. Repeated outcomes and wrong-rule responses help assess that interpretation but do not, by themselves, identify a unique latent-state mechanism.

Variance descriptions must respect the nesting of block, packet, damage mask and recipient realization. The TT004 binomial intervals for independent fresh assays cannot be applied to these shared-mask repeats unchanged. This development pilot has no confirmatory robustness verdict, claimed equivalence margin or newly calibrated horizon-32 forecast. Any proposed uncertainty method must be validated for this sampling design before use; otherwise report the complete descriptive paired counts with that limitation.

## Verification and execution

Before new assays, verify source packet and completion hashes and reproduce selected existing E051 terminal trajectories byte exactly. Check immutable packet copies, cue/reset/noise axes, strict category scoring, independent stream construction and lack of label access. Independently replay all new assay dynamics, then reconstruct categories and reported contrasts from saved mean-port arrays. Stop and retain failures rather than changing selection or thresholds after looking at outcomes.

Benchmark the complete assay and audit workflow using excluded technical cases. Use one CPU and one numerical thread. Freeze a conservative forecast and a one-hour pilot ceiling before launch. If the forecast exceeds that ceiling, revise and version the design before exposing new scientific outcomes; do not silently cut completed cases or expand the budget. There is no credible runtime estimate yet.

If implemented and launched, use a persistent host process with frozen inputs, closed stdin, local log/PID and durable COMPLETE/FAILED outputs. The earlier TT003 sandbox launch did not survive its parent environment; reuse its corrected host-launch method. Make one bounded startup check and leave the scientific job unpolled until the user requests status or a completion notification arrives. No automatic successor.

This study can improve the observation contract. Full-candidate uncertainty, abstention calibration and a sealed prospective forecast comparison remain subsequent work even if all readout conditions perform well.

## Implementation contract v1

Within each context the order is nine rebuilding/writer packet combinations, then erased and foreign acquired controls; terminal conditions are matched, independent noise, independent reset, independent both. Masks and replicate draws are shared across packet types and terminal conditions. The four source blocks each contribute two contexts with opposite founder rules. Each context has its own semantic streams; a rule label is never used to generate draws. The benchmark uses one excluded engineered context with the full 11-packet, four-condition, four-mask, two-repeat design and full native read duration. The fixture uses one such context, two masks and 32 read steps. No new scientific packet is assayed in those technical runs, apart from exact replay of already saved E051 assays used for compatibility checks.

Retain full terminal states, late port traces, input packets, masks, birth arrays, normalizers and per-update state/noise SHA256 commitments. A separate implementation regenerates every draw and update and verifies all retained arrays and commitments. An additional scalar analysis audit reconstructs categories, cue scores, descriptive tables and paired contrasts without importing production scoring. Analysis reports complete four-block descriptive outcomes and no confidence intervals or p-values. Duplicate disagreement is computed within the shared mask; it is not an independent-fresh-damage statistic.

The conservative forecast is three times benchmark simulation-plus-audit time times the eight pilot contexts, plus twice benchmark technical-check time, eight times benchmark analysis time, and 60 seconds. This fixed formula includes plotting and scalar analysis checks; the one-hour ceiling is unchanged. Reserve at least 256 MiB, or twice the scaled benchmark outputs if larger. New native assays run detached and unpolled, even if the final forecast is below ten minutes, matching the user's preference. Qualification and benchmark results remain separate scientific exclusions.
