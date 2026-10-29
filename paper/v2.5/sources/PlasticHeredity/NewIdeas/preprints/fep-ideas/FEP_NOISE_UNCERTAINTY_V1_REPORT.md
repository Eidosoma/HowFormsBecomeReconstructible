# Robust recovery is feasible; learning the noise rate is not necessary for it

Completed and independently verified 28 October 2026 under the
[prospective protocol](FEP_NOISE_UNCERTAINTY_V1.md).

**The joint-noise model passes at all three tested noise rates.** Its
episode-level mixture keeps stable cost within the original fixed budget,
recovers more cheaply than always buying, and beats the frozen hybrid's
recovery cost in the same worlds. Every purchased answer is charged.
The exact certificate also proves minimum mean B+R subject to all three
stable-cost constraints in this finite randomized policy class.

**The simpler control passes too.** Changing only the weights of two existing
policies restores the same functional guarantees. Those policies still assume
5% noise. Learning the noise rate is therefore not necessary for feasibility
in this test. The new optimum improves mean B+R by only
**0.2793%** over this two-policy control;
that comparison changes policy-search scope as well as the inference model.

## Model and fixed requirements

The agent has ten tasks and a 1/2 prior probability of one hidden reversal,
uniform over onset times. The free sensor observes a fair target through the
current orientation and noise. An accurate purchased target costs .1; an
unaided error costs 1. Unbought targets and losses remain hidden. Free sensor
readings alone provide no evidence about orientation or reliability.

The new hidden episode parameter is sensor noise: 4%, 5% or 6%, initially
equally likely and independent of reversal onset. The agent keeps an ordinary
joint posterior over 33 noise/onset hypotheses. A purchased target updates
both uncertainties; they need not remain independent. No true noise or onset
enters the policy's action interface. Noise is constant within an episode and
there is no learning between episodes or discovery of a new model family.

S is stable-world cost per task. B includes the whole episode, before and
after a reversal, weighted by the declared prior. R averages post-change cost
per remaining task over the ten onsets. The objective is the uniform mean
C=mean(B+R) across noise classes. The fixed budget is
**K=0.0955500613134765625** at each rate. Success additionally requires R<.1 and R below
the same frozen hybrid at that true rate. These are expectations, not a
pathwise cap on an individual episode's bill.

## Verified outcomes

| Noise | Joint mixture S | Joint mixture R | Hybrid R | Joint mixture B | Fixed-pool R |
| --- | --- | --- | --- | --- | --- |
| 4% | 0.092527218 | 0.089246880 | 0.094353415 | 0.090603995 | 0.089510635 |
| 5% | 0.094010189 | 0.093072589 | 0.096674669 | 0.093257088 | 0.093546244 |
| 6% | 0.095550061 | 0.096831025 | 0.098977431 | 0.095914277 | 0.097524308 |

Relative to the matched hybrid, the joint mixture reduces recovery cost by
**5.412%, 3.726% and 2.169%** at 4%, 5% and 6% noise. Full prior cost falls
**3.681%, 2.744% and 1.865%**. Its S is also below the matched hybrid at all
three rates. The 6% stable constraint is exactly binding; the other two have
positive margins. Always buying has S=B=R=.1 and exceeds K.

| Noise | Policy | Stable S | Recovery R | Full prior B |
| --- | --- | --- | --- | --- |
| 4% | Joint-noise mixture | 0.092527218 | 0.089246880 | 0.090603995 |
| 4% | Fixed-pool mixture | 0.091884663 | 0.089510635 | 0.090391595 |
| 4% | Frozen hybrid | 0.094340304 | 0.094353415 | 0.094066535 |
| 4% | Best saved feasible deterministic | 0.088474667 | 0.097545376 | 0.090521850 |
| 4% | Unconstrained joint-noise | 0.106178901 | 0.067692357 | 0.092999186 |
| 4% | Erased-label constrained mixture | 0.093325092 | 0.110642222 | 0.098959951 |
| 5% | Joint-noise mixture | 0.094010189 | 0.093072589 | 0.093257088 |
| 5% | Fixed-pool mixture | 0.093675965 | 0.093546244 | 0.093296679 |
| 5% | Frozen hybrid | 0.095550061 | 0.096674669 | 0.095888634 |
| 5% | Best saved feasible deterministic | 0.090648894 | 0.101245896 | 0.093725197 |
| 5% | Unconstrained joint-noise | 0.108471124 | 0.073110322 | 0.096037266 |
| 5% | Erased-label constrained mixture | 0.094437577 | 0.110518475 | 0.099949939 |
| 6% | Joint-noise mixture | 0.095550061 | 0.096831025 | 0.095914277 |
| 6% | Fixed-pool mixture | 0.095550061 | 0.097524308 | 0.096221644 |
| 6% | Frozen hybrid | 0.096817212 | 0.098977431 | 0.097736776 |
| 6% | Best saved feasible deterministic | 0.092859002 | 0.104875048 | 0.096914536 |
| 6% | Unconstrained joint-noise | 0.111032619 | 0.078507215 | 0.099225069 |
| 6% | Erased-label constrained mixture | 0.095550061 | 0.110394728 | 0.100939926 |

The unconstrained joint-noise policy still overspends in stable worlds.
Adding a richer belief model alone does not enforce the functional budget.
The erased-label constrained policy meets every stable budget but fails
recovery at every rate. Its nominal 5% R is .110518475. The inherited exact
5% erased-label minimum R at the same K is
**0.107564895767>.1**; its saved certificate and
independent verification record were checked. Since 5% is one required world,
this rules out joint robust success for that erased-label class. It does not
extend a nominal bound to different physical noise rates.

## What the certificate proves, and what randomization does

The solver minimized C under S at 6% <= K, using an exact supporting-chord
search. Its solution also meets S<=K at 4% and 5%, checked directly without a
monotonicity assumption. The relaxation's lower bound is consequently attained
by a feasible solution of the full three-constraint problem:

```text
C = 0.186308617797262
mu = 3.208408181220860
C = min_policy(C_policy + mu*S_6%) - mu*K
exact duality gap = 0
```

The episode-start choice uses 0.299563705309 on `oracle006`, 0.700436294691 on `oracle004`.
It is independent of the hidden noise and reversal. Both components then act
deterministically on time and their joint beliefs. The mixture, not each
component separately, meets the combined requirements.

| Noise | Component | Episode weight | Stable S | Recovery R | Full prior B |
| --- | --- | --- | --- | --- | --- |
| 4% | oracle006 | 0.299563705309 | 0.088474667 | 0.097545376 | 0.090521850 |
| 4% | oracle004 | 0.700436294691 | 0.094260420 | 0.085697766 | 0.090639127 |
| 5% | oracle006 | 0.299563705309 | 0.090648894 | 0.101245896 | 0.093725197 |
| 5% | oracle004 | 0.700436294691 | 0.095447753 | 0.089577016 | 0.093056887 |
| 6% | oracle006 | 0.299563705309 | 0.092859002 | 0.104875048 | 0.096914536 |
| 6% | oracle004 | 0.700436294691 | 0.096700978 | 0.093390744 | 0.095486484 |

None of the **9 saved deterministic candidates** passes jointly.
The best stable-feasible candidate encountered, `oracle006`, exceeds .1
recovery cost at 5% and 6% and loses to the hybrid at all three rates.
This is not proof that no deterministic robust policy exists. The oracle
search certifies the randomized optimum, not global deterministic optimality.

The erased arm also has an exact three-budget optimum, C=0.210468413627,
but stable-feasible optimality is separate from the failed recovery criterion.

## The conservative fixed-policy control

The previous high-S and low-S components remain unchanged, including their
5% likelihood and posterior transitions. Only the episode-start probability
of the high-S component changes: from about .93570 in the earlier nominal
mixture to **0.541495628412**. The low-S component takes the
remaining probability. The exact feasible high-component interval is
[0.000000000000, 0.541495628412]; the chosen
endpoint minimizes mean B+R within this fixed pool.

Its C is **0.186830368568**, and it passes every primary recovery
and stable criterion as well as all matched-hybrid stable comparisons.
This establishes a simple robust fallback without a new noise-learning rule.
It remains an episode mixture, not a deterministic or per-episode guarantee.

Against the old unconstrained 5% recovery planner under the same uniform
noise distribution and B+R objective, the new unconstrained joint model lowers
C by **0.000012810396**, about **.007571%**.
The improvement is in full cost; its R is slightly higher at every rate.
Neither unconstrained policy satisfies the stable budget. Do not describe
this matched-objective comparison as a demonstrated recovery gain.

## How much noise learning occurred

The uniform initial noise probabilities have multiclass Brier loss 2/3.
For the final mixture, terminal beliefs give:

| True noise | Expected probability on true noise | Noise Brier loss |
| --- | --- | --- |
| 4% | 0.337441260066 | 0.660720775801 |
| 5% | 0.333343494276 | 0.669360019901 |
| 6% | 0.337408139983 | 0.661726309972 |

Averaging over the full joint prior, probability on the true noise class is
**0.336064298109** and Brier loss is
**0.663935701891**. The Brier improvement is
**0.002730964775**, or **0.4096%** of the initial loss.
The verifier checks exactly that mean Brier loss equals one minus expected
probability on the true class. Erased-label beliefs stay uniform with zero gain.

There is measurable but small learning among nearby supplied noise rates in
ten tasks. This proper-score improvement is not a physical-cost saving and
does not prove that belief movement caused the economic improvement. In
particular, the fixed-pool control already achieves feasibility.

## Acquisition, interpretation and economics

| Noise | Policy | Stable buys | Stable errors | Post-change buys | Post-change errors | Capped delay | No post-change buy probability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4% | Joint-noise mixture | 8.709480 | 0.054324 | 2.700739 | 0.232633 | 0.129261 | 0.000294 |
| 4% | Fixed-pool mixture | 8.553724 | 0.063474 | 2.587972 | 0.252351 | 0.145005 | 0.000611 |
| 4% | Frozen hybrid | 8.996043 | 0.043799 | 3.826982 | 0.158921 | 0.100396 | 0.000167 |
| 5% | Joint-noise mixture | 8.710319 | 0.069070 | 2.726922 | 0.256963 | 0.129375 | 0.000510 |
| 5% | Fixed-pool mixture | 8.554375 | 0.081322 | 2.610380 | 0.277810 | 0.145235 | 0.001005 |
| 5% | Frozen hybrid | 8.993529 | 0.056148 | 3.834633 | 0.173268 | 0.100647 | 0.000264 |
| 6% | Joint-noise mixture | 8.710357 | 0.084465 | 2.753452 | 0.280736 | 0.129664 | 0.000805 |
| 6% | Fixed-pool mixture | 8.553839 | 0.100117 | 2.632932 | 0.302793 | 0.145704 | 0.001517 |
| 6% | Frozen hybrid | 8.990271 | 0.069145 | 3.842633 | 0.187442 | 0.100973 | 0.000384 |

The retained policies acquire evidence autonomously and interpret purchased
labels through their declared generative model. The erased arm still buys
accurate answers for current tasks but cannot use them for future inference;
its recovery failure persists even under optimal budgeted action. For the
unconstrained retained arm, the failure is economic: stable spending remains
too high despite useful evidence. These comparisons keep evidence acquisition,
retention/interpretation and cost protection distinct. They do not turn
supplied-feedback improvements into autonomous evidence.

| Noise | Onset | Joint mixture full cost/task | Full episode delta vs hybrid | Recovery delta vs hybrid |
| --- | --- | --- | --- | --- |
| 4% | stable | 0.092527218 | -0.018130851973 | — |
| 4% | 1 | 0.152380136 | -0.157060863709 | -0.015706086371 |
| 4% | 2 | 0.060380136 | -0.157060863709 | -0.017451207079 |
| 4% | 3 | 0.091464067 | 0.145478840576 | 0.018184855072 |
| 4% | 4 | 0.069322078 | -0.125211417036 | -0.015422363944 |
| 4% | 5 | 0.075013736 | -0.076439123483 | -0.009864042343 |
| 4% | 6 | 0.080773091 | -0.068331350647 | -0.010215296244 |
| 4% | 7 | 0.086296520 | -0.019453219408 | -0.000532971179 |
| 4% | 8 | 0.086753081 | -0.017434821538 | -0.000034877375 |
| 4% | 9 | 0.092082191 | -0.017246623260 | -0.000003197785 |
| 4% | 10 | 0.092342673 | -0.018440049561 | -0.000020165060 |
| 5% | stable | 0.094010189 | -0.015398719987 | — |
| 5% | 1 | 0.157699506 | -0.124126368786 | -0.012412636879 |
| 5% | 2 | 0.067699506 | -0.124126368786 | -0.013791818754 |
| 5% | 3 | 0.096673469 | 0.157291824390 | 0.019661478049 |
| 5% | 4 | 0.074672105 | -0.101851803121 | -0.012517503874 |
| 5% | 5 | 0.079351157 | -0.063191722828 | -0.008160407804 |
| 5% | 6 | 0.084102852 | -0.055110690321 | -0.008176282864 |
| 5% | 7 | 0.088614105 | -0.016513158398 | -0.000539505046 |
| 5% | 8 | 0.089092901 | -0.014507602495 | -0.000046293185 |
| 5% | 9 | 0.093419454 | -0.014208055897 | -0.000005655982 |
| 5% | 10 | 0.093714822 | -0.015977984622 | -0.000032181369 |
| 6% | stable | 0.095550061 | -0.012671507276 | — |
| 6% | 1 | 0.162898834 | -0.092301784211 | -0.009230178421 |
| 6% | 2 | 0.074898834 | -0.092301784211 | -0.010255753801 |
| 6% | 3 | 0.101809999 | 0.169126497192 | 0.021140812149 |
| 6% | 4 | 0.079928417 | -0.079539259459 | -0.009753666306 |
| 6% | 5 | 0.083620293 | -0.050096448377 | -0.006472142176 |
| 6% | 6 | 0.087387141 | -0.042679304302 | -0.006283141796 |
| 6% | 7 | 0.090930986 | -0.013488862005 | -0.000503626954 |
| 6% | 8 | 0.091402386 | -0.011654665846 | -0.000054328379 |
| 6% | 9 | 0.094792006 | -0.011217642682 | -0.000008407310 |
| 6% | 10 | 0.095116026 | -0.013631466010 | -0.000043634488 |

Signed differences are new policy minus hybrid. The two delta columns use
different denominators: complete episode bill and recovery cost per remaining
task. All adverse differences and equality cases remain visible. The primary
threshold concerns mean R, not every onset separately. Exact comparisons to
all eight frozen controls are saved in `DERIVED_COMPARISONS.json`.

## Verification, resources and records

Qualification passed **277 counted assertions** across
**14 short settings**, evaluating **786 policy-tree entries**
over settings. It enumerated all 3, 15 and 255 contingent trees at horizons
1, 2 and 3, and erased action strings through horizon 4. It checked exact
scalar optima and all feasible single/two-policy constrained mixtures, two
priors, fixed multipliers/budgets, duplicate-likelihood collapse, joint
posterior dependence, uninformative free observations and erased beliefs.
Qualification took **1.123 seconds**.

The separate verifier imports no planner. It rebuilds normalized joint Bayes
Bellman scores, every saved action/transition/root, and each world's costs
using integer forward probability propagation. The main evaluator instead
uses homogeneous integer-scaled planning and rational backward evaluation.
It also reconstructs mixture weights, dual certificates, all budgets and
recovery gates, controls, inherited bound and terminal-noise scores.
It passed **194,822 assertions**, covering **36 graphs,
2,855 graph states, 768 world evaluations,
342 diagnostic worlds and 6 certificates**,
including two short fixtures. This is independent reconstruction by the same
author, not external replication or sampled evidence.

The main result contains **16 saved graphs, 2,783 graph states and
14 oracle calls**. Main calculation took **15.081 seconds**;
verification took **183.233 seconds**. The T=7 benchmark took
**0.522 seconds**, forecasting **204.526 seconds**.
Execution used one CPU at nice 10 with library threads fixed at one and no
bytecode. The forecast permitted attached execution. No scientific failure,
source correction, retuning or scientific rerun occurred.

All **18 frozen inputs, 3 snapshots and
10 manifest-listed outputs** verify. The sealed
**5,560,444-byte** attempt is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-uncertainty-v1/attempt-01/`.
Report snapshots, exact derived comparisons and provenance are separate in
`reporting-2026-10-28/`. All generated records remain on `/mnt/bioIce1`.
Source and research notes stay in this folder; sister projects and manuscripts
were not edited. Nothing remains running.

## FEP meaning and the next bounded question

This extends the generative model from uncertainty about hidden state to
joint uncertainty about state and observation reliability. Purchased evidence
updates both; belief-dependent decisions can preserve recovery under an
explicit functional constraint. Bayesian/VFE inference is a component of
that FEP interpretation. The action objective remains constrained task cost,
not a new canonical EFE or evidence of a uniquely FEP advantage.

The big-picture answer is positive but limited: autonomous recovery with the
whole bill paid is feasible at all three specified noise rates. Richer
inference learns a little, while a conservative mixture of older policies
already provides protection. The earlier frozen-policy mismatch failure
remains valid. The larger 401-component model's baseline and failed joint
criterion remain unchanged; this small exact result is not a transfer result.

The recommended next question is whether these two **frozen** successful
mixtures satisfy the same inequalities throughout the continuous 4%–6%
noise interval. Their finite-horizon costs are polynomials in true noise, so
a bounded exact interval check could strengthen the robustness claim without
new policy search. Three tested points alone do not prove it between them.
Deterministic robustness and noise rates outside the tested family remain
open. This study is closed; no successor or larger-model transfer was launched.

| Record | SHA-256 |
| --- | --- |
| FREEZE.json | `5d6f1296cc7faf76ed43e085c06e81549da821af249962adca620dd7d847bd2e` |
| QUALIFICATION.json | `cb4b94deec7637acb57f9d6a261a1f797e157586dc5c8680e81bcbc44aa0db7f` |
| BENCHMARK.json | `94b755591a0e345edd0970a9c66441046aae09c514c1d65eb443c154ca9c2af8` |
| RESULTS.json | `8a15aa8ff26ee87668e6bf95ab066409e0217e0852a88ad380c485a7e7081f9c` |
| MANIFEST.json | `f79c2eed2451706f3fae0258c4b2b23508aca62f28f8b357472ff12233736dbc` |
| READBACK.json | `1f13e8d824ea9baa83e408329396c0997ffcfb0f0bd55c361ab4e37b1bcc1de9` |
