# Generalization attribution: structural beliefs, parameter uncertainty and stopping

**Completed 23 September 2026.** [Frozen specification](FEP_GENERALIZATION_ATTRIBUTION_V1.md),
[frozen checker](check_fep_generalization_attribution.py).

Completing calibration to the existing cap of 64 makes mean full cost worse
in every one of the five known problem environments, for both controllers.
That particular continuation is not a remedy. At the same saved histories,
retained independence or insufficient posterior weight on dependence accounts
for most of the larger decision gaps in the declared substitution analysis.
The small symmetric failure has a different explanation: parameter uncertainty
near the decision threshold. In the worst environments, inaccurate parameter
estimates actually compensate for some of the structural loss.

These are explanations of known outcomes, not a new performance test or an
improved agent. The preceding [125-world result](FEP_GENERALIZATION_V1_REPORT.md)
remains unchanged: primary mean cost .072615202930, 27.38% below always
checking, with 86 better and 39 worse worlds. Both controllers benefit in
86 of 89 positive-headroom worlds; all 36 zero-headroom worlds remain in the
mean. No new aggregate of the five selected failures is constructed here.

## What was held fixed

The agent calibrates two sensors against known inputs, then answers hidden
binary tasks or buys a perfect reference. Calibration costs .001 per pair;
references cost .1; wrong answers cost 1. All costs below are per task over
the fixed 100-task deployment horizon, including calibration where stated.
The calibration cap is 64. Errors remain stationary and IID, targets fair,
and warnings use the existing XOR transfer. Deployment supplies no updates.

The supplied candidate models are independent sensor errors with Beta(1,1)
priors and a joint error table with Dirichlet(.5,.5,.5,.5). Their prior weights
remain .9/.1. The primary selects the MAP model; the comparator averages
posterior predictions. Both retain their original stopping schedules and
response tables. The exact posterior/evidence formulas reproduce the sealed
ledgers. No optimizer, new information bonus, new EFE, price or prior change
was introduced.

The physical error law Q is evaluator knowledge only. Its decision floor
B(Q) still pays for a reference and receives no free target labels. The
following five cases are exactly the three missed opportunities and two tied
worst-cost cases specified before this attribution calculation:

| Saved case | Q in error order 00, 01, 10, 11 | B(Q) |
|---|---|---:|
| `a15_b15_pos05` | (.78625, .06375, .06375, .08625) | .099 |
| `a15_b45_neg05` | (.43375, .41625, .11625, .03375) | .087 |
| `a45_b15_neg05` | (.43375, .11625, .41625, .03375) | .087 |
| `a15_b35_pos05` | (.60125, .24875, .04875, .10125) | .100 |
| `a35_b15_pos05` | (.60125, .04875, .24875, .10125) | .100 |

Swapping sensors gives identical aggregate costs in each unequal pair. Tables
below display each pair together for brevity; both orientations, their bins
and examples are retained separately in the external record. The complete
125-world aggregate is preserved as context, with a hashed reference to its
complete results and all ten known controls.

## Same histories: where the decision gap sits

At each stop, the evaluator substitutes the true within-model parameters,
holding the selected model or posterior model weight fixed. For the independent
component it uses the product of Q's true marginals; for the joint component
it uses Q. The same response rule converts the substituted prediction into
an action, including asking at ties. In this declared order,

```
parameter contribution = cost(saved action) - cost(substituted action)
structure/weight remainder = cost(substituted action) - B(Q)
decision regret = parameter contribution + structure/weight remainder
full cost - B(Q) = decision regret + calibration expense
```

The parameter term is signed. The remainder is nonnegative, but is not an
irreducible lower bound for every independent-model policy or a unique causal
attribution. Estimates can compensate for factorization. These terms must
not be added to the separate continuation comparison as disjoint causes.

| Environment | Controller | Decision regret | Structure/weight remainder | Signed parameter term | Calibration |
|---|---|---:|---:|---:|---:|
| .15/.15, t=+.5 | MAP | .001033099289 | .000000000000 | +.001033099289 | .000492391338 |
| .15/.15, t=+.5 | Average | .001034274962 | .000000000000 | +.001034274962 | .000499053815 |
| .15/.45 and swap, t=−.5 | MAP | .012807414005 | .011903402369 | +.000904011636 | .000529664608 |
| .15/.45 and swap, t=−.5 | Average | .012492061779 | .011832592698 | +.000659469081 | .000534846016 |
| .15/.35 and swap, t=+.5 | MAP | .013398065773 | .023824767823 | −.010426702050 | .000511800138 |
| .15/.35 and swap, t=+.5 | Average | .012560626681 | .017754301408 | −.005193674727 | .000523232707 |

The symmetric miss has zero structure/weight remainder: under the substitution,
both factorizations and every retained mixture make optimal decisions. Its
primary regret combines .000452985527 from excess checking on agreement and
.000580113762 from unsafe reporting on disagreement, plus negligible wrong
direction. The available advantage over always checking is only .001. Thus
calling this solely a failure to select the joint model would be incorrect.

For .15/.45 and its swap, the structure/weight remainder is **92.94%** of MAP
decision regret and **94.72%** for averaging. MAP retains independence on
91.564634% of stopped probability. All of its structural remainder occurs
on agreement histories with independence selected. The parameter term adds
loss overall, but conceals offsets: MAP gross positive and negative parameter
contributions are +.003452917382 and −.002548905746; averaging gives
+.003440609956 and −.002781140874. Agreement estimates partly compensate;
disagreement estimates add unsafe reporting. Averaging improves the result
without removing the same coverage failure, so hard model selection alone
is not a sufficient explanation.

For .15/.35 and its swap, always checking is already optimal. MAP retains
independence on 76.854090% of stopped probability. The structural remainder
is .023824767823, larger than the observed decision regret .013398065773,
because parameter error offsets .010426702050. Its gross parameter terms
are +.001444074437 and −.011870776487. Averaging has the same direction:
gross +.003052260287 and −.008245935013, net −.005193674727. In this
substitution, correcting parameters alone would worsen performance. No
component is clipped to force an apparently cleaner explanation.

All exact stopping-count, MAP-label and warning-class joint bins are saved,
including empty cells. For averaging the MAP label is diagnostic, not its
deployment operation. The structural remainder lies on agreement in these
unequal cases; disagreement has zero structural remainder and positive
parameter loss. Excess checking is exactly absent in the two worst worlds
because a reference is already optimal under both warning classes.

## More calibration: completing to 64 does not rescue these cases

For each saved history and deployment rule, exact backward expectation gives
the task cost after completing the same IID stream to 64. There is no
minimization or reoptimization. Every additional sample is charged. Positive
completion benefit means stopped full cost minus completed full cost is
positive; the continuation is then better conditionally in that physical world.

| Environment | Controller | Original full cost | Fixed-64 full cost | Completion benefit | Early-stop probability with positive conditional benefit |
|---|---|---:|---:|---:|---:|
| .15/.15, t=+.5 | MAP | .100525490627 | .100790650425 | −.000265159798 | .548275% |
| .15/.15, t=+.5 | Average | .100533328777 | .100726859752 | −.000193530975 | .010785% |
| .15/.45 and swap, t=−.5 | MAP | .100337078613 | .100544269081 | −.000207190469 | 16.074068% |
| .15/.45 and swap, t=−.5 | Average | .100026907795 | .100090291745 | −.000063383950 | 10.114960% |
| .15/.35 and swap, t=+.5 | MAP | .113909865911 | .116042496850 | −.002132630939 | 27.272586% |
| .15/.35 and swap, t=+.5 | Average | .113083859388 | .113210257459 | −.000126398070 | 25.240146% |

The last column is conditional on stopping before 64, not on all histories
and not a fraction of realized future samples that help. Completion can help
individual histories even though its mean is worse. Positive and negative
contributions to mean benefit are both retained:

| Environment | Controller | Gross positive completion gain | Gross negative completion gain |
|---|---|---:|---:|
| .15/.15, t=+.5 | MAP | +.000000705589 | −.000265865387 |
| .15/.15, t=+.5 | Average | +.000000015861 | −.000193546836 |
| .15/.45 and swap, t=−.5 | MAP | +.000227805762 | −.000434996231 |
| .15/.45 and swap, t=−.5 | Average | +.000048396559 | −.000111780509 |
| .15/.35 and swap, t=+.5 | MAP | +.000324127715 | −.002456758655 |
| .15/.35 and swap, t=+.5 | Average | +.000220552709 | −.000346950780 |

Stopped-law averaging of the continuation exactly recovers the unconditional
fixed-64 cost, for both schedules and both deployment rules. Completion benefit
is exactly zero at cap. These checks retain the true first-stop probabilities,
not unrestricted multinomial weights. This rules out this fixed completion
as a mean-cost repair in the five cases; it does not rule out every alternative
stopping policy, observation interface, acquisition budget or future study.

The saved acquisition belief gives a nonpositive completion-benefit upper
bound at every diagonal stop. Its physically weighted mean benefit estimates,
rounded here, are −.000246846067/−.000123125628 in the symmetric case,
−.000179699439/−.000092333775 in the negative-dependence pair, and
−.000499642963/−.000103185551 in the worst pair, for MAP/average respectively.
The external record retains both exact endpoints of every mean interval;
each inherited history bound has width at most 2^-40. Physical positive gains
therefore identify conditional forecast disagreement in those worlds, not an
invalid posterior or a failed VFE minimization. No subjective forecast is
invented for crossed histories where the original ledger supplies none.

## Swapping deployment rules at the same stopping histories

E denotes MAP and A model averaging. L(s,d) charges the calibration from
schedule s and deploys rule d on exactly those histories. Both substitution
orders reproduce the diagonal difference exactly:

```
L(E,E)-L(A,A) = [L(E,E)-L(E,A)] + [L(E,A)-L(A,A)]
              = [L(E,E)-L(A,E)] + [L(A,E)-L(A,A)].
```

| Environment | L(E,E) | L(E,A) | L(A,E) | L(A,A) |
|---|---:|---:|---:|---:|
| .15/.15, t=+.5 | .100525490627 | .100500854495 | .100572593139 | .100533328777 |
| .15/.45 and swap, t=−.5 | .100337078613 | .100144872891 | .100453375367 | .100026907795 |
| .15/.35 and swap, t=+.5 | .113909865911 | .113304007710 | .114736220705 | .113083859388 |

Averaged deployment is better at either saved schedule in every focus case.
Nevertheless, in the symmetric case the original averaged controller is
slightly worse overall because the stopping-schedule effect offsets that
deployment gain. In the unequal cases averaging's own schedule helps its
deployment, while that same schedule worsens MAP deployment. There is no
single schedule contribution independent of the deployment rule. Every crossed
full cost still exceeds .1; none rescues these particular failures.

## What the saved histories look like

The frozen rule selects the largest probability-weighted contribution to each
of excess checking, unsafe reporting and positive completion gain, separately
for each case/controller. There are **26 present examples and four explicit
absences**; the latter are excess checking in both worst worlds for both
controllers. All counts, probabilities, actions, evidence odds and forecast
bounds are saved. Counts below use error order 00, 01, 10, 11.

- In the symmetric world's primary excess-checking example, counts
  (38,3,3,6) stop at n=50. Joint posterior weight is 96.96%, so independence
  is not the issue at this history. MAP estimates agreement-report risk at
  14.44% (full posterior 14.22%) and checks; physical risk is 9.89%, just
  below the 10% threshold. Parameter substitution changes to the optimal report.
- Its primary unsafe-reporting example, (54,0,5,5) at cap, has 99.90% joint
  weight. MAP estimates disagreement-report risk at 8.33%; physical risk is
  50%. The learned parameter asymmetry makes a report appear cheaper than
  checking. Parameter substitution restores checking.
- In .15/.45, primary counts (19,22,7,1) stop at n=49 and retain independence;
  joint weight is 21.06%. Agreement-report risk is estimated at 16% versus
  the physical 7.22%, so a useful report is missed. Substituting true
  independent parameters still checks: this example retains structural loss.
- In the worst .15/.35 world, primary counts (39,15,3,5) stop at n=62.
  Independence is retained with joint weight 11.74%. The agent reports on
  agreement at estimated risk 7.40% (full posterior 8.03%); physical risk is
  14.41%. True independent parameters still report, while known-Q checks.
- Positive continuation is not empty: primary counts (38,14,1,5) in that
  worst world stop at n=58. Completing to 64 has conditional physical benefit
  +.006807687809, despite a saved subjective interval near −.002803194285.
  Its stopped probability is .002921301539 and weighted positive gain
  .000019887309. Other histories' losses outweigh such gains in the mean.

These predeclared illustrations are not representative samples or new gates.
Their exact first-stop probabilities differ by controller even when the same
count vector is selected.

## Verification and preserved evidence

The first attempt completed without failed qualification/execution, frozen-
source correction, rerun, sampling, optimization or tuning. The preceding
generalization study's failed first attempt and separate correction remain
preserved; first-attempt success here does not rewrite that history.

Qualification records **3,019,455 checks**, including ledger checks and the
benchmark. Independent exact checks cover evidence/odds/actions through n=4,
physical target/error enumeration under five focus and four synthetic laws,
two outcome-dependent cap-three stopping schedules and direct enumeration of
all future error sequences. Archived schema/cost bridges are exercised before
execution. The small arithmetic qualification segment takes 1.824073571 seconds.
The five-case, top-two-layer benchmark covers 468,325 states in 6.199267146
seconds and forecasts **335.601993267 seconds**, below the ten-minute threshold.
Attached execution therefore follows the user's runtime rule.

The main timed calculation takes **59.763254447 seconds wall** and
59.749557644 seconds CPU on one Python 3.10.12 process, from
2026-09-23T16:02:32.078457+00:00 to 16:03:31.853492+00:00. It uses
136,499 count rows, 259,142 reachable controller/count rows and 814,385
full-lattice states per physical case. All **8,165,575 recorded assertions**
pass, including the carried qualification/benchmark counts and 110 main
bridges to sealed generalization outcomes. These are repeated software and
arithmetic invariants, not independent experiments or a separate replication.

Readback verifies all **12 input, 18 output and 308 preserved identities**.
Both preceding generalization attempts, earlier source/report freezes and
manuscripts remain unchanged. There is no pending calculation or readback.
The **16,008,383-byte** record is exclusively at:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-generalization-attribution-v1/attempt-01/`

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Frozen specification | 9,333 | `1578a6d593a8b2e93e54e8f71acef00408e723ed298ca49d5b8199eb793595b1` |
| Frozen checker | 28,240 | `bd0992e2e2a91fe9962f54dc6ca5e4a5f319ad0d0713721debbdb7c546ffa456` |
| PREPARATION.json | 75,756 | `c86fd14c0b2bd08efb616ddd80e2bad1eb81ff1e5fa14a384df75cda99f2f56a` |
| QUALIFICATION.json | 611 | `7f4d0e1a80207c811701d019c966a5eb72c061639cfa013efe57ce74c9db1b5b` |
| RESULTS.json | 8,118,311 | `b482a9590a1472ab576d78d5e3388a0883ec7cc3cc7d871a7a2fd4e9c1c3f1ba` |
| RUN_LOG.txt | 551 | `7ae5b7299f55e745233c165e86a3c5e440e35112ff39e752f9e6bf8e19a24044` |
| MANIFEST.json | 80,558 | `0d2ec5f0d05682a12e1cbacaebda267a37034b4aba45cd9269dfc5f24a1d0660` |

RESULTS and the five case files retain exact rational values as well as display
floats. The complete crossed costs, signed contributions, joint attribution
bins, bounded forecasts, selected examples and absences are included. No new
prior-wide oracle was evaluated. Source and research notes remain local;
no sister folder or manuscript was written.

## Consequence for the FEP track

VFE remains the exact evidence/inference machinery: within each candidate,
minimized F is negative log evidence, and the structural prior combines with
that evidence to determine model weights. The finite family contains the
physical joint law; the result is not proof that it cannot represent the
environment. It shows that its learned finite-data structure weights and
parameters can imply poor check/report choices in particular worlds, even
with valid inference. Paid decision value remains a separate endpoint.

Next recommended is one bounded **joint-model deployment ablation on the
same saved calibration histories across all 125 worlds**. Use the existing
learned Dirichlet joint component, not true Q. Compare it with the original
MAP and averaged responses under both original stopping schedules, charging
the same calibration and keeping every zero-headroom world. Freeze the design
before calculating the new ablation costs. Do not optimize a new schedule
or tune structural weights from these failures.

This asks whether evidence-based competition with independence earns its
place in the task at the current budget. The earlier
[factor-revision test](FEP_FACTOR_REVISION_V1_REPORT.md) already used a joint-
from-start control on five fixtures with fixed budgets; this would extend
that control to the saved adaptive histories and the broader fixed population.
It would be a post-result mechanism comparison, not fresh validation or proof
of a generally better agent. The joint component may incur costs elsewhere,
especially where independence is appropriate. No successor, new controller
promotion, feedback extension, manuscript integration or sister work was launched.
