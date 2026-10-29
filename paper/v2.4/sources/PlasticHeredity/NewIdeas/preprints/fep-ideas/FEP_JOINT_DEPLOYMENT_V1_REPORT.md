# Joint deployment: a small mean gain, two repaired misses and retained tradeoffs

**Completed 23 September 2026.** [Frozen specification](FEP_JOINT_DEPLOYMENT_V1.md),
[frozen checker](check_fep_joint_deployment.py).

Using the existing learned joint sensor model on the same saved calibration
histories improves mean cost across the 125-world population. On the primary
MAP stopping schedule, cost falls from **.072615202930 to .072093741101**:
a **.718117%** improvement over the original MAP deployment. It also beats
matched model averaging. Two of the three positive-headroom failures are
repaired, giving **88/89 coverage**, but complete coverage still fails.

The tradeoff is real. Joint deployment worsens 48 of 125 worlds against
matched MAP, including the independent-error slice on average, and slightly
worsens the older nine-world panel against its original controller. The
remaining symmetric miss gets worse. Both saved schedules give the same
three-pass/one-fail primary-criterion pattern. No schedule or controller is
promoted from this post-result comparison.

## What changed and what this tests about FEP

The ablation uses the joint component already supplied to the agent. Given
calibration counts c, its exact prediction is `(c_e + .5)/(n + 2)`. Deployment
conditions on that component rather than selecting between independence and
dependence or averaging their predictions. Its Dirichlet(.5,.5,.5,.5) prior
is unchanged. The deployed structural weights deliberately change; this is
not a claim that joint deployment preserves the original mixture belief.

Both original stopping schedules remain frozen. Calibration still uses the
original independent/joint mixture with .9/.1 structural weights; no joint-only
acquisition policy is optimized. All three deployment rules receive identical
counts on each matched schedule and use the same report/reference rule, with
reference at ties. True Q is never provided to the agent.

Known-input calibration costs .001 per pair, at most 64 pairs; deployment
lasts 100 tasks, wrong answers cost 1 and a perfect reference costs .1.
Errors are stationary IID, hidden binary targets fair, and warnings follow
the supplied XOR transfer. Deployment gives no feedback. Model vocabulary,
within-component priors, prices and observation access are fixed.

VFE supplies exact posterior inference and model evidence. This study tests
the task value of retaining structural competition at deployment, not a new
EFE or information bonus. At **every saved history**, posterior averaging's
immediate risk under the original full mixture is no greater than the joint
rule's risk. Those exact checks pass. Joint deployment's better physical-panel
mean therefore does not refute Bayesian averaging: this equally weighted grid
is a different distribution from the original learner prior. No new integrated
prior-wide risk or oracle was calculated.

The population and original failures were already known before this ablation
was proposed. New ablation costs were calculated only after its contract and
source freeze. This is an explanatory mechanism comparison with exact model
expectations, not a fresh validation set or an independent empirical replication.

## Mean performance and the four fixed criteria

E is the original MAP calibration schedule, declared primary. A is the
original averaged schedule, a required secondary control. Every row includes
calibration. Always referencing without calibration costs .1. The known-Q
mean task floor remains .068664; it pays for references and receives no
free task labels. Captured headroom is a cost fraction, not accuracy.

| Saved schedule | Deployment | Mean full cost | Captured headroom | Beneficial positive-headroom worlds | Better / tied / worse than always referencing |
|---|---|---:|---:|---:|---|
| E, primary | MAP | .072615202930 | 87.390851% | 86/89 | 86 / 0 / 39 |
| E, primary | Average | .072416675080 | 88.024397% | 86/89 | 86 / 0 / 39 |
| E, primary | Joint | **.072093741101** | **89.054949%** | **88/89** | **88 / 0 / 37** |
| A, secondary | MAP | .072709056182 | 87.091345% | 86/89 | 86 / 0 / 39 |
| A, secondary | Average | .072377838200 | 88.148334% | 86/89 | 86 / 0 / 39 |
| A, secondary | Joint | .072068342454 | 89.136002% | 88/89 | 88 / 0 / 37 |

For both schedules, joint mean cost is strictly below matched MAP, matched
averaging and always referencing: **criteria 1–3 pass**. Joint cost is not
below .1 in every positive-headroom world: **criterion 4 fails**. The original
controllers' gates remain unchanged, including their three coverage failures.

Primary joint deployment saves **27.906259%** against always referencing,
compared with the original 27.384797%. The incremental improvement over the
original learned controller is .718117%, not 27.9%. Its gain over matched
averaging is .445939%. Secondary joint deployment saves 27.931658% against
always referencing. The numerically smaller secondary mean does not change
which schedule is primary.

All 125 worlds retain equal weight, including both sensor orders and all
36 zero-headroom worlds. The latter still incur excess cost under joint
deployment. The ten earlier controls stay separate and contribute nothing
to this mean. Every original diagonal result across all 135 laws reproduces
exactly, as do all four earlier crossed costs in the five attribution cases.

## Improvements and harms at matched histories

Negative joint-minus-original differences favor joint deployment. These
matched comparisons charge identical calibration, so the calibration contrast
is exactly zero.

| Schedule | Matched comparator | Mean joint-minus-comparator cost | Worlds improved / tied / worsened | Gross helpful contribution | Gross harmful contribution |
|---|---|---:|---|---:|---:|
| E | MAP | −.000521461829 | 72 / 5 / 48 | −.001078292264 | +.000556830434 |
| E | Average | −.000322933979 | 66 / 5 / 54 | −.000921511972 | +.000598577993 |
| A | MAP | −.000640713728 | 76 / 5 / 44 | −.001160945429 | +.000520231700 |
| A | Average | −.000309495746 | 68 / 5 / 52 | −.000894667286 | +.000585171540 |

Gross contributions separate histories with lower or higher conditional
physical task cost, then average over all stopped histories and worlds.
They are not individual realized-task win rates or clipped world-level
contrasts. On primary E histories, joint changes the MAP response table with
mean probability 8.552322%; conditional physical cost is lower on 5.033071%,
higher on 3.015202% and equal on 91.951727%. A changed response table can
have equal physical cost, including changes on unreachable warnings.

Against primary MAP, wrong-report loss falls by .000693933055 while reference
expense increases by .000172471225, yielding the net .000521461829 saving.
The known-Q gap decomposition shows reductions in both excess checking
(−.000304824837) and unsafe reporting (−.000216717119), with a small increase
in wrong report direction (+.000000080126). More references overall can
coexist with fewer unnecessary references because their placement changes.

Primary joint's remaining gap to known-Q is .003429741101: calibration
.000475224710, excess checking .001656428824, unsafe reporting .001297983305
and wrong direction .000000104262. These are additive costs, not disjoint
error counts or guaranteed recoverable savings. The evaluator receives
knowledge the learner must acquire.

The largest primary harm relative to MAP is +.002284458649 in independent
.15/.25 and its swap. The largest primary gain is −.005835394617 in
.25/.25 at t=−.5. Every tied extremum, signed per-world result and matched
response-code probability remains available in the record; these examples
do not define a newly selected performance population.

## Where structural competition helps and hurts

Each slice below averages all 25 marginal pairs with the stated dependence
setting. The interpolation parameter t is not Pearson correlation.

| Dependence t | E/MAP | E/Average | E/Joint | A/MAP | A/Average | A/Joint |
|---|---:|---:|---:|---:|---:|---:|
| −1 | .051739610221 | .051700561873 | .051362128048 | .051804475188 | .051696590163 | .051362706267 |
| −.5 | .070592301756 | .070507248281 | .069477175093 | .070634698503 | .070444995670 | .069473857710 |
| 0, independent | .075285503119 | .075285179843 | .076242295732 | .075297973360 | .075284784288 | .076205810396 |
| +.5 | .086654128820 | .086350419977 | .085329340217 | .086939656322 | .086281704942 | .085292357841 |
| +1 | .078804470732 | .078239965424 | .078057766412 | .078868477538 | .078181115935 | .078006980053 |

Joint mean cost improves against both matched rules in the four dependent
slices and worsens in the independent slice, under either schedule. Retaining
the simpler factorization therefore has a task benefit where it is appropriate;
it does not repay its losses across this particular equal-weight population.
This is a population-dependent tradeoff, not evidence that structural model
selection is always harmful or that the .9/.1 prior alone caused every loss.

The five known diagnostic cases are retained individually in the record.
Swapped pairs have identical aggregate costs and are grouped here only for
display. There is no five-case performance average.

| Diagnostic environment | E/MAP | E/Average | E/Joint | A/MAP | A/Average | A/Joint |
|---|---:|---:|---:|---:|---:|---:|
| .15/.15, t=+.5 | .100525490627 | .100500854495 | .100605697423 | .100572593139 | .100533328777 | .100632246087 |
| .15/.45 and swap, t=−.5 | .100337078613 | .100144872891 | .094803965385 | .100453375367 | .100026907795 | .094886009242 |
| .15/.35 and swap, t=+.5 | .113909865911 | .113304007710 | .109197997315 | .114736220705 | .113083859388 | .109367913978 |

The negative-dependence pair now beats always referencing under both schedules.
The symmetric case remains the sole positive-headroom failure and gets worse
against either matched deployment. Its primary joint raw task cost is already
.100113306085 before calibration, so removing calibration expense alone would
not make that saved deployment useful against always referencing.

The worst total-cost worlds remain .15/.35 at t=+.5 and its swap. Joint
deployment reduces their primary cost to .109197997315 from .113909865911,
but always checking is already optimal there and the residual harm remains.
These outcomes fit the earlier attribution's distinction between structural
and parameter effects, without making that bookkeeping a unique causal proof.

## Older controls remain an adverse check

The older nine-case panel is not included in the new mean. Joint deployment
slightly worsens its mean against each schedule's original controller:

| Control population | E/MAP | E/Average | E/Joint | A/MAP | A/Average | A/Joint |
|---|---:|---:|---:|---:|---:|---:|
| Original nine-case mean | .076026980104 | .076032614987 | .076110733306 | .076121297998 | .076016683060 | .076097350656 |
| Excluded old shared diagnostic | .097011123876 | .097174421749 | .096805288938 | .096804901873 | .097015253542 | .096656215395 |

The original nine-case primary increases by .000083753202 with joint deployment;
the original averaged controller's matched increase is .000080667595. The old
shared diagnostic improves, but stays excluded. All ten individual control
outcomes, including harms, are retained. The new 125-world improvement does
not erase this adverse panel result, the earlier fixed-budget joint comparison,
or the failed deployment-feedback extensions.

## Verification and sealed record

The first attempt passes without failed qualification/execution, frozen-source
correction, rerun, sampling, schedule optimization or prior/price tuning.
All older failed attempts and corrections remain preserved.

Qualification records **717,443 assertions**, including exact joint evidence
ratios through n=6, posterior choice against direct enumeration of all 81
response tables, exact threshold ties, and physical cost checks under 142
laws. Two outcome-dependent cap-three schedules reproduce all six crossed
response laws and their matched code-pair laws by direct ordered-stream
enumeration. Ten complete known diagonal bridges pass before main execution.
Joint/full-mixture action checks cover every one of the 136,499 saved count
rows. Qualification arithmetic and control integration take 3.974849648 seconds.

The 135-law, 2,048-row benchmark takes .700655675 seconds and forecasts
**306.794529145 seconds**, below the ten-minute detachment threshold. Main
execution is attached and takes **54.612804837 seconds wall** and
54.585980852 seconds CPU on one Python 3.10.12 process. It runs from
2026-09-23T16:41:19.338206+00:00 to 16:42:13.975507+00:00.

All **1,569,714 cumulative recorded assertions** pass, including the carried
qualification counts and 6,172 bridge assertions across both phases. These
are repeated arithmetic/software checks, not independent experiments. Exact
integers and rationals determine policies, stop masses, signs and criteria;
floats are used only for display and timing. The record covers 136,499 count
rows and 259,142 reachable schedule/count pairs across 135 physical laws.

Readback verifies **12 input, 15 output and 331 preserved identities**. The
36,502,104-byte record is exclusively at:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-joint-deployment-v1/attempt-01/`

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Frozen specification | 8,456 | `36bea9696d4324341f0a8cc12c1726992758097555fcdf83dd38f2969d2cdb77` |
| Frozen checker | 21,087 | `f33c9685fb466b1707a1548ce3bd4e5ff61560c9be964ebd676346f08a89c499` |
| POPULATION.json | 56,892 | `042e42fbddb495ce674cde77f73c2b3bebe2db90965f6602f225dbfb80aabe29` |
| JOINT_DEPLOYMENT.jsonl.gz | 502,571 | `be6c917ab65e30315c760b33566e86ae2700a17531e2963a1e85b587f97ae773` |
| QUALIFICATION.json | 877 | `5ae32d86922ff7ed97cd9db4187635e8063e2d47bc7856cb17693d6fb84bfcd7` |
| RESULTS.json | 35,503,172 | `5d680d6951a72739c04a9b0ae65e14099e741f51615658ef855fac2da7952747` |
| RUN_LOG.txt | 646 | `fdcc5e706f35f41f820fccbfa2e48bf667a8f9fc6fb95cffcdeff2a448b4765e` |
| MANIFEST.json | 85,223 | `4755c7658411aca690ec6967f95ce0258aadb302ea4e95e1affb9b53692ae37e` |

The response ledger saves counts and the new joint code; original stopping
multiplicities/codes remain pinned in the earlier ledger. RESULTS retains
exact and display values for every world, all six deployments, paired
response probabilities, signed contributions, five slices, complete criteria
and separate controls. The original full-panel aggregate is preserved as
context. No calculation or readback remains pending. Earlier sources,
artifacts and manuscripts are unchanged; all project writing stays local.

## Next scientific question

The joint component works well enough to be a useful FEP-model lead: a small
overall gain and two repaired misses with unchanged observations and budget.
The independent-slice and old-panel regressions make its population dependence
equally clear. It is a supplied richer likelihood, not learned discovery of
a causal mechanism, a full online world-model learner or a unique FEP advantage.

Next recommended is **one separately frozen validation on off-grid reliability
and dependence settings**, keeping this joint ablation and both original
schedules/controls unchanged. Specify the new population and weights before
calculating any of its task costs, include zero-headroom worlds, and retain
all current adverse controls separately. Assess mean benefit and coverage
again without selecting a favorable schedule or tuning priors. That tests
whether this post-result lead transfers before changing acquisition or the
main controller. No successor, feedback extension, manuscript integration
or sister-project work has been launched.
