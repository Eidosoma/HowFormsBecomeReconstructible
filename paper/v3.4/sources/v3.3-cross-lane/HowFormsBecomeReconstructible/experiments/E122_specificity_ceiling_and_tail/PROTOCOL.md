# E122 — protected-copy specificity and the long renewal tail

2 November 2026. Freeze before any new scientific protected-foreign read or
continuation. The 64 E014 blocks 12000–12063 are a known cohort: all four founders,
two recipients, formation failures and both budgets remain. New horizons are a
prospective continuation of those records, not a new formation confirmation.
E119–E121 are complete. This study is next under the user's priority instruction.

## Apparatus and interventions

Retain the E001/E006/E014 unprescribed 16×16 sheet equations, 300-step reading,
1,000-step writing, float64 fields, and 128-byte/factor-4 and 2,048-byte/factor-1
codecs. Continue the exact outgoing-after-16 own and cyclic-foreign packets
through generations 17–256, transmitting every outgoing record without selection.
Use the original `block+1000000`, `gN` birth/read/write streams. Shared nuisance
draws across arms and budgets remain. No guide, teacher, extra injury or new
initial source is introduced.

The four assessment routes are renewed own, renewed foreign, protected own
acquisition, and protected foreign acquisition. Foreign donor is `(founder+1)%4`
within the same background; every route is scored against the recipient's own
founder prototype. Foreign protected bytes are supplied to that recipient's
draws, not substituted by relabeling another recipient's existing observation.

Checkpoints are 1, 3, 8, 16, 32, 64, 128 and 256. Early own/foreign/protected-own
states must reproduce the archive exactly. Every probe uses the original
`terminal` stream, independent of renewal, with no feedback or outgoing write.
Protected bytes and their readouts are identical across horizons. This does not
create new independent protected observations. Two renewal slots replace the
ten-slot legacy panel only after exact projection checks on the excluded fixture.

## Scores, primary estimate and uncertainty

Qualified agreement Q is the fraction of all 256 cells whose sign (`v>0`) matches
the own prototype and whose amplitude strictly exceeds .2. Sign-only agreement,
amplitude qualification, and all four sign×amplitude categories remain separate.
Save counts against all four candidate prototypes, own-versus-foreign cell gains
and losses, all individual observations and within-source distributions.
Prototypes are evaluation resources, not inputs to the supplied writer.

Average the eight founder/recipient observations within each block. The renewed
gap is N(g)=Q_own(g)−Q_foreign(g); the protected gap is D=Q_protected_own−
Q_protected_foreign. Normalized specificity is **mean(N)/mean(D)**, not the mean
of record-level ratios. The primary estimate is the qualified ratio for **128
bytes after 256 rewrites**, accompanied by its raw N and D and all four absolute
agreement curves. Report whether N and D have positive lower 95% bounds and
whether the Fieller set is bounded; do not replace these with a favorable
secondary checkpoint or the other budget. Other horizons, budgets and sign-only
normalization are explicit secondary estimates. Amplitude is not renamed identity.

Use 10,000 whole-block paired bootstrap resamples, common across budgets,
checkpoints, numerator and denominator. Report pointwise 95% intervals, paired
between-budget contrasts, and the complete per-block values. Use Student-t
Fieller sets for the ratio of the paired means (63 degrees of freedom), with
its joint-normal approximation stated. Preserve bounded, two-ray, half-line,
all-real and empty sets. Roundoff-only correction of a near-zero discriminant
does not alter the denominator. No epsilon division or [0,1] clipping. Save all
bootstrap numerators, denominators and ratios, including nonfinite draws; if a
nonfinite ratio occurs, report the percentile interval unavailable rather than
drop that draw. Report zero and negative denominator counts.

Protected copying is an operational reference under this apparatus and cohort,
not a proven maximal capacity or a number of historical bits.

## Tail models and direct late-change test

Fit raw qualified N(g) by equal-weight squared error across checkpoints. Models:
`C+A*exp(-g/tau)`, `A*exp(-g/tau)`, and `A*(1+g/tau)^(-p)`. C is signed and bounded
to [−1,1]; A is signed and bounded to [−2,2]. Tau spans .25–65,536 generations.
Use a fixed 257-point geometric tau grid for exponentials; the power grid has
129 tau values and 65 geometric p values spanning 1/32–8. Conditional linear
coefficients are solved with exact box-constrained profile least squares.
Take the global minimum on the declared grid, resolving exact ties by grid
order. This inspectable finite search replaces local multistart optimization;
its discretization and boundary fits remain explicit.

Fit through 64 and predict 128/256 before fitting all checkpoints for descriptive
parameter estimates. Report late-horizon mean-squared prediction error and
plateau-minus-each-zero-asymptote error differences. Negative differences favor
the plateau model's prediction; they do not prove an asymptote. These are held-out
times from the same sources, not an independent decoder or tissue test. Refit
models on the first 2,000 of the same paired block resamples. Retain every fit,
boundary count, parameter interval, residual and model-conditional C/D ratio.
Nonfinite or failed computations stop with retained diagnostics; do not drop
replicates or choose a different fit window. Weakly identified or boundary tau/p
must be visible even when a fitted C interval is positive.

Directly estimate N(256)−N(128). Define practical late equivalence as its whole-
block 95% interval lying strictly inside **±0.25 percentage points**. This is
less than one cell's 1/256 contribution to an individual agreement score and
about 18% of the previously observed 1.39-point compact gap. It was selected
before new outcomes; it is not widened after seeing the data. Report both budgets
separately. No nonsignificant decline becomes a plateau claim. Finite-horizon
retention or model fit cannot establish indefinite memory, multiple basins or
exclusion of very slow mixing/metastability.

## Verification, exports and bounded cost

Verify all 192 scientific raw archives against E014's original completion hashes;
keep the original files unchanged. Technical source 900014 is excluded from
scientific inference. Reproduce its first three generations, generation 16 and
checkpoint readers at both budgets. Independently coded indexed-stencil replay
checks new generations **17, 32, 64, 128 and 256** and **every checkpoint reader**
in every source. All boundaries are continuous and retained, but exhaustive
stepwise replay of the other generations is not claimed. Recount sign/amplitude
categories independently and verify sums versus block estimates.

Retain compact boundary packets and per-lineage counts throughout. Retain native
float64 recipient and actual writer states at all eight checkpoints, original
prototypes/background, masks/births, source/donor mappings outside decoder arrays,
per-file hashes and schema. E123 reuses this export after its own analysis freeze;
no identity decoder is fitted here and no duplicate simulations are requested.

Benchmark one complete excluded block at both budgets through 256, including
selected replay, all checkpoints, storage and the full fitting budget. For
statistical timing only, replicate that block's summary to 64 rows; mark this
technical replication and never treat it as 64 independent sources. Estimate
science runtime from measured per-block dynamics and actual analysis cost,
using a conservative threefold allowance, and check disk reserve. At most four
workers, one numerical thread each, within the shared twelve-CPU ceiling.
Jobs over ten minutes run detached with frozen inputs, PID/log and durable
status, one bounded startup check, then user-triggered status only. No automatic
restart, additional horizon, outcome-based sample extension or successor.
The manuscript hold remains in effect.
