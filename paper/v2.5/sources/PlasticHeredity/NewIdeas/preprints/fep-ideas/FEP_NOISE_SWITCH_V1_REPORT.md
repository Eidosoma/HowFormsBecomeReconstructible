# One late reliability change breaks the fixed budget, while recovery gains survive

Completed and independently verified 29 October 2026 under the
[prospective protocol](FEP_NOISE_SWITCH_V1.md).

**Both frozen mixtures fail the overall robustness criterion.** Each passes
17 of the 18 reliability-switch schedules. Both fail when noise falls from
6% to 4% on task 10: orientation-stable cost slightly exceeds the original
fixed budget. The violation is exact, despite being small.

**Recovery still beats the hybrid and always purchasing in every schedule.**
Full prior cost and matched-hybrid stable comparisons also pass everywhere.
The result isolates a fragile absolute cost limit; it does not erase the
surviving autonomous recovery benefit or establish that richer inference is
required. All purchased-feedback costs are included.

## What was tested

The ten-task experiment keeps probability 1/2 of one hidden orientation
reversal, uniform onset conditional on reversal, .1 per accurate purchased
target, unit unaided-error cost and hidden unbought targets/losses. Sensor
noise changes once, from 4% to 6% or 6% to 4%, starting at each task 2–10.
The 18 schedules are evaluated separately, crossed with the orientation-stable
world and all ten reversal onsets. There is no averaging over switch times
to decide primary success.

“Stable” means the orientation does not reverse; sensor reliability can still
change. S is that world's cost per task. B includes every error and purchase
in the whole episode under the fixed reversal prior. R averages post-reversal
cost per remaining task over onsets. The unchanged budget is
**K=.0955500613134765625**. Each schedule requires S<=K, R<.1 and R below the
same hybrid evaluated in that schedule.

All five graphs and both episode-choice weights are unchanged. The joint
agent still represents one constant noise parameter from .04/.05/.06; the
fixed-pool components and hybrid still assume .05. They receive no true noise
rate, switch time or reversal time. This is a frozen-policy stress test,
not a newly learned dynamic-noise model or a retuned controller.

## The failure and the remaining gains

For the sole failing schedule, 6%→4% at task 10:

| Policy | Orientation-stable S | S − K | Relative excess | Recovery R | Full prior B |
| --- | --- | --- | --- | --- | --- |
| Joint-noise mixture | 0.095559925757 | 0.000009864444 | 0.010324% | 0.094047698 | 0.095138827 |
| Conservative fixed pool | 0.095566639051 | 0.000016577738 | 0.017350% | 0.094703234 | 0.095442783 |

The matched hybrid has S=.096824894760, R=.097680478977 and
B=.097420359287 in this schedule. Both mixtures still improve those
comparisons. Always purchasing costs .1 for S, B and R and exceeds K.
The failure is against the original absolute stable budget, not against a
newly adjusted threshold. Costs are exact expectations, not sampling noise.

The smallest primary margins, preserving ties, are:

| Policy | Margin | Minimum | Schedule(s) |
| --- | --- | --- | --- |
| Joint-noise mixture | K − S | -0.000009864444 | 6%→4% at task 10 |
| Joint-noise mixture | .1 − R | 0.002968975264 | 4%→6% at task 2 |
| Joint-noise mixture | Hybrid R − R | 0.002146406748 | 4%→6% at task 2 |
| Conservative fixed pool | K − S | -0.000016577738 | 6%→4% at task 10 |
| Conservative fixed pool | .1 − R | 0.002259375773 | 4%→6% at task 4 |
| Conservative fixed pool | Hybrid R − R | 0.001448382455 | 4%→6% at task 4 |

Both R margins stay strictly positive in every schedule. The joint model's
largest R is .097031024736 after a 4%→6% change at task 2; the fixed pool's
largest R is .097740624227 after a 4%→6% change at task 4. Both models have
their largest switch-schedule S and B at the late 6%→4% change. These maxima
do not substitute for the separate matched-hybrid comparisons above.

| Schedule | Joint S − K | Fixed-pool S − K | Joint R | Fixed-pool R | Hybrid R | Both primary gates |
| --- | --- | --- | --- | --- | --- | --- |
| 4%→6% at task 2 | -0.002000000000 | -0.002000000000 | 0.097031025 | 0.097724308 | 0.099177431 | PASS |
| 4%→6% at task 3 | -0.002059349398 | -0.002074793003 | 0.096978803 | 0.097652596 | 0.099188225 | PASS |
| 4%→6% at task 4 | -0.002679293755 | -0.002995840252 | 0.097023821 | 0.097740624 | 0.099189007 | PASS |
| 4%→6% at task 5 | -0.002731877671 | -0.003068568437 | 0.096974486 | 0.097710000 | 0.099191054 | PASS |
| 4%→6% at task 6 | -0.002784060684 | -0.003118026286 | 0.096567722 | 0.097302321 | 0.098797642 | PASS |
| 4%→6% at task 7 | -0.002822492824 | -0.003159943326 | 0.095978230 | 0.096754596 | 0.098496595 | PASS |
| 4%→6% at task 8 | -0.002848255386 | -0.003377236327 | 0.095022245 | 0.095817397 | 0.097812234 | PASS |
| 4%→6% at task 9 | -0.002958231744 | -0.003609462522 | 0.093762731 | 0.094506058 | 0.097205052 | PASS |
| 4%→6% at task 10 | -0.003026854753 | -0.003672462681 | 0.092053511 | 0.092340691 | 0.095635466 | PASS |
| 6%→4% at task 2 | -0.001022842892 | -0.001665398424 | 0.089046880 | 0.089310635 | 0.094153415 | PASS |
| 6%→4% at task 3 | -0.000970656558 | -0.001593242950 | 0.089105193 | 0.089389343 | 0.094137087 | PASS |
| 6%→4% at task 4 | -0.000373212769 | -0.000698649911 | 0.089073399 | 0.089313217 | 0.094135012 | PASS |
| 6%→4% at task 5 | -0.000311978229 | -0.000629512939 | 0.089143953 | 0.089357367 | 0.094130241 | PASS |
| 6%→4% at task 6 | -0.000262967911 | -0.000582179208 | 0.089545195 | 0.089759448 | 0.094511758 | PASS |
| 6%→4% at task 7 | -0.000219543172 | -0.000528573257 | 0.090134383 | 0.090302859 | 0.094836393 | PASS |
| 6%→4% at task 8 | -0.000184395107 | -0.000348408847 | 0.091086569 | 0.091231364 | 0.095508657 | PASS |
| 6%→4% at task 9 | -0.000095287610 | -0.000076051712 | 0.092334339 | 0.092550552 | 0.096128337 | PASS |
| 6%→4% at task 10 | 0.000009864444 | 0.000016577738 | 0.094047698 | 0.094703234 | 0.097680479 | FAIL |

In all 18 schedules, both mixtures meet the secondary matched-hybrid stable
comparison and have B below the hybrid and always purchasing. The joint
mixture's J=B+R is lower than the fixed pool's in all 18. The simpler fixed
pool has the same primary failure, so this comparison does not establish a
causal benefit or necessity of explicit noise learning.

## Why a cleaner final reading can increase stable cost

This is a post-result algebraic diagnosis using the **existing** task-10
switch and constant-6% control. It introduces no new condition or policy.
Those schedules are identical through task 9. The action distribution and
beliefs before the final decision are therefore identical. Exact readback
also confirms equal total purchases and equal pre-action orientation Brier
scores in every reversal world.

In the orientation-stable world, the task-10 action probabilities are:

| Policy | Purchase probability (%) | Follow probability (%) | Invert probability (%) | Extra stable cost/task |
| --- | --- | --- | --- | --- |
| Joint-noise mixture | 99.506778 | 0.000000 | 0.493222 | 0.000009864444 |
| Conservative fixed pool | 99.171113 | 0.000000 | 0.828887 | 0.000016577738 |
| Frozen hybrid | 99.615864 | 0.000000 | 0.384136 | 0.000007682719 |

Most histories lead to a purchase. On a small fraction, previous noisy
observations have led the controller to invert a sensor whose orientation
never actually reversed. With inversion, the error probability is 1−x.
Changing x from .06 to .04 raises that probability from .94 to .96. A cleaner
sensor makes this already mistaken inversion more consistently wrong.

The exact excess over the constant-6% control is

```text
change in stable cost/task = .02 × (P[invert] − P[follow]) / 10.
```

Here P[follow]=0. This identity reproduces the recorded cost increases
exactly, using an independent integer forward reconstruction of task-10
action occupancy. Purchase counts do not change: the extra cost consists
entirely of unaided errors. For the two mixtures the constant-6% stable cost
already equals K, so this small increase crosses the budget immediately.

The physical reliability change is not observable before this final action,
and information purchased afterward cannot influence another task. The
diagnosis therefore does not show failed online detection of that last-step
change. It shows that the fixed budget has no reserve for a change in the
consequences of rare false-orientation decisions. It is a local economic
fragility tied to mistaken inversions, not an increase in feedback spending.

## Acquisition and orientation-belief diagnostics

For the failing schedule, stable counts refer to the no-reversal world.
Post-switch quantities below use the full reversal prior and concern only
the final task; those populations should not be conflated:

| Policy | Stable purchases | Stable errors | Prior post-switch purchases | Switch delay | No post-switch purchase | Prior orientation Brier | Post-switch Brier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Joint-noise mixture | 8.710357 | 0.084564 | 0.607343 | 0.392657 | 0.392657 | 0.074938 | 0.069475 |
| Conservative fixed pool | 8.553839 | 0.100283 | 0.602281 | 0.397719 | 0.397719 | 0.075420 | 0.070038 |
| Frozen hybrid | 8.990271 | 0.069222 | 0.837950 | 0.162050 | 0.162050 | 0.074205 | 0.069907 |

For a last-task switch, the capped delay and missing-purchase probability
coincide. A missing final purchase does not mean the agent lacks information
from earlier purchases. The mixtures often answer directly in changed worlds,
which saves fees but can increase errors. The stable-world action table is
the relevant decomposition for the failed S constraint.

The retained reversal probability is scored before each action against the
actual orientation. Joint-model noise classes are marginalized before that
binary Brier score; mixtures average component scores with component identity
retained. Always purchasing has no assigned belief score. Both mixtures have
slightly worse full-prior orientation Brier loss than the hybrid in all 18
switch schedules, despite cheaper R and B. These scores describe accuracy
under selected observation histories, not calibration or a causal test of
interpretation. Paying for more information can improve a belief score while
being worse under the declared economic objective.

## Onset-specific adverse outcomes

For both mixtures, complete episode cost worsens relative to the hybrid at
reversal onset 3 in all 18 schedules. The other nine changed worlds and the
orientation-stable world have lower complete bills than the matched hybrid.
This does not prevent the fixed-K failure described above.

Recovery cost also worsens at onset 3 in every schedule. The joint mixture
has three additional adverse recovery cases when noise rises from 4% to 6%
on task 10: onset 7 worsens by .003889935380, onset 8 by .000222067209 and
onset 9 by .000011585083 per remaining task. Its complete episode bill is
still lower in those worlds. The fixed pool has no additional recovery
reversals in this schedule. All signed onset comparisons against the hybrid,
always purchasing and the other mixture are saved, including harms and ties.

The primary R criterion averages over reversal onsets. Passing it does not
promise improvement at every onset or protection for every realized episode.
Both mixtures still use an independent episode coin; no deterministic
robustness result is produced here.

## Verification and records

Qualification passed **7,524 counted assertions** across **1,869 short
tree/schedule cases**, enumerating all 3, 15 and 255 contingent trees through
T=3 with joint-noise beliefs and every short switch/constant schedule. Further
fixtures cover .05 beliefs, a rho=1/3 physical prior, erased labels, fixed
mixtures, boundary switch times and separate event delays. It took
**9.427 seconds**.

Independent verification imports no evaluator. It replays complete binary
noise histories with the exact time-specific integer probability product,
reconstructs graph visits and Brier scores, verifies the frozen likelihood
edges and mixture identities, and rebuilds every gate and signed comparison.
It passed **13,067,465 assertions**, covering **1,182,912 complete noise
histories, 1,179 graph/world evaluations and 1,642 checked graph states**,
including short fixtures. The analytic always-purchase control is checked
separately. All shared physical costs at constant 4%, 5% and 6% reproduce the
previous exact interval polynomials. Verification success is distinct from
the two negative scientific robustness verdicts.

Main calculation took **43.979 seconds**, verification **26.698 seconds**,
on one CPU at nice 10 with library threads one and no bytecode. The two-direction
T=7 timing benchmark took **0.503 seconds**, forecasting
**373.551 seconds** and allowing attached execution. No integrity failure,
sealed-source correction, retuning or adaptive scientific rerun occurred.
The final-task explanation is labeled post-result analysis of existing data.
This is independent reconstruction by the same author, not external
replication or sampled uncertainty evidence.

All **10 frozen inputs, 3 snapshots and 11 manifest-listed outputs** verify.
The sealed **23,807,575-byte** record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-switch-v1/attempt-01/`.
Derived summaries, the late-switch diagnosis, report snapshots and provenance
are separate in `reporting-2026-10-29/`. All generated data remain on
`/mnt/bioIce1`; source and small notes remain here. Sister projects and
manuscripts were not edited. Nothing remains running.

## FEP meaning and next decision

The model's fixed likelihood assumptions still support useful autonomous
evidence-guided recovery under these small reliability changes. They do not
preserve the original absolute budget in every tested schedule. The positive
constant-noise interval proof remains valid; its scope did not cover changing
noise. This test neither proves dynamic-noise robustness impossible nor
establishes that a switching-likelihood model is necessary.

The FEP issue is the gap between coherent belief updating under a supplied
generative model and functional guarantees under changed observation dynamics.
Bayesian/VFE inference remains part of this interpretation. The action target
is constrained task cost, not a new canonical EFE or a uniquely FEP advantage.
The larger 401-component model keeps its prior baseline and failed joint
criterion; these small exact experiments do not transfer results to it.

The recommended next bounded question is whether the same component policies
can regain enough budget reserve through a newly specified mixture while
preserving recovery across the stationary and one-switch conditions. That
would test whether cost allocation alone can close this gap before attributing
it to insufficient model richness. Any reweighting belongs in a new prospective
study; the present failed weights and evidence remain frozen. No successor,
retuning, dynamic likelihood model, wider switch family or larger-model
transfer has been launched.

| Record | SHA-256 |
| --- | --- |
| FREEZE.json | `e2f01da0fc69a41cb3533b345d7b68fe5a5a994d01e46cde13b84dc13fc62ed7` |
| GRAPHS.json | `90b28bc4bf70c3322dbf00613ad3a9e85b637074ac0349de23cc85aa18b2cf25` |
| QUALIFICATION.json | `23917654cd4f37100b2c7a6931d799ec543409ab4c30d37ad1dd36f0156c8979` |
| BENCHMARK.json | `a825529e9568a13dbd9004fb6454a5f8e9b00ac1e05ea3a23056cdbc9cab4b4c` |
| RESULTS.json | `d9435f47811df4d40b6781de9452ca5f4fde46a7084be870b826ba9a4fc3ff86` |
| MANIFEST.json | `fe5e3dafff68bc992a96b1cc7c177069b667a6106ef89a1dba2ced251da03ae5` |
| READBACK.json | `fc00fd5663df0b71716e9494444d9e0f81632837099fbc4eef0486311c911cc5` |
