# E122 planning draft — specificity scale, decay and a possible plateau

**Implementation update, 2 November:** this original planning record is retained.
The [protocol](PROTOCOL.md) now fixes the primary estimate, ±0.25-point late
equivalence margin, Fieller/paired-bootstrap handling and deterministic tail
model grids. Sources are hash-verified and executable checks pass. Full native
benchmark `benchmark_v1` passed in 8m39.69s. Scientific `continuation_v1` launched
at 13:57:30 UTC after qualification and sample freeze, completed at 16:44:25 UTC
and passed verified closeout at 17:22:35 UTC. Both final history gaps are positive
and both late changes meet the frozen equivalence margin; the infinite-horizon
asymptote remains unresolved. See [interpretation](INTERPRETATION.md) and [README](README.md)
for current status; the original planning text below is historical.

1 November 2026. Explicit user request: add this as the high-priority next study.
E119–E121 are already running; E122 precedes the deferred E118 saved-lineage
diagnosis. No E122 dynamics, new protected-foreign reads or fitting have run.
Finalize implementation details and freeze the protocol before new outcomes.

## Existing evidence and question

E014's retained own-history increments are 1.482 → 1.387 percentage points for
128-byte records and 2.103 → 1.402 points for 2,048-byte records, from one to
sixteen completed rewrites. The compact curve also dips at an intermediate
checkpoint. Its unresolved change does not establish equivalence or a plateau.
The primary question is how much of the history distinction accessible under
protected copying survives renewal, and whether later decline remains visible.

All 64 E014 blocks 12000–12063, four founders and two recipient lineages per
founder remain. Keep failed formation and every own/foreign pair. This is a
prospective continuation of a known cohort, not a fresh formation replication.
Keep original heterogeneous formation, public grid, reader, writer, codec,
threshold and same-own-founder scoring. Do not import a new guided writer.

## Four matched routes and the protected reference

For each block, founder, recipient and budget retain:

1. Own-record renewal, carrying its actual body-written descendant.
2. Matched foreign-record renewal, initialized with the next cyclic founder's
   record in the same background, then carrying its own actual descendants.
3. Protected own acquisition bytes, never rewritten.
4. Protected foreign acquisition bytes, never rewritten, with the same foreign
   donor mapping as the renewed foreign arm.

All four are scored against the **same own-founder prototype** in the same
recipient nuisance environment. A protected-foreign observation is not obtained
by casually relabeling another founder's protected-copy observation: that can
change the recipient's draws as well as its record. Supply the foreign bytes to
the intended recipient and preserve matching explicitly.

Prefer continuation from E014's exact outgoing-after-16 packets. Reproduce the
unchanged first three trajectories and after-16 reference as technical checks;
then continue at generation 17 with the original semantic stream numbering.
No restart, restored own donor, survivor selection, or foreign reselection.
Keep protected bytes from the original acquisition, not from generation 16.
The original ten control arms remain in the historical archive; the new long
continuation need only simulate own and foreign renewal. Protected routes need
checkpoint reads, not redundant 1,000-step write simulations. A reduced-slot
implementation must match the corresponding legacy slots exactly before use.

## Normalized specificity and its uncertainty

At budget b and completed-rewrite horizon g, define block-level paired gaps

    N_b(g) = Q_renewed_own(g) − Q_renewed_foreign(g)
    D_b    = Q_protected_own − Q_protected_foreign
    S_b(g) = mean_blocks N_b(g) / mean_blocks D_b.

Q is the original fraction of all 256 cells with the own founder's sign and
|v| > .2. Average founders/recipients within blocks before averaging blocks.
The primary ratio is a **ratio of population means**, not an average of unstable
per-record or per-block ratios. Preserve the raw numerator, denominator and all
four agreement curves in percentage points on the same native scale. Report
the normalized curve alongside them, never in place of them.

Use the same whole-block resamples for numerator, denominator, horizons and
budgets, preserving their covariance. Before qualification, implement and test
Fieller confidence sets for the paired mean ratio and the paired-bootstrap
sensitivity calculation. If the denominator is not separated from zero, report
the resulting unbounded/disjoint or otherwise unstable normalized uncertainty.
Do not drop inconvenient bootstrap denominators, silently divide by an epsilon,
or clip normalized values to [0,1]. Values outside this range are possible.

Protected copying supplies an **operational reference scale under this codec,
reader and cohort**, not a proven maximum information capacity of the format.
Renewal could in principle improve a particular read over protected acquisition
bytes. Consequently the word “ceiling” must not imply an established universal
bound or a number of transmitted bits.

SR001 is in the sibling project at
`WhereDoFormsComeFrom/experiments/multiscale-error-lane/REGISTRATION_SR001.md`.
Its registered score is `(a − max_f a_f) / (1 − .75)`, using three fixed shifted
placements and inversion-invariant agreement. Its denominator is a known
template separation, not an estimated E014 protected-copy contrast. Adopt the
normalization principle while retaining E014's actual score, foreign-founder
design and denominator uncertainty; do not copy the constant .25 into E014.

## Checkpoints and score decomposition

Retain existing checkpoints 1, 3, 8 and 16 and add **32, 64, 128 and 256**.
Use the original independent `terminal` stream, paired across horizons, routes
and budgets. These probes never feed back. Protected probes are therefore
exactly constant across horizons; repeated plotting does not add observations.
Add the protected-foreign reference at the early checkpoints under the same
reader environment so the entire curve has a consistent denominator.

At every checkpoint report:

- All four routes' qualified own-founder agreement.
- Sign agreement alone and amplitude qualification alone.
- The joint sign-match × amplitude-qualified counts, retaining the identity
  that qualified agreement is their intersection.
- Own/foreign raw gaps and protected-relative gaps for qualified agreement
  and sign agreement; amplitude differences are reported without relabeling
  amplitude as founder-specific information.
- Within-pair gains/losses, whole-block distributions, formation status and
  all-target prototype scores, without filtering or counting cells as replicates.

The existing E014 compact count package supplies the early decomposition.
It is not a substitute for the actual outgoing packets needed for continuation.

## Decay and plateau: candidate analysis to freeze before fitting

Fit each budget's raw paired gap across the declared checkpoints, then express
its fitted tail relative to the protected denominator with joint uncertainty.
Start with the requested model

    N(g) = C + A exp(−g / tau),  tau > 0,

alongside a nested zero-plateau exponential and a slow zero-asymptote alternative
(for example `A (1 + g/tau)^(-p)`, p > 0). Do not constrain C to be positive and
then present its positivity as a discovery. Freeze parameter bounds, fitting
loss, multi-start grid, failure handling, and comparison rule before new reads.
Record weakly identified time constants, boundary fits and failed fits; do not
silently discard bootstrap replicates or select a favorable fitting window.

Use paired whole-block resampling of the complete trajectory. Report uncertainty
in C, tau and S(infinity), fitted/residual curves and a held-out late-checkpoint
prediction comparison. A suitable fixed division is fit through 64 and evaluate
128/256, followed by a clearly labeled all-checkpoint parameter estimate.
Nonmonotonic early data may expose model inadequacy; do not force a monotone
story if the residuals disagree. The exponential is an empirical candidate,
not an assumed universal law for every mixing process.

Also report the direct 128→256 gap change and an explicit practical equivalence
test, with the margin chosen and justified before fitting. “No significant
decline” is not the equivalence criterion. Do not let a fitted positive plateau
replace the actual final-horizon contrast and denominator checks.

Even a supported positive tail over 256 rewrites is a **finite-window result**.
Very slow decay or metastability may mimic a plateau. Several persistent basins
would be a further mechanistic hypothesis requiring transition evidence; neither
indefinite memory nor distinct basins follows solely from this curve fit.

## Storage, runtime and qualification

The presence inventory finds all 128 original lineage NPZs (3,227,309,039 bytes)
and 64 source NPZs at `E014_long_renewal/runs/confirmation_v2/`. Before launch,
verify their hashes against the old completion record and pin the exact source
packets, prototypes, codecs and scripts. Preserve the original archive unchanged.

Benchmark a full-width disposable case through the full proposed 256-rewrite
horizon, including auditing, compact serialization and model fitting. Measure
own/foreign dynamics separately from reference reads, then forecast all 64
blocks and both budgets under the available shared CPU budget. No ETA is yet
claimed for E122. If over ten minutes, run detached under the existing policy.

Keep per-lineage scalar/joint-count outcomes, byte hashes and compact boundary
packets throughout, plus full fields at the selected checkpoints. Do not save
all intermediate activity fields or every integration step. Check boundary
continuity, exact protected bytes, legacy projection, observer nonfeedback,
donor/background matching, score identities and byte budgets. Independently
replay selected predetermined lineage segments and every checkpoint reader;
report that scope precisely rather than claiming exhaustive trajectory replay.

No automatic launch behind current jobs. This is the explicitly prioritized
next study; its final protocol, executable tests, benchmark and launch follow
the running reviewer work. No automatic horizon extension beyond 256 or cohort
increase based on the emerging curve.

## Compatible auxiliary identity export, added 1 November

The user queued [E123](../E123_history_identity_audit/PLAN.md) as a separate
retained-data analysis. During E122 implementation, preserve candidate prototypes,
actual historical donor mapping, source/background IDs, packet bytes and the
selected checkpoint/body fields with native dtype, hashes and boundary timing.
Use the common source/prediction-table schema so E123 can consume these outputs
without new trajectories. Keep grouping/target labels separate from decoder
arrays. The four-candidate dictionary is evaluator information, not a native
reader/writer input. This export requirement changes neither E122's scientific
specificity endpoints nor its current planning-only status; fitted decoding
needs a separate post hoc freeze and does not authorize manuscript changes.
