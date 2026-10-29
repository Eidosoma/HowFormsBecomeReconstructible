# A deterministic policy meets the noisy recovery and stable cost criteria

Completed and independently verified 28 October 2026 under the
[prospective specification](FEP_DETERMINISTIC_RECOVERY_V1.md).

**A single deterministic policy now passes all three criteria in the supplied
ten-task noisy model.** Recovery cost is **.089292515**, below the hybrid's
**.096674669** and always buying's .1. Stable cost **.095535118** is below the
fixed hybrid budget **.095550061**. Full prior cost is **.093035942**. Every
purchase and error is included, including costs before a reversal.

Relative to the hybrid, recovery improves **7.636%**, full expected cost
**2.975%**, and stable cost **.01564%**. The stable margin is small:
**.0000149433453125 per task**. This is exact feasibility under a correct
supplied model, not evidence of robustness to noise-rate errors or scale.

The bounded search evaluated **695 candidates**: the unchanged anchor and
694 single-state action overrides. Twelve satisfy the stable budget; exactly
one satisfies the joint criterion. That same candidate minimizes both B+R
and R among the stable-feasible candidates. It proves deterministic existence,
not global deterministic optimality or broad generalization.

## The rule that makes the difference

The anchor is the higher-stable-cost component of the previous optimal
mixture, selected by its frozen S>K. Its full-horizon continuation preference
and multiplier, approximately **2.562254054**, remain fixed. This is the
component's saved multiplier, not a newly tuned value or the mixture's final
supporting multiplier. The only changed action is at one ordinary belief state.

The unique history reaching that state is:

1. Follow the sensor on task 1.
2. Buy accurate answers on tasks 2 through 8.
3. The sensor agrees with those answers on tasks 2 through 6, then disagrees
   on tasks 7 and 8.
4. On task 9, buy another answer instead of immediately inverting the sensor.

Here agree/disagree is `D=Y xor X`, which is observable only after purchase.
At task 9 the posterior reversal probability is **2750841/2826290**, about
**.973304580**; the posterior probability of no change throughout the episode
is about **.024268564**. The policy cannot see the true onset.

If the extra answer agrees with the sensor, the unchanged continuation buys
again on task 10. If it disagrees, the continuation inverts on task 10. The
original anchor inverted on both tasks 9 and 10 without this extra evidence.
Thus one rule change may also affect a later purchase through the updated
beliefs; it is not necessarily only one additional fee on every affected path.

The ordinary current error risk of inversion at the guard is about **.074025878**,
below the .1 answer price. Buying is not justified by immediate task risk alone.
The constrained policy accepts that cost to reduce expensive false reversals
in stable worlds and to obtain evidence for its final action.

The guard is reached with probability **.00193445234375** in stable worlds
(about .19345% of episodes), but with probability **.69833729609375** when
reversal starts at task 7. All world-specific reach probabilities are saved.
These are evaluator probabilities, not information given to the policy.

The deployed rule is a deterministic map from time and beliefs to action.
It uses no episode coin, seed or uninformative free-reading bits as a randomizer.
Its standalone graph has **348 reachable decision states**. Observation noise
still makes episode outcomes variable, so S remains an expected-cost limit.

## Costs against the frozen comparisons

| Policy | Stable S | Recovery R | Full prior B |
| --- | --- | --- | --- |
| Previous hybrid | 0.095550061 | 0.096674669 | 0.095888634 |
| Ordinary full-horizon objective | 0.095957881 | 0.088057055 | 0.092987279 |
| Unconstrained recovery preference | 0.109781319 | 0.072509281 | 0.096634985 |
| Frozen high-S component | 0.095855753 | 0.088256995 | 0.093000368 |
| Previous randomized optimum | 0.095550061 | 0.088998756 | 0.093041923 |
| Deterministic candidate 37 | 0.095535118 | 0.089292515 | 0.093035942 |
| Always buy | .100000000 | .100000000 | .100000000 |

The randomized constrained optimum retains the lower B+R value. The new
policy's **B+R=.182328457** exceeds that exact lower bound by
**.000287778500310**, about **.1581%**. Its R is **.3301%** higher than the
mixture's, while B is **.00643%** lower. Removing episode randomization does
not preserve every endpoint of the mixture unchanged.

Against ordinary planning, the deterministic policy reduces S **.4406%**,
while increasing B **.0523%** and R **1.4030%**. Ordinary planning remains a
strong reference but exceeds the specified stable budget. The result should
not be described as a general advantage over Bayesian planning.

Against the previous unconstrained recovery preference, stable cost falls
**12.977%** and B **3.724%**, while R rises **23.146%**. That earlier fast recovery
violated the stable budget. The deterministic result satisfies the functional
trade-off rather than preserving its earlier recovery score without cost.

## The complete stable-feasible subset

Actions B, F and R mean buy, follow and invert. The state includes the full
ordinary posterior; equal task numbers alone do not identify the guard.

| Candidate | Task | Changed action | Stable S | Recovery R | B+R | Joint criterion |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | B to F | 0.090828103 | 0.107176390 | 0.204624788 | FAIL |
| 5 | 3 | B to F | 0.091101625 | 0.099792870 | 0.193439493 | FAIL |
| 7 | 4 | B to F | 0.091297704 | 0.100455785 | 0.194117221 | FAIL |
| 9 | 5 | B to F | 0.092062596 | 0.100100600 | 0.193789131 | FAIL |
| 11 | 6 | B to F | 0.091775001 | 0.102783737 | 0.196593394 | FAIL |
| 13 | 7 | B to F | 0.091666213 | 0.106459494 | 0.200451916 | FAIL |
| 15 | 8 | B to F | 0.092024087 | 0.111190697 | 0.205389648 | FAIL |
| 17 | 9 | B to F | 0.092364067 | 0.119020627 | 0.213233387 | FAIL |
| 19 | 10 | B to F | 0.092538651 | 0.146185913 | 0.240503908 | FAIL |
| 23 | 9 | B to F | 0.095515773 | 0.111668470 | 0.207962943 | FAIL |
| 29 | 8 | B to F | 0.095497880 | 0.106552223 | 0.202993472 | FAIL |
| 37 | 9 | R to B | 0.095535118 | 0.089292515 | 0.182328457 | PASS |

All other candidates violate S<=K. Candidate 37 is the primary choice, the
minimum-R feasible choice and the sole passing witness within this fixed
class. No second override, expanded search, parameter adjustment or selective
endpoint was introduced after observing results. The search is an exact design
calculation within the known model, not a held-out empirical evaluation.

## Acquisition and economic consequences

| Policy | Stable purchases | Stable errors | Post-change purchases | Post-change errors | Capped first-purchase delay | No post-change purchase probability |
| --- | --- | --- | --- | --- | --- | --- |
| Hybrid | 8.993528690 | 0.056147744 | 3.834633121 | 0.173268344 | 0.100647131 | 0.000263824 |
| Frozen high-S component | 8.989932312 | 0.059564303 | 2.617007233 | 0.234149638 | 0.101712026 | 0.001006769 |
| Deterministic policy | 8.993704494 | 0.055980730 | 2.698652435 | 0.230067378 | 0.101141363 | 0.000629551 |

Relative to the anchored component, the added confirmation increases purchases
and reduces errors in stable worlds enough to satisfy the budget. It also
reduces the probability of making no post-change purchase. All inference
updates remain the same exact Bayesian rule; the intervention changes
acquisition and its downstream decisions, not the inference mechanism.

Relative to the hybrid, the deterministic policy buys fewer post-change
answers and makes more post-change errors on average. Purchase savings exceed
the error cost. Its first post-change answer is slightly later on average,
so successful recovery does not mean buying every answer sooner. Different
feedback histories do not establish a causal interpretation defect.

## Every onset and full episode accounting

| Onset | Deterministic recovery | Hybrid recovery | Full episode cost change per task |
| --- | --- | --- | --- |
| 1 | 0.156315635 | 0.170112142 | -0.013796507347 |
| 2 | 0.068128483 | 0.083457936 | -0.013796507347 |
| 3 | 0.070049663 | 0.082430358 | -0.009904555630 |
| 4 | 0.072537752 | 0.085510408 | -0.009080859050 |
| 5 | 0.076207385 | 0.084450549 | -0.004945898684 |
| 6 | 0.080474733 | 0.089206591 | -0.004365929206 |
| 7 | 0.085937571 | 0.088061285 | -0.000859048114 |
| 8 | 0.084747730 | 0.084909839 | -0.000056681112 |
| 9 | 0.098714299 | 0.098739496 | 0.000017674300 |
| 10 | 0.099811893 | 0.099868088 | -0.000116094191 |

Recovery cost is lower than the hybrid at all ten onsets. Full episode cost
is lower in ten of the eleven worlds, counting the stable world, but is
**.0000176743 per task higher at onset 9**. The mean full cost still improves.
This exception matters: lower post-change cost alone does not guarantee a
lower complete bill in every world.

Against ordinary planning, full episode cost improves in three worlds and
worsens in eight; recovery is worse at all ten onsets. Against the previous
unconstrained recovery preference, full cost improves in six worlds and
worsens in five; recovery is again worse at all onsets. All signed differences
are saved separately, including comparisons with both mixture components.

The earlier exact minimum-R certificates remain unchanged. At the noiseless
budget .05, minimum R=.128019841 exceeds .1 even with randomization. In the
noisy erased-label class, minimum R=.107564896 also exceeds .1. Deterministic
policies cannot improve on those randomized lower bounds. These controls are
inherited and verified against their sealed records, not rerun or relabelled
as new experiments. Different budgets prevent interpreting the noisy success
as evidence that sensor noise helps.

## Exact methods and verification

The main calculation uses an additive intervention identity: the anchor's
full expected cost plus the probability of reaching the changed state times
the difference between its alternative and original continuations. The prefix
policy is unchanged, the override occurs at most once, and both paid-label
branches remain active. It saves every candidate's world costs and gate, plus
a common table of **2,221 continuation states**. The anchor has 347 reachable
states, giving exactly 1+2*347=695 candidates.

Qualification passed **1,341 counted assertions** in **38 short cases**.
Every short candidate was replayed over complete noise strings at T=1–3,
two priors, three noise levels and two fixed multipliers, with additional
T=4 fixtures. There were 28 cases with a stable-feasible candidate and ten
without one. Qualification took **.221 seconds**.

The independent verifier imports no planner. It reconstructs normalized Bayes
Bellman decisions at the fixed anchor multiplier, checks ordinary posterior
edges and the deterministic action interface, and propagates integer masses
through each complete candidate graph. This does not use the main local-cost
difference identity. It reconstructs every world and selection, checks the
standalone chosen graph and first-feedback diagnostics, verifies the frozen
comparisons and inherited bounds, and checks feasible J against the earlier
randomized lower bound.

It passed **122,873 assertions**, covering **766 candidates, 7,987 candidate
world expectations, 2,294 continuation states and one selected standalone
graph**, including short fixtures. The main result alone has 7,645 candidate
world rows. This is separate numerical reconstruction by the same author,
not external replication or sampled statistical evidence.

Main calculation took **3.242 seconds**, verification **23.689 seconds**, on
one CPU at nice 10. The .238-second benchmark forecast **158.611 seconds**,
so attached execution met the ten-minute rule. All **14 frozen inputs, three
snapshots and ten manifest-listed outputs** verify. No failure, correction,
restart, scientific rerun or parameter tuning occurred. All work is complete;
nothing remains running.

## FEP meaning and next test

The project now has a deterministic feasibility witness linking generative
beliefs, chosen paid evidence and an explicit functional constraint. A high
probability of reversal does not eliminate the economic value of checking
before a costly false reversal. Evidence remains useful for subsequent action;
the erased-label control's exact bound rules out the same target without it.

This is a supplied-model, constrained task-cost policy. It is not a newly
claimed canonical EFE, a unique FEP advantage, an online learned rule, or a
validated improvement in the larger 401-component model. That model retains
its prior hybrid baseline and failed joint criterion. Supplied-feedback
improvement and autonomous recovery evidence remain distinct.

The next proposed test is to evaluate this fixed policy under small errors
in its assumed sensor-noise rate, including the full bill and stable-budget
violations. The small stable margin makes that calibration question useful
before a larger campaign. Compare fixed controls under the same perturbed
worlds and preserve failures without retuning the guard. No such successor
or larger-model transfer has been launched.

## Storage and provenance

The sealed **4,588,049-byte** record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-deterministic-recovery-v1/attempt-01/`.
Stdout is a sibling. This report, exact derived comparisons, generator and
completion provenance are separate in `reporting-2026-10-28/`. Source and
small research notes remain here; all generated output data use the external
FEP store. Manuscripts and sister projects were not edited.

| Record | SHA-256 |
| --- | --- |
| FREEZE.json | `229fdd2797eb62e80d3fa4c63e5d70bc34af6ddc90c7042d4d545e3a76fa50eb` |
| QUALIFICATION.json | `e752c9f99dffb6ae65e8261b5d9a5b5cc1851f31351a2da48d4c2640289a4d10` |
| BENCHMARK.json | `31388b14da46041e0fef4cfc968fc4f7742dae955dbca8bc8215a09d298f8359` |
| RESULTS.json | `25a717bca9d0486e39bb73d1e341465cfd8ba462d1124d111ff2a3c2c3a32638` |
| MANIFEST.json | `cdddfa85af314ab120348d55baa10f7cfe2187181c9f18f7ecb764d246e94ed6` |
| READBACK.json | `6a338cab734e29badeb994873be26d1c98c0c79bcb231ef36381b512aa9f8ced` |
