# E053 — fresh confirmation under combined numerical stresses

Authorized on 10 October 2026: “lets go,” following E052's completed result.
E051 and E052 outcomes have been seen. Independent rebuilding cue noise is a
lead selected from those results; this is a new held-out test, not a revision
of E052's failed primary. All settings below are fixed before new trajectories.

## Question and design

Does the original full bridge writer with independent cue noise retain useful
rebuilding when arithmetic precision, record resolution, record corruption and
normalization limits act together?

Use 32 fresh blocks **36000–36031**, four founders and four recipients per block:
**512 lineages per condition**. All lineages enter all conditions, including
acquisition failures. No prior scientific cases are pooled. Prior E-series run
manifests and selected E052 receipts are hashed in SOURCE_DATA.json; block IDs
must be disjoint. Block 900041 supplies excluded fixture/benchmark trajectories;
synthetic channel checks have no scientific observations.

Cross matched versus independent **rebuilding cue noise** (rho=1 or 0) with ten
numerical regimes, giving **20 condition histories** per lineage:

| Regime | Grid Q | Record noise N | Floor F | Arithmetic A |
| --- | --- | --- | --- | --- |
| reference | — | — | — | float64 |
| grid_2m16 | 2^-16 | — | — | float64 |
| record_noise_1e4 | — | SD 1e-4 | — | float64 |
| floor_1e4 | — | — | 1e-4 | float64 |
| grid_noise | 2^-16 | SD 1e-4 | — | float64 |
| grid_floor | 2^-16 | — | 1e-4 | float64 |
| noise_floor | — | SD 1e-4 | 1e-4 | float64 |
| grid_noise_floor | 2^-16 | SD 1e-4 | 1e-4 | float64 |
| arithmetic32 | — | — | — | float32 |
| combined32 | 2^-16 | SD 1e-4 | 1e-4 | float32 |

Q/N/F form a complete 2x2x2 factorial design. Arithmetic is tested only at the
unstressed baseline and under all three stresses; this is not a full four-factor
design. The numerical levels are E052's primary levels, in dimensionless model
units. They are not biological calibrations. The writer is never selected or
tuned using these new outcomes.

## Fixed apparatus and composed channel

Retain E052's 16x16 tissue, teaching 512/capture 128, rebuilding 2048/settling
1024, holding 128, observation 32, dt .2, activity noise .02, birth SD .05,
gain 2, beta 3, 24 absent non-port cells per rebuild and strict margin >.25.
Repeat 32 damaged rebuilds. Initial activities remain identical across cues.
Teaching and terminal-assay cue randomness remain paired. Teaching and holding
remain float64. Capture precedes holding; holding cannot change the record.

The fixed writer transforms activity x=tanh(3v), forms d=(x+−x−)/2 and q=d_i*d_j,
and writes q except when q==0, when it writes ordinary coactivity. It replaces
every available weight and zeros physically unavailable edges. There is no
preservation threshold or tolerance fallback.

Each condition passes its own record through the following channel **once** at
acquisition and once after each capture: **33 applications** total. Final assays
receive the already processed record and never apply the channel again.

1. On physically available weights that are nonzero in the pre-channel packet,
   add Gaussian noise of the declared SD and clip to [-1,1]. Exact zeros and
   physical erasures are protected. Perturb each undirected reciprocal edge once.
2. If Q is enabled, round the resulting values to multiples of 2^-16, using
   nearest, ties-to-even rounding. This may erase values, including newly
   corrupted small values.
3. If A is enabled, round the result to float32 and expand it exactly into the
   common float64 packet container. Reading and capture then compute in float32.

Noise before rounding makes the transmitted combined record stay on the grid.
Noise after rounding is a different apparatus, outside this test. There is no
channel route to create edges from pre-channel exact zeros. The chosen nonzero
support can differ between diverging condition histories; this is part of the
declared channel. Gaussian draws are shared between conditions, independent of
activity noise. Retain E052's `rng('E052', block, 'record_noise', generation)`
namespace so excluded single-stress histories can reproduce it exactly; fresh
block IDs supply fresh scientific streams. Birth/update/innovation/injury streams
retain the E051/E052 definitions and paired-founder convention.

Float32 calculation uses typed activity, weights, constants, denominators,
neighbor sums, drift, transformed activity and writer products. Unit Gaussian
pair construction remains float64 and is cast before typed scaling. Offline
port means and scoring remain float64 and never feed back into dynamics.
Keep the common 4096-byte packet container; no compression claim is made.

After physical injury, recompute D=sum(abs(surviving incoming weights)). Use
N/max(D,epsilon) for D>0 and explicit zero drive for D=0. For combined32,
epsilon=1e-4 is represented in float32. The native terminal reader uses the
same arithmetic and floor; the common reader uses float64 and zero floor.
Both readers receive the same processed record. A difference between them
locates a final-reader effect; equality does not prove irreversible information
loss. Record-only native/common readers are identical and deduplicated.

## Outcomes and inference

Assay h0,8,16,24,32 under intact, scattered-24 and square-9 injury, with paired
cues and initial activity as in E052. Score both cue episodes correctly only
when each strict output margin exceeds .25. Include erased-record controls for
all four distinct readers and one unmodified-acquisition reference at h0.
There are 36 unique panels per later horizon and 37 at h0. Neither source
success nor intermediate performance filters cases or changes the run length.

The **primary endpoint** is h32 native-reader scattered-injury both-cue success
under **independent rebuilding cue noise**, comparing combined32 with reference.
Resample the **32 independent blocks**, retaining all paired histories within
each block. Use 10,000 common bootstrap draws from
`rng('E053', 'bootstrap', 'combined_numerical_confirmation')`, with percentile
95% intervals. The lineages and condition histories are not independent units.

Three requirements must all pass, using strict inequalities:

- Reference success lower 95% bound >.75.
- Combined32 success lower 95% bound >.75.
- Combined32 minus reference lower 95% bound >−.05.

The joint label is COMBINED_NUMERICAL_ROBUSTNESS_ESTABLISHED only if all three
pass; otherwise COMBINED_NUMERICAL_ROBUSTNESS_NOT_ESTABLISHED. Classify a loss
exceeding five points only if the difference's upper 95% bound <−.05. Failure
to establish noninferiority is not by itself evidence of that loss. Technical
runs have null decisions and null gates. There is no optional stopping.

All other endpoints and intervals are **pointwise secondary**: other regimes,
matched-noise control, native/common differences, earlier horizons, injury forms,
pairing effects and differences in stress effects between pairings. At h32
scattered success, estimate QxN, QxF and NxF interactions with the third factor
absent, and QxNxF by the standard eight-cell alternating sum. Estimate the
additional arithmetic effect combined32−grid_noise_floor, and its difference
from arithmetic32−reference. Compute each from block contrasts before inference.
Do not promote a winning secondary comparison into the primary.

## Evidence, verification and execution

Retain acquired, pre-channel and transmitted packets; full body end fields;
injury and birth arrays; denominators and attenuation; repair tags and their
next-body survival/relative strength; channel and writer counts; port means;
all case scores; and hashes of every intermediate array and holding state.
Noise-stage and grid-stage packets are independently replayed against their
hashes. Additional counts separate grid-induced and precision-induced zeroing.
Those counts concern the indicated channel stage; total lost-nonzero counts
compare the pre-channel packet to the transmitted one.

Carry forward E052's diagnostics and their conventions: live non-input cells,
positive-denominator bins, pre-channel writer repair distinct from channel
changes, and zero for conditional ratios with no exposure, with raw exposures
retained. Channels average over 33 applications; body diagnostics over 32;
legacy returning-edge ratios use g2–32. These are descriptive mechanisms, not
proof that a particular edge type causes success or failure.

Freeze 25 scientific inputs before checks. The production code and independent
auditor are separately adapted from audited E052; the auditor imports older
auditors and declarative metadata, never E053 production dynamics. Require
equation/channel/order/precision/inference checks, complete excluded fixture
and benchmark replays, and byte-exact agreement of **ten** E052 single-stress
histories at all 32 boundaries and both terminal reader types. Inspect figures.
All failures remain retained and require versioned retries.

Benchmark before scientific execution. Conservative runtime is three times
simulation plus audit worker time, multiplied by 16 for full reading, four for
recipients and ceil(32/workers) batches, plus 120 seconds. Reserve 1.5 times
benchmark run bytes times four recipients times 32 blocks, plus 128 MiB.
At most eight one-thread workers, within the shared 12-CPU budget. Runs forecast
above 600 seconds detach with frozen inputs, local PID/log and durable status.
One bounded startup check; subsequent status checks only on user request.
No automatic restart or successor. All writes stay in this experiments tree.

This tests finite robustness of the declared apparatus. Independently noisy
teaching/terminal assays, imperfect resets in combination, other stress orders
or strengths, optimized writers, a longer horizon and indefinite heredity remain
outside its scope. Full end fields permit later exploratory m/d analyses, but
those are not new primary mechanism claims here.
