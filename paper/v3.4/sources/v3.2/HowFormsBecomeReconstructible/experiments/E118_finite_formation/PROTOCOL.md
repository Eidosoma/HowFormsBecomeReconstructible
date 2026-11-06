# E118 — acquisition and renewal under finite rules throughout

Authorised 31 October 2026 after E117. Freeze after excluded qualification and
before any new scientific acquisition. No E112/E116 scientific packet enters
this experiment. Use 32 untouched source IDs 1180000–1180031, four founders,
four recipients, native/mixture × sham/pulse, and two terminal injury draws.
Keep every case, including empty repair selections and delivered no-ops.

Compare five fixed formulations: original T0F0Q0, tolerance-only T1F0Q0,
floor-only T0F1Q0, grid-only T0F0Q1, and combined T1F1Q1. This deliberately
omits the three two-factor ancestry branches to limit cost; it identifies
single changes and the combined formulation, not a full factorial decomposition.
T is abs(d_i*d_j)<=1e-4 versus exact zero; F is max(D,1e-4) for positive D,
with zero drive for D=0; Q is the 2^-16 ties-to-even storage grid versus identity.
Keep float64 arithmetic, paired cue resets/noise in renewal, dt .2, noise .02,
birth SD .05, beta 3, strict per-cue success margin >.25 and final 32 observations.

## Acquisition and record-write inventory

E016's consistent teaching runs on a fixed unit scaffold, uses fixed-four
normalization, and averages ordinary coactivity over the final 128 of 512
teaching steps in each cue episode. Learned weights never feed back into
teaching. There is no cue-product fallback or natural-strength denominator
in that phase. Therefore T and F have no acquisition operator to change; Q
acts on the first completed acquired record. The unit scaffold is exactly on
the finite grid. Accumulation/scoring arithmetic remains float64, and no
uncommitted coactivity average is reused as a weight before this first channel.
Do not replace teaching with a different learning rule to create a T effect.

Each formulation starts from its own channel-applied acquired packet. Generate
32 renewal boundaries with its own floor, tolerance and storage channel;
then its own E055 sham/pulse body and immediate post-pulse capture, three E058
continuations, native/mixture construction, one E077 recovery rewrite, pruning,
one further E077 rewrite, and both fresh-reader draws. Retain the original
stream namespaces and schedules, sharing nuisance draws across formulations.
E055 body noise is the original independent-per-cue body noise; renewal and
terminal noise remain paired. No independent-noise writer arm is added.

The mixture takes magnitudes from that formulation's own immediate post-pulse
packet on support shared with its own three-continuation descendant, preserving
the descendant's signs. Other edges use the descendant. Apply the channel to
the constructed packet too (an exact idempotence check on grid-valued inputs).
No ideal-history packet, magnitude donor, or repair enters a finite lineage.
Store every capture before and after its channel separately. Physical injury
remains separate from storage erasure and floor attenuation.

The 128-step holding periods after a capture have no dependency path to the
transmitted record or next freshly reset body; omit them, as in E116. Preserve
capture times and verify reference capture/read fields against the excluded
legacy archive. There is no horizon extension.

## Pruning policy and estimand

For each formulation, tag recovery edges whose incoming stored weight is zero,
whose pre-channel capture is nonzero, and whose own tolerance rule selected
ordinary fallback. Fix these tags before observing any terminal outcome and
before the recovery output channel. Prune those coordinates once from the
delivered recovery packet. Retain tags whose delivered value is zero as no-ops.
Keep the exact outside bytes, positive pruning zeros, empty selections, tag
counts, delivered counts, and tag overlap/difference with the reference.

Primary effects compare each formulation's own repair-pruning policy. Finite
and reference pruned endpoints can therefore remove different coordinates.
Their retention contrast estimates the complete formulation-plus-policy
change, not an effect of finite numerics on identical edge interventions.
No common-coordinate claim is made. This choice keeps the finite branch
independent of reference history; it cannot be changed after observing outcomes.

Native terminal readers use the formulation's floor. Also read the outgoing
floor-positive packets with a zero-floor common reader and identical nuisance
draws; identical floor-zero calls are shared, not additional evidence. These
readers do not undo earlier rounding or altered ancestry. Terminal readers
and the one pruning writer use 2,048 steps, 1,024 settling, in science.

## Fixed outcomes and inference

The sole primary is the combined formulation in pooled mixture contexts.
Keep E116's ten requirements unchanged: lower 95% bound for P0−I0 >0;
upper bound for P1−I1 <0; each I0/P0/I1/P1 lower success bound >.50;
each finite-minus-matched-reference endpoint lower bound >−.05. The 50%
threshold is operational usefulness, not chance. All ten must pass; a boundary
touch is unresolved. A failed joint claim is not evidence that all finite
formation is impossible. Native records, separate numerical changes, histories,
injuries and common readers remain secondary, with no substituted primary.

Use 10,000 paired whole-source resamples, E118 seed in plan.py; 32 sources are
independent units. Keep continuous margins, signed/aligned transfer, all four
absolute endpoints, both common endpoints, complete immediate/later event
tables, finite-reference harms, and every unchanged case. Report pointwise
95% intervals without claiming simultaneous coverage. No interim significance
test, outcome-based replacement, sample extension or automatic successor.

## Checks, runtime and storage

Check the fresh-ID registry before any scientific generation. Independently
replay teaching, every ancestry/pulse/continuation body and every new pruning
writer/reader; compare every step hash and terminal/capture fields. Use
independent grid, tolerance and normalization equations, with known-answer
tests. Verify baseline projections against excluded legacy source 9000980;
all archived files must have matching completion hashes. Excluded IDs
9000980/9000981 are technical evidence only and cannot enter inference.

Benchmark the full five-condition path at all four recipients and all 32
ancestry boundaries, with 128-step reads and 8-step pulse. Scale each measured
stage to the 2,048-step scientific schedule, including independent replay,
serialization and summary allowance. Use at most four workers and twelve shared
CPUs, numerical threads one. Price the full cohort before freezing; a threefold
conservative allowance must fit 48 hours, and disk reserve must be available.
This is a resource ceiling, not intended runtime or permission to extend work.
If too costly, preserve the benchmark and revise the design before science.
Detach forecasts over 600 seconds with durable receipts and one bounded startup
check, then await user-triggered status. Do not tune levels or sample size from
scientific outcomes. No overwrite or automatic restart.
