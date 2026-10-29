# E102 — selected sign arrangement at fixed strengths and sign counts

24 October 2026. Authorized after E101. Reuse all 32 known E098 histories
980000–980031 without selection. E101 found that transferred signs help at
transferred magnitudes, while signs alone do not help and magnitudes alone harm.
Test whether the donor's sign placement matters beyond its numbers of positive
and negative selected connections. This is an outcome-informed mechanism test
with new reader nuisances, not fresh-source confirmation.

## Four records and a constrained permutation

Keep the paired outside background and all original support. Selected donors
use ordinary coactivity; outside capture remains as originally supplied.

| Variant | Selected content | Slots |
| --- | --- | --- |
| B | Paired signs and magnitudes; exact E101 N00 | 0–3 |
| M | Paired signs, independent magnitudes; exact E101 N01 | 4–7 |
| D | Independent signs and magnitudes; exact E101 N11 | 8–11 |
| S | D's selected signs permuted at fixed edge magnitudes | 12–15 |

Retain erased-writer controls at slots 16/17. No new signs-only-at-paired-
magnitudes, intact or outside-swap reads; all their original endpoints remain
historical. Independently reconstruct E099 capture, E100 regions and E101
components before the new intervention.

For each task/arm/founder/recipient, obtain the two terminal injury masks from
the fixed E102 reader streams **without running reader dynamics**. Partition
the selected nonzero edges by the two-bit signature
`alive_draw0 + 2*alive_draw1`, giving four disjoint strata. Within each stratum,
list edge indices in C order and apply one PCG64 permutation seeded by
`rng('E102', task, 'selected_sign_permutation', arm, founder, recipient, stratum)`.
Move only the donor sign bits: `copysign(abs(D[target]), D[source])`. Store the
complete source-index map, masks and survival signatures. Do not move magnitudes,
zeros (including their sign bits), support or outside bytes.

Use this one S record in both terminal draws. Empty, singleton, homogeneous-sign
and accidentally unchanged permutations remain unchanged; no reroll, replacement
or selection by changes, scores or benefits. Do not condition on birth states,
noise draws, reader trajectories or outcomes. The independently generated injury
masks must match those later returned by the reader exactly.

This preserves D/S positive and negative selected counts within every stratum,
hence globally **and among surviving connections under each injury**. M/D/S
have identical absolute weights, natural denominators and absolute normalized
couplings before and after injury. All variants have identical selected support
and outside weight bytes. The control is injury-conditioned; it tests sign
arrangement under these two declared injuries, not an injury-independent writing
algorithm. It does not preserve each cell's incident sign counts, signed weight
sums, weighted sign mass or cycle consistency. Report those changes where
measured and do not identify any one as the mechanism solely from this contrast.

## Frozen prediction and inference

**The donor sign arrangement outperforms the count-matched rearrangement at fixed
strengths, and the joint selected-transfer benefit repeats.** Require both
pooled-mixture lower bounds strictly positive in adjusted **97.5% whole-block
bootstrap intervals**, 10,000 shared resamples of the 32 independent source
blocks:

1. D−S: donor arrangement advantage.
2. D−B: repeated joint selected transfer.

Both positive yields `ARRANGEMENT_CONTRIBUTES_WITH_REPEATED_SELECTED_TRANSFER`.
Report negative and unresolved directions explicitly. Three percentage points
is a practical reporting reference, not another gate. No extension, changed
threshold, alternative permutation or selected subset after outcomes. One
permutation per record is one randomized perturbation, not an exhaustive null
distribution; bootstrap intervals are over source blocks, not permutation tests.

Secondary pointwise 95%: donor signs D−M; shuffled signs S−M; shuffled transfer
S−B; magnitudes alone M−B; native groups, sham/pulse splits, two draws, margins,
signed/aligned transfer and structural diagnostics. Keep both paths
`D−B = (D−M)+(M−B) = (D−S)+(S−B)` and `D−M = (D−S)+(S−M)`.
Neither path gives a unique mediation fraction. D−S alone does not establish
net repair over B, and unresolved is not equivalence. Keep every gain, harm,
zero, exact-context recurrence and all 16 four-record outcome configurations;
these configurations are not a new 2×2 intervention factorial.

## Endpoints, readers and bounded execution

Retain all E098 immediate/later, E099 capture, E100 region and E101 component
endpoints, including the original signs-only N10 result. Reproduce 42 historical
tables and the E100/E101 contrast-event distributions and identities. No old
endpoint enters new intervals or new-minus-old inference. Old/new draw labels
use different nuisance streams. No ancestry or supplying-writer dynamics repeat.

Unchanged E077 production and independent reader: float64, dt .2, noise .02,
birth SD .05, 24 scattered non-port injuries, paired terminal cue birth/noise,
natural normalization with zero drive at zero denominator and no positive floor.
New E102_terminal_0/1 phases in the E077 namespace, matched across variants.
Scientific reads: 2048 steps, 1024 settling, final 32 observations; strict all-port
signed margins >.25. Four founders, four recipients, four arms, two draws and
32 sources give **2,048 contexts / 4,096 context-draw rows / 36,864 terminal cue
observations**, plus retained erased controls. Two draws do not add source blocks.

Use only excluded E101 benchmark blocks 9000980/9000981 for fixtures (R=1,
24/12 steps, final 4) and timing (R=1, 512/256 steps, final 32). Test independent
scalar/vector permutation reconstruction and inverse recovery, exact count and
coupling invariants, signed zeros/tiny weights, empty/singleton/homogeneous and
all-selected cases, mismatched supports and corrupted sources/maps/masks,
strict thresholds, all outcome configurations and both primary requirements.
Replay an archived reader exactly and independently replay every new update,
score and diagnostic. Preflight all scientific sources and save the permutation
inventory and packet hashes **without new reader outcomes**. Retain every case
regardless of how many signs can move.

Inspect the benchmark figure and verify files before qualification. Scale the
slower block's reader time by 4 recipients × 4 duration and static time by four;
add 180 seconds for summaries, a threefold timing allowance and 1.5 uncompressed
storage reserve. Up to four one-thread workers within the shared twelve-CPU
ceiling; conservative forecast must fit six hours or receive a documented resource
review before new scientific readers. Runs over ten minutes detach with unique
frozen inputs/log/PID/status and one bounded startup check. Later status is
user-driven. No automatic polling, extension, restart or successor. All writes
stay under experiments; manuscript integration remains separate.
