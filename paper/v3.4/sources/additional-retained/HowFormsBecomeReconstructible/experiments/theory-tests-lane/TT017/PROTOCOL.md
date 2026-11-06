# TT017 prospective birth reset pairing validation

Test whether the fixed conventional repair improves uninterrupted function by
more than five percentage points over no repair when cue episodes have independent
birth/reset states as well as independent ongoing noise. TT016 supplies exposed
design information: with matched resets and independent ongoing noise, its gain
was .123046875 on 64 blocks, with pooled within-history block SD .1036053. The new
reset condition may have a different effect and variance. No prior lineage enters
the new cohort. Passing this primary establishes benefit in the independent-reset
condition; it does not establish equivalence between reset regimes.

Generate exactly 64 new blocks, 17000000–17000063, in namespace
TT017_reset_pairing_v1. Assign the four existing histories cyclically, 16 blocks
per history. Four paired founders and four recipients give 16 records per block
and 1,024 records overall. The bounded metadata identity search and excluded fixture
17000999 are recorded in RESERVATION.json. This search provides no independent
custody, programme-wide exposure guarantee or technical blinding.

Keep native consistent teaching (512 steps, final 128 captured) and 14 preliminary
rebuilds unchanged, with matched teaching, reset and ongoing cue randomness.
The histories use tolerance 1e-4 at no generations; generation 3; generations
3,5,7,9,11,13; or generations 3,9,10,11,12,13. Generation 14 always uses the exact
writer. Preserve the lattice, ports, 24 missing non-port cells per rebuild, dt .2,
noise .02, birth SD .05, writer beta 3, 2,048 reader steps and 1,024 settling steps.
Discarded holding states remain omitted because their random stream does not
carry forward. The endpoint concerns record succession across rebuilding.

Enroll every generation-14 outgoing record, including failures, without replacement
or outcome-based eligibility. Seal packets, initial pass labels and prior injury
masks before continuation. Fork each record into eight policies: no repair,
one-time repair at generation 15, repeated repair at every generation, and repeated
shuffled-sign repair, each under matched or independent cue resets. Only reset
pairing changes between these two regimes. All eight policies receive independent
ongoing cue noise. Acquisition and preliminary histories remain fixed by design;
the intervention starts at generation 15 and repeats through generation 32.

At each continuation, draw standard Gaussian arrays z and e of native shape
(2,4,16,16) from the original and innovation streams. The first cue starts from
.05*z in both reset regimes. The second cue starts from .05*z in the matched
regime and .05*e in the independent regime. Duplicate paired founders as before.
Then impose the usual injury zeros and input cue pins; retain the unclamped
birth arrays as well as the resulting native trajectories. Sharing the realized
first draw across regimes does not make the two cue resets dependent in the
independent regime. Reset marginals, the injury distribution and noise amplitude
are unchanged. All four repair policies within each reset regime share their
reset and forcing draws, preserving paired policy comparisons.

Use native E022 stream keys with identity
TT017_reset_pairing_v1_continuation:<block> and the separate innovation namespace
in plan.json. Consume one original and one innovation draw for reset before the
reader loop. TT016 discarded the initial innovation; TT017 uses it for independent
reset, preserving the later RNG positions. At every reader step, the first cue
uses the next original draw and the second the next innovation draw under every
policy. Preserve the native unused square-injury draws. This exact stream contract
allows matched-reset branches to reproduce exposed TT016 independent-noise states.
Retain reset and ongoing forcing moments separately, counting original founder
families once rather than counting replicated policies or founders as new draws.

Continue all branches through generations 15–32 after failure, using only their
own actual body-written successor. The unchanged repair reads the current record
O and fixed options, infers signs with 16 starts, at most 64 sweeps and seed
2026101004, and fills exactly zero edges using the median absolute nonzero O weight.
Preserve all observed edges; empty records stay empty. No protected incoming
history, injury label, outcome or future forcing is available to the repair.
Check all nine optimizer outputs with the separate Prim solver and independently
reconstruct every completion. Shuffle inferred signs on each shuffled branch's
own missing edges, preserving support, magnitudes and sign counts. Keys include
block, generation, founder and recipient and are shared across reset regimes.
Retain unchanged shuffles. One-time and repeated preparations and outcomes must
agree at generation 15 within each reset regime.

The single primary is repeated repair minus baseline uninterrupted intended-task
success under independent resets and independent ongoing noise. A reconstruction
passes only if its minimum signed margin is strictly greater than .25 over both
cue episodes and both output ports, using the last 32 reader observations. All
18 reconstructions must pass; terminal recovery cannot undo earlier failure.
Score the opposite task separately. Average the 16 paired record differences
within each block, then average the four equally weighted history strata. Blocks
are the independent inference units, not records, generations, cues or draws.

Practical success requires the one-sided 95% stratified Welch–Satterthwaite lower
bound to exceed .05 strictly. Five additional uninterrupted lineages per hundred
is the retained operational requirement for recurring intervention, not a universal
biological constant. For each stratum, v_h=s_h^2/16, V=sum(v_h)/16 and
df=(sum(v_h))^2/sum(v_h^2/15). At zero variance use the conservative Hoeffding bound
for 64 independent block contrasts bounded in [-1,1]. An upper one-sided bound
strictly below .05 gives practical superiority unsupported; otherwise failure to
meet the lower gate is inconclusive. Student-t coverage is approximate. Check
bounds with integer sums/squares and a separate quantile function. Report two-sided
bounds and 20,000 stratified bootstrap draws descriptively. No subgroup, matched
reset, shuffled or terminal result can rescue a failed primary.

Sixty-four blocks are a fixed precision/resource allocation. Before any test
generation retain power sensitivity at assumed means .07, .10 and .123046875 and
block SDs .075, .10, .15, .20 and .25, with conservative reference df=15. The exposed
TT016 effect and variance are design information from matched resets, not known
parameters for independent resets. There is no power guarantee, interim aggregate
scientific analysis, sample extension, optional stopping, block replacement,
repair tuning or outcome-dependent change of endpoint.

Secondary endpoints are every policy's uninterrupted and terminal success,
recovery, mean cycle success, initial successful run, opposite-task success,
generation curves, history strata and initially passing/failing strata. Report
repeated-minus-baseline, one-time-minus-baseline, repeated-minus-one-time and
repeated-minus-shuffled in each reset regime, all four cross-regime policy changes,
and the change in repair advantage. Bootstrap intervals are descriptive and not
multiplicity-adjusted. There is no equivalence or noninferiority test. Empty strata
have undefined rates. Retain unfavorable terminal or opposite-task findings.
Resource, reset, forcing and writer-fallback diagnostics do not establish causal
mediation. Equal record bytes and reader steps do not imply equal repair work;
shuffled policies match their own inputs while cumulative added weights may differ.

Every teaching, preliminary rebuild and continuation receives full independent
native replay. Production uses the qualified acquisition adapter and roll-based
equations; replay uses indexed-neighbor equations and a flat exact writer.
Their shared mathematical specification and code ancestry are explicit. Reset
construction is implemented separately in production and replay. Require byte
identity for all native arrays, reset moments and ongoing noise moments. Check
all 75,776 optimizer calls, 147,456 constructed continuation records, 14,336
preliminary contexts and 147,456 continuation contexts. Expected scope is 18,624
native array comparisons and 1,152 checks each for reset and ongoing forcing.
Independent scalar compensated sums score every raw observation window, with
means/margins within 1e-12 and flags exact. Check every table, endpoint summary,
interval and decision. Added-weight scalar sums retain the prior eight-epsilon
times absolute sum plus four least-subnormal bound. Save all native states,
packets, masks, raw windows, optimizer diagnostics and resource accounts.

Freeze executable registration before qualification and before test generation.
Qualification uses exposed teaching and preliminary records, a full eight-policy
matched-reset regression against known TT016 independent-noise arrays, and the
excluded fixture. Check native reset draws, unchanged marginals and RNG positions,
independence of ongoing cue noise in every arm, paired interventions, original-cue
identity, own-successor continuity, all-zero records, unchanged shuffles, strict
threshold edges, missing blocks, empty strata, positive/negative/zero-variance
decisions, and deliberate birth/reset/noise/score/interval corruptions. A favorable
terminal, matched-reset or subgroup result must not rescue a failed primary.

Benchmark complete teaching/replay, three known preliminary rebuilds, all initial
repair calls and two full eight-policy continuations with replay. Forecast
1.5*64*(teaching + 14*maximum preliminary time +
18*(complete checked repair time + maximum full continuation time)) + 600 seconds.
Include evidence writes and scalar scoring. Require a forecast below 24 hours
and sufficient storage for the scaled evidence, two input copies and a 1 GiB
reserve. Foreground qualification has a 600-second ceiling. Preserve a failed
gate and report it; do not reduce the design to fit a failed budget gate.

Use one worker and one numerical thread within the shared twelve-CPU limit.
Detach the long validation with closed stdin, unique log/PID, frozen input copies
and durable status. Perform one startup check, then leave it unpolled until the
user asks. Admission may wait on CPU capacity alone. No automatic successor,
scientific retry or scope change. Full scoring and completion reporting follow
all fixed blocks automatically. A positive result concerns this supplied simulator
and fixed repair, with unchanged acquisition and apparatus. It does not establish
autonomy, external replication, apparatus transfer or a prediction unique to RDT.
