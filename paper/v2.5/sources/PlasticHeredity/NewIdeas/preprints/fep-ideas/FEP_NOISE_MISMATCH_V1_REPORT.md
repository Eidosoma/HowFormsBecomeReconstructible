# Recovery gains survive noise mismatch but the stable cost guarantee fails

Completed and independently verified 28 October 2026 under the
[prospective specification](FEP_NOISE_MISMATCH_V1.md).

**Both declared robustness verdicts fail.** The frozen deterministic policy
passes at true noise rates 4% and 5%, but fails the stable-cost criterion at
6%. Recovery still beats both the matched hybrid and always buying at all
three rates. Total expected physical cost is also lower than the hybrid.
The cost-protection failure does not erase those remaining functional gains.

At 6% true noise, recovery is **5.923% cheaper** and full prior cost **2.290%
lower** than the same frozen hybrid in the same world. Stable cost is
**1.358% above the original fixed budget**, and **.0310% above the matched
hybrid**. The exact nominal success remains valid; it does not provide the
claimed robustness across this three-point test.

## What was held fixed

The agent still assumes **5%** independent sensor noise. Its saved posterior
transitions, task-9 confirmation rule, continuation decisions and preferences
are unchanged. The six comparison graphs and previous mixture weights are
also frozen. Only the actual sensor noise changes to **4%, 5% or 6%**: one
percentage point below or above the assumed rate. No model learning,
replanning, controller search, guard adjustment or new random sample occurs.

The task retains ten decisions, a known initial orientation, probability 1/2
of one hidden uniform-onset reversal, .1 for an accurate purchased answer,
and unit unaided-error cost. Unbought targets and losses remain hidden.
Purchased answers stay correct; noise affects the sensor-to-target relation.
The known-orientation noise floor changes with the actual rate.

S is stable-world cost per task, B is prior-weighted full physical cost, and R
is post-change cost per remaining task averaged equally across onsets. Every
purchase and error is charged. The original stable budget stays fixed at
**K=.0955500613134765625**, rather than moving after outcomes.

## Primary and matched comparison results

| True noise | Policy S | Hybrid S | Policy R | Hybrid R | Policy B | Hybrid B |
| --- | --- | --- | --- | --- | --- | --- |
| 4% | 0.094306553 | 0.094340304 | 0.085427001 | 0.094353415 | 0.090599751 | 0.094066535 |
| 5% | 0.095535118 | 0.095550061 | 0.089292515 | 0.096674669 | 0.093035942 | 0.095888634 |
| 6% | 0.096847253 | 0.096817212 | 0.093115216 | 0.098977431 | 0.095498889 | 0.097736776 |

Both gates require R below .1 and below the hybrid evaluated at the same
actual noise rate. The primary gate additionally requires S<=the original K.
The separate matched gate requires S<=the hybrid's S at that actual rate.
Neither replaces the other after results.

| True noise | Original fixed-budget gate | Matched-hybrid gate | S minus fixed K | S minus matched hybrid S |
| --- | --- | --- | --- | --- |
| 4% | PASS | PASS | -0.001243507894 | -0.000033750199 |
| 5% | PASS | PASS | -0.000014943345 | -0.000014943345 |
| 6% | FAIL | FAIL | 0.001297191400 | 0.000030040672 |

At 4% noise, recovery and full-cost improvements over the hybrid are **9.461%**
and **3.685%**. At 5% they reproduce the earlier **7.636%** and **2.975%**
improvements exactly. At 6% they shrink to **5.923%** and **2.290%**.
All recovery comparisons to .1 and the matched hybrid pass.

At 6%, both controllers exceed the original stable budget, reflecting the
changed physical task. The deterministic policy additionally exceeds the
matched hybrid by **.000030040672126 per task**. Thus the failed matched gate
cannot be explained solely by keeping an old absolute budget in a noisier
world. The excess is small but violates the specified criterion exactly.
The study uses rational expectations, not a sampled uncertainty interval.

## The confirmation rule still helps its anchored component

The fixed rule buys another answer at the task-9 state where the sensor first
agreed with purchased targets five times and then disagreed twice. That
history retains an assumed reversal probability of **.973304580** at all
true noise rates, because the agent's likelihood remains .05.

The rule continues to lower stable cost relative to the unmodified anchored
component: by **.000219903**, **.000320635** and **.000430549 per task** at
4%, 5% and 6% respectively. The worse-noise failure does not show that the
confirmation rule stopped helping. It shows that this full fixed policy no
longer meets its cost-protection requirement.

The previous randomized mixture also fails stable protection at 6%:
S=.097035505 exceeds both K and the matched hybrid's .096817212. Sensitivity
therefore predates the move to a deterministic rule. This evaluation does
not optimize a different mixture or apply nominal optimality bounds to the
perturbed worlds.

## Belief calibration under the changed likelihood

The diagnostic below conditions on each policy's retained graph state. It
uses the true rate only in offline evaluation. That value is never supplied
to the agent and never changes its actions.

| True noise | Retained-posterior Brier loss | Calibration discrepancy | True reversal probability at guard | Stable-world guard probability |
| --- | --- | --- | --- | --- |
| 4% | 0.067905636 | 0.000157452 | 0.982732735 | 0.001304596 |
| 5% | 0.070965334 | 0.000000000 | 0.973304580 | 0.001934452 |
| 6% | 0.074159616 | 0.000135875 | 0.962048839 | 0.002642054 |

At the confirmation state, the true conditional reversal probability is
**.982732735** at 4% noise and **.962048839** at 6%, compared with the retained
belief **.973304580**. The agent is underconfident there in the cleaner world
and overconfident in the noisier world. Stable-world reach probability rises
from about **.13046%** to **.26421%** across those conditions, changing how often
the confirmation costs and benefits occur.

Across all decisions, the exact calibration discrepancy is positive off the
nominal likelihood and zero at 5%. Its value is squared probability error,
not a physical task-cost amount. The verifier checks the decomposition

```text
retained-posterior Brier loss
  = true conditional variance given retained state + calibration discrepancy.
```

A correct update under the assumed .05 likelihood is still internally
consistent when that likelihood is wrong about the world. The mismatch is
not a numerical Bayes-update defect. Physical difficulty also changes across
these conditions, so these diagnostics do not by themselves identify how
much performance could be recovered by learning or replanning at the true rate.

The erased-label control has zero calibration discrepancy at every rate,
but its Brier loss is **.17875** and physical cost remains .1. Its coarse
retained state carries little useful information. Zero state-conditional
miscalibration alone therefore does not establish useful inference or action.

## Acquisition and economic accounting

| True noise | Policy | Stable purchases | Stable errors | Post-change purchases | Post-change errors | Capped delay | No post-change purchase probability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4% | Deterministic policy | 8.996435425 | 0.043421992 | 2.678381852 | 0.204864726 | 0.100619910 | 0.000356457 |
| 4% | Hybrid | 8.996042981 | 0.043798738 | 3.826981789 | 0.158920728 | 0.100395702 | 0.000166985 |
| 5% | Deterministic policy | 8.993704494 | 0.055980730 | 2.698652435 | 0.230067378 | 0.101141363 | 0.000629551 |
| 5% | Hybrid | 8.993528690 | 0.056147744 | 3.834633121 | 0.173268344 | 0.100647131 | 0.000263824 |
| 6% | Deterministic policy | 8.989913658 | 0.069481161 | 2.719159976 | 0.254850401 | 0.101888218 | 0.001008634 |
| 6% | Hybrid | 8.990271285 | 0.069144992 | 3.842632686 | 0.187442039 | 0.100972871 | 0.000384136 |

At 6% noise the deterministic policy buys slightly fewer answers in stable
worlds than the matched hybrid, but its additional errors more than offset
that small fee saving. In changed worlds it still buys fewer post-change
answers and makes more post-change errors; the purchase savings preserve its
recovery advantage. The absolute budget failure and the surviving recovery
benefit are both visible in the full bill.

First-post-change feedback is slightly later on average, and absent on some
paths. Absence of a post-change purchase alone does not establish absence of
useful earlier information. These policies select different histories;
the diagnostics do not isolate a causal interpretation defect.

## All onsets and fixed controls

| Reversal onset | Recovery at 4% | Recovery at 5% | Recovery at 6% |
| --- | --- | --- | --- |
| 1 | 0.151249930 | 0.156315635 | 0.161276320 |
| 2 | 0.061388811 | 0.068128483 | 0.074751467 |
| 3 | 0.063737753 | 0.070049663 | 0.076257766 |
| 4 | 0.066771614 | 0.072537752 | 0.078215221 |
| 5 | 0.071167407 | 0.076207385 | 0.081150711 |
| 6 | 0.076460670 | 0.080474733 | 0.084450752 |
| 7 | 0.083444828 | 0.085937571 | 0.088552941 |
| 8 | 0.081406626 | 0.084747730 | 0.087975486 |
| 9 | 0.098777837 | 0.098714299 | 0.098751169 |
| 10 | 0.099864533 | 0.099811893 | 0.099770323 |

The .1 absolute threshold applies to the declared mean R. Onset 1 remains
above .1 at every noise rate. Relative to the hybrid, however, recovery cost
is lower at all ten onsets in each condition.

| True noise | Full cost lower | Equal | Higher | Recovery lower | Equal | Higher |
| --- | --- | --- | --- | --- | --- | --- |
| 4% | 10 | 0 | 1 | 10 | 0 | 0 |
| 5% | 10 | 0 | 1 | 10 | 0 | 0 |
| 6% | 9 | 0 | 2 | 10 | 0 | 0 |

Full-cost comparisons count the stable world as well as ten onset worlds.
At 4% and 5%, the sole full-cost worsening is onset 9. At 6%, the stable world
also becomes slightly costlier. Thus nine changed worlds still have lower
complete bills at 6%, while onset 9 does not. All signed comparisons against
ordinary, recovery, anchored, low-component and mixed controls are retained
in the reporting artifact, including adverse changes and ties.

| True noise | Frozen policy | Stable S | Recovery R | Full prior B |
| --- | --- | --- | --- | --- |
| 4% | High-S mixture component | 0.094526456 | 0.084137550 | 0.090460115 |
| 4% | Deterministic policy | 0.094306553 | 0.085427001 | 0.090599751 |
| 4% | Erased labels / always buy | 0.100000000 | 0.100000000 | 0.100000000 |
| 4% | Hybrid | 0.094340304 | 0.094353415 | 0.094066535 |
| 4% | Low-S mixture component | 0.088764694 | 0.095856272 | 0.090310673 |
| 4% | Frozen randomized mixture | 0.094155973 | 0.084891068 | 0.090450506 |
| 4% | Ordinary full-horizon policy | 0.094580834 | 0.083945523 | 0.090421749 |
| 4% | Unconstrained recovery preference | 0.107049857 | 0.066989737 | 0.093261314 |
| 5% | High-S mixture component | 0.095855753 | 0.088256995 | 0.093000368 |
| 5% | Deterministic policy | 0.095535118 | 0.089292515 | 0.093035942 |
| 5% | Erased labels / always buy | 0.100000000 | 0.100000000 | 0.100000000 |
| 5% | Hybrid | 0.095550061 | 0.096674669 | 0.095888634 |
| 5% | Low-S mixture component | 0.091101625 | 0.099792870 | 0.093646624 |
| 5% | Frozen randomized mixture | 0.095550061 | 0.088998756 | 0.093041923 |
| 5% | Ordinary full-horizon policy | 0.095957881 | 0.088057055 | 0.092987279 |
| 5% | Unconstrained recovery preference | 0.109781319 | 0.072509281 | 0.096634985 |
| 6% | High-S mixture component | 0.097277802 | 0.092316717 | 0.095568577 |
| 6% | Deterministic policy | 0.096847253 | 0.093115216 | 0.095498889 |
| 6% | Erased labels / always buy | 0.100000000 | 0.100000000 | 0.100000000 |
| 6% | Hybrid | 0.096817212 | 0.098977431 | 0.097736776 |
| 6% | Low-S mixture component | 0.093509592 | 0.103674496 | 0.096992918 |
| 6% | Frozen randomized mixture | 0.097035505 | 0.093047026 | 0.095660163 |
| 6% | Ordinary full-horizon policy | 0.097447431 | 0.092124654 | 0.095598034 |
| 6% | Unconstrained recovery preference | 0.112848023 | 0.078011825 | 0.100202704 |

All controls use their original .05 beliefs and saved actions. The mixture
uses its original component-choice weights. Its Brier losses and calibration
terms are averaged while retaining component identity as part of state.
Always buying is represented physically by the erased-label graph and also
checked against the analytic .1 comparator.

## Verification and records

The evaluator uses rational backward recursion for physical costs and
forward state-reach probabilities for calibration. Qualification passed
**11,258 counted assertions** across **2,730 short cases**, covering all
contingent trees through T=3, two priors and five true noise rates, plus an
erased-label fixture. Qualification took **5.644 seconds**.

The independent verifier imports no evaluator or planner. It replays complete
noise bitstrings with integer masses, reconstructs costs and visits, checks
the .05 posterior edges and graph identities, independently computes the
calibration decomposition and verifies mixture arithmetic, nominal
reproduction and both gates. It passed **291,223 assertions**, covering
**236,644 complete noise paths, 247 graph/world expectations, 2,075 checked
graph states and 6,182 calibration-state records**, including short fixtures.
The main record contains 231 direct graph/world expectations and 33 mixture
world expectations. The nominal shared costs and listed diagnostics reproduce
exactly. This is separate reconstruction by the same author, not external
replication or sampled evidence.

Main evaluation took **5.507 seconds**, verification **3.390 seconds**, on one
CPU at nice 10. The 7% timing-only benchmark took **1.797 seconds** and
forecast **141.565 seconds**; it is not a fourth scientific condition. Attached
execution met the ten-minute rule. No failure, correction, restart, retuning,
scientific rerun or condition extension occurred.

All **16 frozen inputs, three snapshots and eleven manifest-listed outputs**
verify. The sealed **3,975,179-byte** attempt is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-mismatch-v1/attempt-01/`.
Stdout is a sibling. Report snapshots, exact derived comparisons and completion
provenance are separate in `reporting-2026-10-28/`. All generated data remain
on the external drive. Source and research notes stay here; manuscripts and
sister projects were not edited. Nothing remains running.

## FEP meaning and next decision

The useful evidence-acquisition strategy survives this noise perturbation
comparatively: it retains lower mean recovery and full cost than the hybrid.
Its nominal cost guarantee does not survive. This identifies a distinction
between internally coherent beliefs under a supplied likelihood and functional
protection when that likelihood is wrong.

The next proposed bounded question is whether explicitly representing noise
uncertainty can preserve recovery while satisfying the cost limit across the
three declared rates. Establish that feasibility before a larger campaign;
retain these frozen controllers as controls and keep budget violations visible.
This study has not learned a noise model, constructed a robust controller or
proved that robustness is impossible. Three evaluated rates also do not prove
a result throughout the continuous interval between them.

The action objective remains constrained task cost, not a new canonical EFE
or a unique FEP advantage. The larger 401-component model retains its prior
hybrid baseline and failed joint criterion. Earlier positive nominal results,
supplied-feedback evidence and negative robustness evidence remain distinct.
No successor, robust-controller construction or larger-model transfer has
been launched.

| Record | SHA-256 |
| --- | --- |
| FREEZE.json | `9f9cf5aad135ba7897c3f1fcbb57166e99705823cc90cbc0d49a4512acf696ad` |
| GRAPHS.json | `fae0f8726213d0c30f785fe0d9ce86a65976a923941114a26a9285caabe1f703` |
| QUALIFICATION.json | `9f7d33daa8d12ec92d7ae132bcd96848b63f7a6d184028860013accc3f5cc019` |
| BENCHMARK.json | `5a2a953f901e4f2f60cd3f60b0099282346d678970ae51c92a122963e07ede65` |
| RESULTS.json | `c668d060d704a688489eab5ff4c29b8357a6f49c8d2a0eac6f22473f3bcda15d` |
| MANIFEST.json | `ec13f6929a93fa0053194e16f569e72476f487ecbca2f609144b38160f1e3271` |
| READBACK.json | `a1005c0275fa3ad343d5020636f415896d014a4a0ee2948223069abd780976c9` |
