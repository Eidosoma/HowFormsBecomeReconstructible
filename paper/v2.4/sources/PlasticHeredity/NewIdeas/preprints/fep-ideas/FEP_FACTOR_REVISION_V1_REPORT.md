# Factor revision: a useful edit, with a functional counterexample

**Completed 21 September 2026.** [Prospective contract](FEP_FACTOR_REVISION_V1.md),
[frozen checker](check_fep_factor_revision.py).

The primary functional test passes. With 64 paired calibration trials, an
agent allowed to remove a wrong sensor-independence assumption predicts the
shared-error environment better and reduces task cost after calibration.
It also beats the acquisition-free strategy of always asking a perfect
reference. The equal independent/shared comparison passes both cost gates.

This is a working **bounded model-revision component**: a supplied factor-join
primitive with learned probabilities. It is not discovery of a physical common
cause, unrestricted structure learning, or a unique FEP advantage. Under
partial dependence, the same edit improves predictions but worsens task cost
relative to keeping the independent model. That negative control is central.

## What the agent learned and what we supplied

The starting program treats sensor errors as independent. Its two error rates
are unknown and learnable. The single allowed edit replaces the product with
a four-cell joint error distribution, also learned from the calibration data.
Both representations induce exactly the same marginal predictive error rates
on every history. Differences therefore come from dependence and its effect
on decisions, not privileged knowledge of either sensor's accuracy.

Variational free energy supplies the model-evidence criterion:
`min_q F_m = -log p(data|m)`. Exact conjugate integration makes that equality
available without approximation gaps. With the frozen .9/.1 structural prior,
the agent accepts the join only when its Bayes factor exceeds 9. This is also
ordinary Bayesian MAP model selection. We separately compare retaining both
models through posterior averaging. The VFE inference interpretation follows
the [discrete-state synthesis](https://arxiv.org/html/2001.07203v2); the
particular conjugate edit is our declared finite construction.

At deployment the agent observes both warnings and either answers the hidden
binary question or asks a perfect reference. Wrong answers cost 1 and asking
costs .1. It chooses the smaller posterior expected loss. This decision rule
has no intrinsic information bonus and is not presented as a new EFE.
Calibration costs .001 per paired trial, shared by all four learned methods.
The fixed horizon is 100 fresh tasks; no deployment feedback updates the model.

Paired known-positive calibration, symmetric error transfer to both hidden
inputs, stationary errors, the reference and the new task are supplied. This
does not extend the old two-task continuation process or inherit its safety
guarantees. The proposal question was inspired by
[Pinductor's executable model refinement](https://arxiv.org/html/2605.13740v1);
we do not implement its LLM, partial-observation learning method or benchmarks.
Our known-input calibration is additional supervision.

## Primary cost results

Loss is per deployment task, including `.064/100 = .00064` calibration cost
for learned methods. Lower is better. Always asking costs .1 without
calibration; following A also costs .1 in the first four truth fixtures.

| Truth | Keep independent | Allow edit | Joint from start | Model average | Known-Q oracle, no calibration |
|---|---:|---:|---:|---:|---:|
| Independent errors | .047029785 | .047163623 | .048128082 | .047143583 | .046 |
| Shared errors | .110518198 | **.096494477** | .096397254 | .096794066 | .090 |
| Partial dependence | **.078810753** | .084959996 | .087013840 | .083651922 | .078 |
| Anticorrelated errors | .031240417 | .031213306 | .031056444 | .031214006 | .030 |
| Marginal error-rate shift | .099681217 | .099698847 | .099813005 | .099700895 | .098 |
| Equal independent/shared average | .078773992 | **.071829050** | .072262668 | .071968824 | .068 |

Under shared errors, the edit reduces net loss by .014023721 relative to the
parameter-learning independent model: about **12.69%**. Against always asking,
it saves .003505523, or **3.51%**. Its raw loss is .095854477; the break-even
calibration price against always asking is .006477379 per pair, compared with
the prospectively fixed .001. This boundary is a result, not a selected price.

The edit is accepted on 98.87049% of shared-error calibration histories and
changes the deployed response table on 91.81006%. On the independent truth,
the acceptance probability is .463405%. This is an exact probability for this
one truth/budget, not a universal or sequential false-alarm guarantee.

The always-rich model is slightly better under shared errors alone. The
revision gate is slightly better in the fixed equal independent/shared average
because it usually keeps the simpler model when independence is appropriate.
The average also slightly favors MAP editing over model averaging, but it is
an evaluator's two-truth average, not Bayes risk under the learner's full prior.
It therefore establishes no general dominance over Bayesian model averaging.
The stronger controls remain close; the main success is useful function.

## Predictions and task behavior are different endpoints

Future conditional warning log loss, in nats per fresh error pair:

| Truth, N=64 | Keep independent | Allow edit | Joint from start | Model average |
|---|---:|---:|---:|---:|
| Independent | .840281630 | .840628994 | .846816425 | .840591173 |
| Shared | .840281630 | **.664154781** | .662306635 | .664787691 |
| Partial | .840281630 | **.826954236** | .804356830 | .817961392 |
| Anticorrelated | .840281630 | .840270967 | .825011817 | .838410652 |
| Marginal shift | 1.126229373 | 1.126745258 | 1.134536009 | 1.126583258 |

On shared errors, editing reduces wrong reports from .098848843 to .035525647
but increases reference use from .110293555 to .603288303. The avoided errors
outweigh the reference and calibration costs. This is useful learning, not
only a fit improvement or a lower internal objective.

On partial dependence, editing also reduces wrong reports (.059771109 to
.049398038), but reference use rises from .183996437 to .349219580. The extra
reference cost exceeds the avoided error loss. Net cost increases by
.006149243, despite better predictive log loss. The always-rich and
model-averaged controls show the same direction relative to independence.
The true partial-dependence oracle has the same response table as the
independent oracle, so discovering dependence does not itself require a
different optimal action in this fixture.

The smaller budgets were registered diagnostics and were not used to choose
the primary budget:

| Shared truth | Edit acceptance | Independent net loss | Edit net loss | Joint from start | Model average |
|---|---:|---:|---:|---:|---:|
| N=0 | 0% | .100000000 | .100000000 | .100000000 | .100000000 |
| N=8 | 9.49222% | .107498654 | .107498654 | .104349291 | .104349291 |
| N=32 | 80.66050% | .109713731 | .102813275 | .101841685 | .103828427 |
| **N=64, primary** | **98.87049%** | .110518198 | **.096494477** | .096397254 | .096794066 |

At N=8 the edit improves prediction without changing any task response table.
At N=32 it helps relative to independence but still loses to always asking.
The N=64 result pays for its calibration under the fixed cost/horizon. These
are exact expectations at four declared budgets, not a fitted learning curve
or a searched minimum sample size. Every truth/budget/method result is in the
external results file, including the marginal-shift loss at N=8.

## Identifiability verdict

The independent, shared, partial and anticorrelated truths have the same
.1/.2 error marginals. Reading one sensor per fresh trial yields the same law
under all four, including adaptive channel selection. Synchronous paired
calibration supplies the missing dependence evidence. Its cost is explicit.

The shared-uniform error sampler and a directed conditional error sampler
produce identical paired observations. Thus the learned factor does not
identify which physical causal story generated the dependence. Known inputs
remove shared-world confounding, but no sensor intervention distinguishes
the remaining stories. The agent has learned a useful joint likelihood,
not demonstrated discovery of a hidden common cause.

## Verification and sealed evidence

The first execution completed without failure, correction, rerun or tuning.
One Python 3.10.12 process took **9.754196079 seconds wall** and
9.736767304 seconds CPU. It began at 2026-09-21T22:42:15.261252+00:00 and
finished at 22:42:25.029802+00:00. No long run or detached job was needed.

Qualification passed 2,723 checks in about .059 seconds before outcome
enumeration. These include exact evidence/predictive ratios, ordered-history
versus count probabilities, matched marginals, generated grammar, the
identifiability constructions, all 81 possible task response tables for each
oracle, and explicit model/world VFE identities. Continuous conjugate VFE
minimization is analytic; the numerical VFE checks concern finite posteriors.

The calculation covers **54,616 calibration histograms**, four learned
methods, five truth fixtures and N=0,8,32,64. It integrates all calibration
histories and future one-task outcomes; linearity gives the expected cost of
the fixed 100-task horizon without sampling complete task sequences. Integer
and rational arithmetic determine evidence comparisons, task choices, count
mass and aggregate task loss. Log losses use binary64. The maximum recorded
qualification/normalization residual is 1.1102230246251565e-15 against 1e-10.
This residual does not purport to bound every transcendental aggregate error.

All 1,171,796 assertions pass, mostly repeated normalization and oracle-bound
invariants. That number is a software-verification count, not a number of
independent experiments. All five primary scientific gates pass. A subsequent
read-only integrity check matched 2 inputs, 7 outputs and 14 preserved local
source/report/manuscript identities. The verifier and experiment share this
research workflow; this is not an independent replication.

The **14,804,924-byte** external record is:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-factor-revision-v1/attempt-01/`

| File | Bytes | SHA-256 |
|---|---:|---|
| Contract | 12,156 | `c28d6f62242dbff43a79ade0d04c3aaee63361b198f5ec5797d732b4bca28e78` |
| Checker | 18,354 | `208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880` |
| PREPARATION.json | 5,356 | `9e952838534915d0653b95ef3360906640ee89478808d11a1a3aa8265f03ebab` |
| QUALIFICATION.json | 430 | `b8bbd60bf6caffe991e89b961ade2359fb1f75bc1a4d6a7fe0a1ec2029f5a2f3` |
| HISTOGRAMS.jsonl.gz | 14,659,004 | `a9220e7f53f11de209ed6d8061b4f0f7cf01f0abb20bb7976310700046ed2db2` |
| RESULTS.json | 102,197 | `e0d73e9415dd0d00fe030325768a0a67b90334cb831244513ecf178552e04800` |
| RUN_LOG.txt | 636 | `31b7e95a69ff855b3155a08bae9204209ea64085d8ae3ff1465d19d320d6ae85` |
| MANIFEST.json | 6,791 | `1666bab83fe475199da13b7e7c254fd230a583c7558cc4af989d747e868421a4` |

The compressed histogram ledger contains the counts, evidence scores,
structural posterior weight, edit choice, predictive distributions, task
response tables and exact evaluator probability numerators. The frozen
checker reconstructs exact choices from the counts; displayed predictive
probabilities in that ledger are rounded binary64. Aggregate task losses
also retain their exact rational values. Earlier studies and manuscripts
were not edited. The live project notes now point here.

## Consequence for the FEP track

We now have a modest positive example: minimized VFE/model evidence can guide
a declared structural edit that supports better paid decisions. The important
restriction is the observation interface and the useful action enabled by the
edit. Better evidence or prediction alone remains insufficient for function.
The result is shared with Bayesian reasoning, and the edit language still
supplies the representational capacity.

Next recommended is a bounded design for **choosing whether paired calibration
is worth buying**, instead of receiving a fixed block. Keep the useful shared
case and the harmful partial-dependence control; price acquisition by later
task outcomes and state the model-evidence contribution separately. This is
a proposal, not a launched study. Do not tune this completed edit or continue
its budgets. No manuscript integration or sister-project work is queued.
