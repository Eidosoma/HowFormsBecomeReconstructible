# D118 — reference content and normalization in renewal

Completed2026-09-14. Post-hoc retained-state mechanism audit, not a new
trajectory experiment or independent confirmation. D117's positive renewal
criterion remains unchanged; L20 stays STRESS_TESTED / MIXED as written.
[Method](../protocols/L20_REFERENCE_PROJECTION_AUDIT_V1.md),
[D117 result](L20_THREE_BOUNDARY_REWRITE_2026-09-13.md).

## Plain-language finding

The pattern is already present in the descendant's newly acquired reference,
R, before rewriting begins. The first write copies a normalized version of
that reference into theta at full strength. Normalization also boosts a
reader-disabled record, but does not give that record the taught pattern.
Content and amplitude therefore have distinct roles in the implemented route.

This is more specific than “three increasingly slow filters did it.” R is
a temporal average by construction. The first post-erasure theta write is
an immediate normalized readout, not a slow buildup of theta amplitude.
Later writing still changes the field. We have not yet established that
the first record alone is sufficient for development in a fresh recipient,
or that the remaining999 writes are dispensable.

## What was checked

All1536 saved first-writing transitions from D117: eight blocks, four paired
lives, two roles, eight conditions, three generations. The192 primary
read–erase–rewrite transitions are a named subset.29 synthetic/source-graph
tests pass0.57s. The existing D117 saved audit passes291 input/19 output
hashes and full in-run replay proofs. No world dynamics, counterfactual
rollout, new parent/reader cohort, parameter search or success gate.

Source equations were traced directly to
[cascade/project_theta](../../writable_landlord/src/writable_landlord/pipeline.py),
[blueprint_step](../../blueprint_web/src/blueprint_web/engine.py) and
[ladder_step](../../ladder_web/src/ladder_web/engine.py). Independently restated
first R/theta updates agree with saved states with maximum error0 across
all1536 transitions.1152 enabled projections preserve field ordering; none
hits the source denominator floor. Positive-lambda cancellation on erased
writes agrees within3.33e−16, primary subset2.22e−16.

## Reference acquisition comes before the first theta write

With rho=.002 and300 reading steps,

`R300 = .998^300 * Rbirth + .002 * sum(.998^(300-t) * Vt, t=1..300)`.

The coefficient on birth reference is0.548482. That is a recurrence weight,
not the percentage of final information attributable to birth. The body-
history term was inferred from the saved endpoints by subtracting the
decayed birth term; it is not an independently recorded full V history.

In the192 primary transitions, mean spatial standard deviations are:
decayed birth component0.108275, accumulated body-history component0.372450,
whole read-end R0.387980. Their covariance prevents adding standard deviations
or treating them as a variance/causal partition. The ratio of the two component
mean standard deviations is3.44, not “77% learned information.”

The accumulated-history target margin is positive in all192 primary rows,
range0.04025–0.19818, mean0.174404. This margin is
mean(field*(own_target-other_target)/2), in field units, not the body
qualification score. The pooled birth margin cancels between paired opposite
scoring roles by construction; it does not prove that every birth has no
chance alignment. Read-off history likewise has no pooled directional margin
by the same role symmetry, not an empirical absence theorem.

## The first write is almost a normalized readout of existing R

The actual sequence is body update, reference update, then theta update:

`R1 = .998*R_before + .002*V1`

`theta1 = project(.001*tanh(R1), spatial_std=.3)` after theta erasure.

Outside the1e−9 denominator floor this equals `project(tanh(R1), .3)`.
The positive lambda scale cancels. It does not cancel generally after theta
is nonzero, and it does not cancel inside the floor. Tests cover both limits.
The active lambda/rho ratio is1/2, not a large asymptotic timescale separation.

For primary transitions, the unprojected candidate's mean spatial std is
0.000362914 (range0.000320386–0.000398162). Projection brings it to0.3 on
the first write. The multiplier averages828.98, range753.46–936.37.
**This is relative to the lambda-weighted candidate, not an829-fold boost
of R itself.** R already has mean std0.388; normalization largely undoes the
tiny write coefficient at an erased birth.

The first theta differs from projection of the pre-write R by mean absolute
0.000535 (range0.000415–0.000696). The spatial std of the new-body injection
.002*V1 is on average0.004474 times that of .998*R_before. That roughly0.45%
ratio is a comparison of correlated term sizes, not a causal fraction:
V1 already depends on the reference through body feedback. It cannot show
what happens if R is disabled or changed consistently through the trajectory.

## Same normalization, very different content

These are sign agreements of internal fields, pooled descriptively over the
192 repeated transitions. They are NOT fresh-body amplitude-qualified fidelity
and must not replace D117's93.59%/86.67% terminal-body result.

| Internal stage | Intact reading, target-sign agreement | Reading disabled, target-sign agreement |
| --- | --- | --- |
| Body at end of reading | 92.94% | 50.03% |
| R at end of reading | 96.22% | 49.41% |
| Theta after the first write | 96.25% | 49.48% |
| Theta after1000 writes | 96.88% | 49.50% |

Both conditions have first-theta std0.3. Read-off receives an even larger
multiplier, mean1460.57, range1249.45–1846.79, because its unprojected field
is weaker. Greater amplification does not manufacture the missing target-
specific geometry. Projection subtracts a common mean and rescales by a
positive scalar; it is permutation-equivariant and has no target-address
input. D117's correct/wrong/shuffled controls, not the arithmetic alone,
provide the functional content evidence.

R's greater sign agreement than the instantaneous body is consistent with
temporal averaging. It is not a causal mediation estimate or a noise-spectrum
measurement establishing every layer to be slower and cleaner. Final theta
still differs from first theta by mean absolute0.042635, so the small average
sign improvement does not prove later writing functionally irrelevant.

The auxiliary `ema` array is updated but does not feed the active V/R/theta
path: blueprint calls ladder rung A; the only `ema` reads are its own update/
forwarding and return. Source-AST checks cover those three functions. R, by
contrast, has both comparator feedback into V and writer input into theta.
An EMA-only ablation would be redundant in this particular path. This is a
source-graph statement, not a new intervention experiment.

## Inference and next focused coding proposal

D117 still supports an engineered, renewable theta carrier across three fresh
descendants. D118 identifies a useful distinction: body experience acquires
R's pattern; projection puts its readout at full theta strength immediately.
Neither R's necessity independently of body feedback, projection-off behavior,
nor one-write fresh-recipient sufficiency follows from these saved states.
No upgrade to the full L17/L20 prose, clean-filtering claim or biology.

**Recommended next:** a first-write versus1000-write theta-only handoff into
matched fresh readers, with both records at the existing norm.3, paired
value-multiset-preserving shuffles and qualified reading controls. This tests
whether the late writing phase adds readable content beyond the immediate
normalized reference copy, without another norm/rate/threshold search.
Freeze the reader streams, contrast and stopping rule before new readouts;
existing D117 histories remain known reused sources, not a fresh renewal
replication. A nonsignificant full-minus-first contrast would not establish
equivalence. Proposal only: no new experiment protocol, identities or launch.

## Retention and verification

Audit identity `l20_reference_projection_audit_v1_attempt1`. Completed
2026-09-14 at13:20:33.844325 UTC in19.2173153320s. One worker, six-CPU
affinity maximum, numeric threads one, bytecode off.319 pinned inputs,
three hashed outputs plus completion;3,623,273 B total (~3.46MiB), external.
No failed attempt, automatic retry or successor.

Independent vectorized NumPy/stdlib-only recomputation of primary/read-off
amplification, R accounting, term ratios and internal sign metrics matches
retained summaries to1e−12. All319 input/three output hashes match; all1536
rows retained. D117's source/data/result note remain unchanged and are now
pinned inputs to this audit. This is E3 numerical accounting plus source
algebra, not a new E5 cohort or independently implemented dynamical model.

- [Summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_reference_projection_audit_v1_attempt1/summary.json), SHA `7fc2a7af82074eabf09d17424f88bfac4849276efa50a1c2bb76f4403b52d2a4`.
- [All transitions](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_reference_projection_audit_v1_attempt1/transitions.json), SHA `da055f1546b10545646599e218d60b955fd88e0b558f6a13eae3461e4c55134f`.
- [Inputs](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_reference_projection_audit_v1_attempt1/INPUTS.json), SHA `8eaf9dfff490bb8ca7ef83219de09dadae80d83817594a011cdd26e87d455dfc`.
- [Completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_reference_projection_audit_v1_attempt1/COMPLETE.json), SHA `ee950828441062b1bea4c92360ca2d22fad0cdc8d8dd66698bca9699a0e9dc3f`.

Only code/docs are local. All fixtures, report and audit artifacts are on
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/`; existing reserve and
>600s detached/unpolled policy unchanged. No new long-running job.
