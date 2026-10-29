# Recovery preferences in an exact hidden reversal model

Completed and verified 24 October 2026 under the
[prospective specification](FEP_RECOVERY_OBJECTIVE_V1.md). The construction
keeps the physical model, observations, feedback price and ordinary posterior
fixed, and changes the action objective to give recovery explicit weight.

**The construction and its bounded feasibility gate pass.** With retained
paid evidence, recovery cost is **.017348113**, versus **.073964914** for the
previous hybrid analogue: a **76.545% reduction**. Stable cost is equal at
**.05**, and prior-weighted full cost falls **27.219%**, from .0525 to .03821.
The new policy receives no actual change time and makes no unverified
inversions in any of the 101 evaluated worlds.

There is a substantial trade-off against the ordinary full-cost optimum:
recovery improves **82.872%**, but full prior cost rises **54.477%** and stable
purchases rise **18 → 50**. This result makes the preference trade-off explicit;
it does not establish that the chosen weight is uniquely appropriate.

These are exact consequences in the supplied perfect-evidence, single-reversal
model. They do not change the larger 401-component experiment's previous
failed joint criterion or establish a deployment improvement there.

## Objective and physical accounting

Keep 100 tasks, a known initial orientation, and a single hidden reversal
with probability 1/2, uniformly distributed over all 100 onsets. Otherwise the
world stays stable. Free readings are uninformative about orientation. Buying
costs .1, solves the current task and supplies its correct label; an unaided
mistake costs 1. Only purchased labels enter inference. A retained label
identifies orientation perfectly in this idealized model.

Let B be prior-weighted cost per task over full episodes, including every
stable, pre-change and post-change purchase. Let R be mean recovery cost per
remaining task, normalized separately at each onset and then averaged equally
across onsets. Optimize

```text
J_lambda = B + lambda R.
```

Lambda=0 is the ordinary full-cost control; lambda=1 gives the two average-cost
quantities equal numerical weight. The latter was fixed before outcomes as a
diagnostic preference, not selected by searching weights or inferred from FEP.
Every physical purchase is charged once. J adds priority to recovery costs;
it is a weighted decision score, not a second monetary bill.

The ordinary control matches every saved action and cost from the
[previous exact calculation](FEP_CHECKING_TRADEOFF_V1_REPORT.md). Its original
sources and records were not changed. The previous hybrid, CT4, always-buy and
frontier entries below are read from that same-model record, with no pooled
empirical data or re-execution of their old code.

## Full comparison and separate criteria

The last column scores every policy under the same B+R objective. The ordinary
policy was optimized for B, so comparisons of differently weighted root values
are not substituted for this common score.

| Policy in the same idealized model | Stable cost | Recovery R | Full prior cost B | Common score B + R |
| --- | ---: | ---: | ---: | ---: |
| Ordinary full-horizon optimum | 0.018000000 | 0.101282997 | 0.024735000 | 0.126017997 |
| Recovery preference, retained labels | 0.050000000 | 0.017348113 | 0.038210000 | 0.055558113 |
| Recovery preference, erased labels | 0.111000000 | 0.093197486 | 0.102450000 | 0.195647486 |
| Previous hybrid analogue | 0.050000000 | 0.073964914 | 0.052500000 | 0.126464914 |
| Previous CT4 | 0.023000000 | 0.091024735 | 0.025750000 | 0.116774735 |
| Always buy | 0.100000000 | 0.100000000 | 0.100000000 | 0.200000000 |
| Previous 18-purchase frontier | 0.018000000 | 0.072475257 | 0.027190000 | 0.099665257 |

The frozen feasibility gate for the retained-label policy has three parts:
R below .1, R below the previous hybrid, and stable cost no greater than the
previous hybrid. All pass; the stable comparison is an equality. This is an
exact deterministic model result, with no sampling confidence interval.

Relative to the ordinary optimum, R falls .101282997 → .017348113 while B
rises .024735 → .038210. Stable cost rises .018 → .05, or 177.778%, though it
remains equal to the hybrid and below always buying. The ordinary optimum
still minimizes its own objective. Exact optimization already guarantees the
direction of this B/R trade-off; its existence alone is not a new discovery.
The magnitudes, physical decisions and external feasibility checks are the
substantive results here.

The comparison with the ordinary full-horizon control changes only the
preference weight. The comparison with the hybrid also removes its compulsory
checking rule, so its gains cannot be attributed solely to the weight. In
changed worlds the hybrid buys 50 times and makes .50 errors on average;
the new policy buys 19.42 times and makes .70 errors. Its savings relative to
that rule therefore depend heavily on avoiding purchases after the orientation
has become known, as permitted by this idealized one-change model.

Relative to the hybrid, recovery improves at 99 of 100 onsets and ties at
onset 100. Full-episode cost improves in 99 worlds and ties in two, including
the stable world. Relative to the ordinary optimum, recovery improves at 75
onsets, ties at 14, and worsens at 11: **5, 6, 12, 18, 24, 30, 36, 42, 57, 67,
77**. Full-episode cost is higher in 37 of 101 worlds, lower in 63 and equal in
one. All signed outcomes remain in the saved per-world records.

Recovery under the new policy ranges from .001030928 to .1 across onsets;
none exceeds always buying, and the last-task reversal ties it. The familiar
onsets are shown without replacing the all-onset endpoint:

| Policy | Onset 13 | Onset 38 | Onset 63 | Onset 88 |
| --- | ---: | ---: | ---: | ---: |
| Ordinary optimum | 0.057954545 | 0.065079365 | 0.107894737 | 0.315384615 |
| Recovery preference | 0.012500000 | 0.001587302 | 0.028947368 | 0.007692308 |
| Erased labels | 0.097727273 | 0.096825397 | 0.094736842 | 0.084615385 |
| Previous hybrid | 0.061363636 | 0.050793651 | 0.076315789 | 0.053846154 |

## Hidden time enters through beliefs

For a possible onset tau, define the task weight

```text
w_t(tau) = 1/T + lambda*1{tau<=t}/[rho*(T-tau+1)].
J_lambda = E_prior sum_t w_t(tau) L_t.
```

The evaluator uses the physical onset to score trajectories. The agent has
no such input. Before verification, it sums weighted losses over its ordinary
posterior over possible onsets. After the last purchase confirming the old
orientation at k, let D=T-rho*k and
`H(t,k)=sum_{j=k+1}^t 1/(T-j+1)`. Its current weighted scores are

```text
follow = [rho*(t-k)/T + lambda*H(t,k)] / D
invert = (T-rho*t)/(T*D)
buy    = c*[1/T + lambda*H(t,k)/D].
```

Future scores then include the ordinary Bayesian branches from a purchased
label. No likelihood, prior or hazard is changed to favor the desired action.
In particular, a utility-weighted distribution is not substituted for the
posterior. Unpaid answers supply neither labels nor evaluation losses.

The independent verifier groups trajectories by the actual paid observations
available before each action. Identical observed histories give identical
actions across different hidden onsets. It also checks each saved action
against a separate integer Bellman calculation. This validates the information
boundary, rather than merely assuming that the evaluation code kept it intact.

## Weight and error must be averaged jointly

The recovery weight and the probability of an error depend on the same hidden
onset. In general `E[w L]` is not `E[w] E[L]`.

The prospectively specified terminal fixture has T=40, no previous purchase,
rho=1/2, c=.1 and lambda=1. Correct weighted scores are:

| Calculation | Follow | Invert | Buy | Selected action |
| --- | ---: | ---: | ---: | --- |
| Joint latent-state expectation | .119463576 | .012500000 | .013196358 | Invert |
| Incorrect product of means | .065981788 | .065981788 | .013196358 | Buy |

Direct exact summation over all latent onsets confirms the first row. This
fixture exposes an implementation error to avoid when extending the objective;
it is not an observed main-policy failure. The retained-label main policy
makes no unverified inversion, despite that action being allowed.

## What the policy does and what erasure reveals

| Policy | Stable buys | Stable errors | Mean changed buys | Mean changed errors | Changed worlds with no later purchase |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary optimum | 18 | 0 | 9.370000000 | 2.210000000 | 4 |
| Recovery preference | 50 | 0 | 19.420000000 | 0.700000000 | 0 |
| Erased labels | 91 | 2 | 91.000000000 | 0.290000000 | 2 |

The retained-label policy checks at tasks 4, 8, 11, 14, then approximately every
three tasks early on, every two later, and every task from 82 through 100 along
the stable path. These are consequences of the fixed objective and model,
not a separately imposed checking schedule. After a bought answer identifies
reversal, it stops paying and answers in the new direction. The stable world
therefore has 50 purchases; changed episodes average 19.42.

The objective gives late recovery a larger relative weight, so the agent
continues checking through task 100. It acquires post-change evidence at every
onset, and the stable world has zero mistaken answers. The favorable result
therefore does not come from guessing a reversal in unchanged worlds.

The erased-label control illustrates why recovery scores still need the
other diagnostics. It buys 91 answers but cannot retain their evidence. It
then inverts without verification on tasks 99 and 100 in every world. For
reversals on those tasks its scored recovery is zero even though it purchases
no post-change label. In the stable world those same choices cause two errors.
Its stable cost is **.111**, and full prior cost **.10245**, both worse than
always buying, despite average R=.093197486 being below .1.

Thus a low recovery score alone does not prove that an agent acquired and
used evidence. Retained evidence matters to the useful combined behavior in
this test. Erasure changes later decisions too; it is a policy-level mechanism
comparison rather than a unique additive causal decomposition.

## FEP interpretation and remaining limits

The generative model and variational-free-energy-minimizing belief update are
unchanged. The new ingredient is an explicit preference over consequences:
recovery contributes to the action score alongside total physical cost.
Bayesian planning implements that preference under the same observations.
This is not a new canonical EFE, a learned normative preference, or a uniquely
FEP advantage. It is a concrete demonstration that correct inference and
functional success also depend on what the agent is asked to optimize.

The result relies on a known initial orientation, perfectly informative paid
evidence, a correct change prior, and no second change. It supplies a valid
objective construction and an exact positive example. It does not establish
that lambda=1 will work in the larger uncertain model, where a purchased target
can still leave the sensor's orientation ambiguous. The earlier supplied-
feedback and autonomous results remain separate evidence.

## Execution and verification

Qualification passed **2,287 assertions**, including exhaustive pre-detection
action strings for horizons 1–6, change probabilities 1/3, 1/2 and 1, both
weights, and both retention modes. It verifies joint latent-state expectations,
normalization, observable histories and exact cost identities.

The separate saved-data verifier imports no planner and passed **63,252
assertions**. It rebuilds all **303 policy/world trajectories and 30,300 saved
actions**, reconstructs integer-scaled optimal values and physical costs,
checks identical paid histories, compares every lambda=0 action with the frozen
control, and independently verifies the counterexample and feasibility gate.
No simulated policy episode was rerun by the verifier. This is independent
numerical reconstruction by the same author, not external replication.

All **eight frozen inputs, three source snapshots and nine manifest-listed
outputs** verify. Main execution took **1.913 seconds**, with **.083 seconds**
for readback, on CPU 0 at nice 10. The .304-second benchmark forecast 148.472
seconds, permitting attached execution. No failure, correction, restart,
weight tuning or sample extension occurred; no job remains running.

All **167,622 bytes** of the sealed attempt are under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-recovery-objective-v1/attempt-01/`.
Stdout is a sibling. Completion reporting is separate in
`reporting-2026-10-24/`, with hashes and saved reporting calculations. Generated
data stay on the external drive; source and research notes remain local.

| Record | SHA-256 |
| --- | --- |
| `FREEZE.json` | `493c55f0dbf3da2de6d50a157480dc47925eaaf0e5793451e58e805a3e07f690` |
| `QUALIFICATION.json` | `49f7e0b5e674f1710d48e952d7dfec9acfcf3cb6e49e3c59d7a879f7fa232311` |
| `BENCHMARK.json` | `62e4fd64dfbbbcd1d981e680bb83f682c151bf5728eeabda80f81d0ad8d8fa7b` |
| `RESULTS.json` | `0b13b694c749810ab6434e4446e7fb8275db987306ccd68581e63ebf52179f26` |
| `MANIFEST.json` | `72e413c63852e178ba9c17809f742d2897748bc26fe431c28b1105bef96655c6` |
| `READBACK.json` | `0ba9dffb2c6feb75fe721b80960ac4d9c33979142a37eb875e7555e7efb781b2` |

## Decision and next test

This bounded objective construction is complete. Keep the larger model's
previous hybrid baseline and its original verdict. The next proposed test
should retain accurate paid target answers but introduce sensor noise, so
one bought answer no longer resolves orientation perfectly. A small fixed
exact comparison can test whether the preference construction remains useful
when several observations are needed, before a larger campaign is justified.
No such successor, larger-model replacement, manuscript integration or
sister-project write has been launched.
