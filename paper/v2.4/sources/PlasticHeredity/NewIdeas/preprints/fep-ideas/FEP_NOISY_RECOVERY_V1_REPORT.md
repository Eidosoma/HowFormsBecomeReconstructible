# Recovery preferences with ambiguous sensor evidence

Completed and independently verified 27 October 2026 under the
[prospective specification](FEP_NOISY_RECOVERY_V1.md).

**The combined performance criterion fails.** With 5% sensor noise, the
recovery-weighted policy lowers recovery cost to **.072509281**, versus
**.096674669** for the hybrid and .1 for always buying. But stable-world cost
rises to **.109781319**, versus the hybrid's **.095550061** and .1 for always
buying. Relative and absolute recovery criteria pass; the stable-cost criterion
and therefore the joint criterion fail.

The matched ten-task noiseless control also fails the stable-cost criterion.
The failure cannot be attributed solely to introducing noise. Both conditions
use ten tasks, whereas the earlier positive perfect-evidence test used 100;
that change also changes the per-task change hazard and remaining opportunity
to learn. The earlier results are preserved, not pooled or relabelled.

## What was changed and held fixed

The physical task has a known initial orientation, one possible hidden reversal,
and no repeated change. With probability 1/2 the world stays stable; otherwise
the onset is uniform over tasks 1–10. A fair target X gives reading
`Y=X xor Z xor N`, with independent sensor noise N. Free readings have the
same distribution in either orientation and cannot identify reversal.

The matched conditions have epsilon=0 and epsilon=.05. A purchased target
answer remains **accurate**, costs **.1**, and solves the current task. An
unaided mistake costs 1, and its loss/target stays hidden. Noise makes the
relationship between that target and the sensor ambiguous; it does not make
the purchased answer unreliable or change its price. The supplied noise rate,
prior and observation law are correct. Noise-rate learning and model
misspecification are not tested.

Both full-horizon policies use the same ordinary posterior over hidden onset.
The ordinary objective minimizes full prior-weighted physical cost B; the
recovery objective minimizes **B+R**, where R is recovery cost per remaining
task, averaged equally over onsets. The equal preference weight is unchanged
from the preceding design. Every stable and pre-change fee remains in B.

The hybrid uses ordinary CT4 proposals and enforces its maximum one-task gap
without feedback. Its future proposals do not anticipate that compulsory rule.
The erased-label policy keeps the recovery objective but discards labels before
future inference; purchases still solve the current task. Always buying remains
the analytic .1 comparator. These are same-model controls, not replays of the
larger 401-component controller.

## Noisy costs and all declared criteria

All values are exact expectations expressed as decimals, with no Monte Carlo
sampling or confidence intervals. The common score column evaluates every
policy under B+R, regardless of the objective that selected its actions.

| Policy with 5% sensor noise | Stable cost | Recovery R | Full prior cost B | Common score B + R |
| --- | ---: | ---: | ---: | ---: |
| Ordinary full-horizon objective | 0.095957881 | 0.088057055 | 0.092987279 | 0.181044334 |
| Recovery objective with retained labels | 0.109781319 | 0.072509281 | 0.096634985 | 0.169144266 |
| Hybrid compulsory-check rule | 0.095550061 | 0.096674669 | 0.095888634 | 0.192563303 |
| Recovery objective with erased labels | 0.100000000 | 0.100000000 | 0.100000000 | 0.200000000 |
| Always buy | .100000000 | .100000000 | .100000000 | .200000000 |

Against the hybrid, the recovery objective lowers R **24.997%**, but raises
stable cost **14.894%** and full prior cost **.778%**. Against the ordinary
full-horizon objective, it lowers R **17.656%** while raising full prior cost
**3.923%**. The two full-horizon policies isolate the preference change;
comparison with the hybrid also changes the compulsory checking rule.

Its full prior cost .096634985 remains below always buying because changed
worlds offset part of the stable-world harm. That average does not satisfy
the separately declared stable-cost requirement. No criterion or weight was
changed after observing the result.

## The matched noiseless control matters

| Noise | Policy | Stable cost | Recovery cost | Full prior cost |
| --- | --- | ---: | ---: | ---: |
| 0% | Ordinary full-horizon objective | 0.050000000 | 0.183456349 | 0.065000000 |
| 0% | Recovery objective with retained labels | 0.100000000 | 0.029289683 | 0.077500000 |
| 0% | Hybrid compulsory-check rule | 0.050000000 | 0.213103175 | 0.075000000 |
| 5% | Ordinary full-horizon objective | 0.095957881 | 0.088057055 | 0.092987279 |
| 5% | Recovery objective with retained labels | 0.109781319 | 0.072509281 | 0.096634985 |
| 5% | Hybrid compulsory-check rule | 0.095550061 | 0.096674669 | 0.095888634 |

At ten tasks, the noiseless recovery policy buys at every stable-world task,
whereas the hybrid buys five times. It has much lower recovery cost but twice
the stable cost, so its joint criterion already fails. Sensor noise further
raises the recovery policy's stable cost above .1 through mistaken responses
and raises its recovery cost .029289683 → .072509281.

The earlier 100-task result established a positive example under that horizon
and its associated hazard. This check shows the example does not establish a
uniform guarantee across horizons or noise conditions. It does not invalidate
the earlier calculation, and the ten-task control prevents a misleading claim
that noise alone caused loss of the joint success.

## Every onset and signed effects

| Reversal onset | Ordinary recovery | Recovery objective | Hybrid recovery |
| ---: | ---: | ---: | ---: |
| 1 | 0.156066864 | 0.065565682 | 0.170112142 |
| 2 | 0.067852071 | 0.061989020 | 0.083457936 |
| 3 | 0.069752147 | 0.063172617 | 0.082430358 |
| 4 | 0.072182401 | 0.065000744 | 0.085510408 |
| 5 | 0.075489985 | 0.067473812 | 0.084450549 |
| 6 | 0.080043503 | 0.070848867 | 0.089206591 |
| 7 | 0.076766032 | 0.075431823 | 0.088061285 |
| 8 | 0.084063080 | 0.082934002 | 0.084909839 |
| 9 | 0.098650244 | 0.075867815 | 0.098739496 |
| 10 | 0.099704226 | 0.096808427 | 0.099868088 |

Under noise, recovery cost is lower at every onset than both ordinary and
hybrid policies. Nonetheless, full-episode cost is higher in **7 of 11 worlds**
than ordinary planning and in **5 of 11 worlds** than the hybrid, counting the
stable world. The other four and six worlds respectively improve; there are
no exact ties in those noisy full-episode contrasts.

In the noiseless control, recovery improves at five onsets and ties at five
versus ordinary planning; it improves at nine and ties at one versus the
hybrid. Full cost rises in six and four worlds respectively. Complete per-world
values and signed contrasts are preserved; no favorable onset replaces the
all-onset endpoint.

The known-orientation cost floor is .05 per task under noise and zero in the
noiseless control, because the .1 correct-answer purchase is more expensive
than an optimally oriented sensor response. The unknown-orientation policies
need not attain those diagnostic floors.

## Evidence acquisition and interpretation

The finite check confirms that feedback no longer certifies orientation. In
the fixed initial diagnostic, a contradictory bought signal at task 1 leaves
**P(reversal)=1/2**. A second contradictory bought signal at task 2 raises it
to **190/199, approximately .95477**. All originally supported onset hypotheses
retain positive mass. These are prescribed histories used to check inference,
not recovery-performance estimates or a universal two-answer guarantee.

The acquisition and first-feedback diagnostics in the actual noisy policies are:

| Noisy policy | Capped first-feedback delay | Probability of no post-change purchase | Mean squared orientation error after first feedback, conditional on receiving it |
| --- | ---: | ---: | ---: |
| Ordinary full-horizon objective | 0.102023512 | 0.001126918 | 0.180802300 |
| Recovery objective with retained labels | 0.025243943 | 0.011507434 | 0.207287966 |
| Hybrid compulsory-check rule | 0.100647131 | 0.000263824 | 0.180653640 |
| Recovery objective with erased labels | 0.000000000 | 0.000000000 | 0.546250000 |

Delay is capped by the available post-change window when no purchase occurs.
The recovery policy acquires its first post-change answer earlier on average,
yet has a greater probability of making no post-change purchase on some paths.
Prior observations and choices can already point it in the reversed direction;
absence of a later purchase alone does not prove absence of useful evidence.

Its conditional orientation error immediately after the first paid answer is
also higher than for ordinary or hybrid planning. These policies select
different histories and first-purchase times, so the comparison does not show
an incorrect Bayes update or isolate a causal interpretation defect. The
independent calculations confirm the posterior itself is correct under the
supplied model.

The erased-label control buys every answer in both conditions. It cannot retain
orientation evidence and obtains no acquisition saving; its costs remain .1.
Retaining evidence improves B+R under the chosen objective, but that alone does
not establish acceptable stable-world behavior.

## Why stable worlds become expensive

| Noisy policy | Stable purchases | Stable errors | Mean changed purchases | Mean changed errors |
| --- | ---: | ---: | ---: | ---: |
| Ordinary full-horizon objective | 8.988730816 | 0.060705725 | 6.187196924 | 0.281447088 |
| Recovery objective with retained labels | 9.884925655 | 0.109320628 | 6.450472913 | 0.189839212 |
| Hybrid compulsory-check rule | 8.993528690 | 0.056147744 | 7.433997342 | 0.218872334 |
| Recovery objective with erased labels | 10.000000000 | 0.000000000 | 10.000000000 | 0.000000000 |

Under noise the recovery policy either buys or inverts; it never follows the
sensor in its reachable decision graph. In a stable episode it averages
**.115074345 inverted responses**, versus **.006471310** for the hybrid and
**.011269184** for ordinary planning. These are expected action counts, not
probabilities of at least one error. An inverted response in that stable world
is wrong with probability .95, producing the reported .109320628 expected
stable errors.

Some recovery-policy inversions occur with ordinary posterior reversal
probability as low as **.677996422**. Its expected number of stable-world
unaided decisions whose ordinary posterior error risk exceeds the .1 purchase
price is **.047139295 per episode**. This count is zero for the ordinary and
hybrid policies. The recovery objective can favor those choices because it
weights consequences in changed worlds more strongly. This is consistent
with its objective; it is not a numerical update failure or hidden-onset leak.

For this supplied physical law, stable cost can be decomposed exactly as

```text
.05 + .05 * E[purchases]/10 + .90 * E[wrong-orientation responses]/10.
```

The .05 is the known-orientation noise floor. The second term prices purchases
relative to that floor; the third prices responses in the wrong orientation.
These are diagnostic costs relative to an informed reference, not proof that
all checking expenditure is avoidable for an uncertain agent.

| Stable-world contribution | Ordinary | Recovery objective | Hybrid |
| --- | ---: | ---: | ---: |
| Known-orientation noise floor | .050000000 | .050000000 | .050000000 |
| Purchases above that floor | .044943654 | .049424628 | .044967643 |
| Wrong-orientation responses | .001014227 | .010356691 | .000582418 |
| Total stable cost | .095957881 | .109781319 | .095550061 |

Both purchasing and premature reversal responses contribute to the harm. The
stable-cost requirement is an external check here, not a constraint enforced
by B+R. A fixed preference weight cannot be treated as if it guaranteed that
constraint.

## FEP meaning and next decision

The agent uses a specified generative model, exact ordinary Bayesian/VFE beliefs,
and actions selected by expected consequences. The recovery preference improves
the endpoint it values while harming another required aspect of function. This
is a concrete limitation of this objective in this model, not a disproof of
FEP or a validation of a unique FEP advantage. B+R remains an explicit task-cost
objective rather than a newly asserted canonical EFE.

Do not promote the fixed recovery weight as a generally successful controller.
Keep the larger model's previous baseline. The next proposed analytic question
is whether the stable-cost limit can be represented as an explicit constraint,
using beliefs about the no-change hypothesis while keeping physical state
hidden. Establish feasibility before another policy test or larger campaign;
do not quietly search weights until the current gate passes. No such successor
has been implemented or launched.

## Exact verification and storage

Qualification passed **315 assertions**, including complete contingent policy
trees at horizons 1–3 (3, 15 and 255 trees), erased action strings through
horizon 4, two priors, three qualification noise levels, and both objectives.
It verifies the zero-noise limit against the frozen perfect-evidence code
through horizon 6 and checks the ambiguous-feedback diagnostic exactly.

The independent verifier imports no planner. It solves the normalized Bayes
recursion separately from the main homogeneous integer-weight calculation,
checks every graph edge and selected action, and replays saved actions over
all complete noise strings. It passed **58,712 assertions**, enumerating
**45,692 noise paths** across the main and short verification fixtures. The
main result contains **1,231 decision-graph nodes and 88 world expectations**.
Unobserved noise is integrated exactly; there are no new random samples or
statistical precision claims. This is separate numerical reconstruction by
the same author, not external scientific replication.

All **nine frozen inputs, three source snapshots and ten manifest-listed
outputs** verify. Main computation took **3.451 seconds** and independent
readback **28.445 seconds**, on CPU 0 at nice 10. The .493-second benchmark
forecast **279.808 seconds**, so attached execution met the ten-minute rule.
No failure, correction, restart, parameter tuning or sample extension occurred.
All computation and required verification are complete.

The sealed **917,968-byte** record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noisy-recovery-v1/attempt-01/`.
Stdout is a sibling. Reporting snapshots and derived comparisons are separate
under `reporting-2026-10-27/`. All generated data remain on the external drive;
source and research notes stay in this folder. Manuscripts and sister projects
were not edited.

| Record | SHA-256 |
| --- | --- |
| `FREEZE.json` | `1a4b20f48603a55d48e65b459d0a758d0350002a4c77898c7da7bfe0e0889db8` |
| `QUALIFICATION.json` | `bc114ebf5be3a9cc0cc7c37aa9ee484c33386658bb3c04a3320de62d32b66ea8` |
| `BENCHMARK.json` | `11e681b58ae42a3758da3bfda41a3fe7c0dbd82c0fa2404467d4d5f9a9b5a1e5` |
| `RESULTS.json` | `abb3bf931a11540766de9b0f438d6d84f1d397d63aa330797dc2ac340e930ac8` |
| `MANIFEST.json` | `042c47b376dd68e2b2459803897a69fc3a4dc77fd71922ad72251cd3355acecc` |
| `READBACK.json` | `e78c755a1482d74a994dceb80d99d4894d5adceb68c603b497e4aac7a7fcbc6a` |
