# TT016 prospective serial durability validation

Test whether the fixed conventional repair improves uninterrupted function under
independent ongoing cue noise by more than five percentage points over no repair.
TT015 supplies exposed development evidence: a 9.375-point mean advantage on 16
blocks, with pooled within-history block SD 0.07439. TT014 separately validated
one reconstruction. Neither cohort enters this new serial validation.

Generate exactly 64 new blocks, IDs 16000000–16000063, in namespace
TT016_serial_durability_v1. Assign the four existing histories cyclically, 16
independent blocks per history. Each has four paired founders and four recipients,
giving 16 records per block and 1,024 records overall. The accessible metadata
search and excluded fixture 16000999 are recorded in RESERVATION.json. Search
coverage is bounded and does not provide independent custody or technical
blinding in this shared workspace.

Keep qualified native consistent teaching (512 steps, final 128 captured) and
14 preliminary rebuilds, with the same four exact/tolerance writer schedules:
no tolerance; generation 3 only; 3,5,7,9,11,13; and 3,9,10,11,12,13. Tolerance is
1e-4; every history uses the exact writer at generation 14. Keep the lattice,
ports, 24 missing non-port cells per rebuild, dt .2, noise .02, birth SD .05,
writer beta 3, 2,048 reader steps and 1,024 settling steps. Discarded holding
states remain omitted because their random stream does not carry forward.
This evaluates record succession rather than uninterrupted bodily continuity.

Enroll every generation-14 outgoing record without outcome eligibility or
replacement. Commit all enrolled packets, initial pass labels and prior masks
before starting continuation. Fork each into eight policies: no repair, one-time
repair at generation 15, repeated repair, and repeated shuffled-sign repair,
each under ongoing cue-noise correlations 1 and 0. The .999 regime from TT015 is
omitted prospectively to prioritize the independent-noise mechanism controls.
Teaching and birth/reset noise remain matched. Injuries and original forcing are
paired across policies; founder pairs remain paired. Use the native E022 RNG key
with identity TT016_serial_durability_v1_continuation:<block>, plus the separate
fixed innovation namespace in plan.json. Preserve the unused birth innovation
and native unused square-injury draws. The exact rho=1 path copies the original
noise; rho=0 uses its independent innovation for the second cue episode.

Continue every branch through generations 15–32, even after failure. Repair only
the current incoming body-written record. Use unchanged qualified recipient
completion and optimizer options (16 starts, 64 sweeps maximum, fixed seed
2026101004). Infer missing signs from O and fixed input pins, fill exactly zero
edges with the median absolute nonzero O magnitude, preserve all nonzero edges,
and leave an empty record empty. Incoming protected histories and injury labels
are unavailable to the repair. Independently check all nine optimizer outputs
with the separate Prim solver and reconstruct the completion. Shuffle inferred
signs on each shuffled branch's own missing edges, retaining support, magnitude
and sign counts. Shuffle keys include block, generation, founder and recipient,
and are paired across noise regimes. Do not discard unchanged shuffles. After
each reconstruction, only that branch's actual exact-writer output crosses the
next boundary. One-time and repeated preparations and outcomes must agree at
generation 15 within each regime.

The single primary outcome is passing the intended task at every one of the
18 continuation reconstructions. Success at one reconstruction is the strict
minimum signed margin >.25 over both cues and output ports, averaged over the
last 32 reader observations. Score the opposite task independently. A failure
followed by recovery does not pass the primary. Average the 16 paired record
differences (repeated minus baseline) within each independent-noise block, then
average the four equally weighted history strata. The inferential unit is the
block, not a record, cue, generation or noise draw.

Practical success requires the one-sided 95% stratified Welch-Satterthwaite lower
bound for that primary contrast to exceed .05 strictly. Five additional
uninterrupted lineages per hundred over the whole horizon is the chosen
operational benefit required for recurring intervention; it is not a universal
biological threshold. Fix this before any new test outcomes. For each stratum,
v_h=s_h^2/16, V=sum(v_h)/16 and df=(sum(v_h))^2/sum(v_h^2/15). If variance is zero,
use the conservative Hoeffding bound for 64 independent [-1,1] block contrasts.
An upper one-sided bound strictly below .05 yields practical superiority
unsupported; an unmet lower gate otherwise yields inconclusive. This approximate
block inference is independently checked with integer sums/squares and a
separate quantile function. Report two-sided bounds and 20,000 stratified
bootstrap draws descriptively. No secondary, subgroup or terminal result can
replace the primary; no equivalence or noninferiority claim is specified.

Sixty-four blocks are a fixed precision and resource choice. Retain prospective
power sensitivity across effects .07, .09375 and .12 and block SDs .075, .10,
.15, .20 and .25, using conservative reference df=15. Development effect and
variance estimates are uncertain; this is not a power guarantee. Do not resize,
extend the horizon, stop early, replace blocks or tune the repair using new
outcomes. There is no interim aggregate scientific analysis.

Secondary results include every policy's uninterrupted and terminal success,
recovery, mean cycle success, initial successful run, opposite-task success,
generation curves, all four histories and initially passing/failing strata.
Report paired repeated-minus-baseline, one-time-minus-baseline,
repeated-minus-one-time and repeated-minus-shuffled contrasts in each noise
regime; cross-regime changes for all four policies and the change in the repair
advantage are descriptive. Bootstrap intervals receive no multiplicity-adjusted
confirmatory interpretation. Retain empty strata as undefined rates. Report all
resource, forcing and writer-fallback diagnostics without causal mediation
claims. Equal allocated bytes or reader steps do not make longitudinal policies
equal in total computation or added edge weight.

Every teaching, preliminary rebuild and continuation receives full independent
native replay. Production uses the qualified published acquisition/lineage code
and roll-based continuation equations; replay uses the qualified indexed-neighbor
core and flat writer. Their common mathematical specification and retained
source ancestry are explicit. All native arrays require byte identity. Audit
all 75,776 optimizer calls and 147,456 continuation records; verify all 14,336
preliminary rebuild contexts and 147,456 continuation contexts. Reconstruct all
injuries, captures, branch handoffs, noise moments and fallback diagnostics.
Independently score every raw 32-observation window with scalar compensated sums
(means/margins within 1e-12, flags exact), all tables and all summary/gate decisions.
Noise moments require byte equality. Scalar added-weight sums use the prior
bound of eight epsilon times absolute sum plus four least subnormal units.
Preserve all raw packets, bodies, windows, optimizer fields and resource evidence.

Freeze the full executable registration before qualification and before any test
cohort generation. Qualify known retained teaching, exact/tolerance/post-pulse
rebuilds, and previously audited full-size continuation states. Test changed
eight-policy schedules, own-successor continuity, exact matched-noise behavior,
all-zero records, strict threshold edges, empty strata, positive/negative and
zero-variance decisions, and deliberate corruptions. Include a failed
uninterrupted primary with favorable terminal and subgroup results. Fixture
identities and known development records never enter the test cohort.

Benchmark complete known teaching/replay, three known preliminary renewals, all
initial-generation repair calls and two full eight-policy continuation reads with
independent replay. Forecast 1.5*64*(teaching + 14*maximum preliminary rebuild +
18*(maximum full checked repair + maximum full continuation with replay)) + 600
seconds. Include scalar scoring, resource checks and retained-file writes in the
measured stages. Require the forecast below 24 hours and a scaled storage estimate
plus a 1 GiB reserve. Qualification has a 600-second foreground ceiling. Do not
reduce the design if a gate fails; preserve the failure and report it.

Use one numerical worker and one library thread within the shared 12-CPU limit.
Detach the long validation with closed stdin, frozen input copies, unique log/PID
and durable RUNNING/COMPLETE/FAILED. One startup check, then scientific status only
at the user's request. If capacity is full, a detached admission process may
check CPU capacity alone before launching this one registered study. No automatic
successor, scientific retry or scope change. Complete scoring and reporting run
automatically after all fixed blocks pass technical verification.

A positive result would validate serial benefit of this supplied conventional
repair within the same simulator and apparatus. It would not establish autonomy,
external replication, transfer or a prediction unique to RDT.
