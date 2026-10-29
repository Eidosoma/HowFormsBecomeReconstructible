# Both frozen mixtures work throughout the 4%–6% noise interval

Completed and independently verified 28 October 2026 under the
[prospective specification](FEP_NOISE_INTERVAL_V1.md).

**Both mixtures meet every primary inequality for every fixed true noise rate
in the closed interval [4%,6%].** They preserve the original stable-cost limit
and recover more cheaply than the frozen hybrid and always purchasing, with
all feedback fees charged. This is an exact polynomial certificate over the
continuum, beyond the three previously evaluated rates.

The guarantee concerns expected costs averaged over the declared reversal
onsets, noise histories and episode-start policy choice. Both mixtures are
**worse when reversal occurs at task 3, throughout the interval**. They improve
the other nine reversal timings. The mean criterion succeeds without an
improvement at every onset or on every individual episode.

## What stayed fixed

The ten-task environment retains probability 1/2 of one hidden reversal,
uniform onset conditional on reversal, accurate purchases costing .1, unit
unaided-error cost and hidden unbought targets/losses. The actual sensor rate
is constant within an episode; noise bits are independent conditional on it.
The stable budget stays **K=.0955500613134765625**.

All five component/comparator graphs and both mixtures' weights are byte-for-byte
equivalent to their predecessor records. The joint mixture still updates
beliefs over .04/.05/.06 and hidden reversal onset. The conservative fixed-pool
components and hybrid still use their original .05 likelihood. The actual
rate enters offline physical evaluation only. There is no replanning, revised
posterior, policy search or mixture retuning.

S is stable-world expected cost per task. B counts the whole episode under
the declared prior. R averages post-change cost per remaining task over
onsets. Every purchase is charged in B, including purchases before reversal.

## Worst costs and exact margins

Verified derivative certificates show that S, B and R are nondecreasing
throughout the interval for both mixtures and the hybrid. Their maximum
values therefore occur at **6%**:

| Policy | Maximum stable S | Maximum recovery R | Maximum full prior B |
| --- | --- | --- | --- |
| Joint-noise mixture | 0.095550061 | 0.096831025 | 0.095914277 |
| Conservative fixed-pool mixture | 0.095550061 | 0.097524308 | 0.096221644 |
| Frozen hybrid | 0.096817212 | 0.098977431 | 0.097736776 |
| Always purchase | .100000000 | .100000000 | .100000000 |

The primary margins are nonincreasing and attain their minima at 6% too:

| Policy | Required margin | Exact minimum, rounded | Verdict |
| --- | --- | --- | --- |
| Joint-noise mixture | K − S | 0.000000000000 | PASS |
| Joint-noise mixture | .1 − R | 0.003168975264 | PASS |
| Joint-noise mixture | Hybrid R − R | 0.002146406748 | PASS |
| Conservative fixed-pool mixture | K − S | 0.000000000000 | PASS |
| Conservative fixed-pool mixture | .1 − R | 0.002475691549 | PASS |
| Conservative fixed-pool mixture | Hybrid R − R | 0.001453123034 | PASS |

The stable margin is exactly zero at the right endpoint, which is allowed
by S<=K. The two recovery inequalities are strict and have positive margins.
There is no spare stable-budget margin at 6%; this is not a claim about
noise rates outside the interval.

The secondary checks also pass everywhere: each mixture has S no higher
than the matched hybrid, and B strictly below both the hybrid and always
purchasing. At the 6% worst case, the joint mixture's R is about 2.169% below
the hybrid and its B about 1.865% below. Recovery and total physical cost
remain separate reported quantities.

## How the interval proof works

With a frozen finite graph, every purchased-label branch is weighted by x or
1-x, and every unaided error probability is also x or 1-x. Expected physical
cost is consequently a rational polynomial of degree at most ten in the
true rate x. The evaluator builds these polynomials backward through each
graph, then combines worlds and fixed policy weights exactly.

For each inequality, transform the margin polynomial onto [0,1] and write
it in the Bernstein basis. The basis functions are nonnegative and sum to
one, so the smallest coefficient bounds the margin below everywhere.
Each of the six primary checks succeeds with one certificate covering the
whole interval; no subdivision is needed. The smallest stable coefficient
is zero, while all recovery coefficients are strictly positive.

Every main diagnostic certificate also resolves without subdivision.
Qualification separately exercises subdivision, counterexamples and an
intentional “inconclusive” case, so absence of subdivision in this result is
not an assumption of the method. No floating-point tolerance, numerical root
finder or sampled grid supplies the proof.

The independent verifier reconstructs all polynomials by replaying complete
noise histories and aggregating integer costs by the number of flipped bits.
It verifies each saved Bernstein representation at degree+1 distinct exact
points; the degree bound makes those equalities a polynomial identity.
Together with the coefficient signs and closed-interval coverage, that
establishes the universal inequalities.

## Mixture protection and onset-specific harm

The episode coin is independent of noise and reversal. Its components then
follow deterministic belief-dependent rules. The components' 6% costs show
why the average guarantee should not be assigned to each one:

| Mixture | Frozen component | Episode probability | S at 6% | R at 6% |
| --- | --- | --- | --- | --- |
| Joint-noise mixture | joint_oracle006 | 0.299563705309 | 0.092859002 | 0.104875048 |
| Joint-noise mixture | joint_oracle004 | 0.700436294691 | 0.096700978 | 0.093390744 |
| Conservative fixed-pool mixture | fixed_low_component | 0.458504371588 | 0.093509592 | 0.103674496 |
| Conservative fixed-pool mixture | fixed_anchor | 0.541495628412 | 0.097277802 | 0.092316717 |

Each high-spending component breaches K at 6%; each conservative component
has R>.1 there. The fixed combinations pass. This study searches for no new
deterministic rule and does not settle deterministic feasibility.

Compared with the hybrid, both mixtures have lower full episode cost in the
stable world and nine of the ten changed worlds, throughout the interval.
Their recovery cost is lower at those same nine onsets. **Onset 3 is strictly
worse for both full and recovery cost at every rate in the interval.**

The endpoint increases below are new policy minus hybrid. Full cost is
normalized per task; recovery cost is normalized per remaining task:

| Policy | Onset-3 full increase, 4% | Onset-3 full increase, 6% | Onset-3 recovery increase, 4% | Onset-3 recovery increase, 6% |
| --- | --- | --- | --- | --- |
| Joint-noise mixture | 0.014547884 | 0.016912650 | 0.018184855 | 0.021140812 |
| Conservative fixed-pool mixture | 0.028361885 | 0.029835244 | 0.035452356 | 0.037294056 |

These endpoint values illustrate the adverse effect; separate interval sign
certificates establish that it persists between them. Exact polynomials and
sign certificates for every onset are retained in the main result. The
declared average R criterion does not require every onset to beat .1 or the
hybrid. The onset-specific cost is therefore a limit of the result, not a
discarded failure or a changed success definition.

## What the richer FEP model adds

The joint mixture has lower B+R than the conservative fixed-pool mixture
at every rate in the interval. The exact advantage ranges from
**0.000051355502** at 4% to **0.001000650820** at 6%,
with the endpoints attaining the certified minimum and maximum. B+R is the
declared combined objective; it is not a single physical episode bill.

The earlier three-point average gain of about .2793% remains valid. The
fixed-pool control nevertheless also succeeds throughout the interval while
retaining its nominal .05 inference rules. Explicit noise learning is not
necessary for this robust feasibility result. Comparing the joint optimum
with a two-policy pool also changes policy-search scope, so the difference
does not isolate a causal benefit of noise learning.

At intermediate rates such as 4.5%, the exact true rate is absent from the
joint agent's three-hypothesis likelihood family. Its fixed decisions still
meet the functional requirements. This strengthens the evidence for useful
action despite limited likelihood mismatch; it does not establish accurate
noise identification or calibrated beliefs at every intermediate rate.
No new belief-quality diagnostic was calculated here.

The FEP interpretation remains joint uncertainty about hidden state and
observation reliability guiding purchased evidence. Bayesian/VFE updating
is part of that account. The action objective is still constrained task cost,
not a new canonical EFE or a uniquely FEP advantage.

## Scope of optimality

The inherited zero-gap certificate minimizes C averaged over .04/.05/.06,
subject to the 6% stable constraint. Since its frozen solution also satisfies
every stable constraint in the continuous interval, that same lower bound
is attained under the stronger interval constraint set. Thus optimality
persists for **the unchanged three-point objective**, within the declared
finite randomized-policy framework.

This is not optimality for a continuous prior over noise, a minimax recovery
objective, every individual onset, or deterministic controllers. The report
does not silently replace the objective when extending the feasibility check.

## Verification and records

Qualification passed **57,916 counted assertions** across **273 policy trees**:
all 3, 15 and 255 contingent trees at horizons 1, 2 and 3. Every world's
metrics match complete-noise expectations at six distinct rates, more than
the polynomial degree bound requires. Additional checks cover an erased-label
sequence, a fixed mixture and twelve analytic certificate fixtures. A narrow
negative interior well is detected despite positive endpoints; endpoint
equality, an interior zero, subdivision and proof exhaustion are distinguished.
Qualification took **2.784 seconds**.

Independent verification passed **758,567 assertions**, replaying
**67,664 complete noise histories** for **79 graph/world pairs**,
including short fixtures and the analytic always-purchase control. It checks
**1,604 frozen graph states**, all graph/weight identities,
every cost polynomial, exact reproduction at .04/.05/.06, and
**141 certificates** including qualification fixtures.
The main result has 129 certificates, including primary/secondary criteria,
both signs of onset differences and derivative diagnostics. Expected
counterexamples to the opposite sign are diagnostic evidence, not integrity
failures. All primary and secondary scientific checks pass; none is unresolved.

Main polynomial calculation took **3.132 seconds**, independent
verification **0.975 seconds**. The truncated T=7 timing benchmark took
**0.562 seconds** and forecast **146.980 seconds**. Execution used
one CPU at nice 10, one library thread and no bytecode. The forecast allowed
attached execution. No integrity failure, source correction, retuning or
scientific rerun occurred. This is independent reconstruction by the same
author, not external replication or sampled uncertainty evidence.

All **14 frozen inputs, 3 snapshots and 11 manifest-listed outputs**
verify. The sealed **1,405,475-byte** record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-interval-v1/attempt-01/`.
Exact derived summaries, report snapshots and reporting provenance are
separate in `reporting-2026-10-28/`. All generated data stay on `/mnt/bioIce1`;
source and small notes stay in this folder. Sister projects and manuscripts
remain untouched. Nothing remains running.

## Big picture and next decision

We now have exact continuous-interval evidence that paid autonomous recovery
can work in the small supplied task while respecting the stable cost limit.
The success is conditional on a fixed noise rate within each episode and the
declared onset distribution. It strengthens the local functional result;
it does not change the larger 401-component model's baseline or failed joint
criterion, nor merge supplied-feedback evidence into autonomous recovery.

The recommended next bounded question is whether both frozen mixtures retain
their gains when sensor reliability changes once during an episode. That
directly tests the constant-reliability assumption left intact here. Keep the
same hybrid and always-purchase controls and full economic accounting before
considering a richer dynamic likelihood model. This is proposed only: no
successor, wider interval, drifting-noise test, policy search, larger-model
transfer or manuscript integration has been launched.

| Record | SHA-256 |
| --- | --- |
| FREEZE.json | `6bafa4beb6ff22322c1f0a64234c933716795b629649347fb0365a469a4cf374` |
| GRAPHS.json | `90b28bc4bf70c3322dbf00613ad3a9e85b637074ac0349de23cc85aa18b2cf25` |
| QUALIFICATION.json | `6d78de3ce402de4e6a7cb5205d8a171040df9542746c630412d398f22d3bc1c8` |
| BENCHMARK.json | `a33a5773d5922143104c1c392a608dccc1ab1e9c19774788619d8c50b72e3839` |
| RESULTS.json | `e56d966181170daece0679d63a3694067a2d5b5ad406ee9bf997acc53a6379ff` |
| MANIFEST.json | `fce21f5ab43610ffbc5f138562594fcee3c1e01d9e87f0dab8f10c9f2c90b484` |
| READBACK.json | `9a47a1c46203336781229fdc2943e9673a9f96eeab6bbc526852c9f92b1ac2c6` |
