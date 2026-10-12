# Generalization v1: useful average performance, with three missed opportunities

**Completed 23 September 2026, on attempt two.** The unchanged calibrated
agent passes the prospective population-benefit criterion across 125 new
environments. It costs **27.38% less than always buying a reference answer**
on average and captures **87.39% of the improvement available to a known-Q
evaluator**. It improves on always referencing in **86 of the 89 environments
where an improvement is possible**. The stricter functional-coverage criterion
therefore fails. Both verdicts are retained.

Model averaging has the same pass/fail pattern and the same three coverage
failures, with slightly better mean cost. Thirty-six additional environments
offer no advantage over always referencing even to an informed evaluator;
the agent incurs excess cost in all of them. They remain in the population
mean. Thus the full count is 86 better and 39 worse out of 125, with no ties.

The [specification](FEP_GENERALIZATION_V1.md) was frozen before qualification.
The [original checker](check_fep_generalization.py) reached all integrations
but failed at a saved-record field lookup before exporting new results.
The [documented correction](FEP_GENERALIZATION_V1_CORRECTION.md) and
[revision-two checker](check_fep_generalization_r2.py) preserve that attempt
and change the lookup, qualification and provenance only. No population,
policy, cost formula or success criterion changed.

## Population and unchanged FEP mechanism

The new panel crosses five error rates independently for each sensor,
a,b in {.05,.15,.25,.35,.45}, with five dependence settings
t in {−1,−.5,0,.5,1}. At t=0 errors are independent. Negative t interpolates
toward the feasible minimum coincident-error probability, which is zero
throughout this panel. Positive t interpolates toward fully nested errors.
The definition is not Pearson correlation or identification of a common cause.
All 125 distinct laws receive equal weight, including both sensor orders.
None duplicates the ten known controls, which are evaluated separately.

The original MAP and model-averaged controllers keep their saved stopping
histories and response tables. Both learn through initial calibration and
then hold deployment behavior fixed; there is no deployment feedback here.
The independent and joint error models, .9/.1 structural prior, conjugate
parameter priors, fair binary targets, stationary IID error pairs, XOR
warnings and calibration/deployment transfer relation are unchanged.
There are 100 deployment tasks, a wrong report costs 1, a perfect reference
costs .1, and a calibration pair costs .001, with cap 64.

VFE supplies the existing exact posterior and model evidence. Calibration
planning uses expected future task loss and acquisition expense. This tests
the breadth of useful behavior produced by that model; it introduces no new
EFE, information bonus, policy optimizer or unique FEP advantage. The new
panel remains a finite, supplied sensor task under stationary physics, not
an empirical replication or a test of general intelligence.

## Registered results

Full costs include calibration, references and errors, divided by 100 tasks.
All decisions and signs use exact rational arithmetic; displayed decimals
are rounded. The primary remains MAP regardless of the comparison's outcome.

| Outcome | Primary MAP | Model average |
|---|---:|---:|
| Full mean cost | .072615202930 | .072377838200 |
| Always-reference cost | .100000000000 | .100000000000 |
| Cost reduction against always referencing | 27.384797% | 27.622162% |
| Population-benefit criterion | **Pass** | **Pass** |
| Environments with positive known-Q improvement | 89 | 89 |
| Such environments with net benefit | 86 | 86 |
| Functional-coverage criterion | **Fail: 3 cases** | **Fail: 3 cases** |
| Zero-headroom environments retained | 36 | 36 |
| All environments: better / tied / worse than referencing | 86 / 0 / 39 | 86 / 0 / 39 |
| Expected calibration pairs | 47.522471 | 47.836291 |
| Probability of stopping before 64 | 80.130286% | 76.153401% |

Coverage among positive-headroom cases is 96.63%, but the registered criterion
requires every such case to benefit. That criterion fails without rounding
or a result-selected tolerance. No new comparison with fixed-64 calibration
was evaluated, so the smaller mean number of pairs is not a new efficiency
claim against that controller.

The known-Q evaluator observes the same warning and pays the same reference
price, but knows the error law without calibration. It receives no free true
target. Its panel floor is exactly 8583/125000 = .068664, leaving
3917/125000 = .031336 available improvement over always referencing.

| Bound comparison | Primary MAP | Model average |
|---|---:|---:|
| Gap above the known-Q floor | .003951202930 | .003713838200 |
| Available improvement captured | 87.390851% | 88.148334% |

Captured improvement is the ratio of population mean advantages, not the
mean of environment percentages and not an accuracy score. The bound supplies
information the learner must acquire, so the remaining gap need not be
attainable at its budget. These fractions exceed the old panel's approximately
85.3%, but the evaluation population changed and the agent did not improve.

## Dependence settings, without selecting a favorable subset

Each row averages all 25 marginal-error combinations. The final column is
the same for both controllers and counts beneficial cases among those with
positive headroom. Slice means are descriptive, not additional success gates.

| Dependence t | Known-Q mean floor | Primary cost | Averaged cost | Primary captured | Averaged captured | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| −1 | .050000 | .051739610221 | .051696590163 | 96.5208% | 96.6068% | 25/25 |
| −.5 | .066040 | .070592301756 | .070444995670 | 86.5951% | 87.0289% | 17/19 |
| 0 | .072640 | .075285503119 | .075284784288 | 90.3308% | 90.3334% | 14/14 |
| +.5 | .080640 | .086654128820 | .086281704942 | 68.9353% | 70.8590% | 9/10 |
| +1 | .074000 | .078804470732 | .078181115935 | 81.5213% | 83.9188% | 21/21 |

All five slice means are below .1. Partial positive dependence has the lowest
fraction of available improvement captured; mutually exclusive errors have
the highest. This describes these fixed slices and weights, without claiming
a universal ordering of dependence difficulty or identifying its causal
mechanism. The full record retains every environment and both sensor orders.

## Where the remaining cost arises

The exact decomposition remains

```
full cost = known-Q floor + calibration
            + excess checking + unsafe reporting + wrong direction.
```

“Unsafe reporting” means answering when even the better report has higher
expected cost than checking. “Wrong direction” is the extra loss from choosing
the worse of the two reports. These are additive costs, not disjoint counts
of wrong answers; an optimal informed report can itself be wrong.

| Gap component | Primary cost | Primary gap share | Averaged cost | Averaged gap share |
|---|---:|---:|---:|---:|
| Calibration | .000475224710 | 12.027343% | .000478362911 | 12.880553% |
| Excess checking | .001961253661 | 49.636875% | .001755965423 | 47.281689% |
| Unsafe reporting | .001514700423 | 38.335172% | .001479481440 | 39.836992% |
| Wrong direction | .000000024136 | .000611% | .000000028425 | .000765% |

The original nine-case panel had unsafe reporting as its largest component;
this new population has excess checking as the largest. Both kinds of error
remain material, so neither “check more” nor “check less” follows as a general
remedy. Agreement contributes .002111092679 of primary decision regret and
disagreement .001364885541; the corresponding averaged values are .002018308307
and .001217166982. These exclude calibration and sum to the decision gap.

Actual primary raw cost is .072139978220, consisting of .016035065088
wrong-report loss and .056104913132 reference expense. That corresponds to
about 1.603507 wrong reports and 56.104913 references per 100-task episode.
Averaging gives .071899475288 raw cost, 1.607696 wrong reports and 55.822513
references. The gap components subtract the informed alternative's cost;
they are not total error/reference counts.

## Every missed opportunity and the worst total losses

These are all three positive-headroom failures. The two unequal-sensor cases
are distinct panel members with swapped sensor order and exactly equal costs.
They remain separate in the aggregate.

| a | b | t | Known-Q floor | Primary full cost | Averaged full cost |
|---:|---:|---:|---:|---:|---:|
| .15 | .15 | +.5 | .099 | .100525490627 | .100533328777 |
| .15 | .45 | −.5 | .087 | .100337078613 | .100026907795 |
| .45 | .15 | −.5 | .087 | .100337078613 | .100026907795 |

At .15/.15/+.5, available improvement is only .001 per task. Primary
calibration costs .000492391338, excess checking .000452985527 and unsafe
reporting .000580113762. Raw deployment cost is already .100033099289,
slightly above always referencing, before charging calibration. Averaging
also exceeds .1 before calibration. This failure is not exclusively a
calibration charge.

At .15/.45/−.5 and its swap, headroom is a more substantial .013 per task.
The primary gap includes .009406281741 excess checking, .003401132263 unsafe
reporting and .000529664608 calibration. Raw deployment cost .099807414005
is below .1, but its small saving does not repay learning. Averaging comes
closer: raw cost .099492061779 and calibration .000534846016 leave full cost
.100026907795. It still fails the strict criterion. The lost opportunity
therefore cannot be described solely as an almost-zero theoretical advantage.

The worst full cost occurs at .15/.35/+.5 and its swap: **.113909865911**
for the primary and **.113083859388** for averaging. The known-Q floor is
.1 there, so no sensor-based advantage over always referencing is available.
Primary unsafe-reporting loss is .013398064927 and calibration .000511800138;
excess checking is exactly zero. These worst cases are not dropped because
they lie outside the coverage denominator. Across all 36 zero-headroom worlds,
mean excess cost is .003618830095 primary and .003487812877 averaged.

## Interpretation and next lead

The broader evaluation supports useful function beyond the original nine
worlds, including independently varying sensor quality and negative error
dependence. It does not establish uniform usefulness: the three missed
opportunities and 36 zero-headroom excess costs remain explicit. Averaging
improves mean cost but retains the same coverage failures, so those failures
cannot be assigned solely to hard model selection from this comparison.
The current study does not identify which posterior beliefs caused each loss.

The next recommendation is a bounded attribution of the three coverage
failures and the tied worst-cost cases using their saved calibration histories.
Distinguish structural model selection, estimated error probabilities and
stopping decisions, while retaining the whole 125-case population as context.
This would identify which part of the FEP belief-to-action mechanism warrants
a prospective intervention. The cases are now known; such attribution would
be explanatory, not fresh validation. No price, prior, confidence correction,
controller, feedback extension or next calculation is selected or launched.

The previous nine-case and shared-case results reproduce exactly. Earlier
own-prior guarantees, useful calibration, failed feedback extensions and all
older gates retain their original scope. No new prior-wide oracle calculation,
model misspecification diagnosis or manuscript integration is supplied here.

## Qualification, correction and execution record

The first frozen source passed 283,193 preparation assertions, then raised
`KeyError: 'task_headroom'` during the known-control bridge after all 135
integrations. The old field is controller-level, not inside `no_update`.
Nine bridge assertions had passed and 560,518 assertions were counted overall.
No new policy cost, aggregate or gate was exported or inspected. The failed
3,187,431-byte `attempt-01` and its original source remain intact.

Revision two changes that lookup and adds a full ten-control replay to
qualification, plus explicit failed-attempt provenance. Both source revisions
and the correction note are frozen. This is one source correction and one
main rerun; it must not be reported as an unbroken first-attempt success.
All scientific definitions and numerical integration formulas are unchanged.

Revised qualification passes **284,109 assertions** in 2.314920253 seconds.
Independent fair-target/error enumeration covers all nine symmetric tables
under 142 laws: 125 new, ten known and seven synthetic controls. Two
outcome-dependent toy stopping schedules through cap three are checked
against all ordered full error histories. Zero-probability warnings, reversed
sensors, reference ties and known-Q zero-regret actions are covered.
All ten complete known-control bridges also pass before main execution.

The 2,048-row, 135-law benchmark takes .358570578 seconds. Its conservative
forecast is 185.594776 seconds, below ten minutes, permitting attached
execution. Main attempt two starts at 2026-09-23T11:59:29.328317+00:00 and
finishes at 11:59:56.653162+00:00. It takes **27.315624377 seconds wall** and
27.313611613 seconds CPU on one Python 3.10.12 process.

All **562,659 assertions pass**, including 1,242 old-control bridge assertions
across qualification and execution. The saved ledger contains 136,499 count
rows and 259,142 reachable controller/count rows. Assertions are repeated
integrity/arithmetic checks, not independent experiments. Expectations are
exact; there was no sampling, policy reoptimization or outcome tuning.

Readback verifies all **10 input, 14 output and 288 preserved** identity entries,
including every first-attempt artifact. The successful record is 11,583,379
bytes; both attempts total 14,770,810 bytes. Generated records are exclusively
under `/mnt/bioIce1/fep-ideas/formal-checks/fep-generalization-v1/`.

`attempt-02/POPULATION.json` fixes every law and weight. The complete
[`attempt-02/RESULTS.json`](/mnt/bioIce1/fep-ideas/formal-checks/fep-generalization-v1/attempt-02/RESULTS.json)
contains every new/known environment, all cost and regret components, stop
distributions, response-table probabilities, warning breakdowns, undefined
headroom ratios, slice means and gate verdicts. Source snapshots, preparation,
qualification, durable logs and the manifest accompany it. All preceding
frozen artifacts and manuscripts are unchanged; the six live notes now record
the result and its limitations. No calculation or readback remains pending.

| Artifact | SHA-256 |
|---|---|
| Original specification | `0664d6787dcc5e34f0ed0f0f5eef4a456d88d06eace0529bcef204192d9edc4c` |
| Original checker | `0bb15729648438af336b897d355e0ef03aef47e72e505a17db391c475fde8123` |
| Revision-two checker | `b0c6520e63b60f709674b6de9ba9c17fda7fcea47c04fd71b4667b8c21641f63` |
| Correction note | `d1e4ac4ae79571952b30689a7472c1ed010bc14a2da1eb312cec192f8bea4778` |
| First failure | `0bf5826ec51b2ceef2d01a4ef7d727c01a500a60c2bfd46b5df68bb3bc85b43e` |
| Successful manifest | `05a124a7408b5d37a9f275e085dce9f31d53f5eea2aed666260b29808393911b` |
| Results | `d5cce54ba0117447cc871e3c2ae22307b6c2ff47610bcc1961f6ec05502dcbc6` |
| Population | `042e42fbddb495ce674cde77f73c2b3bebe2db90965f6602f225dbfb80aabe29` |
| Qualification | `a5e301cd9c3fbfe40f1182934877d4d9d09b9088dd4d2b3e723e5b2920ac1725` |
