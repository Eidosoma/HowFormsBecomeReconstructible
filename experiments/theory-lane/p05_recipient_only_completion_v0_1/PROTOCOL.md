# Completion from the surviving record

This development assay tests whether ordinary sign completion helps when repair
receives only the outgoing recipient record O. The preceding assay inferred signs
from O but supplied saved incoming magnitudes and donor-conditioned support. Its
completion result was 26.74%, versus 26.94% for own signs and 22.61% for O, with
eight blocks weighted equally. The completion-minus-O interval included zero.
Those results motivate this follow-up; they do not establish equivalence or repair
benefit. Keep the same 64 exposed generation-14 failures and all eight blocks.

## Repair rule and supplied information

Keep the previous completion optimizer unchanged: normalized recipient edge
influences, four input cells pinned positive, sixteen starts, at most sixty-four
checkerboard sweeps, seed 2026101004 and the same exact tie conventions. Let s be
its selected node signs and q_ij=s_i*s_j. No output targets, donor information,
incoming record, injury mask, body state or assessment outcome enters the solver.

For the complete recipient-only rule, define M by O_ij==0 on the fixed 512-edge
toroidal lattice. Define m as the median of absolute nonzero O weights, or zero
if none exist. Fill every edge in M with m*q_ij and preserve all other O weights.
The API receives only O and the frozen optimizer options. The known lattice,
input locations, optimizer, compute budget and reader are supplied apparatus.
Zeros can be genuine absent edges rather than damage. The rule deliberately does
not consult historical support or the original injury mask to distinguish them.

The scalar median is a fixed conventional imputation, chosen for simplicity and
resistance to a few extreme observed magnitudes. No cutoff, gain, edge budget,
fitting or outcome-based selection is allowed. All-zero O remains erased. The
rule is not claimed to be the best possible magnitude estimator; a failure can
reject this rule without proving that historical information is necessary.

## Information removal controls

Let I be the incoming record and A the original injury-unavailable edge set.
Let B=A intersect {I!=0}, and let K be the preceding donor-conditioned common
support. These sets and I are used only for the historical reference controls.
All repairs preserve every nonzero outgoing weight.

| Index | Record | Added edges and weights |
|---|---|---|
| 0 | incoming | Original I, separate reference |
| 1 | outgoing | O, no additions |
| 2 | common_completion | K with abs(I)*q, preceding completion construction |
| 3 | full_own | B with I |
| 4 | full_completion | B with abs(I)*q, no donor selection |
| 5 | support_imputed | B with m*q, historical support remains |
| 6 | recipient_completion | Every zero O edge with m*q |
| 7 | recipient_shuffled | Same support, magnitudes and sign counts as 6; signs permuted |
| 8 | erased | No edges |

Shuffle row-major inferred signs on M using PCG64 from the SHA256 stream key
[namespace, block, "shuffle", history, founder, recipient]. This random control
does not optimize or use a target output. Report how many signs change; retain
cases with identical shuffles. The primary rule itself has no case labels.

The path 2 to 4 removes donor selection, 4 to 5 removes saved magnitudes, and
5 to 6 removes historical support. These are path-specific intervention effects,
not a full factorial decomposition. Adding edges changes reader normalization
and connectivity. Report added edge counts and absolute weight as resources;
there is no claim of cost-free reconstruction or compression.

## Frozen predictions and inference

The primary directional forecast is positive recipient_completion minus outgoing
intended-task success under fresh injury and noise. A nonpositive point estimate
fails the forecast for this rule and panel. A positive estimate whose descriptive
interval includes zero leaves benefit unresolved. Do not replace a failed primary
with a favorable secondary comparison.

Secondary contrasts are recipient minus shuffled; full completion minus common
completion; full own minus full completion; imputed support minus full completion;
recipient minus imputed support; recipient minus full completion; recipient minus
full own; and full completion minus outgoing. Also report primary effect on the
opposite mapping. No equivalence or noninferiority claim is specified. Repair
beating O without beating its sign-shuffled control would not isolate inferred
sign placement as the source of benefit. Beating both supports ordinary repair
under the supplied apparatus; it does not uniquely confirm RDT.

Use 16 fresh uniformly drawn 24-cell non-port injuries per case and fresh native
reset/noise. All nine variants share each context; both cues retain native matched
randomness. Use namespace P05_recipient_only_completion_v0_1; injury keys are
[namespace, block, "injury", replicate, founder//2, recipient], and read keys are
[namespace, block, "read", replicate]. Preserve the unchanged 2048-step native
reader, 1024 settling steps, dt .2, noise .02, birth SD .05, clip +/-2, and strict
minimum intended margin >.25 across the last 32 updates. Score both mappings;
weak or mixed outputs pass neither. No writing occurs during assessment.

Use one additional fresh-noise draw under the original injury. Records 2 through
5 must then give exactly O's trajectory. Records 6 and 7 may also fill historical
zeros outside that injury; their identity with O is required only for cases with
no such edges. Do not erase those genuine intervention effects from the control.
Erasure must pass neither mapping. Replay every original incoming read exactly.
There are 9792 scientific/control paired-cue contexts, plus 64 known replays.

Average draws within cases, cases within blocks, and the eight blocks equally.
Report pooled counts separately. Use 20000 whole-block bootstrap resamples with
PCG64 seed 2026101005 and paired indices. These are descriptive intervals on eight
exposed blocks. Fresh noise is not an independent hypothesis holdout. No states
are dropped and no effect-based stopping or extension is allowed.

## Validation and execution

Independently check all 64 completion solutions with the unchanged flat Prim-based
optimizer, and reconstruct all nine records with scalar grid loops. Bind the
previous frozen controls and selected completion signs. Check counterexamples,
all-zero records, hidden-information exclusion, preservation of observed weights,
scale behavior, shuffled controls and a synthetic failed-forecast report with
deliberately corrupted analysis. Check the separate native reader on nontrivial
fixtures and all nine records in the first case of every block, original draw 0
and fresh draw 4. Verify raw windows, scores, tables, paired counts and bootstraps.

Benchmark duplicated known incoming records only: largest block, nine variants,
two original streams. Forecast 1.5 times scaled native runtime plus 180 seconds;
require at most 3600 single-thread seconds. Freeze before fresh native outcomes.
Use one worker and one numerical thread within the shared 12-CPU ceiling. A run
over 600 seconds is detached, with PID, log, startup acknowledgment and durable
COMPLETE/FAILED receipts. Analysis and verification run automatically to completion.
No polling and no automatic successor.
