# Fresh assay repeatability and short renewal feasibility

TT003 is a bounded native development pilot for the RDT-P01 v0.2 observation contract. The user authorized it on 8 October 2026. It asks how much fresh-assay variability occurs with the packet fixed, how response categories change after two renewals, and whether short data support informative fits. It makes no long-horizon accuracy, confidence-coverage or RDT confirmation claim.

## Packets and experimental unit

Use E041 blocks 32000 and 32001, founder indices 0 and 1, and source depths 0 and 32: eight fixed packets nested within two independent source blocks. Depth 0 is the consistent-teaching acquired packet; depth 32 is full bridge rewriting, original recipient index 0. This index-based selection precedes reading the selected packets and does not select on success. E041 outcomes are already development evidence. Retain source-file hashes, packet bytes and each packet's declared ancestral rule. These two blocks cannot support a population-level robustness or theory decision.

## Native dynamics and measurement

Keep the E041 16 by 16 reciprocal nearest-neighbor lattice, source/output ports, normalized incoming drive with no positive denominator floor, dt .2, noise .02, birth SD .05, 2048 reading updates, 1024 unamplified settling updates, gain 2, and final 32-step mean-port score. Each fresh body independently removes 24 non-port cells and incident edges. Within each paired-cue assay, births, update noise and damage are identical across the two cue signs. Ancestral-rule labels enter scoring only.

Full rewriting uses the original exact-zero bridge: tanh(3*v), cue-difference edge products where nonzero, and ordinary mean coactivity where the difference product is exactly zero. Capture precedes 128 holding updates. Only the captured packet continues; the holding body, readout and assay randomness cannot modify it. The adapter must agree exactly with the frozen original E041 reader and rewriting branch on excluded fixture inputs. All native pilot events receive a separate dynamics replay using auditor primitives, with source, stream, intermediate and output checks.

Classify a fresh assay as A if both cues pass both strict output margins for the declared ancestral rule, B if they pass the opposite rule, and N otherwise. Both margins must exceed .25; equality fails. A and B are mutually exclusive. Nonfinite values or technical failures stop the run, with all prior output retained, rather than removing an observation.

## Paths, repetitions and controls

For each source packet, use 16 independently seeded short paths conditional on that fixed packet. Observe depths 0, 1 and 2 for full rewriting and a protected-copy reference. Each readout is a separate fresh clone; it does not write to the continuing record. Protected copying passes the original bytes unchanged and supplies an observation-only reference, without a claim of matched implementation cost. Its depth-zero primary assay is shared with rewriting; subsequent assays use paired random draws across the two policies.

At every rewriting boundary, including depth zero, make two independent fresh assays of the same path packet. The first enters the 27-category short-history counts; the second measures within-packet assay disagreement. The depth-zero second assay and the protected-copy later assays also measure variation with the original record fixed. Repeated paths are not independent founders.

At depth zero, make 16 matched assays per source packet for each control: all-zero packet, label-independent uniform[-1,1] random packet, the matched opposite-rule founder's packet, and the own packet with reading communication disabled. Erased and disabled-reader responses must agree under identical randomness and must classify N under paired cues. Random and foreign controls have no required favorable outcome. Swapping the declared scoring rule must swap A/B and preserve N.

Random keys include experiment/version, block, source depth, founder-pair index, path, event kind, depth and repeat, with separate birth/noise/damage streams. They exclude task labels and policy where conditions are paired. Opposed founders within a pair share event streams. Assay streams are disjoint from renewal and holding streams. Changing the number or order of assays must leave renewal packets unchanged. The packet source is the only mutable state passed between renewal cycles.

This gives 1,536 paired-cue fresh assays and 256 paired-cue renewal bodies across the eight packets; shared depth-zero observations are counted once. A paired-cue body entails two cue trajectories. The simulation and audit are both charged. No long continuation is generated.

## Analysis and uncertainty limits

Report all packet-specific A/B/N counts, continuous margins, duplicate-assay disagreement, fixed-packet repeatability, control outcomes, packet hashes and short-path pattern counts. Do not pool heterogeneous starting packets into one stationary model. Fit the frozen two-mode candidate separately to each packet and policy, retaining all eight optimizer starts. Report boundary estimates, convergence, unsupported categories, differences between fitted and empirical marginal probabilities, and the joint-pattern likelihood gap to the saturated empirical distribution. These are in-sample feasibility diagnostics, not goodness-of-fit decisions.

Fit the ordinary three-category output Markov baseline on the same short paths; unobserved source rows remain unsupported. The same structured conventional HMM ties the candidate by construction. Save any depth-32 point extrapolation as explicitly unvalidated. No confidence interval or coverage claim accompanies it. A single observed category or a missing A/B category is an explicit rare-loss/identification warning, not evidence of perfect persistence. Record spread across successful optimizer starts as a numerical diagnostic, not a confidence interval.

Clone disagreement shows that the observed category is not a deterministic function of packet bytes alone. It does not by itself falsify every latent-state HMM; marginal and joint observation assumptions need separate assessment. Agreement in 16 paths does not establish deterministic observation. Population inference, sampling-calibrated long-horizon uncertainty and a sufficiently powered native test remain later work.

## Validation, execution and retention

Before scientific execution, check strict category boundaries and label involution, source integrity, clone immutability, no task-label route into dynamics, stream separation/order invariance, physical edge deletion, capture timing, normalization under safe positive binary rescaling, corruption detection, and byte-exact native fixture compatibility. Preserve failures and never overwrite completed runs.

The fixture uses engineered excluded packets, two paths, 24 read steps, 12 settling steps, four observed steps and eight holding steps. The benchmark uses the same two technical opposed-rule packets and two paths, 128 read steps, 64 settling steps, 32 observed steps and 128 holding steps. Both run the complete adapter, evidence storage, analysis and separate replay. They are not scientific evidence.

Use one worker and one numerical thread. Forecast pilot wall time conservatively as three times benchmark simulation-plus-audit time multiplied by (8/2)*(16/2)*(2048/128), plus four times analysis time and 90 seconds. Reserve max(512 MiB, 1.5*32*benchmark output bytes). Freeze all code, native references, theory references, source packets and parameters before launch. If the forecast exceeds 600 seconds, launch detached with stdin closed, a local console log, PID, frozen inputs and durable RUNNING/COMPLETE/FAILED records. After one bounded launch check, do not poll; the user requests subsequent status. Completion reports and plots are generated by the job itself.
