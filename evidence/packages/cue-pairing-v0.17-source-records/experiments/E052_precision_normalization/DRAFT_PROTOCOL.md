# E052 — precision, record corruption and strength normalization

**Planning draft, 8 October 2026. Not frozen, implemented or launched.**
Requested scope: plan the robustness study proposed by the second reviewer.
E051 continues under its original protocol. This plan uses no E051 scientific
outcomes to select settings or cases. The operational matrix is [PLAN.json](PLAN.json).

## Question and scope

Does the original full bridge-rewriting mechanism retain useful function when
small recorded values can be rounded, corrupted or attenuated by the reader?
Separate four mechanisms: lower arithmetic precision, coarser record values,
additive record noise and a positive denominator floor. Their interactions with
cue pairing are part of the design; combinations of the numerical challenges
themselves are outside this first study.

Use the original exact-zero writer throughout. Do not adopt whichever E051
writer performs best, add preservation, or tune a new fallback threshold here.
This tests robustness of the specified mechanism, rather than selecting a new
one. A later sign/retention intervention addresses why full rewriting helps.

## Cohort and comparison matrix

Propose 32 fresh blocks **35000–35031**, four founders and four recipients per
block: **512 lineages**. Reserve those IDs in the planning record and recheck
disjointness before freezing. All lineages enter every condition; retain failures
at acquisition and all later times. No prior scientific cases are pooled.

Cross each numerical regime below with rebuilding cue-noise correlation
**1, .999 and 0**. Initial activities remain identical across cues. This gives
**33 matched conditions**, each with its own 32-generation record history.
The independent sample size is 32 blocks, not 16,896 counterfactual histories.

| Regime | Changed component | Proposed setting | Role |
| --- | --- | --- | --- |
| reference | None | Original float64 arithmetic/records, no corruption, zero floor | Reference |
| record32 | Stored precision | Round records to float32; read/write in float64 | Precision control |
| arithmetic32 | Arithmetic beyond record32 | Read/write in float32 and retain float32 record values | Primary challenge |
| grid_2m16 | Stored resolution | Uniform grid spacing 2^-16 | Primary challenge |
| grid_2m12 | Stored resolution | Uniform grid spacing 2^-12 | Secondary stronger challenge |
| record_noise_1e4 | Record noise | Gaussian SD 1e-4 on nonzero available values | Primary challenge |
| record_noise_1e3 | Record noise | Gaussian SD 1e-3 on nonzero available values | Secondary stronger challenge |
| record_noise_leakage_1e4 | Noise support control | Gaussian SD 1e-4 on all available values, including zeros | Secondary creation-of-connections control |
| floor_1e6 | Reader denominator | max(D, 1e-6) | Secondary smaller floor |
| floor_1e4 | Reader denominator | max(D, 1e-4) | Primary challenge |
| floor_1e2 | Reader denominator | max(D, 1e-2) | Secondary larger floor |

These are proposed numerical stress levels in the model's dimensionless units,
not biological calibration. They are selected before inspecting E051 outcomes.
Grid spacing is not a claim of 16-bit or 12-bit encoding over [-1,1]. Float32
retains a wide exponent range, whereas a uniform grid can erase tiny nonzero
values. Both tests are useful and measure different limitations.

The arithmetic32 comparison is deliberately nested: it includes the record32
representation and additionally lowers computation precision. Compare
arithmetic32 with record32 to diagnose the additional arithmetic effect, and
with reference for the total effect. Do not describe it as an independent
arithmetic-only factorial arm.

## Fixed model and procedure

Retain E051's consistent teaching and physical model: 16x16 tissue, four
founders per block, teaching 512/capture 128, rebuilding 2048 with 1024 settling,
holding 128, observe 32, dt 0.2, activity noise 0.02, birth SD 0.05, gain 2, writer beta 3,
24 absent non-port cells per rebuild, and strict output margin >0.25. Source
input ports alone are clamped during rebuilding. Keep teaching and holding
in their original float64 implementation. Capture still precedes holding;
holding cannot revise the captured record.

For every generation, use the following order:

1. Receive that condition's own previously transmitted packet.
2. Apply the current physical injury. Decode weights in the assigned arithmetic
   type, and compute the local absolute-strength sum after injury.
3. Rebuild under the assigned arithmetic and denominator rule, using its fixed
   cue-noise correlation and shared initial activity.
4. Capture the current body with the original exact-zero bridge rule, using
   the assigned arithmetic. Rewrite all available values and zero unavailable
   edges. Record both the pre-channel packet and the body end activity.
5. Complete the unchanged holding phase. Convert float32 end activity to
   float64 for holding where necessary; this conversion has no route back into
   capture or the transmitted packet.
6. Apply the assigned record channel once to the captured packet. Pass that
   same transmitted packet to the next body and any terminal assay at this
   horizon. Never reapply corruption just because a diagnostic assay is run.

Apply the same record channel once to copies of the common acquired packet
before generation 1. Thus there are 33 channel applications: acquisition plus
32 writes. Keep the unmodified acquired packet as provenance and score it once
with the common reader. The h0 per-regime assays measure the post-channel packet;
they can reveal loss before repeated rebuilding begins. No initial-performance
filter changes cohort membership.

## Precision, channel and floor definitions

**Arithmetic.** For arithmetic32, weight operands, activity, constants, neighbor
sums, denominators, drift updates, transformed activity, cue differences,
coactivity and writer branch products use float32. Specify and test primitive
evaluation order; do not merely cast the final packet or allow silent float64
promotion. Generate correlated unit Gaussian draws using the existing float64
stream construction, then cast them to the assigned arithmetic before multiplying
by the typed birth/noise scale. Opposing cues share exact copies at rho=1.
All offline observations, port means, time-window averages, margins and inference
use a common float64 scoring procedure that does not feed back into dynamics.

Keep the canonical 4096-byte float64 packet container in every condition for
compatibility. Float32 record values are rounded first and then represented
exactly in that container. This changes numerical content, not payload size.
It is not a compression experiment. Teaching remains common and unchanged.

**Stored precision/grid.** record32 rounds every transmitted value to float32
at each channel application. Grid regimes use
`Q_delta(w) = delta * round_to_nearest_ties_to_even(w/delta)` with the specified
power-of-two spacing. Arithmetic otherwise remains float64. Preserve exact zero
slots and all physically erased edges. Retain rounding errors and zeroed-edge
counts. The reference path bypasses transformations and must preserve bytes.

**Record noise.** Generate an independent Gaussian draw for each stored
undirected edge, using the paired-founder convention and a new E052 namespace.
For physically available, currently nonzero weights, apply
`clip(w + sigma*z, -1, 1)`. Retain clipping, zero-crossing and sign-change counts.
In the two main noise regimes, exact-zero values and physical erasures remain
zero, isolating corruption of existing values. The separately identified
record_noise_leakage_1e4 control adds the same noise to all physically available
slots, including exact zeros. It tests an additional route for creating
connections; physical erasures still remain zero. Perturb each reciprocal edge
once, not separately at its two endpoints. This draw is independent of activity
noise and shared across comparison conditions where applicable. With sigma=0,
bypass the channel. Compare the two SD 1e-4 support conventions directly, and
count connections created by the channel separately from those created by writing.

**Normalization.** Let `D_i = sum_j abs(w_ij)` after the current injury. For
positive D, use `u_i = sum_j w_ij*v_j / max(D_i, epsilon)`; for D=0 explicitly
set u=0. Recompute D in each body and after assay injury. Do not use D+epsilon,
rescale weights, or change the underlying interaction graph. At epsilon=0,
dispatch to the unchanged reader. Apply the floor in rebuilding and in the
condition's native terminal assay; holding remains unchanged.

## Two complementary terminal assays

At h0,8,16,24,32, test the same already processed record under intact, scattered24
and square9 injuries with both:

- Its **native reader**, using the assigned arithmetic and denominator floor.
- The **common reader**, using original float64 arithmetic and zero floor.

Use matched assay injury and underlying random draws, identical starts/noise
across the two cue episodes, original read/settling duration, and the common
scoring convention. Include erased-record controls for each distinct reader
definition. If native and common readers are identical, compute once and retain
an explicit mapping; do not count duplicated observations as independent.

Native performance is the primary practical outcome. If common reading recovers
performance that native reading loses, the same final record remains usable
under the original decoder. If both fail, the tested common reader also fails;
that alone does not prove irreversible information loss. These assays separate
current expression from changes accumulated in the record history. They do not
isolate every upstream cause of a failed history.

## Prespecified inference to freeze with implementation

Primary endpoint: **h32 native-reader scattered-terminal both-cue success**.
Primary inference concerns **paired rebuilding cues (rho=1)**. The other cue
correlations estimate interaction with the dependency E051 is testing. They
cannot rescue a failed primary and are not selected based on E051's outcome.

For arithmetic32, grid_2m16, record_noise_1e4 and floor_1e4, require both an
absolute success lower 95% bound >.75 and a challenged-minus-reference lower 95%
bound >-.05. Also require the paired reference absolute lower bound >.75.
All **nine requirements** must pass for a joint claim of robustness at these
declared levels under paired cues. Do not generalize that claim to all numerical
levels, unpaired cues or combinations of numerical changes.

Report each estimate even if the joint result fails. A failed noninferiority
requirement is not evidence of a five-point loss. A particular loss exceeds
five points only when that contrast's upper 95% bound is < -.05; otherwise the
comparison can remain unresolved. Individual interval statements are pointwise.

Secondary outcomes include all other regimes, native-versus-common assays,
shorter horizons, intact/square injury, body scores, arithmetic32-minus-record32,
leakage-minus-zero-preserving noise at SD 1e-4, and the pairing interaction for
each challenge c and rho in {.999,0}:

`[Y(c,rho)-Y(reference,rho)] - [Y(c,1)-Y(reference,1)]`.

Resample whole blocks with 10,000 shared draws under
`['E052','bootstrap','precision_normalization']`; use 2.5% and 97.5% quantiles.
There is one joint primary conjunction and no familywise success claim across
the secondary grid. No optional stopping, replacement of failed arms, selected
lineages, increased sample size or threshold changes after scientific outcomes.
All technical scientific-success fields remain null.

## Mechanism observations

Retain raw per-lineage measurements before and after the record channel and
after the next physical injury. In addition to task scores and E051's fallback
and repair measures, record:

- Positive denominator distributions, zero-input counts, and the fraction of
  live non-input cells with 0<D<epsilon. For floor regimes retain D/max(D,epsilon)
  as an attenuation measure, with D=0 reported separately.
- Nonzero weights lost to rounding; absolute channel errors; noise-induced
  sign changes and clipping; and floating-point underflow/subnormal counts at
  defined record/capture stages. Separate arithmetic from channel-created zeros.
- Survival and relative influence of newly repaired connections at the next
  read. A cell returning in the current body has zero inherited incident weights;
  the usefulness of its new connections is tested in subsequent bodies. Carry
  the previous repair tags forward rather than treating current returning-cell
  D=0 as evidence of a denominator-floor effect.
- Full end activity and pre/post-channel records, permitting m/d decomposition
  and signed-interaction analyses. Sampled cue difference under independent noise
  is not automatically a reliable causal cue response.

These measurements explain where a perturbation acts; associations are not
causal mediation claims. No sign-flip/retention intervention is included here.

## Validation, freezing and execution

Before new scientific trajectories, implement the model and independent auditor,
freeze the finalized protocol/code/input index, and run excluded validation:

- The three unchanged reference trajectories (rho 1/.999/0) must reproduce E051's
  excluded fixture and benchmark records/scores at all 32 boundaries and selected
  assays byte exactly. Reuse its stream namespaces with fresh scientific block
  IDs; new record noise has a separate E052 namespace.
- Check actual dtypes and rounding points, precision-sensitive branch selection,
  quantizer ties and error bounds, exact-zero/physical-erasure protection,
  reciprocal-edge updates and clipping. record32 must leave arithmetic float64;
  arithmetic32 must actually compute the reader/writer in float32.
- Verify invariance under safe power-of-two scaling when epsilon=0, attenuation
  below a positive floor, unchanged behavior above it, and explicit zero drive
  for D=0. These are equation tests, not evidence of serial robustness.
- Verify channel timing/counts, shared versus independent streams, native/common
  use of the same transmitted packet, common scoring, correct primary axes,
  strict inequalities, technical exclusion and rejection of corrupted evidence.
- Independently replay teaching, typed dynamics/capture, channel draws, holding,
  assays, diagnostics and every inference summary. Preserve failed attempts.

Use block 900041 only for technical compatibility/throughput; its outcomes cannot
select scientific parameter levels. A new excluded fixture and benchmark must
cover all 33 conditions, all 32 generations and both assay definitions. The
reference E051 fixture is R2, teaching 12/capture 6/observe 4, read 24/settle 12/hold 8;
its benchmark is R1 with original teaching/capture, read 128/settle 64/hold 128.
No new fixture, benchmark or scientific job has been started for this plan.

The implementation should batch float64 and float32 trajectories separately to
prevent array promotion, while preserving matched random draws. Avoid computing
duplicate native/common assays. Benchmark the complete workflow, including
independent replay and retained artifacts, before assigning an ETA or capacity
forecast. Use at most eight workers and one numerical thread per worker, within
the shared ceiling of 12 logical CPUs. Check active allocations before execution; planning
does not reserve cores or schedule a launch when E051 finishes.

Follow RUN_POLICY for >600-second forecasts: detached process, stdin `/dev/null`,
local PID/log, frozen configuration, durable status and one bounded startup
check, then user-requested status only. All writes stay in the experiment tree.
This draft is complete as a planning deliverable; implementation, input freeze,
excluded validation/benchmark, execution preflight and scientific execution
remain subsequent work.
