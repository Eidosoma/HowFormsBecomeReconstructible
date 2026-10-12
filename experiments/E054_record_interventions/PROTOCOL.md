# E054 — what features of a record support reconstruction?

Design fixed 10 October 2026 before intervention outcomes. This is a mechanistic
follow-up using existing E051 records, not an independent confirmation of E051
or E053. E053 completion, independent audit and closeout are operational launch
prerequisites; its outcomes do not choose this study's design. No automatic launch.

## Cohort and common assay

Use all E051 blocks 34000–34031, all four founders and four recipients, without
success filtering: 512 lineages per history. Five histories: acquired, then h32
full rewrite and preservation under matched cue noise, then the same two policies
under independent cue noise (E051 condition indices 0, 4, 20, 24). Acquisition is
repeated over recipient slots; these are not independent source acquisitions.
E051 supplies both policies, which E053 does not. All inference resamples whole
blocks. Prior outcomes motivated this follow-up and are acknowledged as seen.

Each intervention changes a copy of a fixed record. Use fresh E054 random streams
with matched reset/noise and injury draws across histories and arms; the two cue
episodes share reset/noise within the terminal assay. Float64, zero denominator
floor, 2048 read steps, first 1024 without amplification, final 32 observations,
dt=.2, noise=.02, birth SD=.05, strict output margin .25. Intact, scattered24 and
square9 injuries retain every port cell. No rewriting or holding in this assay.
Technical block 900041 is excluded: fixture uses E051 fixture sources, R2,
24/12 read/settle and four observations; benchmark uses E051 benchmark sources,
R1, 128/64 steps and 32 observations. Neither yields scientific classifications.

## Eleven arms, chosen before outcomes

1. Untouched record.
2. All values multiplied by .5: normalization null; reject support underflow.
3. Permute magnitudes within positive and negative classes. Signs, support and
   each sign class's magnitude multiset remain fixed; relative strength changes.
4. Equalize all nonzero magnitudes to their global mean, retaining signs/support
   and total absolute mass. Tests signs and support with uniform relative strength.
5. Anchored switching: select eight non-port cells uniformly without replacement;
   w'_ij=s_i*w_ij*s_j. All port s=+1. Transform the matched reset and every noise
   draw by s as well. This is a pathwise symmetry control in real arithmetic.
6. Isolated sign flips: same occupied edit count and eight rank-bin magnitude
   counts as switching. Draw independently in each stratum; overlap is allowed.
   Stable (magnitude, edge-index) ordering defines bins. This matches magnitude
   strata, not exact mass or location; retain both differences and actual parity.
7. Delete precisely the edges selected for arm 6; keep every survivor unchanged.
8. Delete those edges and restore their exact original signed values: null.
9. Delete a matched subset of newly repaired returning edges at g32.
10. Delete other occupied edges matched to arm 9 by count in the same eight
    magnitude strata. A returning edge touches a g31-absent/g32-present cell,
    is available at g32, has zero effective incoming weight, and nonzero outgoing
    weight. Within each bin retain min(target, other) eligible edges, then choose
    uniformly up to arm 5's edit count across eligible targets; match other edges
    in each chosen bin. All cases remain, including zero-exposure cases. Acquisition
    has no repair tags and arms 9/10 are no-ops, excluded from repair interpretation.
11. Erased record: assay negative control.

Selections use history, founder-pair and recipient semantic keys, never scores.
Magnitude permutations may differ between rule partners because sign classes
differ. Cell selections and random-stream keys are paired across their rules.
Both sign arms preserve magnitudes, support and D. Switching preserves every
cycle sign; isolated flips can create or remove negative cycles. Deletions change
D and therefore normalized surviving interactions as well as access. No claim
of a pure access intervention at fixed effective coupling is made.

## Outcomes and inference

Save every intervened record, selection/permutation map, reset, terminal field,
late output trace, injury mask, denominator and directed normalized coupling.
Report both-cue success, per-cue minimum task margin, raw T and aligned r*T where
T=((A_plus-A_minus)-(B_plus-B_minus))/4. Retain actual edit counts, mass and port
proximity; support, input/output reachability, components and negative parity in
a deterministic spanning-forest cycle basis, before and after injury. Cycle bases
are identical for support-preserving arms; negative counts across different
supports are descriptive, not a basis-invariant measure of frustration.

The three prespecified sensitivity contrasts concern h32 matched-noise full
rewrite, scattered injury: magnitude permutation minus untouched; isolated signs
minus anchored switching; edge deletion (arm 7) minus untouched. Use 10000 paired
whole-block bootstrap resamples and two-sided 98.333333% intervals (Bonferroni
family of three). Label loss exceeding five points only if upper bound < -.05;
loss bounded within five points if lower bound > -.05; otherwise unresolved.
These are follow-up sensitivity estimates on the reused cohort, not a fresh
confirmatory claim or an exclusive competition between mechanisms. Different
intervention doses prevent ranking feature importance by loss magnitude alone.

Secondary 95% pointwise intervals cover every history/injury, equalization,
repair-target minus matched-other deletion, and each policy-by-intervention
difference-in-differences separately for the two rebuilding noise histories.
Report signed transfer and coupling change beside function. Generic sensitivity
alone does not establish the cause of the rewriting advantage; policy interaction
is informative but not proof of a unique mechanism. Repair exposure/matching and
changes in reachability qualify the targeted comparison.

Before interpreting sensitivity, require exact restoration equivalence, unchanged
scale support, and maximum aligned normalized-coupling error <= 1e-12 for scale
and switching. Record terminal/output discrepancies. If scale or anchored-switch
output discrepancies exceed 1e-8, suppress mechanistic classifications and flag
the numerical control failure. Finite arithmetic is not assumed byte symmetric.
Independent audit reconstructs all source extractions, interventions, graph and
coupling diagnostics, fresh-reader trajectories, scores and statistical summaries.

## Execution

Freeze code and source receipts before the retained fixture/benchmark. E051's
completed audit and closeout, source file hashes, technical checks and independent
replays must pass before launch. Benchmark forecasts time and space; use a detached
scientific workflow, unique local logs/PID/status, at most eight single-thread
workers and <=12 total shared CPUs. Preparation uses one worker while E053 runs.
No polling, restart, or automatic successor. All writes remain in this tree.
One-read–rewrite–read repairability and stressed readers are later experiments.
