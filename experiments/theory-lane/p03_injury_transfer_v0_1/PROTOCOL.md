# Rewriting and transfer across injury patterns, P03 development v0.1

The user authorized this bounded experiment after the fixed-injury result.
All 64 previously selected generation-14 failures are retained, across eight
exposed blocks and four writer histories. The preceding fixed-injury experiment
found an equal-block rewrite advantage of 8.02 percentage points; its original
states and outcomes are known. This is outcome-informed development, with new
injury and reading randomness frozen before new native outcomes. It is not an
independent confirmation or a general damage/resource-boundary test.

## Intervention and prediction

For every case compare four fixed records: the actual incoming generation-13
packet, actual generation-14 original-writer outgoing packet, an erasure-only
packet, and an all-zero packet. Erasure-only multiplies the incoming weights by
the availability of edges under the original generation-14 injury. It preserves
all surviving incoming weights and removes only edges incident to those injured
cells. It does not copy outgoing magnitudes, signs, or learned zero patterns.
The outgoing packet may restore previously absent connections; outgoing minus
erasure-only includes those changes as well as reweighting. It is not a pure
sign intervention or a comparison with exactly matched nonzero support.

Read each packet under two regimes: the original fixed injury and fresh injury
patterns with the same 24 removed non-port cells. Packets do not change between
regimes, and previously absent weights are not healed by moving the injury.
Within the original regime incoming and erasure-only must be identical after
reader masking and produce byte-identical trajectories. This is an exact
implementation control. The all-zero record must produce cue-identical outputs
and zero both-cue successes in either regime.

The primary directional prediction is that the outgoing-minus-incoming success
difference remains positive on average under fresh injuries. Compute each case's
mean over 16 paired draws, average cases equally within each block, and then
weight the eight blocks equally. Freeze this direction before reading new native
outcomes. Report the effect and all block values whether positive, zero or
negative; no practical-benefit threshold or significance gate is invented.

Predeclared secondary contrasts are outgoing minus erasure-only, erasure-only
minus incoming, and the difference between fresh and original rewrite effects.
The decomposition is exactly additive at the success-rate level; it does not
make the nonlinear mechanisms independent. Report both regimes, all four rates,
pooled paired rescues/harms and all per-case outcomes. A positive effect only
under the original mask narrows transfer to that original context. A zero or
negative primary estimate fails the directional prediction in this development
panel. Broad intervals leave the population effect uncertain. A positive
primary estimate is development support, not confirmation of RDT as a whole.

## Sampling and resource contract

For each block and replicate 0–15, independently sample 24 cells uniformly
without replacement from the 244 non-port cells for every native founder-pair /
recipient context. The seed key is namespace, block, `injury`, replicate,
founder//2, recipient. Histories sharing that context use the same mask. Patterns
are not selected for connectivity, overlap, diagnostics or outcomes, and are not
redrawn to improve them. Each pattern is paired with one fresh reset/noise draw;
the estimand averages over both injury and read randomness. Sixteen draws do not
estimate a precise conditional capacity for each individual new mask.

The read stream uses namespace, block, `read`, replicate, independently of mask
generation. As in the checked native model, draw the complete two-founder-pair,
four-recipient panel each step, share noise between cues and paired founders,
and use common draws across histories, packet options and the two injury regimes.
The original regime receives the same 16 new read streams, enabling a paired
comparison of rewrite effects. This does not test independent cue noise.

Use the native reader unchanged: dt 0.2, noise 0.02, birth SD 0.05, clipping at
plus/minus 2, input clamps, injured cells zeroed each update, 1,024 settling
updates and 1,024 amplification updates. No writing occurs during reads. The
endpoint requires all four task-aligned cue/output means, averaged over the
last 32 observations, to be strictly above 0.25. There are 8,192 packet/read
trajectories: 64 cases x 2 regimes x 4 records x 16 paired draws.

The fixed signed-transfer and unsigned-access diagnostics use 64 linear updates
under the actual read mask and are computed before native outcomes. As secondary
comparators, choose between incoming and outgoing by the larger diagnostic;
exact ties give half weight. Compare with always incoming and always outgoing.
All 16 draws evaluate these choices because no native outcomes are used for
selection. No model is fitted. The rule is unchanged from the previous probe,
but its yield here has a different evaluation contract and is not directly
comparable to the previous 12-draw evaluation. No direct-probe baseline is
introduced in this experiment, and there is no budget-matched P08 claim.

Eight blocks remain the inference units. Preserve pairing within blocks, report
all block effects, and use a descriptive 20,000-resample block bootstrap with
seed 2026101001. Per-case 16-draw Wilson intervals describe Monte Carlo variation
over the declared draw law, not uncertainty over new biological or model systems.
No hypotheses, strata, damage levels or time budgets are selected after outcomes.

## Verification, execution and preservation

Bind the preceding completion marker, manifest, frozen preparation and source
arrays by hash. Check enrollment identities, all original masks, incoming and
outgoing bytes, and the erasure construction. Preserve masks, packet bytes,
diagnostics, reset states, endpoint bodies, last-32 output windows and scores.

Before scientific launch, test varying masks, paired randomness, case/variant
order invariance, erasure controls, strict scoring and the reporting interface.
Benchmark the largest block using four duplicated known incoming packets and
two duplicated original read streams at 2,048 updates; require byte-exact native
replay. The runtime forecast is 1.5 times measured seconds times the ratio of
scientific, original-replay and independent-audit cell-updates, plus 180 seconds.
The forecast ceiling is 3,600 single-thread seconds. Exceeding it stops launch
without changing the cohort, draws or protocol. Keep at least 1 GiB free.

During the run, replay every case's known original native read. Independently
rescore all raw windows and every table and diagnostic choice. A separate flat
neighbor implementation audits the first enrolled case of every block at draw
4, all four records and both injury regimes, and dense operators audit its
diagnostics. Independently regenerate every fresh mask and reconstruct the
erasure-only packets. Original inputs and completed runs are never overwritten.

Use one detached host process with one numerical thread, /dev/null stdin,
durable logs/PID and RUNNING/COMPLETE/FAILED receipts. Freeze source and prepared
inputs before launch; execute the frozen copy. The worker automatically performs
analysis, verification, report and figures. Leave it unpolled until the user
requests status or it finishes. No automatic successor or external message.
