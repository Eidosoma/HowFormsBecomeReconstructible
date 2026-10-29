# Exact checking tradeoff with hidden reversal

Completed and verified 24 October 2026 under the
[prospective specification](FEP_CHECKING_TRADEOFF_V1.md).

**The declared feasibility test passes in the simplified model.** A schedule
using 18 purchases in a stable 100-task episode has stable cost .018 and
recovery cost .072475257. The old hybrid analogue buys 50 times when stable,
costing .05, with recovery cost .073964914. The 18-purchase schedule therefore
saves **64% in stable periods and 2.014% during recovery**, with all purchases
charged. Its recovery cost is also 27.525% below always buying at .1.

This is an exact result for an intentionally favorable model: a purchased
answer identifies the orientation perfectly, and no second change can occur.
It is not an achieved improvement in the larger 401-component model. The
[previous autonomous comparison](FEP_PLANNED_RECOVERY_V1_REPORT.md) and its
failed joint criterion remain unchanged.

A second result changes the priority of the next question: the selected
full-horizon Bayes optimum minimizes total cost but has recovery cost
**.101282997**, exceeding always buying. Optimizing the whole episode and
optimizing the specified recovery endpoint can recommend different policies.

## What is known and what must be learned

The initial orientation is known. Each independent fair target produces a free
binary reading that is either correct or inverted. A hidden reversal occurs
once with probability 1/2, uniformly over all 100 possible onsets; otherwise
the world stays stable. The sensor law and this prior are supplied correctly.
Free readings have exactly the same distribution in both orientations.
An unaided error costs 1. A purchase costs .1, answers the current task correctly,
and reveals its target. Evaluation losses and unbought targets are hidden.

With retained feedback, one purchase after reversal identifies the new
orientation exactly. A verified reversal cannot recur. This removes noisy
interpretation, unknown reliability, calibration cost and model misspecification
from the larger problem. It isolates the cost of acquiring information and
using it over time. It is neither an empirical population estimate nor a
formal lower bound applicable to all the larger model's physical laws.

The finite calculation integrates over the stable world and every onset,
without Monte Carlo sampling or confidence intervals. Readout/target sequences
integrate out by symmetry. All 606 policy/world trajectories and 60,600 decisions
are retained; the 101 checking-budget solutions have their own saved schedules.

## Exact policy comparison

All entries are cost per task. Recovery first normalizes each onset by its
remaining task count and then averages all 100 onsets equally. Full-episode
costs include every purchase before and after change. The prior-weighted
objective averages stable and changed full-episode cost with equal weights.

| Policy | Stable cost | Recovery cost | Changed full episode | Prior-weighted full episode |
| --- | ---: | ---: | ---: | ---: |
| Full-horizon optimum | 0.018000000 | 0.101282997 | 0.031470000 | 0.024735000 |
| Full-horizon optimum with gap rule | 0.050000000 | 0.077908861 | 0.055000000 | 0.052500000 |
| Old hybrid analogue | 0.050000000 | 0.073964914 | 0.055000000 | 0.052500000 |
| Unconstrained four-step planner | 0.023000000 | 0.091024735 | 0.028500000 | 0.025750000 |
| Always buy | 0.100000000 | 0.100000000 | 0.100000000 | 0.100000000 |
| Discard bought labels | 0.081000000 | 0.118236184 | 0.100000000 | 0.090500000 |

The full-horizon planner saves **3.942% in prior-weighted full cost** compared
with CT4 (.025750 → .024735), while its recovery cost is **11.270% higher**
(.091024735 → .101282997). This is a comparison of the specified policies
under the fixed tie rule, not a claim about every possible optimal tie choice.

The two constrained policies tie at .0525 on their optimized full-episode
objective, yet differ in recovery. The full-horizon constrained policy buys
on odd tasks along its stable path; the hybrid buys on even tasks. Their
terminal alignment matters to the recovery endpoint. Model-expected optimality
does not imply improvement on each conditional endpoint.

The old hybrid here is a faithful analogue of its decision rule in the new
small model, not the original controller evaluated again. None of these
numbers should be compared as paired outcomes with the earlier cohort.

## The checking budget frontier

The frontier applies to policies that follow the last verified orientation,
check at chosen times, and stop buying once they observe reversal. Each row
minimizes recovery cost at that exact stable-world purchase count. It does not
cover policies that guess a reversal before verifying it. All 101 rows are
retained, including the endpoints. Randomization before an episode gives the
lower convex envelope; all 101 points are vertices in this calculation.

| Stable-episode purchases | Stable cost | Recovery cost | Prior-weighted full cost |
| ---: | ---: | ---: | ---: |
| 0 | 0.000000000 | 1.000000000 | 0.252500000 |
| 5 | 0.005000000 | 0.253197684 | 0.051350000 |
| 10 | 0.010000000 | 0.138392943 | 0.033670000 |
| 13 | 0.013000000 | 0.105030642 | 0.029630000 |
| 14 | 0.014000000 | 0.096950669 | 0.028625000 |
| 17 | 0.017000000 | 0.077714195 | 0.027430000 |
| 18 | 0.018000000 | 0.072475257 | 0.027190000 |
| 20 | 0.020000000 | 0.063859620 | 0.026620000 |
| 25 | 0.025000000 | 0.047980302 | 0.027120000 |
| 50 | 0.050000000 | 0.017302893 | 0.038330000 |
| 100 | 0.100000000 | 0.005187378 | 0.075250000 |

**Eighteen purchases is the smallest deterministic budget meeting the frozen
joint feasibility condition:** strictly lower stable cost than the hybrid,
and recovery strictly below both the hybrid and always buying. Budgets 18–49
meet it. At 17 purchases, recovery .077714195 still exceeds the hybrid. Fourteen
is the first integer budget below always buying, but it does not yet beat the
hybrid. Randomized mixtures can achieve intermediate expected budgets; 18 is
not a universal minimum expected purchase count over randomized policies.

The selected 18-purchase schedule, followed only while reversal remains
unobserved, is:

```text
10, 20, 29, 37, 45, 52, 59, 65, 71, 76, 81, 85, 89, 92, 95, 97, 99, 100
```

It stops after a bought label reveals reversal, so changed episodes average
6.98 purchases and 2.94 errors. Its changed full-episode cost is .03638 and
prior-weighted full cost is .02719, 48.210% below the hybrid's .0525.
Thus the result does not hide extra pre-change fees in its recovery endpoint.
It is still **9.925% more costly overall than the full-horizon optimum**,
which spends the same 18 purchases in stable episodes but places them differently.
The two policies solve different objectives.

The 100-budget row is also not “always buy”: it stops buying once reversal
is learned. Its recovery cost .005187378 is the average of a single .1 purchase
divided by the remaining task count at each onset. Always buying continues
spending .1 per task after it has already learned the orientation.

## Why the objectives diverge

A mistake on the last task after a last-task reversal contributes 1 to that
onset's normalized recovery cost. Under the full-episode objective it is only
one error in a 100-task episode, occurring in one of the 100 possible changed
worlds. The recovery criterion gives late events much greater relative weight.

Consequently, the recovery-optimal 18-purchase schedule concentrates checks
near the end, including task 100. The full-cost optimum stops at task 96 and
accepts undetected reversals on the last four tasks. That can minimize its
expected full cost while failing the recovery threshold. This is a preference
and evaluation distinction, not a faulty Bayesian update or a proof that
longer planning is inherently harmful.

A scientific follow-up should make the desired balance between stable costs,
whole-episode costs and recovery explicit before choosing a new policy. This
calculation does not authorize replacing the previous experiment's endpoint
or declaring its failure a success under a different score.

## Acquisition and use of evidence

| Policy | Stable purchases | Mean changed purchases | Mean changed errors | Onsets with no later purchase |
| --- | ---: | ---: | ---: | ---: |
| Full-horizon optimum | 18 | 9.370000000 | 2.210000000 | 4 |
| Full-horizon optimum with gap rule | 50 | 50.000000000 | 0.500000000 | 1 |
| Old hybrid analogue | 50 | 50.000000000 | 0.500000000 | 0 |
| Unconstrained four-step planner | 23 | 11.500000000 | 1.700000000 | 5 |
| Always buy | 100 | 100.000000000 | 0.000000000 | 0 |
| Discard bought labels | 81 | 81.000000000 | 1.900000000 | 0 |

Once a retained purchase reveals reversal, unaided answers are correct by
construction. The unconstrained retained-label policies make no further
purchases. The compulsory policies keep buying despite known orientation:
across the 100 changed worlds, the full-horizon constrained policy makes
2,401 purchases after retained detection and the hybrid makes 2,450.
This is a real cost of the imposed rule in this model, where further change
is impossible; it is not evidence that continued checking is generally wasteful.

Erasing labels yields .0905 prior-weighted full cost and .118236184 recovery
cost, versus .024735 and .101282997 for the chosen full-horizon retained-label
policy. Retention supports useful future behavior. The lesion changes later
actions as well as beliefs, so this is a policy-level mechanism comparison,
not an additive causal attribution for the larger experiment.

The requested familiar onsets are shown separately; they are descriptive
subsets and do not replace the all-onset endpoint:

| Policy | Onset 13 | Onset 38 | Onset 63 | Onset 88 |
| --- | ---: | ---: | ---: | ---: |
| Full-horizon optimum | 0.057954545 | 0.065079365 | 0.107894737 | 0.315384615 |
| Full-horizon optimum with gap rule | 0.050000000 | 0.065079365 | 0.050000000 | 0.123076923 |
| Old hybrid analogue | 0.061363636 | 0.050793651 | 0.076315789 | 0.053846154 |
| Unconstrained four-step planner | 0.023863636 | 0.033333333 | 0.028947368 | 0.084615385 |
| Always buy | 0.100000000 | 0.100000000 | 0.100000000 | 0.100000000 |
| Discard bought labels | 0.171590909 | 0.100000000 | 0.100000000 | 0.100000000 |

## FEP interpretation

For the finite hidden-state model, variational free energy satisfies
`F(q) = KL(q || posterior) - log P(observed history)`; the exact posterior
minimizes it. Beliefs about reversal determine the expected consequence of
buying or answering. The free reading supplies no orientation information;
the paid target can do so, and the subsequent cost depends on retaining it.

Action choice here minimizes expected task cost. The full-episode optimum
and the recovery frontier embody different task preferences; neither is
relabelled as a new canonical expected-free-energy functional. Agreement
with Bayesian planning is expected within this formulation and does not
weaken the result. The substantive FEP question is whether the selected
beliefs and preferences support the useful behavior we actually want.

The positive feasibility result says that hidden reversals and a .1 fee do
not by themselves force the hybrid's expenditure in this idealized setting.
It does not establish that the same schedules work with uncertain reliability,
ambiguous feedback, additional change families or a misspecified prior.
In particular, the exact optimum does not support treating a longer horizon
alone as a solution to recovery performance.

## Verification and records

The forward calculation uses exact fractions. Qualification passed **753
assertions**, including enumeration of all pre-detection action strings and
all checking subsets for horizons 1–6, under change probabilities 0, 1/2 and 1.
It checks Bayes probabilities, terminal behavior, clock feasibility, erased
memory, warning symmetry and independently enumerated policy costs.

The separate verifier imports no scientific planner. It passed **85,561
assertions**, rebuilding saved traces, costs, acquisition records and endpoint
weights. It verifies full-horizon Bellman values using integer-scaled costs,
and every frontier optimum using a backward integer recursion distinct from
the forward fraction calculation. It checks the lower convex envelope and
frozen feasibility gate. It reruns no simulated policy episodes. This is
independent numerical verification by the same author, not external replication.

All **six frozen inputs, three source snapshots and nine manifest-listed
outputs** verify. No failure, correction, retuning, restart or sample extension
occurred. The benchmark at different parameters took .318493 seconds; its
conservative forecast was 149.859 seconds, permitting attached execution.
Main computation took **2.994 seconds**, and readback **.270 seconds**, on one
CPU (CPU 0), nice 10. No long job remains running.

The 377,147-byte sealed record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-checking-tradeoff-v1/attempt-01/`.
Stdout is a sibling. Reporting snapshots and provenance are separate under
`reporting-2026-10-24/`; all generated data stay on the external drive.

| Record | SHA-256 |
| --- | --- |
| `FREEZE.json` | `aafd9c3af32bc2fc956273fe5d3743c5c0aab7eace7e01631f95fe33aa3cb35a` |
| `QUALIFICATION.json` | `431620dde862242e454e1d2b2ad7f1b4f61c3678cf6f5da9321de2c52e178afd` |
| `BENCHMARK.json` | `e9d5157f9a78eeae810fbd997a6afb6f3750381ccec87c7ce47cbbd8760ad6a6` |
| `RESULTS.json` | `cfd30dceb93ae6e17735d8cfa87f543815f47d4e4ef40b03ac674135827248ac` |
| `MANIFEST.json` | `85a5d60326923bc13a2358e10c76ff5c7a73ad95065c1ba2cf1f24e03ac65ce7` |
| `READBACK.json` | `832127a74e99100fde9a9724ddb6ac36f9400ceb87348c58175655beff5024db` |

## Decision and next lead

Keep the existing hybrid as the larger model's working baseline. This bounded
exact test is complete and provides a positive feasibility example, together
with a concrete warning about optimizing total cost while judging recovery.

The next proposed task is a small analytic objective-alignment design: express
the desired recovery/stability trade-off using the agent's beliefs over hidden
change time, with every fee retained in accounting, before testing another
controller. Actual change time must remain hidden. No successor has been implemented or launched. Manuscript integration and
sister projects remain untouched.
